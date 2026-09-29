"""Clipboard fragments (ADR 0014): copy part of a schematic and paste it here or in another project.

A fragment is a self-contained, versioned snapshot of systems and cells with the links between
them. Copying never changes the project. Pasting creates everything with new ids, keeps the
internal links (validated like any other link) and drops links to cells outside the fragment.
Pasted cells are ``never_run``: results and provenance are not copied. Form cells are the
exception (fragment v2): their artifact is input data, so it travels with the fragment and the
pasted cell keeps whether it was applied (revalidated) and where each value came from.
"""

from typing import Any, Literal

from pydantic import Field, ValidationError

from hestia_project.base import Schema
from hestia_project.catalog import StageType
from hestia_project.errors import InvalidFragmentError, InvalidOperationError
from hestia_project.forms import form_from_artifact, new_form_state, status_for
from hestia_project.model import Cell, CellStatus, FieldSource, Position, Project, System
from hestia_project.schematic import (
    SYSTEM_GAP,
    Outcome,
    add_link,
    clean_name,
    free_position,
    get_cell,
    get_system,
    new_id,
    unique_system_name,
)

FRAGMENT_KIND = "hestia.fragment"
"""Marker that identifies a fragment, e.g. in the system clipboard."""

FRAGMENT_SCHEMA_VERSION = 2
"""Version of the fragment schema. Bump on any incompatible change to these models.

- 1: systems, cells and internal links.
- 2: form cells carry their artifact (``FragmentCell.form``). Version 1 is still accepted.
"""
SUPPORTED_FRAGMENT_VERSIONS = frozenset({1, FRAGMENT_SCHEMA_VERSION})

PASTE_OFFSET = SYSTEM_GAP / 2
"""Shift of pasted systems relative to the originals when no position is given."""


class FragmentForm(Schema):
    """Artifact of a form cell (ADR 0017)."""

    artifact: dict[str, Any]
    applied: bool
    """Whether the artifact was applied in the source (the pasted cell is then validated)."""
    sources: dict[str, FieldSource] = Field(default_factory=dict[str, FieldSource])
    """Where each field value came from, by leaf path. Change ids are not copied."""


class FragmentCell(Schema):
    id: str
    """Id in the source project; only used to resolve links inside the fragment."""
    stage: StageType
    name: str
    form: FragmentForm | None = None


class FragmentLink(Schema):
    source_cell_id: str
    target_cell_id: str


class FragmentSystem(Schema):
    """A system of the source project with the copied cells, in display order.

    ``whole`` is false when only some of its cells were copied: pasting then adds those cells
    to the target system if one is given, or creates a system with this name.
    """

    name: str
    position: Position
    whole: bool
    cells: list[FragmentCell]


class Fragment(Schema):
    kind: Literal["hestia.fragment"] = FRAGMENT_KIND
    schema_version: int = FRAGMENT_SCHEMA_VERSION
    source_project_id: str
    systems: list[FragmentSystem] = Field(default_factory=list[FragmentSystem])
    links: list[FragmentLink] = Field(default_factory=list[FragmentLink])
    """Links between cells of the fragment. Links to cells outside it are not copied."""


# ---------------------------------------------------------------- copy


def copy(project: Project, system_ids: list[str], cell_ids: list[str]) -> Fragment:
    """Snapshot whole systems and loose cells. Does not change the project."""
    if not system_ids and not cell_ids:
        raise InvalidOperationError("No hay nada seleccionado para copiar.")
    whole = [get_system(project, sid) for sid in dict.fromkeys(system_ids)]
    whole_ids = {s.id for s in whole}
    # Loose cells grouped by their system, skipping cells of systems copied whole.
    partial: dict[str, list[str]] = {}
    for cid in dict.fromkeys(cell_ids):
        cell = get_cell(project, cid)
        if cell.system_id not in whole_ids:
            partial.setdefault(cell.system_id, []).append(cid)

    systems: list[FragmentSystem] = []
    copied: set[str] = set()
    for system in whole:
        systems.append(_fragment_system(project, system, system.cell_ids, whole=True))
        copied.update(system.cell_ids)
    for sid, cids in partial.items():
        system = get_system(project, sid)
        ordered = [cid for cid in system.cell_ids if cid in cids]
        systems.append(_fragment_system(project, system, ordered, whole=False))
        copied.update(ordered)

    links = [
        FragmentLink(source_cell_id=lk.source_cell_id, target_cell_id=lk.target_cell_id)
        for lk in project.links
        if lk.source_cell_id in copied and lk.target_cell_id in copied
    ]
    return Fragment(source_project_id=project.id, systems=systems, links=links)


def _fragment_system(
    project: Project, system: System, cell_ids: list[str], whole: bool
) -> FragmentSystem:
    cells = [get_cell(project, cid) for cid in cell_ids]
    return FragmentSystem(
        name=system.name,
        position=system.position.model_copy(),
        whole=whole,
        cells=[
            FragmentCell(id=c.id, stage=c.stage, name=c.name, form=_fragment_form(c)) for c in cells
        ],
    )


def _fragment_form(cell: Cell) -> FragmentForm | None:
    if cell.form is None:
        return None
    return FragmentForm(
        artifact=cell.form.artifact,
        applied=cell.status is not CellStatus.NEVER_RUN,
        sources={path: p.source for path, p in cell.form.provenance.items()},
    )


# ---------------------------------------------------------------- paste


def check_fragment(fragment: Fragment) -> None:
    """Raise ``InvalidFragmentError`` if the fragment is not usable (version, structure)."""
    if fragment.schema_version not in SUPPORTED_FRAGMENT_VERSIONS:
        raise InvalidFragmentError(
            f"El contenido copiado usa la versión {fragment.schema_version} del formato "
            f"y esta versión de Hestia entiende hasta la {FRAGMENT_SCHEMA_VERSION}.",
            schema_version=fragment.schema_version,
        )
    if not any(system.cells for system in fragment.systems):
        raise InvalidFragmentError("El contenido copiado no tiene celdas.")
    ids = [cell.id for system in fragment.systems for cell in system.cells]
    if len(ids) != len(set(ids)):
        raise InvalidFragmentError("El contenido copiado tiene celdas repetidas.")
    known = set(ids)
    for lk in fragment.links:
        if lk.source_cell_id not in known or lk.target_cell_id not in known:
            raise InvalidFragmentError(
                "El contenido copiado tiene un vínculo a una celda que no incluye."
            )


def paste(
    project: Project,
    fragment: Fragment,
    position: Position | None = None,
    target_system_id: str | None = None,
) -> Outcome:
    """Create the fragment's systems and cells with new ids and re-create its internal links.

    - Whole systems become new systems. Names that already exist get « (2)», « (3)»…
    - Loose cells go into ``target_system_id`` when given; otherwise into a new system named
      after the one they were copied from.
    - With ``position``, the fragment's top-left system lands there and the rest keep their
      relative layout. Without it, systems are shifted from the originals and placed where
      they do not overlap others.
    - Every internal link is validated like ``link``; an invalid one rejects the whole paste.
    """
    check_fragment(fragment)
    target = get_system(project, target_system_id) if target_system_id else None
    sources = [s for s in fragment.systems if s.cells]
    anchor = Position(x=min(s.position.x for s in sources), y=min(s.position.y for s in sources))

    mapping: dict[str, str] = {}
    created: list[str] = []
    new_systems: list[System] = []
    into_target = 0
    for source in sources:
        if target is not None and not source.whole:
            system = target
            into_target += len(source.cells)
        else:
            # A single loose cell becomes a system named after it, as when dropping a stage.
            name = (
                source.cells[0].name if not source.whole and len(source.cells) == 1 else source.name
            )
            system = System(
                id=new_id("sys"),
                name=unique_system_name(project, clean_name(name)),
                position=_paste_position(project, source, anchor, position),
            )
            project.systems.append(system)
            new_systems.append(system)
            created.append(system.id)
        for cell in source.cells:
            clone = Cell(
                id=new_id("cell"),
                system_id=system.id,
                stage=cell.stage,
                name=_unique_cell_name(project, system, clean_name(cell.name)),
            )
            _paste_form(clone, cell.form)
            project.cells.append(clone)
            system.cell_ids.append(clone.id)
            mapping[cell.id] = clone.id
            created.append(clone.id)

    for lk in fragment.links:
        try:
            new = add_link(project, mapping[lk.source_cell_id], mapping[lk.target_cell_id])
        except InvalidOperationError as exc:
            raise InvalidFragmentError(
                f"El contenido copiado tiene un vínculo inválido: {exc.message}"
            ) from exc
        created.append(new.id)

    return Outcome(
        summary=_summary(new_systems, len(mapping) - into_target, target, into_target),
        created_ids=created,
    )


def _paste_form(cell: Cell, form: FragmentForm | None) -> None:
    """Default artifact for form cells; the copied one (revalidated) if the fragment has it."""
    cell.form = new_form_state(cell.stage)
    if cell.form is None or form is None:
        return
    try:
        cell.form = form_from_artifact(cell.stage, form.artifact, form.sources)
    except InvalidOperationError as exc:
        raise InvalidFragmentError(
            f"El contenido copiado tiene un artefacto inválido en «{cell.name}»."
        ) from exc
    except ValidationError as exc:
        raise InvalidFragmentError(
            f"El contenido copiado tiene un artefacto inválido en «{cell.name}»."
        ) from exc
    if form.applied:
        cell.status = status_for(cell.form.problems)


def _paste_position(
    project: Project, source: FragmentSystem, anchor: Position, position: Position | None
) -> Position:
    if position is not None:
        return Position(
            x=position.x + source.position.x - anchor.x,
            y=position.y + source.position.y - anchor.y,
        )
    return free_position(
        project,
        source.position.x + PASTE_OFFSET,
        source.position.y + PASTE_OFFSET,
        len(source.cells),
    )


def _unique_cell_name(project: Project, system: System, name: str) -> str:
    taken = {get_cell(project, cid).name for cid in system.cell_ids}
    if name not in taken:
        return name
    n = 2
    while f"{name} ({n})" in taken:
        n += 1
    return f"{name} ({n})"


def _count(n: int, one: str, many: str) -> str:
    return f"1 {one}" if n == 1 else f"{n} {many}"


def _summary(
    new_systems: list[System], n_new_cells: int, target: System | None, into_target: int
) -> str:
    parts: list[str] = []
    if len(new_systems) == 1:
        parts.append(f"el sistema «{new_systems[0].name}»")
    elif new_systems:
        cells = _count(n_new_cells, "celda", "celdas")
        parts.append(f"{len(new_systems)} sistemas con {cells}")
    if target is not None and into_target:
        cells = "la celda" if into_target == 1 else f"{into_target} celdas"
        parts.append(f"{cells} en el sistema «{target.name}»")
    return f"Pegó {' y '.join(parts)}."
