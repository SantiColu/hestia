"""Project schematic model (ADR 0009): systems, cells and links."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from hestia_core.forms import Problem
from hestia_project.base import Schema
from hestia_project.catalog import StageType

SCHEMA_VERSION = 5
"""Version of the project schema. Bump on any incompatible change to these models.

- 1: links name the input they feed (one source per input, ADR 0009).
- 2: links carry the whole context of their source (ADR 0016); ``Link.input`` is gone.
- 3: cells of form stages keep their artifact, problems and field provenance (ADR 0017).
- 4: computation stages (ADR 0021): parameters as a form, results stored apart and referenced
  by id (``Cell.result_id``), result provenance and the problems of the last update.
- 5: the orbit and the attitude modes are environment parameters, not mission fields
  (ADR 0023): mission artifact v2, environment parameters v2.
"""


class CellStatus(StrEnum):
    UP_TO_DATE = "up_to_date"
    OUTDATED = "outdated"
    FAILED = "failed"
    NEVER_RUN = "never_run"


class Position(Schema):
    """Canvas position of a system, in schematic units (px at zoom 1)."""

    x: float
    y: float


class ContextSource(Schema):
    """A stage type of the context used by an update and the state its provider was in."""

    stage: StageType
    cell_id: str
    change_id: str | None
    """Change that set the provider's artifact (form) or result (computation). Null for values
    that predate the history."""


class Provenance(Schema):
    """What produced the result of a computation cell (ADR 0021). Same inputs, same result."""

    produced_at: datetime
    change_id: str | None
    """The update (change of the history) that produced the result."""
    provider: str
    """Implementation that computed it (e.g. ``analytic``)."""
    provider_version: str
    code_version: str
    """Version of ``hestia_core``."""
    context: list[ContextSource] = Field(default_factory=list[ContextSource])
    """In catalog order."""
    parameters_change_id: str | None
    """Change that applied the parameters used. Null: the library defaults, never applied."""


class FieldSource(StrEnum):
    """Where the value of a form field comes from (ADR 0017)."""

    ENTERED = "entered"
    """Entered by hand, by a human or an agent."""
    IMPORTED = "imported"
    """Imported from a spreadsheet."""
    DEFAULT = "default"
    """Library default."""


class FieldProvenance(Schema):
    source: FieldSource
    change_id: str | None
    """Change of the history that set the value (author, date and justification). Null for
    values that predate the history (e.g. defaults of cells from older files)."""


class FormState(Schema):
    """Artifact of a form stage as applied, with its problems and per-field provenance."""

    artifact: dict[str, Any]
    """The stage's artifact model (e.g. ``MissionArtifact``) as JSON."""
    problems: list[Problem] = Field(default_factory=list[Problem])
    """Validation of the artifact when it was applied."""
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict[str, FieldProvenance])
    """By leaf field path (``orbit.altitude``, ``attitude_modes[0].name``). Empty fields have
    no provenance."""
    applied_change_id: str | None = None
    """Change of the last apply. Null until the first apply (or for applies older than
    schema version 4 that the history does not show)."""


class Cell(Schema):
    """An instance of a stage type inside a system."""

    id: str
    system_id: str
    stage: StageType
    name: str
    status: CellStatus = CellStatus.NEVER_RUN
    provenance: Provenance | None = None
    """Computation stages: what produced ``result_id``."""
    form: FormState | None = None
    """Implemented form stages (``mission``): the artifact. Implemented computation stages
    (``environment``): their parameters (ADR 0021)."""
    result_id: str | None = None
    """Computation stages: id of the last result, stored outside the history snapshots. Kept
    when the cell becomes outdated or the next update fails."""
    problems: list[Problem] = Field(default_factory=list[Problem])
    """Computation stages: why the last update failed (status ``failed``)."""


class System(Schema):
    """Named group of cells. ``cell_ids`` keeps display order."""

    id: str
    name: str
    position: Position
    cell_ids: list[str] = Field(default_factory=list[str])


class Link(Schema):
    """Passes the context of ``source_cell_id`` (the cell and everything upstream of it) on to
    ``target_cell_id`` (ADR 0016)."""

    id: str
    source_cell_id: str
    target_cell_id: str


class Project(Schema):
    schema_version: int = SCHEMA_VERSION
    id: str
    name: str
    systems: list[System] = Field(default_factory=list[System])
    cells: list[Cell] = Field(default_factory=list[Cell])
    links: list[Link] = Field(default_factory=list[Link])


class StageResult(Schema):
    """A result of a computation cell (ADR 0021). Immutable once produced.

    Stored apart in the ``.hestia`` and referenced by ``Cell.result_id``, so the history
    snapshots never copy it. A result lives while the project or its history reference it.
    """

    id: str
    cell_id: str
    """Cell that produced it (a duplicated cell may reference it too)."""
    stage: StageType
    parameters: dict[str, Any]
    """Parameters used, as JSON (the stage's parameters model)."""
    data: dict[str, Any]
    """The stage's result model (e.g. ``EnvironmentResult``) as JSON."""
