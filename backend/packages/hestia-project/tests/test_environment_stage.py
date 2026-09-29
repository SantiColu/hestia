"""The environment stage end to end in a project: parameters, update, result, profiles."""

import math
from typing import Any

import pytest

from hestia_core.environment.parameters import EnvironmentParameters
from hestia_core.forms import ProblemCode
from hestia_core.mission import MissionArtifact
from hestia_project.artifacts import apply_artifact, read_artifact, validate_draft
from hestia_project.catalog import StageType, TemplateId
from hestia_project.computations import read_orbit_profile, read_result, update_cell
from hestia_project.document import ProjectDocument
from hestia_project.errors import NotFoundError, StageNotImplementedError
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import Cell, CellStatus, Project
from hestia_project.schematic import Blueprint, create_system

S = StageType
HUMAN = Author(kind=ActorKind.HUMAN, name="ana")
MISSION: dict[str, Any] = {
    "general": {"launch_date": "2028-03-01", "design_life": 365.25 * 86_400},
    "orbit": {"type": "sso", "altitude": 600e3, "ltan": "10:30"},
    "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
    "attitude_modes": [
        {
            "name": "Apuntado nadir",
            "primary_axis": "+Z",
            "primary_target": "nadir",
            "secondary_axis": "+X",
            "secondary_target": "velocity",
        }
    ],
}


def cell_of(project: Project, stage: StageType) -> Cell:
    return next(c for c in project.cells if c.stage is stage)


def phase0(**orbit: Any) -> ProjectDocument:
    doc = ProjectDocument.new("SAT")
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )
    mission = MissionArtifact.model_validate({**MISSION, "orbit": orbit or MISSION["orbit"]})
    mission_id = cell_of(doc.project, S.MISSION).id
    doc.apply(
        Operation.APPLY_ARTIFACT,
        HUMAN,
        "datos",
        lambda p: apply_artifact(p, mission_id, mission),
    )
    return doc


def update(doc: ProjectDocument) -> None:
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    doc.apply(Operation.UPDATE_CELL, HUMAN, "", lambda p: update_cell(p, doc.results, env_id))


def test_parameters_are_a_form_validated_against_the_mission() -> None:
    doc = phase0()
    env = cell_of(doc.project, S.ENVIRONMENT)
    view = read_artifact(doc.project, env.id)
    assert isinstance(view.artifact, EnvironmentParameters)
    assert not view.applied and view.status is CellStatus.NEVER_RUN
    assert view.problems == []
    assert view.provenance["design_values.solar_constant"].source.value == "default"
    assert [e.stage for e in view.context.entries] == [S.MISSION]
    draft = EnvironmentParameters.model_validate({"dispersion": {"geo_max_inclination": 0.1}})
    problems = validate_draft(doc.project, env.id, draft)
    assert [(p.path, p.code) for p in problems] == [
        ("dispersion.geo_max_inclination", ProblemCode.NOT_ALLOWED)
    ]


def test_update_reads_the_summary_and_one_profile_at_a_time() -> None:
    doc = phase0()
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.UP_TO_DATE
    result = read_result(doc.project, doc.results, env.id)
    assert result.environment is not None
    summary = result.environment
    assert summary.provider.name == "analytic"
    assert [c.id for c in summary.conditions] == ["max_eclipse", "min_eclipse"]
    mode_id = summary.attitude_modes[0].id
    assert mode_id.startswith("mode_")  # the mission's id
    assert len(summary.orbit_profiles) == 2 and summary.fluxes
    profile = read_orbit_profile(doc.project, doc.results, env.id, "max_eclipse", mode_id)
    assert len(profile.time) == 120
    with pytest.raises(NotFoundError):
        read_orbit_profile(doc.project, doc.results, env.id, "nope", mode_id)
    with pytest.raises(StageNotImplementedError):
        read_result(doc.project, doc.results, cell_of(doc.project, S.MISSION).id)
    assert result.provenance is not None
    assert result.parameters == read_artifact(doc.project, env.id).artifact.model_dump(mode="json")


def test_custom_conditions_get_backend_ids() -> None:
    doc = phase0()
    env_id = cell_of(doc.project, S.ENVIRONMENT).id
    draft = EnvironmentParameters.model_validate(
        {"custom_conditions": [{"name": "β = 30°", "beta": math.radians(30)}]}
    )
    doc.apply(Operation.APPLY_ARTIFACT, HUMAN, "β", lambda p: apply_artifact(p, env_id, draft))
    applied = read_artifact(doc.project, env_id).artifact
    assert isinstance(applied, EnvironmentParameters)
    condition_id = applied.custom_conditions[0].id
    assert condition_id is not None and condition_id.startswith("cond_")
    update(doc)
    summary = read_result(doc.project, doc.results, env_id).environment
    assert summary is not None and summary.conditions[-1].id == condition_id


def test_an_eccentric_orbit_fails_the_update() -> None:
    doc = phase0(type="keplerian", perigee_altitude=500e3, apogee_altitude=900e3, inclination=1.0)
    update(doc)
    env = cell_of(doc.project, S.ENVIRONMENT)
    assert env.status is CellStatus.FAILED
    assert [p.code for p in env.problems] == [ProblemCode.ECCENTRICITY_OUT_OF_RANGE]


def test_changing_the_mission_outdates_the_environment() -> None:
    doc = phase0()
    update(doc)
    mission_id = cell_of(doc.project, S.MISSION).id
    changed = MissionArtifact.model_validate(
        {**MISSION, "orbit": {"type": "sso", "altitude": 700e3, "ltan": "10:30"}}
    )
    doc.apply(
        Operation.APPLY_ARTIFACT,
        HUMAN,
        "más alto",
        lambda p: apply_artifact(p, mission_id, changed),
    )
    assert cell_of(doc.project, S.ENVIRONMENT).status is CellStatus.OUTDATED
    update(doc)
    summary = read_result(doc.project, doc.results, cell_of(doc.project, S.ENVIRONMENT).id)
    assert summary.environment is not None and summary.environment.orbit.altitude == 700e3
