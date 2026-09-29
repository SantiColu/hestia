"""An open project: schematic, history, undo/redo and unsaved-changes tracking."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from hestia_project.base import Schema
from hestia_project.catalog import StageType
from hestia_project.errors import (
    JustificationRequiredError,
    NothingToRedoError,
    NothingToUndoError,
)
from hestia_project.forms import PENDING_CHANGE
from hestia_project.history import (
    JUSTIFICATION_REQUIRED,
    OPERATION_LABELS,
    Author,
    Change,
    ChangeRecord,
    Operation,
)
from hestia_project.model import Project
from hestia_project.schematic import Outcome, missing_requirements

DEFAULT_PROJECT_NAME = "Sin título"


class DocumentState(Schema):
    """File-level state of the open project."""

    path: str | None
    file_name: str | None
    dirty: bool
    """True when there are changes since the last save (or the project was never saved)."""
    revision: int
    can_undo: bool
    can_redo: bool
    undo_summary: str | None
    """Summary of the change that undo would revert."""
    redo_summary: str | None
    undo_label: str | None
    """Short name of the operation undo would revert (e.g. «renombrar sistema»)."""
    redo_label: str | None


class ProjectView(Schema):
    project: Project
    document: DocumentState
    missing: dict[str, list[StageType]]
    """Cells whose context lacks required stage types (cell id → missing types, ADR 0016).
    Cells with everything they need are not listed."""


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
            undo_label=OPERATION_LABELS[self._undo[-1].change.operation] if self._undo else None,
            redo_label=OPERATION_LABELS[self._redo[-1].change.operation] if self._redo else None,
        )

    def view(self) -> ProjectView:
        project = self.project.model_copy(deep=True)
        missing = {c.id: m for c in project.cells if (m := missing_requirements(project, c.id))}
        return ProjectView(project=project, document=self.state(), missing=missing)

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
        """Run ``fn`` on a copy of the project and commit it only if it succeeds.

        Exceptions of ``fn`` (including ``artifacts.NoChange``) leave the project untouched.
        """
        justification = justification.strip()
        if operation in JUSTIFICATION_REQUIRED and not justification:
            raise JustificationRequiredError("Esta operación exige una justificación.")
        working = self.project.model_copy(deep=True)
        outcome = fn(working)
        change_id = uuid.uuid4().hex
        _stamp(working, change_id)
        record = self._record(
            operation, author, justification, outcome, self.project, working, change_id=change_id
        )
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
        change_id: str | None = None,
    ) -> ChangeRecord:
        seq = (self.history[-1].change.seq + 1) if self.history else 1
        change = Change(
            id=change_id or uuid.uuid4().hex,
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


def _stamp(project: Project, change_id: str) -> None:
    """Point the field provenance set by an operation to the change that records it."""
    for cell in project.cells:
        if cell.form is None:
            continue
        for provenance in cell.form.provenance.values():
            if provenance.change_id == PENDING_CHANGE:
                provenance.change_id = change_id
