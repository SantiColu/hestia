"""An open project: schematic, history, undo/redo and unsaved-changes tracking."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from hestia_project.errors import (
    JustificationRequiredError,
    NothingToRedoError,
    NothingToUndoError,
)
from hestia_project.history import (
    JUSTIFICATION_REQUIRED,
    Author,
    Change,
    ChangeRecord,
    Operation,
)
from hestia_project.model import Project
from hestia_project.schematic import Outcome

DEFAULT_PROJECT_NAME = "Sin título"


class DocumentState(BaseModel):
    """File-level state of the open project."""

    path: str | None
    file_name: str | None
    dirty: bool
    """True when there are changes since the last save (or the project was never saved)."""
    revision: int
    can_undo: bool
    can_redo: bool
    undo_summary: str | None
    redo_summary: str | None


class ProjectView(BaseModel):
    project: Project
    document: DocumentState


class ProjectDocument:
    """Owns the project state. All writes go through ``apply``, ``undo`` or ``redo``.

    The undo/redo stacks live only while the project is open; the history is persisted.
    """

    def __init__(
        self,
        project: Project,
        path: Path | None = None,
        history: list[ChangeRecord] | None = None,
    ) -> None:
        self.project = project
        self.path = path
        self.history: list[ChangeRecord] = history or []
        self._undo: list[ChangeRecord] = []
        self._redo: list[ChangeRecord] = []
        self.revision = 0
        self.saved_revision = 0

    @classmethod
    def new(cls, name: str | None = None) -> "ProjectDocument":
        return cls(Project(id=uuid.uuid4().hex, name=name or DEFAULT_PROJECT_NAME))

    # ------------------------------------------------------------ state

    @property
    def dirty(self) -> bool:
        return self.revision != self.saved_revision

    def mark_saved(self, path: Path) -> None:
        self.path = path
        self.saved_revision = self.revision

    def state(self) -> DocumentState:
        return DocumentState(
            path=str(self.path) if self.path else None,
            file_name=self.path.name if self.path else None,
            dirty=self.dirty,
            revision=self.revision,
            can_undo=bool(self._undo),
            can_redo=bool(self._redo),
            undo_summary=self._undo[-1].change.summary if self._undo else None,
            redo_summary=self._redo[-1].change.summary if self._redo else None,
        )

    def view(self) -> ProjectView:
        return ProjectView(project=self.project.model_copy(deep=True), document=self.state())

    def changes(self) -> list[Change]:
        return [record.change for record in self.history]

    # ------------------------------------------------------------ writes

    def apply(
        self,
        operation: Operation,
        author: Author,
        justification: str,
        fn: Callable[[Project], Outcome],
    ) -> Change:
        """Run ``fn`` on a copy of the project and commit it only if it succeeds."""
        justification = justification.strip()
        if operation in JUSTIFICATION_REQUIRED and not justification:
            raise JustificationRequiredError("Esta operación exige una justificación.")
        working = self.project.model_copy(deep=True)
        outcome = fn(working)
        record = self._record(operation, author, justification, outcome, self.project, working)
        self.project = working
        self._undo.append(record)
        self._redo.clear()
        return record.change

    def undo(self, author: Author, justification: str = "") -> Change:
        if not self._undo:
            raise NothingToUndoError("No hay cambios para deshacer.")
        target = self._undo.pop()
        outcome = Outcome(summary=f"Deshizo: {target.change.summary}")
        record = self._record(
            Operation.UNDO,
            author,
            justification.strip(),
            outcome,
            self.project,
            target.before,
            reverts=target.change.id,
        )
        self.project = target.before.model_copy(deep=True)
        self._redo.append(target)
        return record.change

    def redo(self, author: Author, justification: str = "") -> Change:
        if not self._redo:
            raise NothingToRedoError("No hay cambios para rehacer.")
        target = self._redo.pop()
        outcome = Outcome(summary=f"Rehizo: {target.change.summary}")
        record = self._record(
            Operation.REDO,
            author,
            justification.strip(),
            outcome,
            self.project,
            target.after,
            reverts=target.change.id,
        )
        self.project = target.after.model_copy(deep=True)
        self._undo.append(target)
        return record.change

    def _record(
        self,
        operation: Operation,
        author: Author,
        justification: str,
        outcome: Outcome,
        before: Project,
        after: Project,
        reverts: str | None = None,
    ) -> ChangeRecord:
        seq = (self.history[-1].change.seq + 1) if self.history else 1
        change = Change(
            id=uuid.uuid4().hex,
            seq=seq,
            timestamp=datetime.now(UTC),
            author=author,
            justification=justification,
            operation=operation,
            summary=outcome.summary,
            created_ids=outcome.created_ids,
            outdated_cell_ids=outcome.outdated_cell_ids,
            reverts=reverts,
        )
        record = ChangeRecord(
            change=change,
            before=before.model_copy(deep=True),
            after=after.model_copy(deep=True),
        )
        self.history.append(record)
        self.revision += 1
        return record
