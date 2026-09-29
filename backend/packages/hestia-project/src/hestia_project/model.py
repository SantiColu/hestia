"""Project schematic model (ADR 0009): systems, cells and links."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from hestia_project.base import Schema
from hestia_project.catalog import StageType

SCHEMA_VERSION = 2
"""Version of the project schema. Bump on any incompatible change to these models.

- 1: links name the input they feed (one source per input, ADR 0009).
- 2: links carry the whole context of their source (ADR 0016); ``Link.input`` is gone.
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


class Provenance(Schema):
    """What produced a cell's current outputs. Empty until stages can run."""

    produced_at: datetime
    code_version: str
    input_cell_ids: list[str] = Field(default_factory=list[str])


class Cell(Schema):
    """An instance of a stage type inside a system."""

    id: str
    system_id: str
    stage: StageType
    name: str
    status: CellStatus = CellStatus.NEVER_RUN
    provenance: Provenance | None = None


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
