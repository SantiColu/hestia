"""Schematic operations (ADR 0009).

Every operation mutates the given ``Project`` in place and returns an ``Outcome``. Callers
(``ProjectDocument``) run operations on a copy and commit only on success, so a failed
operation never leaves a half-applied change.

Rules enforced here:

- A link is valid only if the source stage type feeds an input of the target stage type
  (``catalog.STAGES``), the target input has no other source and the link graph stays acyclic.
- Changing the inputs of a cell (link, unlink, deleting its source) marks it and everything
  downstream as ``outdated``, across systems. Cells that never ran stay ``never_run``.
"""

import uuid
from collections.abc import Iterable

from pydantic import Field, model_validator

from hestia_project.base import Schema
from hestia_project.catalog import STAGES, TEMPLATES, StageType, TemplateId, accepts
from hestia_project.errors import InvalidOperationError, NotFoundError
from hestia_project.model import Cell, CellStatus, Link, Position, Project, System

MAX_NAME_LENGTH = 80

# Layout estimates used only to place new systems where they do not overlap existing ones.
SYSTEM_WIDTH = 240.0
SYSTEM_GAP = 80.0
_HEADER_HEIGHT = 44.0
_ROW_HEIGHT = 32.0


class Blueprint(Schema):
    """What to create: a template (whole phase) or a single stage. Exactly one is set."""

    template: TemplateId | None = None
    stage: StageType | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "Blueprint":
        if (self.template is None) == (self.stage is None):
            raise ValueError("set exactly one of 'template' or 'stage'")
        return self

    def stages(self) -> tuple[StageType, ...]:
        if self.template is not None:
            return TEMPLATES[self.template].stages
        assert self.stage is not None
        return (self.stage,)

    def default_name(self) -> str:
        if self.template is not None:
            return TEMPLATES[self.template].default_name
        assert self.stage is not None
        return STAGES[self.stage].default_name


class Outcome(Schema):
    """Result of an operation: what it did, what it created and what became outdated."""

    summary: str
    created_ids: list[str] = Field(default_factory=list[str])
    outdated_cell_ids: list[str] = Field(default_factory=list[str])


# ---------------------------------------------------------------- lookups


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def get_system(project: Project, system_id: str) -> System:
    for system in project.systems:
        if system.id == system_id:
            return system
    raise NotFoundError(f"No existe el sistema {system_id!r}.", system_id=system_id)


def get_cell(project: Project, cell_id: str) -> Cell:
    for cell in project.cells:
        if cell.id == cell_id:
            return cell
    raise NotFoundError(f"No existe la celda {cell_id!r}.", cell_id=cell_id)


def get_link(project: Project, link_id: str) -> Link:
    for link in project.links:
        if link.id == link_id:
            return link
    raise NotFoundError(f"No existe el vínculo {link_id!r}.", link_id=link_id)


def downstream(project: Project, cell_ids: Iterable[str]) -> set[str]:
    """Cells reachable from ``cell_ids`` through links, excluding the starting cells."""
    start = set(cell_ids)
    seen: set[str] = set()
    frontier = list(start)
    while frontier:
        current = frontier.pop()
        for link in project.links:
            if link.source_cell_id == current and link.target_cell_id not in seen:
                seen.add(link.target_cell_id)
                frontier.append(link.target_cell_id)
    return seen - start


def invalidate(project: Project, cell_ids: Iterable[str]) -> list[str]:
    """Mark ``cell_ids`` and everything downstream as outdated.

    Only cells with results to invalidate change: ``never_run`` and ``outdated`` stay as they
    are. Returns the ids that changed, in project order.
    """
    targets = set(cell_ids)
    affected = targets | downstream(project, targets)
    changed: list[str] = []
    for cell in project.cells:
        if cell.id in affected and cell.status in (CellStatus.UP_TO_DATE, CellStatus.FAILED):
            cell.status = CellStatus.OUTDATED
            changed.append(cell.id)
    return changed


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise InvalidOperationError("El nombre no puede estar vacío.")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise InvalidOperationError(
            f"El nombre no puede superar {MAX_NAME_LENGTH} caracteres.", name=cleaned
        )
    return cleaned


def _unique_system_name(project: Project, name: str) -> str:
    taken = {s.name for s in project.systems}
    if name not in taken:
        return name
    n = 2
    while f"{name} ({n})" in taken:
        n += 1
    return f"{name} ({n})"


# ---------------------------------------------------------------- link validation


def _input_source(project: Project, target_cell_id: str, input_stage: StageType) -> Link | None:
    for link in project.links:
        if link.target_cell_id == target_cell_id and link.input is input_stage:
            return link
    return None


def check_link(project: Project, source_cell_id: str, target_cell_id: str) -> None:
    """Raise ``InvalidOperationError`` if the link is not valid (see module docstring)."""
    source = get_cell(project, source_cell_id)
    target = get_cell(project, target_cell_id)
    if source.id == target.id:
        raise InvalidOperationError("Una celda no puede vincularse consigo misma.")
    if not accepts(target.stage, source.stage):
        raise InvalidOperationError(
            f"«{source.name}» no puede alimentar a «{target.name}»: "
            "ese vínculo no está entre los válidos del workflow.",
            source_stage=source.stage,
            target_stage=target.stage,
        )
    existing = _input_source(project, target.id, source.stage)
    if existing is not None:
        raise InvalidOperationError(
            f"La entrada de «{target.name}» ya tiene fuente; desvinculala primero.",
            link_id=existing.id,
        )
    if source.id in downstream(project, [target.id]):
        raise InvalidOperationError("El vínculo crearía un ciclo.")


def _add_link(project: Project, source_cell_id: str, target_cell_id: str) -> Link:
    check_link(project, source_cell_id, target_cell_id)
    source = get_cell(project, source_cell_id)
    link = Link(
        id=new_id("link"),
        source_cell_id=source_cell_id,
        target_cell_id=target_cell_id,
        input=source.stage,
    )
    project.links.append(link)
    return link


def link_targets(project: Project, source_cell_id: str) -> list[str]:
    """Cells that the given cell could feed right now."""
    get_cell(project, source_cell_id)
    valid: list[str] = []
    for cell in project.cells:
        try:
            check_link(project, source_cell_id, cell.id)
        except InvalidOperationError:
            continue
        valid.append(cell.id)
    return valid


# ---------------------------------------------------------------- layout


def _estimated_height(n_cells: int) -> float:
    return _HEADER_HEIGHT + _ROW_HEIGHT * max(n_cells, 1)


def _free_position(
    project: Project, x: float, y: float, n_cells: int, exclude: str | None = None
) -> Position:
    """First position at column ``x``, from ``y`` down, that overlaps no other system."""
    height = _estimated_height(n_cells)
    moved = True
    while moved:
        moved = False
        for other in project.systems:
            if other.id == exclude:
                continue
            other_h = _estimated_height(len(other.cell_ids))
            overlaps = (
                other.position.x < x + SYSTEM_WIDTH
                and x < other.position.x + SYSTEM_WIDTH
                and other.position.y < y + height
                and y < other.position.y + other_h
            )
            if overlaps:
                y = other.position.y + other_h + SYSTEM_GAP / 2
                moved = True
    return Position(x=x, y=y)


def _default_position(project: Project, n_cells: int) -> Position:
    if not project.systems:
        return Position(x=0, y=0)
    x = max(s.position.x for s in project.systems) + SYSTEM_WIDTH + SYSTEM_GAP
    return _free_position(project, x, 0, n_cells)


def _position_right_of(project: Project, system: System, n_cells: int) -> Position:
    x = system.position.x + SYSTEM_WIDTH + SYSTEM_GAP
    return _free_position(project, x, system.position.y, n_cells)


# ---------------------------------------------------------------- creation helpers


def _new_cell(project: Project, system: System, stage: StageType, name: str | None) -> Cell:
    cell = Cell(
        id=new_id("cell"),
        system_id=system.id,
        stage=stage,
        name=_clean_name(name) if name else STAGES[stage].default_name,
    )
    project.cells.append(cell)
    system.cell_ids.append(cell.id)
    return cell


def _autolink(project: Project, system: System, new_cell_ids: set[str]) -> list[Link]:
    """Link cells of ``system`` where exactly one cell in the system can feed a free input.

    Only pairs that involve a new cell are considered, so links removed on purpose between
    existing cells are not recreated.
    """
    created: list[Link] = []
    cells = [get_cell(project, cid) for cid in system.cell_ids]
    for target in cells:
        for input_stage in STAGES[target.stage].inputs:
            if _input_source(project, target.id, input_stage) is not None:
                continue
            candidates = [c for c in cells if c.stage is input_stage and c.id != target.id]
            if len(candidates) != 1:
                continue
            source = candidates[0]
            if source.id not in new_cell_ids and target.id not in new_cell_ids:
                continue
            try:
                created.append(_add_link(project, source.id, target.id))
            except InvalidOperationError:
                continue
    return created


def _create_system(
    project: Project, blueprint: Blueprint, name: str | None, position: Position | None
) -> System:
    stages = blueprint.stages()
    system = System(
        id=new_id("sys"),
        name=_unique_system_name(project, _clean_name(name) if name else blueprint.default_name()),
        position=position or _default_position(project, len(stages)),
    )
    project.systems.append(system)
    new_ids = {_new_cell(project, system, stage, None).id for stage in stages}
    _autolink(project, system, new_ids)
    return system


def _free_inputs(project: Project, system: System) -> list[tuple[Cell, StageType]]:
    free: list[tuple[Cell, StageType]] = []
    for cid in system.cell_ids:
        cell = get_cell(project, cid)
        for input_stage in STAGES[cell.stage].inputs:
            if _input_source(project, cell.id, input_stage) is None:
                free.append((cell, input_stage))
    return free


def blueprint_open_inputs(blueprint: Blueprint) -> set[StageType]:
    """Stage types that could feed a system created from ``blueprint`` when branching."""
    scratch = Project(id="scratch", name="scratch")
    system = _create_system(scratch, blueprint, None, Position(x=0, y=0))
    return {input_stage for _, input_stage in _free_inputs(scratch, system)}


def branch_targets(project: Project, blueprint: Blueprint) -> list[str]:
    """Cells onto which ``blueprint`` can be dropped to branch (see ``branch``)."""
    open_inputs = blueprint_open_inputs(blueprint)
    return [cell.id for cell in project.cells if cell.stage in open_inputs]


def branch_options(project: Project, cell_id: str) -> list[Blueprint]:
    """Templates and stages that can be branched from ``cell_id`` (see ``branch``)."""
    cell = get_cell(project, cell_id)
    candidates = [Blueprint(template=t) for t in TEMPLATES] + [Blueprint(stage=s) for s in STAGES]
    return [b for b in candidates if cell.stage in blueprint_open_inputs(b)]


# ---------------------------------------------------------------- operations


def create_system(
    project: Project,
    blueprint: Blueprint,
    name: str | None = None,
    position: Position | None = None,
) -> Outcome:
    """Create a system from a template (cells already linked) or with a single cell."""
    system = _create_system(project, blueprint, name, position)
    return Outcome(
        summary=f"Creó el sistema «{system.name}».",
        created_ids=[system.id, *system.cell_ids],
    )


def add_cell(
    project: Project, system_id: str, stage: StageType, name: str | None = None
) -> Outcome:
    """Add a cell to a system, linking it to cells of the same system when unambiguous."""
    system = get_system(project, system_id)
    cell = _new_cell(project, system, stage, name)
    links = _autolink(project, system, {cell.id})
    outdated = invalidate(
        project, [link.target_cell_id for link in links if link.target_cell_id != cell.id]
    )
    return Outcome(
        summary=f"Agregó la celda «{cell.name}» al sistema «{system.name}».",
        created_ids=[cell.id, *(link.id for link in links)],
        outdated_cell_ids=outdated,
    )


def link(project: Project, source_cell_id: str, target_cell_id: str) -> Outcome:
    new = _add_link(project, source_cell_id, target_cell_id)
    source = get_cell(project, source_cell_id)
    target = get_cell(project, target_cell_id)
    return Outcome(
        summary=f"Vinculó «{source.name}» → «{target.name}».",
        created_ids=[new.id],
        outdated_cell_ids=invalidate(project, [target.id]),
    )


def unlink(project: Project, link_id: str) -> Outcome:
    old = get_link(project, link_id)
    project.links.remove(old)
    source = get_cell(project, old.source_cell_id)
    target = get_cell(project, old.target_cell_id)
    return Outcome(
        summary=f"Desvinculó «{source.name}» → «{target.name}».",
        outdated_cell_ids=invalidate(project, [target.id]),
    )


def branch(
    project: Project,
    cell_id: str,
    blueprint: Blueprint,
    name: str | None = None,
    position: Position | None = None,
) -> Outcome:
    """Create a new system from ``blueprint`` fed by ``cell_id``.

    The new cells whose free inputs accept the source stage type get linked from the source.
    Fails if none does (e.g. dropping «Fase 0» onto a mission cell).
    """
    source = get_cell(project, cell_id)
    if source.stage not in blueprint_open_inputs(blueprint):
        raise InvalidOperationError(
            f"No se puede ramificar «{blueprint.default_name()}» desde «{source.name}»: "
            "ninguna de sus entradas acepta esa celda.",
            cell_id=cell_id,
        )
    source_system = get_system(project, source.system_id)
    n_cells = len(blueprint.stages())
    system = _create_system(
        project,
        blueprint,
        name,
        position or _position_right_of(project, source_system, n_cells),
    )
    links = [
        _add_link(project, source.id, cell.id)
        for cell, input_stage in _free_inputs(project, system)
        if input_stage is source.stage
    ]
    return Outcome(
        summary=f"Ramificó «{system.name}» desde «{source.name}».",
        created_ids=[system.id, *system.cell_ids, *(lk.id for lk in links)],
    )


def rename_system(project: Project, system_id: str, name: str) -> Outcome:
    system = get_system(project, system_id)
    old, system.name = system.name, _clean_name(name)
    return Outcome(summary=f"Renombró el sistema «{old}» a «{system.name}».")


def rename_cell(project: Project, cell_id: str, name: str) -> Outcome:
    cell = get_cell(project, cell_id)
    old, cell.name = cell.name, _clean_name(name)
    return Outcome(summary=f"Renombró la celda «{old}» a «{cell.name}».")


def move_system(project: Project, system_id: str, position: Position) -> Outcome:
    system = get_system(project, system_id)
    system.position = position
    return Outcome(summary=f"Movió el sistema «{system.name}».")


def duplicate_system(project: Project, system_id: str, position: Position | None = None) -> Outcome:
    """Copy a system with its cells, internal links and incoming links from other systems.

    Outgoing links to other systems are not copied: each input has a single source.
    """
    original = get_system(project, system_id)
    copy = System(
        id=new_id("sys"),
        name=_unique_system_name(project, f"{original.name} (copia)"),
        position=position
        or _free_position(
            project, original.position.x, original.position.y, len(original.cell_ids)
        ),
    )
    project.systems.append(copy)
    mapping: dict[str, str] = {}
    for cid in original.cell_ids:
        cell = get_cell(project, cid)
        clone = cell.model_copy(deep=True, update={"id": new_id("cell"), "system_id": copy.id})
        mapping[cid] = clone.id
        project.cells.append(clone)
        copy.cell_ids.append(clone.id)
    created: list[str] = [copy.id, *copy.cell_ids]
    for lk in list(project.links):
        if lk.target_cell_id not in mapping:
            continue
        clone_link = Link(
            id=new_id("link"),
            source_cell_id=mapping.get(lk.source_cell_id, lk.source_cell_id),
            target_cell_id=mapping[lk.target_cell_id],
            input=lk.input,
        )
        project.links.append(clone_link)
        created.append(clone_link.id)
    return Outcome(
        summary=f"Duplicó el sistema «{original.name}» como «{copy.name}».", created_ids=created
    )


def _remove_cells(project: Project, cell_ids: set[str]) -> list[str]:
    """Remove cells and their links; invalidate what they fed. Returns outdated ids."""
    fed = {
        lk.target_cell_id
        for lk in project.links
        if lk.source_cell_id in cell_ids and lk.target_cell_id not in cell_ids
    }
    project.links = [
        lk
        for lk in project.links
        if lk.source_cell_id not in cell_ids and lk.target_cell_id not in cell_ids
    ]
    project.cells = [c for c in project.cells if c.id not in cell_ids]
    for system in project.systems:
        system.cell_ids = [cid for cid in system.cell_ids if cid not in cell_ids]
    return invalidate(project, fed)


def delete_system(project: Project, system_id: str) -> Outcome:
    system = get_system(project, system_id)
    outdated = _remove_cells(project, set(system.cell_ids))
    project.systems.remove(system)
    return Outcome(summary=f"Eliminó el sistema «{system.name}».", outdated_cell_ids=outdated)


def delete_cell(project: Project, cell_id: str) -> Outcome:
    """Delete a cell and its links. A system left without cells is deleted too."""
    cell = get_cell(project, cell_id)
    system = get_system(project, cell.system_id)
    outdated = _remove_cells(project, {cell.id})
    summary = f"Eliminó la celda «{cell.name}»."
    if not system.cell_ids:
        project.systems.remove(system)
        summary = f"Eliminó la celda «{cell.name}» y el sistema vacío «{system.name}»."
    return Outcome(summary=summary, outdated_cell_ids=outdated)
