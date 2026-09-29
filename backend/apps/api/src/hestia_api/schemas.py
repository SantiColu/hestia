"""Request bodies. Responses reuse the pydantic models of ``hestia_project``."""

from pydantic import BaseModel, Field

from hestia_project.artifacts import Artifact, CellArtifact
from hestia_project.base import Schema
from hestia_project.catalog import StageType
from hestia_project.clipboard import Fragment
from hestia_project.computations import CellResult
from hestia_project.document import ProjectView
from hestia_project.history import Change
from hestia_project.model import Position
from hestia_project.schematic import Blueprint

JUSTIFICATION_DOC = (
    "Why the change is made. Stored in the history with the author. "
    "Required (non-empty) for deletions and unlinking."
)


class WriteRequest(BaseModel):
    justification: str = Field(description=JUSTIFICATION_DOC)


class Session(Schema):
    """What this API instance has open. ``project`` is null when nothing is open."""

    project: ProjectView | None


class NewProjectRequest(BaseModel):
    name: str | None = None
    discard_unsaved: bool = Field(
        default=False, description="Replace an open project even if it has unsaved changes."
    )


class OpenProjectRequest(BaseModel):
    path: str = Field(description="Absolute path of the .hestia file.")
    force: bool = Field(
        default=False, description="Take over the file even if another instance holds its lock."
    )
    discard_unsaved: bool = False


class SaveAsRequest(BaseModel):
    path: str = Field(description="Target path. The .hestia extension is added if missing.")


class CloseProjectRequest(BaseModel):
    discard_unsaved: bool = False


class RemoveRecentRequest(BaseModel):
    path: str


class CreateSystemRequest(Blueprint, WriteRequest):
    """Create a system from a template (``template``) or with a single cell (``stage``)."""

    name: str | None = None
    position: Position | None = Field(
        default=None, description="Canvas position. Placed automatically when omitted."
    )


class BranchRequest(CreateSystemRequest):
    """Create a system from a template or stage, fed by the cell in the path."""


class RenameRequest(WriteRequest):
    name: str


class MoveSystemRequest(WriteRequest):
    position: Position


class DuplicateSystemRequest(WriteRequest):
    position: Position | None = None


class AddCellRequest(WriteRequest):
    stage: StageType
    name: str | None = None


class LinkRequest(WriteRequest):
    source_cell_id: str
    target_cell_id: str


class CellIds(Schema):
    cell_ids: list[str]


class CopyRequest(BaseModel):
    """What to copy: whole systems and/or loose cells."""

    system_ids: list[str] = Field(default_factory=list[str])
    cell_ids: list[str] = Field(default_factory=list[str])


class PasteRequest(WriteRequest):
    fragment: Fragment = Field(description="A fragment returned by copy (any project).")
    position: Position | None = Field(
        default=None,
        description="Canvas position of the fragment's top-left system. "
        "When omitted, systems are shifted from the originals.",
    )
    target_system_id: str | None = Field(
        default=None,
        description="System that receives loose cells. When omitted they get a new system.",
    )


class ArtifactDraft(BaseModel):
    """A draft of a form artifact (or of a computation's parameters), possibly incomplete. Its
    stage must match the cell's."""

    artifact: Artifact


class ApplyArtifactRequest(WriteRequest):
    """Replace the cell's artifact with the draft. The justification is required."""

    artifact: Artifact


class ApplyArtifactResult(Schema):
    change: Change | None
    """Null when the content did not change (nothing is recorded)."""
    view: ProjectView
    cell: CellArtifact


class UpdateCellRequest(BaseModel):
    justification: str = Field(
        default="", description="Why the cell is updated. Optional; stored with the author."
    )


class UpdateCellResult(Schema):
    change: Change | None
    """Null when nothing changed (already up to date, or the same failure)."""
    view: ProjectView
    result: CellResult
