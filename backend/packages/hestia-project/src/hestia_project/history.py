"""Change log: every change records author, justification and full before/after snapshots."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from hestia_project.base import Schema
from hestia_project.model import Project


class ActorKind(StrEnum):
    HUMAN = "human"
    AGENT = "agent"


class Author(Schema):
    """Who made a change. Humans and agents are shown the same way in the UI."""

    kind: ActorKind
    name: str


class Operation(StrEnum):
    CREATE_SYSTEM = "create_system"
    ADD_CELL = "add_cell"
    LINK = "link"
    UNLINK = "unlink"
    BRANCH = "branch"
    RENAME_SYSTEM = "rename_system"
    RENAME_CELL = "rename_cell"
    MOVE_SYSTEM = "move_system"
    DUPLICATE_SYSTEM = "duplicate_system"
    DELETE_SYSTEM = "delete_system"
    DELETE_CELL = "delete_cell"
    PASTE = "paste"
    APPLY_ARTIFACT = "apply_artifact"
    UPDATE_CELL = "update_cell"
    UNDO = "undo"
    REDO = "redo"


JUSTIFICATION_REQUIRED: frozenset[Operation] = frozenset(
    {Operation.DELETE_SYSTEM, Operation.DELETE_CELL, Operation.UNLINK, Operation.APPLY_ARTIFACT}
)
"""Destructive operations and applying an artifact: an agent's empty justification is rejected
(ADR 0024). Elsewhere, and always for humans, it may be empty."""

OPERATION_LABELS: dict[Operation, str] = {
    Operation.CREATE_SYSTEM: "crear sistema",
    Operation.ADD_CELL: "agregar celda",
    Operation.LINK: "vincular",
    Operation.UNLINK: "desvincular",
    Operation.BRANCH: "ramificar",
    Operation.RENAME_SYSTEM: "renombrar sistema",
    Operation.RENAME_CELL: "renombrar celda",
    Operation.MOVE_SYSTEM: "mover sistema",
    Operation.DUPLICATE_SYSTEM: "duplicar sistema",
    Operation.DELETE_SYSTEM: "eliminar sistema",
    Operation.DELETE_CELL: "eliminar celda",
    Operation.PASTE: "pegar",
    Operation.APPLY_ARTIFACT: "aplicar cambios",
    Operation.UPDATE_CELL: "actualizar",
    Operation.UNDO: "deshacer",
    Operation.REDO: "rehacer",
}
"""Short name of each operation, as in «Deshacer renombrar sistema» (Edit menu)."""


class Change(Schema):
    """One entry of the project history."""

    id: str
    seq: int
    timestamp: datetime
    author: Author
    justification: str
    operation: Operation
    summary: str
    created_ids: list[str] = Field(default_factory=list[str])
    outdated_cell_ids: list[str] = Field(default_factory=list[str])
    reverts: str | None = None
    """For ``undo``/``redo``: id of the change undone or re-applied."""


@dataclass
class ChangeRecord:
    change: Change
    before: Project
    after: Project
