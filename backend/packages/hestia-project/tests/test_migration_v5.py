"""Projects of schema v4 open with the orbit and the attitude modes in the environment
parameters (ADR 0023), in the project and in the history snapshots."""

import sqlite3
from pathlib import Path
from typing import Any

from hestia_core.mission import MissionArtifact
from hestia_project.artifacts import apply_artifact, read_artifact
from hestia_project.catalog import StageType, TemplateId
from hestia_project.clipboard import copy, paste
from hestia_project.document import ProjectDocument
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import Cell, CellStatus, FieldProvenance, FieldSource, Project
from hestia_project.schematic import Blueprint, context_cells, create_system
from hestia_project.storage import read_project_file, write_project

S = StageType
HUMAN = Author(kind=ActorKind.HUMAN, name="ana")
MISSION: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 157_788_000.0},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
}
ORBIT = {
    "type": "sso",
    "altitude": 600e3,
    "ltan": "10:30",
    "perigee_altitude": None,
    "apogee_altitude": None,
    "inclination": None,
}
MODES = [
    {
        "id": "mode_a",
        "name": "Apuntado nadir",
        "primary_axis": "+Z",
        "primary_target": "nadir",
        "secondary_axis": "+X",
        "secondary_target": "velocity",
    }
]


def cells_of(project: Project, stage: StageType) -> list[Cell]:
    return [c for c in project.cells if c.stage is stage]


def as_v4(project: Project, change_id: str) -> None:
    """Rewrite the form artifacts as a v4 file stored them: mission v1 with the orbit and the
    attitude modes, environment parameters v1 without them."""
    for mission in cells_of(project, S.MISSION):
        assert mission.form is not None
        mission.form.artifact |= {"schema_version": 1, "orbit": ORBIT, "attitude_modes": MODES}
        mission.form.provenance |= {
            "orbit.altitude": FieldProvenance(source=FieldSource.ENTERED, change_id=change_id),
            "attitude_modes[0].name": FieldProvenance(
                source=FieldSource.ENTERED, change_id=change_id
            ),
        }
    for env in cells_of(project, S.ENVIRONMENT):
        assert env.form is not None
        env.form.artifact = {
            k: v for k, v in env.form.artifact.items() if k not in ("orbit", "attitude_modes")
        } | {"schema_version": 1}


def v4_file(tmp_path: Path) -> tuple[Path, str]:
    """A phase 0 system with its mission applied and a lone mission in another system."""
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0), name="F0"),
    )
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(stage=S.MISSION), name="Suelta"),
    )
    mission_id = cells_of(doc.project, S.MISSION)[0].id
    change = doc.apply(
        Operation.APPLY_ARTIFACT,
        HUMAN,
        "datos",
        lambda p: apply_artifact(p, mission_id, MissionArtifact.model_validate(MISSION)),
    )
    project = doc.project.model_copy(deep=True)
    as_v4(project, change.id)
    for record in doc.history:
        as_v4(record.before, change.id)
        as_v4(record.after, change.id)
    path = tmp_path / "v4.hestia"
    write_project(path, project, doc.history)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 4")
    conn.commit()
    conn.close()
    return path, change.id


def test_the_orbit_moves_to_the_environment_downstream(tmp_path: Path) -> None:
    path, change_id = v4_file(tmp_path)
    loaded = read_project_file(path)
    applied, lone = cells_of(loaded.project, S.MISSION)
    assert applied.form is not None
    assert "orbit" not in applied.form.artifact and applied.form.artifact["schema_version"] == 2
    assert not any(p.startswith(("orbit", "attitude_modes")) for p in applied.form.provenance)
    assert applied.status is CellStatus.UP_TO_DATE

    env = next(
        c
        for c in cells_of(loaded.project, S.ENVIRONMENT)
        if context_cells(loaded.project, c.id).get(S.MISSION) == [applied.id]
    )
    view = read_artifact(loaded.project, env.id)
    assert view.artifact.model_dump(mode="json")["orbit"] == ORBIT
    assert view.artifact.model_dump(mode="json")["attitude_modes"] == MODES
    assert view.provenance["orbit.altitude"].change_id == change_id
    assert view.provenance["attitude_modes[0].name"].change_id == change_id
    assert env.status is CellStatus.NEVER_RUN  # parameters never applied: unchanged

    # The lone mission had an orbit and no environment: one is created and linked to it.
    (warning,) = loaded.warnings
    assert "órbita y los modos de actitud" in warning
    created = next(
        c
        for c in cells_of(loaded.project, S.ENVIRONMENT)
        if context_cells(loaded.project, c.id).get(S.MISSION) == [lone.id]
    )
    assert created.system_id == lone.system_id and created.status is CellStatus.NEVER_RUN
    assert created.form is not None and created.form.artifact["orbit"] == ORBIT


def test_history_snapshots_are_upgraded_too(tmp_path: Path) -> None:
    path, _ = v4_file(tmp_path)
    loaded = read_project_file(path)
    for record in loaded.history:
        for snapshot in (record.before, record.after):
            for cell in cells_of(snapshot, S.MISSION):
                assert cell.form is not None and "orbit" not in cell.form.artifact
            for cell in cells_of(snapshot, S.ENVIRONMENT):
                assert cell.form is not None and cell.form.artifact["schema_version"] == 2
    # Snapshots never get new cells: the lone mission's orbit only lives in the project.
    last = loaded.history[-1].after
    assert len(cells_of(last, S.ENVIRONMENT)) == 1
    assert len(cells_of(loaded.project, S.ENVIRONMENT)) == 2


def test_old_fragments_paste_with_upgraded_artifacts(tmp_path: Path) -> None:
    path, _ = v4_file(tmp_path)
    old = read_project_file(path).project
    mission = cells_of(old, S.MISSION)[0]
    fragment = copy(old, [], [mission.id])
    assert fragment.systems[0].cells[0].form is not None
    fragment.systems[0].cells[0].form.artifact |= {"schema_version": 1, "orbit": ORBIT}
    target = ProjectDocument.new("otro")
    target.apply(Operation.PASTE, HUMAN, "", lambda p: paste(p, fragment))
    (pasted,) = cells_of(target.project, S.MISSION)
    assert pasted.form is not None and "orbit" not in pasted.form.artifact
