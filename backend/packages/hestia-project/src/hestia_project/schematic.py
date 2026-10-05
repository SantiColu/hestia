"""Schematic operations (ADR 0009, 0016).

Every operation mutates the given ``Project`` in place and returns an ``Outcome``. Callers
(``ProjectDocument``) run operations on a copy and commit only on success, so a failed
operation never leaves a half-applied change.

Rules enforced here (``docs/workflow-fases-0-1.md``):

- The context of a cell is every cell upstream of it, by stage type. A link passes the whole
  context of its source. ``check_link`` holds the five link rules.
- Linking, unlinking or losing a source marks the target and everything downstream as
  ``outdated``, across systems. Cells that never ran stay ``never_run`` and form stages are not
  outdated by upstream changes (ADR 0017). Computation stages never rerun on their own: an
  upstream change only outdates them (ADR 0021).
"""

import uuid
from collections.abc import Iterable, Mapping

from pydantic import Field, model_validator

from hestia_project.base import Schema
from hestia_project.catalog import (
    ORDER,
    STAGES,
    TEMPLATES,
    StageKind,
    StageType,
    TemplateId,
    before,
)
from hestia_project.errors import InvalidOperationError, NotFoundError
from hestia_project.forms import new_form_state
from hestia_project.model import Cell, CellStatus, Link, Position, Project, StageResult, System

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
    results: list[StageResult] = Field(default_factory=list[StageResult], exclude=True)
    """Results produced by the operation (updates), kept by ``ProjectDocument`` outside the
    history snapshots (ADR 0021)."""


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


def would_invalidate(project: Project, cell_ids: Iterable[str]) -> list[str]:
    """Cells that ``invalidate`` would mark as outdated, in project order. Changes nothing.

    Only cells with results to invalidate count: ``never_run`` and ``outdated`` stay as they
    are, and form stages keep their status (their artifact is entered, not computed from the
    context).
    """
    targets = set(cell_ids)
    affected = targets | downstream(project, targets)
    return [
        cell.id
        for cell in project.cells
        if cell.id in affected
        and STAGES[cell.stage].kind is not StageKind.FORM
        and cell.status in (CellStatus.UP_TO_DATE, CellStatus.FAILED)
    ]


def invalidate(project: Project, cell_ids: Iterable[str]) -> list[str]:
    """Mark ``cell_ids`` and everything downstream as outdated (see ``would_invalidate``).

    Returns the ids that changed, in project order.
    """
    changed = would_invalidate(project, cell_ids)
    by_id = {cell.id: cell for cell in project.cells}
    for cell_id in changed:
        by_id[cell_id].status = CellStatus.OUTDATED
    return changed


def clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise InvalidOperationError("El nombre no puede estar vacío.")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise InvalidOperationError(
            f"El nombre no puede superar {MAX_NAME_LENGTH} caracteres.", name=cleaned
        )
    return cleaned


def unique_system_name(project: Project, name: str) -> str:
    taken = {s.name for s in project.systems}
    if name not in taken:
        return name
    n = 2
    while f"{name} ({n})" in taken:
        n += 1
    return f"{name} ({n})"


# ---------------------------------------------------------------- context (ADR 0016)


class ContextEntry(Schema):
    """A stage type in the context of a cell and the cell that provides it."""

    stage: StageType
    cell_id: str
    cell_name: str
    system_id: str


class CellContext(Schema):
    """Resolved context of a cell: every cell upstream of it, by stage type."""

    cell_id: str
    stage: StageType
    entries: list[ContextEntry]
    """In catalog order. A collector may list several cells of the same type."""
    missing: list[StageType]
    """Required stage types absent from the context, in catalog order. Empty: can run."""


def _stage_name(stage: StageType) -> str:
    return STAGES[stage].default_name


def _names(stages: Iterable[StageType]) -> str:
    return ", ".join(f"«{_stage_name(s)}»" for s in sorted(set(stages), key=ORDER.__getitem__))


def _passes_context(cell: Cell) -> bool:
    """Collectors are terminal: they pass no context downstream."""
    return STAGES[cell.stage].kind is not StageKind.COLLECTOR


def context_cells(project: Project, cell_id: str) -> dict[StageType, list[str]]:
    """Cells upstream of ``cell_id``, by stage type (all of them, not only direct parents).

    A link passes the whole context of its source. Collectors pass nothing. Outside collectors
    each list has one cell when the schematic follows the link rules.
    """
    cells = {c.id: c for c in project.cells}
    parents: dict[str, list[str]] = {}
    for lk in project.links:
        parents.setdefault(lk.target_cell_id, []).append(lk.source_cell_id)
    result: dict[StageType, list[str]] = {}
    seen: set[str] = set()
    frontier = [cell_id]
    while frontier:
        current = frontier.pop()
        for source_id in parents.get(current, []):
            if source_id in seen:
                continue
            seen.add(source_id)
            source = cells[source_id]
            if not _passes_context(source):
                continue
            result.setdefault(source.stage, []).append(source_id)
            frontier.append(source_id)
    return result


def missing_requirements(project: Project, cell_id: str) -> list[StageType]:
    cell = get_cell(project, cell_id)
    present = context_cells(project, cell_id)
    return [s for s in STAGES[cell.stage].requires if s not in present]


def cell_context(project: Project, cell_id: str) -> CellContext:
    cell = get_cell(project, cell_id)
    by_type = context_cells(project, cell_id)
    entries: list[ContextEntry] = []
    for stage in sorted(by_type, key=ORDER.__getitem__):
        for cid in by_type[stage]:
            provider = get_cell(project, cid)
            entries.append(
                ContextEntry(
                    stage=stage,
                    cell_id=cid,
                    cell_name=provider.name,
                    system_id=provider.system_id,
                )
            )
    missing = sorted(
        (s for s in STAGES[cell.stage].requires if s not in by_type), key=ORDER.__getitem__
    )
    return CellContext(cell_id=cell.id, stage=cell.stage, entries=entries, missing=missing)


# ---------------------------------------------------------------- link validation


def _provides(project: Project, cell: Cell) -> set[StageType]:
    """Stage types a link from ``cell`` passes on: the cell itself and its context."""
    return {cell.stage, *context_cells(project, cell.id)}


def check_link(project: Project, source_cell_id: str, target_cell_id: str) -> None:
    """Raise ``InvalidOperationError`` if the link A → B breaks a rule (ADR 0016).

    1. The graph stays acyclic.
    2. B is not a root.
    3. Parents: B had no parent, or the context of A (including A) shares no stage type with
       the current context of B (union). Collectors accept several parents of the same type.
    4. No repeats: the resulting context of B (and of everything downstream of it) repeats no
       stage type and does not contain B's own type. Collectors may repeat types.
    5. Order: every type in the resulting context comes before B's type in the catalog.

    Missing requirements never block a link.
    """
    source = get_cell(project, source_cell_id)
    target = get_cell(project, target_cell_id)
    if source.id == target.id:
        raise InvalidOperationError("Una celda no puede vincularse consigo misma.", rule="cycle")
    if any(
        lk.source_cell_id == source.id and lk.target_cell_id == target.id for lk in project.links
    ):
        raise InvalidOperationError(
            f"«{source.name}» ya alimenta a «{target.name}».", rule="duplicate"
        )
    if STAGES[target.stage].root:
        raise InvalidOperationError(
            f"«{target.name}» es una raíz ({_stage_name(target.stage)}): no admite vínculos "
            "entrantes.",
            rule="root",
        )
    if not _passes_context(source):
        raise InvalidOperationError(
            f"«{source.name}» es un colector: no pasa contexto aguas abajo.", rule="collector"
        )
    if source.id in downstream(project, [target.id]):
        raise InvalidOperationError("El vínculo crearía un ciclo.", rule="cycle")

    target_collects = STAGES[target.stage].kind is StageKind.COLLECTOR
    has_parent = any(lk.target_cell_id == target.id for lk in project.links)
    if has_parent and not target_collects:
        shared = _provides(project, source) & set(context_cells(project, target.id))
        if shared:
            raise InvalidOperationError(
                f"«{target.name}» ya tiene padre y su contexto ya incluye {_names(shared)}: "
                f"«{source.name}» solo puede sumarse si no comparten ningún tipo (unión).",
                rule="parents",
                shared=sorted(shared, key=ORDER.__getitem__),
            )

    probe = Link(id="__probe__", source_cell_id=source.id, target_cell_id=target.id)
    project.links.append(probe)
    try:
        affected = [target.id, *sorted(downstream(project, [target.id]))]
        for cid in affected:
            _check_context(project, get_cell(project, cid), target)
    finally:
        project.links.remove(probe)


def _check_context(project: Project, cell: Cell, target: Cell) -> None:
    """Rules 4 and 5 on the (tentative) context of ``cell``."""
    by_type = context_cells(project, cell.id)
    where = "" if cell.id == target.id else f" (aguas abajo, en «{cell.name}»)"
    if STAGES[cell.stage].kind is not StageKind.COLLECTOR:
        repeated = [s for s, ids in by_type.items() if len(ids) > 1]
        if repeated:
            raise InvalidOperationError(
                f"El contexto de «{cell.name}» repetiría {_names(repeated)}{where}: "
                "cada tipo tiene que venir de una sola celda.",
                rule="repeat",
                repeated=sorted(repeated, key=ORDER.__getitem__),
            )
        if cell.stage in by_type:
            raise InvalidOperationError(
                f"El contexto de «{cell.name}» incluiría otra celda de su mismo tipo{where}.",
                rule="repeat",
                repeated=[cell.stage],
            )
    late = [s for s in by_type if not before(s, cell.stage)]
    if late:
        raise InvalidOperationError(
            f"{_names(late)} no puede ir antes de «{_stage_name(cell.stage)}»{where}: "
            "el contexto sigue el orden del catálogo.",
            rule="order",
            late=sorted(late, key=ORDER.__getitem__),
        )


def is_valid_link(project: Project, source_cell_id: str, target_cell_id: str) -> bool:
    try:
        check_link(project, source_cell_id, target_cell_id)
    except InvalidOperationError:
        return False
    return True


def add_link(project: Project, source_cell_id: str, target_cell_id: str) -> Link:
    check_link(project, source_cell_id, target_cell_id)
    link = Link(id=new_id("link"), source_cell_id=source_cell_id, target_cell_id=target_cell_id)
    project.links.append(link)
    return link


def link_targets(project: Project, source_cell_id: str) -> list[str]:
    """Cells that the given cell could feed right now."""
    get_cell(project, source_cell_id)
    return [cell.id for cell in project.cells if is_valid_link(project, source_cell_id, cell.id)]


# ---------------------------------------------------------------- layout


def _estimated_height(n_cells: int) -> float:
    return _HEADER_HEIGHT + _ROW_HEIGHT * max(n_cells, 1)


def free_position(
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
    return free_position(project, x, 0, n_cells)


def _position_right_of(project: Project, system: System, n_cells: int) -> Position:
    x = system.position.x + SYSTEM_WIDTH + SYSTEM_GAP
    return free_position(project, x, system.position.y, n_cells)


# ---------------------------------------------------------------- creation helpers


def _new_cell(project: Project, system: System, stage: StageType, name: str | None) -> Cell:
    cell = Cell(
        id=new_id("cell"),
        system_id=system.id,
        stage=stage,
        name=clean_name(name) if name else STAGES[stage].default_name,
        form=new_form_state(stage),
    )
    project.cells.append(cell)
    system.cell_ids.append(cell.id)
    return cell


def _autolink(project: Project, system: System, cell: Cell) -> list[Link]:
    """Link a new cell to the cells of its system (``add_cell``).

    1. As target: walk the other cells in reverse catalog order and add each valid link that
       brings a missing requirement, until the requirements are covered.
    2. As source: link it to the cells that miss a requirement it brings, if valid.

    Only links that involve the new cell are created, so links removed on purpose between
    existing cells are not recreated.
    """
    created: list[Link] = []
    position = {cid: i for i, cid in enumerate(system.cell_ids)}
    others = [get_cell(project, cid) for cid in system.cell_ids if cid != cell.id]
    for candidate in sorted(others, key=lambda c: (ORDER[c.stage], position[c.id]), reverse=True):
        missing = set(missing_requirements(project, cell.id))
        if not missing:
            break
        if _provides(project, candidate) & missing and is_valid_link(
            project, candidate.id, cell.id
        ):
            created.append(add_link(project, candidate.id, cell.id))
    for target in others:
        missing = set(missing_requirements(project, target.id))
        if _provides(project, cell) & missing and is_valid_link(project, cell.id, target.id):
            created.append(add_link(project, cell.id, target.id))
    return created


def _create_system(
    project: Project, blueprint: Blueprint, name: str | None, position: Position | None
) -> System:
    stages = blueprint.stages()
    system = System(
        id=new_id("sys"),
        name=unique_system_name(project, clean_name(name) if name else blueprint.default_name()),
        position=position or _default_position(project, len(stages)),
    )
    project.systems.append(system)
    by_stage = {stage: _new_cell(project, system, stage, None) for stage in stages}
    if blueprint.template is not None:
        for source, target in TEMPLATES[blueprint.template].links:
            add_link(project, by_stage[source].id, by_stage[target].id)
    return system


def _link_branch(project: Project, source: Cell, system: System) -> Link | None:
    """Link ``source`` to the first cell of ``system`` (catalog order) that accepts it."""
    cells = sorted(
        (get_cell(project, cid) for cid in system.cell_ids), key=lambda c: ORDER[c.stage]
    )
    for cell in cells:
        if is_valid_link(project, source.id, cell.id):
            return add_link(project, source.id, cell.id)
    return None


def can_branch(project: Project, cell_id: str, blueprint: Blueprint) -> bool:
    """Whether ``blueprint`` can be branched from ``cell_id``. Does not change the project."""
    scratch = project.model_copy(deep=True)
    source = get_cell(scratch, cell_id)
    system = _create_system(scratch, blueprint, None, Position(x=0, y=0))
    return _link_branch(scratch, source, system) is not None


def branch_targets(project: Project, blueprint: Blueprint) -> list[str]:
    """Cells onto which ``blueprint`` can be dropped to branch (see ``branch``)."""
    return [cell.id for cell in project.cells if can_branch(project, cell.id, blueprint)]


def branch_options(project: Project, cell_id: str) -> list[Blueprint]:
    """Templates and stages that can be branched from ``cell_id`` (see ``branch``)."""
    get_cell(project, cell_id)
    candidates = [Blueprint(template=t) for t in TEMPLATES] + [Blueprint(stage=s) for s in STAGES]
    return [b for b in candidates if can_branch(project, cell_id, b)]


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
    """Add a cell to a system and link it to the cells of that system (see ``_autolink``)."""
    system = get_system(project, system_id)
    cell = _new_cell(project, system, stage, name)
    links = _autolink(project, system, cell)
    outdated = invalidate(
        project, [link.target_cell_id for link in links if link.target_cell_id != cell.id]
    )
    return Outcome(
        summary=f"Agregó la celda «{cell.name}» al sistema «{system.name}».",
        created_ids=[cell.id, *(link.id for link in links)],
        outdated_cell_ids=outdated,
    )


def link(project: Project, source_cell_id: str, target_cell_id: str) -> Outcome:
    new = add_link(project, source_cell_id, target_cell_id)
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
    """Create a new system from ``blueprint`` and link ``cell_id`` to its first cell (catalog
    order) that accepts it with a valid link.

    Fails if none does (e.g. «Fase 0» from any cell: its cells are roots or already have their
    parent inside the system).
    """
    source = get_cell(project, cell_id)
    source_system = get_system(project, source.system_id)
    n_cells = len(blueprint.stages())
    system = _create_system(
        project,
        blueprint,
        name,
        position or _position_right_of(project, source_system, n_cells),
    )
    new_link = _link_branch(project, source, system)
    if new_link is None:
        raise InvalidOperationError(
            f"No se puede ramificar «{blueprint.default_name()}» desde «{source.name}»: "
            "ninguna de sus celdas la acepta con un vínculo válido.",
            cell_id=cell_id,
        )
    return Outcome(
        summary=f"Ramificó «{system.name}» desde «{source.name}».",
        created_ids=[system.id, *system.cell_ids, new_link.id],
    )


def rename_system(project: Project, system_id: str, name: str) -> Outcome:
    system = get_system(project, system_id)
    old, system.name = system.name, clean_name(name)
    return Outcome(summary=f"Renombró el sistema «{old}» a «{system.name}».")


def rename_cell(project: Project, cell_id: str, name: str) -> Outcome:
    cell = get_cell(project, cell_id)
    old, cell.name = cell.name, clean_name(name)
    return Outcome(summary=f"Renombró la celda «{old}» a «{cell.name}».")


def _join(parts: list[str]) -> str:
    """«A», «B» y «C»."""
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} y {parts[-1]}"


def _quoted(names: Iterable[str]) -> str:
    return _join([f"«{name}»" for name in names])


def _systems_phrase(systems: list[System], empty: bool = False) -> str:
    """«el sistema «A»», «los sistemas vacíos «A» y «B»»."""
    one, many = (
        ("el sistema vacío", "los sistemas vacíos") if empty else ("el sistema", "los sistemas")
    )
    return f"{one if len(systems) == 1 else many} {_quoted(s.name for s in systems)}"


def move_system(project: Project, system_id: str, position: Position) -> Outcome:
    return move_systems(project, {system_id: position})


def move_systems(project: Project, positions: Mapping[str, Position]) -> Outcome:
    """Move several systems on the canvas in one operation (a multiple selection)."""
    systems = [get_system(project, system_id) for system_id in positions]
    if not systems:
        raise InvalidOperationError("No hay sistemas para mover.")
    for system in systems:
        system.position = positions[system.id]
    return Outcome(summary=f"Movió {_systems_phrase(systems)}.")


def duplicate_system(project: Project, system_id: str, position: Position | None = None) -> Outcome:
    """Copy a system with its cells, internal links and incoming links from other systems.

    Cells keep their status and artifact. Outgoing links to other systems are not copied.
    """
    original = get_system(project, system_id)
    copy = System(
        id=new_id("sys"),
        name=unique_system_name(project, f"{original.name} (copia)"),
        position=position
        or free_position(project, original.position.x, original.position.y, len(original.cell_ids)),
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
    return delete_items(project, [system_id], [])


def delete_cell(project: Project, cell_id: str) -> Outcome:
    """Delete a cell and its links. A system left without cells is deleted too."""
    return delete_items(project, [], [cell_id])


def delete_items(project: Project, system_ids: Iterable[str], cell_ids: Iterable[str]) -> Outcome:
    """Delete systems (with their cells) and cells, with their links, in one operation (a
    multiple selection). A system left without cells is deleted too."""
    systems = [get_system(project, system_id) for system_id in dict.fromkeys(system_ids)]
    picked = {system.id for system in systems}
    cells = [
        cell
        for cell in (get_cell(project, cell_id) for cell_id in dict.fromkeys(cell_ids))
        if cell.system_id not in picked
    ]
    if not systems and not cells:
        raise InvalidOperationError("No hay sistemas ni celdas para eliminar.")
    removed = {cid for system in systems for cid in system.cell_ids} | {c.id for c in cells}
    outdated = _remove_cells(project, removed)
    touched = {cell.system_id for cell in cells}
    emptied = [s for s in project.systems if s.id in touched and not s.cell_ids]
    project.systems = [s for s in project.systems if s.id not in picked and s not in emptied]
    parts = [_systems_phrase(systems)] if systems else []
    if cells:
        noun = "la celda" if len(cells) == 1 else "las celdas"
        parts.append(f"{noun} {_quoted(cell.name for cell in cells)}")
    if emptied:
        parts.append(_systems_phrase(emptied, empty=True))
    return Outcome(summary=f"Eliminó {_join(parts)}.", outdated_cell_ids=outdated)
