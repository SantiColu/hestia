"""The workspace of one Hestia instance: at most one open project, its file and its lock.

This is the façade the API talks to. Every public method is serialized with a lock (the API
serves requests from several threads) and notifies listeners so clients can react in real time.
"""

import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, Field

from hestia_project.document import ProjectDocument, ProjectView
from hestia_project.errors import (
    NoPathError,
    NoProjectOpenError,
    UnsavedChangesError,
)
from hestia_project.history import Author, Change, Operation
from hestia_project.lock import ProjectLock, acquire_lock
from hestia_project.model import Project
from hestia_project.recents import RecentProject, RecentProjects
from hestia_project.schematic import Outcome
from hestia_project.storage import FILE_EXTENSION, read_project, write_project

T = TypeVar("T")


class EventType(StrEnum):
    PROJECT_CREATED = "project_created"
    PROJECT_OPENED = "project_opened"
    PROJECT_SAVED = "project_saved"
    PROJECT_CLOSED = "project_closed"
    PROJECT_CHANGED = "project_changed"


class ProjectEvent(BaseModel):
    """Notification for real-time clients. ``change`` is set for ``project_changed``."""

    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str
    revision: int | None = None
    path: str | None = None
    change: Change | None = None


class MutationResult(BaseModel):
    change: Change
    view: ProjectView


Listener = Callable[[ProjectEvent], None]


def with_extension(path: Path) -> Path:
    return path if path.suffix == FILE_EXTENSION else path.with_name(path.name + FILE_EXTENSION)


class Workspace:
    def __init__(self, home: Path) -> None:
        self.instance_id = uuid.uuid4().hex
        self.recents = RecentProjects(home / "recents.json")
        self._doc: ProjectDocument | None = None
        self._lock: ProjectLock | None = None
        self._mutex = threading.RLock()
        self._listeners: list[Listener] = []

    # ------------------------------------------------------------ events

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def _emit(self, event: ProjectEvent) -> None:
        for listener in list(self._listeners):
            listener(event)

    # ------------------------------------------------------------ access

    def _require(self) -> ProjectDocument:
        if self._doc is None:
            raise NoProjectOpenError("No hay ningún proyecto abierto.")
        return self._doc

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    def view(self) -> ProjectView:
        with self._mutex:
            return self._require().view()

    def history(self) -> list[Change]:
        with self._mutex:
            return self._require().changes()

    def query(self, fn: Callable[[Project], T]) -> T:
        """Run a read-only function against the open project."""
        with self._mutex:
            return fn(self._require().project)

    def recent_projects(self) -> list[RecentProject]:
        return self.recents.list()

    # ------------------------------------------------------------ file lifecycle

    def _check_can_replace(self, discard_unsaved: bool) -> None:
        if self._doc is not None and self._doc.dirty and not discard_unsaved:
            raise UnsavedChangesError(
                "El proyecto abierto tiene cambios sin guardar.",
                path=str(self._doc.path) if self._doc.path else None,
            )

    def _release(self) -> None:
        if self._lock is not None:
            self._lock.release()
        self._lock = None
        self._doc = None

    def new_project(self, name: str | None = None, discard_unsaved: bool = False) -> ProjectView:
        with self._mutex:
            self._check_can_replace(discard_unsaved)
            self._release()
            self._doc = ProjectDocument.new(name)
            view = self._doc.view()
            self._emit(
                ProjectEvent(
                    type=EventType.PROJECT_CREATED,
                    message=f"Nuevo proyecto «{view.project.name}».",
                    revision=0,
                )
            )
            return view

    def open_project(
        self, path: Path, force: bool = False, discard_unsaved: bool = False
    ) -> ProjectView:
        path = path.expanduser().resolve()
        with self._mutex:
            if self._doc is not None and self._doc.path == path:
                return self._doc.view()
            self._check_can_replace(discard_unsaved)
            project, history = read_project(path)
            lock = acquire_lock(path, self.instance_id, force=force)
            self._release()
            self._lock = lock
            self._doc = ProjectDocument(project, path=path, history=history)
            self.recents.touch(path, project.name)
            self._emit(
                ProjectEvent(
                    type=EventType.PROJECT_OPENED,
                    message=f"Abrió {path.name}.",
                    revision=0,
                    path=str(path),
                )
            )
            return self._doc.view()

    def save(self) -> ProjectView:
        with self._mutex:
            doc = self._require()
            if doc.path is None:
                raise NoPathError("El proyecto nunca se guardó: usá «Guardar como».")
            return self._write(doc, doc.path)

    def save_as(self, path: Path) -> ProjectView:
        path = with_extension(path.expanduser()).resolve()
        with self._mutex:
            doc = self._require()
            if path != doc.path:
                new_lock = acquire_lock(path, self.instance_id)
                try:
                    doc.project.name = path.stem
                    self._write(doc, path)
                except BaseException:
                    new_lock.release()
                    raise
                if self._lock is not None:
                    self._lock.release()
                self._lock = new_lock
                return doc.view()
            return self._write(doc, path)

    def _write(self, doc: ProjectDocument, path: Path) -> ProjectView:
        write_project(path, doc.project, doc.history)
        doc.mark_saved(path)
        self.recents.touch(path, doc.project.name)
        self._emit(
            ProjectEvent(
                type=EventType.PROJECT_SAVED,
                message=f"Guardó {path.name}.",
                revision=doc.revision,
                path=str(path),
            )
        )
        return doc.view()

    def close(self, discard_unsaved: bool = False) -> None:
        with self._mutex:
            doc = self._require()
            self._check_can_replace(discard_unsaved)
            name = doc.path.name if doc.path else doc.project.name
            self._release()
            self._emit(ProjectEvent(type=EventType.PROJECT_CLOSED, message=f"Cerró {name}."))

    def shutdown(self) -> None:
        """Release the file lock without checks (process exit)."""
        with self._mutex:
            self._release()

    # ------------------------------------------------------------ writes

    def apply(
        self,
        operation: Operation,
        author: Author,
        justification: str,
        fn: Callable[[Project], Outcome],
    ) -> MutationResult:
        with self._mutex:
            doc = self._require()
            return self._changed(doc, doc.apply(operation, author, justification, fn))

    def undo(self, author: Author, justification: str = "") -> MutationResult:
        with self._mutex:
            doc = self._require()
            return self._changed(doc, doc.undo(author, justification))

    def redo(self, author: Author, justification: str = "") -> MutationResult:
        with self._mutex:
            doc = self._require()
            return self._changed(doc, doc.redo(author, justification))

    def _changed(self, doc: ProjectDocument, change: Change) -> MutationResult:
        self._emit(
            ProjectEvent(
                type=EventType.PROJECT_CHANGED,
                message=change.summary,
                revision=doc.revision,
                path=str(doc.path) if doc.path else None,
                change=change,
            )
        )
        return MutationResult(change=change, view=doc.view())
