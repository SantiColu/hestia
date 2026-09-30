"""The environment stage end to end in a project: parameters, update, result, profiles."""

import math
from datetime import date
from typing import Any

import pytest

from hestia_core.environment.parameters import EnvironmentParameters
from hestia_core.forms import ProblemCode
from hestia_core.mission import MissionArtifact
from hestia_project.artifacts import apply_artifact, read_artifact, validate_draft
from hestia_project.catalog import StageType, TemplateId
from hestia_project.computations import (
    preview_orbit,
    read_orbit_profile,
    read_result,
    update_cell,
)
from hestia_project.document import ProjectDocument
from hestia_project.errors import NotFoundError, StageNotImplementedError
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import Cell, CellStatus, Project
from hestia_project.schematic import Blueprint, create_system

S = StageType
HUMAN = Author(kind=ActorKind.HUMAN, name="ana")
MISSION: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 365.25 * 86_400},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
}
SSO: dict[str, Any] = {"type": "sso", "altitude": 600e3, "ltan": "10:30"}
NADIR: dict[str, Any] = {
    "name": "Apuntado nadir",
    "primary_axis": "+Z",
    "primary_target": "nadir",
    "secondary_axis": "+X",
    "secondary_target": "velocity",
}


def cell_of(project: Project, stage: StageType) -> Cell:
    return next(c for c in project.cells if c.stage is stage)


def phase0() -> ProjectDocument:
    """A phase 0 system with the mission applied and the environment parameters untouched."""
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )
    mission = MissionArtifact.model_validate(MISSION)
    mission_id = cell_of(doc.project, S.MISSION).id
    doc.apply(
        Operation.APPLY_ARTIFACT,
        HUMAN,
        "datos",
        lambda p: apply_artifact(p, mission_id, mission),
    )
    return doc


def parameters(orbit: dict[str, Any] | None = None, **sections: Any) -> EnvironmentParameters:
    return EnvironmentParameters.model_validate(
        {"orbit": orbit or SSO, "attitude_modes": [NADIR], **sections}
    )


def apply_parameters(doc: ProjectDocument, draft: EnvironmentParameters) -> None:
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    doc.apply(Operation.APPLY_ARTIFACT, HUMAN, "órbita", lambda p: apply_artifact(p, env_id, draft))


def configured(orbit: dict[str, Any] | None = None) -> ProjectDocument:
    """``phase0`` with the environment parameters applied: an orbit and one attitude mode."""
    doc = phase0()
    apply_parameters(doc, parameters(orbit))
    return doc


def update(doc: ProjectDocument) -> None:
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    doc.apply(Operation.UPDATE_CELL, HUMAN, "", lambda p: update_cell(p, doc.results, env_id))


def test_parameters_are_a_form_with_the_orbit_and_the_attitude() -> None:
    doc = phase0()
    env = cell_of(doc.project, S.ENVIRONMENT)
    view = read_artifact(doc.project, env.id)
    assert isinstance(view.artifact, EnvironmentParameters)
    assert not view.applied and view.status is CellStatus.NEVER_RUN
    assert [(p.path, p.code) for p in view.problems] == [
        ("orbit.altitude", ProblemCode.REQUIRED),
        ("orbit.ltan", ProblemCode.REQUIRED),
        ("attitude_modes", ProblemCode.REQUIRED),
    ]
    assert view.provenance["orbit.type"].source.value == "default"
    assert view.provenance["design_values.solar_constant"].source.value == "default"
    assert [e.stage for e in view.context.entries] == [S.MISSION]
    # The dispersions follow the orbit of the same draft; the step looks at the mission.
    draft = parameters(
        {"type": "geo"},
        dispersion={"ltan_dispersion": 600},
        sampling={"mission_step": 2 * 365.25 * 86_400},
    )
    problems = validate_draft(doc.project, env.id, draft)
    assert [(p.path, p.code) for p in problems] == [
        ("dispersion.ltan_dispersion", ProblemCode.NOT_ALLOWED),
        ("sampling.mission_step", ProblemCode.MAX),
    ]


def test_update_reads_the_summary_and_one_profile_at_a_time() -> None:
    doc = configured()
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.UP_TO_DATE
    result = read_result(doc.project, doc.results, env.id)
    assert result.environment is not None
    summary = result.environment
    assert summary.provider.name == "analytic"
    assert [c.id for c in summary.conditions] == ["max_eclipse", "min_eclipse"]
    mode_id = summary.attitude_modes[0].id
    assert mode_id.startswith("mode_")  # the backend id of the applied mode
    assert len(summary.orbit_profiles) == 2 and summary.fluxes
    profile = read_orbit_profile(doc.project, doc.results, env.id, "max_eclipse", mode_id)
    assert len(profile.time) == 120
    with pytest.raises(NotFoundError):
        read_orbit_profile(doc.project, doc.results, env.id, "nope", mode_id)
    with pytest.raises(StageNotImplementedError):
        read_result(doc.project, doc.results, cell_of(doc.project, S.MISSION).id)
    assert result.provenance is not None
    assert result.parameters == read_artifact(doc.project, env.id).artifact.model_dump(mode="json")


def test_list_items_get_backend_ids_that_stay() -> None:
    doc = phase0()
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    apply_parameters(
        doc, parameters(custom_conditions=[{"name": "β = 30°", "beta": math.radians(30)}])
    )
    view = read_artifact(doc.project, env_id)
    applied = view.artifact
    assert isinstance(applied, EnvironmentParameters)
    condition_id = applied.custom_conditions[0].id
    assert condition_id is not None and condition_id.startswith("cond_")
    mode_id = applied.attitude_modes[0].id
    assert mode_id is not None and mode_id.startswith("mode_")

    # Insert a mode before it (no id, and a forged id): the first keeps its id and provenance.
    edited = applied.model_copy(deep=True)
    new_mode = edited.attitude_modes[0].model_copy(update={"id": None, "name": "Sol"})
    forged = new_mode.model_copy(update={"id": "mine", "name": "Otro"})
    edited.attitude_modes = [new_mode, forged, *edited.attitude_modes]
    apply_parameters(doc, edited)
    after = read_artifact(doc.project, env_id)
    assert isinstance(after.artifact, EnvironmentParameters)
    ids = [m.id for m in after.artifact.attitude_modes]
    assert ids[2] == mode_id
    assert len(set(ids)) == 3 and "mine" not in ids
    assert after.provenance["attitude_modes[2].name"] == view.provenance["attitude_modes[0].name"]
    update(doc)
    summary = read_result(doc.project, doc.results, env_id).environment
    assert summary is not None and summary.conditions[-1].id == condition_id


def test_an_eccentric_orbit_fails_the_update() -> None:
    doc = configured(
        {"type": "keplerian", "perigee_altitude": 500e3, "apogee_altitude": 900e3, "inclination": 1}
    )
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.FAILED
    assert [(p.path, p.code) for p in env.problems] == [
        ("orbit.apogee_altitude", ProblemCode.ECCENTRICITY_OUT_OF_RANGE)
    ]


def test_changing_the_mission_or_the_orbit_outdates_the_environment() -> None:
    doc = configured()
    update(doc)
    mission_id = cell_of(doc.project, S.MISSION).id
    longer = MissionArtifact.model_validate(
        {**MISSION, "general": {**MISSION["general"], "design_life": 2 * 365.25 * 86_400}}
    )
    doc.apply(
        Operation.APPLY_ARTIFACT,
        HUMAN,
        "más vida",
        lambda p: apply_artifact(p, mission_id, longer),
    )
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.OUTDATED
    update(doc)
    apply_parameters(doc, parameters({**SSO, "altitude": 700e3}))
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.OUTDATED
    update(doc)
    summary = read_result(doc.project, doc.results, cell_of(doc.project, S.ENVIRONMENT).id)
    assert summary.environment is not None and summary.environment.orbit.altitude == 700e3


def test_orbit_preview_of_a_draft_changes_nothing() -> None:
    doc = phase0()
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    before = doc.project.model_copy(deep=True)
    result = preview_orbit(doc.project, env_id, parameters(), date(2028, 6, 1), None)
    assert result.problems == [] and result.preview is not None
    assert result.preview.date.date() == date(2028, 6, 1)
    assert result.preview.mode_id == "mode_1"  # an unapplied mode has a positional id
    assert doc.project == before and doc.revision == 2


def test_orbit_preview_needs_the_orbit_but_not_the_rest() -> None:
    doc = phase0()
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    broken = parameters({"type": "sso", "altitude": 600e3})
    result = preview_orbit(doc.project, env_id, broken)
    assert result.preview is None
    assert [(p.path, p.code) for p in result.problems] == [("orbit.ltan", ProblemCode.REQUIRED)]
    # Problems elsewhere (design values, attitude modes) do not hide the orbit.
    other = parameters(design_values={"solar_constant": 0}, attitude_modes=[])
    drawn = preview_orbit(doc.project, env_id, other)
    assert drawn.preview is not None and drawn.preview.quaternion is None
    far = {"type": "keplerian", "perigee_altitude": 500e3, "apogee_altitude": 900e3}
    rejected = preview_orbit(doc.project, env_id, parameters({**far, "inclination": 1.0}))
    assert [p.code for p in rejected.problems] == [ProblemCode.ECCENTRICITY_OUT_OF_RANGE]


def test_orbit_preview_needs_the_launch_date() -> None:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    result = preview_orbit(doc.project, env_id, parameters())
    assert [p.code for p in result.problems] == [ProblemCode.CONTEXT_INVALID]
    with pytest.raises(StageNotImplementedError):
        preview_orbit(doc.project, cell_of(doc.project, S.MISSION).id, parameters())
