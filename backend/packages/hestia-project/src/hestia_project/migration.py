"""Upgrade projects saved with an older ``SCHEMA_VERSION`` (``docs/workflow-fases-0-1.md``).

Migrations never write to the history: a project opens as it was, upgraded, and the dropped
parts are reported as warnings (shown in Messages).
"""

from copy import deepcopy
from typing import Any

from hestia_core.environment.orbit import Orbit
from hestia_core.mission import MOVED_TO_ENVIRONMENT, MissionArtifact
from hestia_project.catalog import StageType
from hestia_project.errors import InvalidOperationError
from hestia_project.forms import FORMS, status_for, upgrade_artifact
from hestia_project.history import ChangeRecord
from hestia_project.model import Cell, CellStatus, FieldProvenance, FormState, Link, Project
from hestia_project.schematic import (
    add_cell,
    add_link,
    check_link,
    context_cells,
    get_cell,
    get_system,
    is_valid_link,
)


def relink(project: Project, links: list[Link]) -> list[str]:
    """Re-evaluate ``links`` in creation order with the current link rules (ADR 0016).

    Valid links are added to ``project``; the others are dropped. Returns one warning per
    dropped link. ``project`` must have no links yet.
    """
    warnings: list[str] = []
    for lk in links:
        try:
            check_link(project, lk.source_cell_id, lk.target_cell_id)
        except InvalidOperationError as exc:
            source = get_cell(project, lk.source_cell_id)
            target = get_cell(project, lk.target_cell_id)
            warnings.append(
                f"Se descartó el vínculo «{source.name}» → «{target.name}» al actualizar el "
                f"proyecto a las reglas nuevas: {exc.message}"
            )
            continue
        project.links.append(lk)
    return warnings


def recover_applied_changes(project: Project, history: list[ChangeRecord]) -> None:
    """Set ``FormState.applied_change_id`` of applied form cells from the history (v3 → v4).

    The change is the last one after which the cell holds its current artifact while it did
    not before (apply, paste, undo…). Left null when the history does not show it.
    """
    for cell in project.cells:
        if cell.form is None or cell.status is CellStatus.NEVER_RUN:
            continue
        for record in reversed(history):
            after = _cell(record.after, cell.id)
            if after is None or after.form is None or after.form.artifact != cell.form.artifact:
                continue
            before = _cell(record.before, cell.id)
            if (
                before is None
                or before.form is None
                or before.form.artifact != cell.form.artifact
                or before.status is CellStatus.NEVER_RUN
            ):
                cell.form.applied_change_id = record.change.id
                break


def _cell(project: Project, cell_id: str) -> Cell | None:
    return next((c for c in project.cells if c.id == cell_id), None)


# ---------------------------------------------------------------- v4 → v5 (ADR 0023)


Sections = tuple[dict[str, Any], dict[str, FieldProvenance]]
"""Moved sections of a mission (JSON) and their field provenance."""


def move_orbit_to_environment(project: Project, create_missing: bool) -> list[str]:
    """Move the orbit and the attitude modes of each mission (artifact v1) to the environment
    cells that have it in their context (parameters v1), with their provenance (ADR 0023).
    Every form artifact ends at its current version.

    With ``create_missing`` (the current project, not the history snapshots), a mission with
    an entered orbit or attitude modes and no environment downstream gets a new environment
    cell linked to it, so nothing is lost. Returns one warning per created cell.
    """
    moved: dict[str, Sections] = {}
    for cell in project.cells:
        if cell.stage is StageType.MISSION and cell.form is not None:
            moved[cell.id] = _take_orbit(cell)
    used: set[str] = set()
    for cell in project.cells:
        if cell.stage is not StageType.ENVIRONMENT or cell.form is None:
            continue
        mission = _mission_of(project, cell)
        if mission is not None:
            used.add(mission.id)
        if cell.form.artifact.get("schema_version", 1) < 2:
            _give_orbit(cell.form, moved.get(mission.id) if mission else None, mission)
    if not create_missing or FORMS[StageType.ENVIRONMENT].upgrade is None:
        return []
    return [
        _new_environment(project, get_cell(project, mission_id), sections)
        for mission_id, sections in moved.items()
        if mission_id not in used and _entered(sections[0])
    ]


def _mission_of(project: Project, cell: Cell) -> Cell | None:
    mission_ids = context_cells(project, cell.id).get(StageType.MISSION, [])
    return get_cell(project, mission_ids[0]) if mission_ids else None


def _take_orbit(mission: Cell) -> Sections:
    """Upgrade a mission artifact (revalidated) and return the sections it held that moved."""
    assert mission.form is not None
    form = mission.form
    sections = {k: form.artifact[k] for k in MOVED_TO_ENVIRONMENT if k in form.artifact}
    provenance = {
        path: value
        for path, value in form.provenance.items()
        if path.startswith(MOVED_TO_ENVIRONMENT)
    }
    if not sections:
        return sections, provenance
    form.artifact = upgrade_artifact(StageType.MISSION, form.artifact)
    form.provenance = {p: v for p, v in form.provenance.items() if p not in provenance}
    form.problems = FORMS[StageType.MISSION].validate(
        MissionArtifact.model_validate(form.artifact), {}
    )
    if mission.status is not CellStatus.NEVER_RUN:
        mission.status = status_for(form.problems)
    return sections, provenance


def _give_orbit(form: FormState, sections: Sections | None, mission: Cell | None) -> None:
    """Merge the moved sections (none: the defaults) into environment parameters and bring them
    to the current version."""
    spec = FORMS[StageType.ENVIRONMENT]
    if spec.upgrade is None:
        return
    data, provenance = sections if sections is not None else ({}, {})
    form.artifact = spec.upgrade(form.artifact | deepcopy(data))
    form.provenance = form.provenance | provenance
    context = {StageType.MISSION: _artifact(mission)} if mission is not None else {}
    form.problems = spec.validate(spec.model.model_validate(form.artifact), context)


def _artifact(cell: Cell) -> MissionArtifact:
    assert cell.form is not None
    return MissionArtifact.model_validate(cell.form.artifact)


def _entered(sections: dict[str, Any]) -> bool:
    """Whether the moved sections hold anything beyond the defaults."""
    orbit = sections.get("orbit")
    default = Orbit().model_dump(mode="json")
    return bool(sections.get("attitude_modes")) or (orbit is not None and orbit != default)


def _new_environment(project: Project, mission: Cell, sections: Sections) -> str:
    """An environment cell in the mission's system, linked to it, with the moved sections."""
    system = get_system(project, mission.system_id)
    add_cell(project, system.id, StageType.ENVIRONMENT)
    cell = get_cell(project, system.cell_ids[-1])
    if _mission_of(project, cell) is None and is_valid_link(project, mission.id, cell.id):
        add_link(project, mission.id, cell.id)
    assert cell.form is not None
    # Created by the upgrade, not by a change of the history.
    cell.form.provenance = {
        path: FieldProvenance(source=value.source, change_id=None)
        for path, value in cell.form.provenance.items()
    }
    _give_orbit(cell.form, sections, mission)
    return (
        f"Se creó la celda «{cell.name}» en «{system.name}» con la órbita y los modos de "
        f"actitud de «{mission.name}»: ahora son parámetros de Entorno."
    )
