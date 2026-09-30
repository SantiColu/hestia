"""Mission artifact and its validation (docs/etapas/mission.md, ADR 0017)."""

from datetime import date
from typing import Any

from hestia_core.forms import ProblemCode
from hestia_core.mission import Face, MissionArtifact, mission_defaults, validate_mission

C = ProblemCode


def valid() -> MissionArtifact:
    return MissionArtifact.model_validate(
        {
            "general": {"launch_date": "2028-03-01", "design_life": 5 * 365.25 * 86400},
            "envelope": {"size_x": 1.0, "size_y": 1.2, "size_z": 1.5, "mass": 450.0},
        }
    )


def codes(artifact: MissionArtifact) -> set[tuple[str, ProblemCode]]:
    return {(p.path, p.code) for p in validate_mission(artifact)}


def with_(artifact: MissionArtifact, **changes: Any) -> MissionArtifact:
    data = artifact.model_dump()
    for path, value in changes.items():
        *parents, leaf = path.split("__")
        target: Any = data
        for key in parents:
            target = target[int(key)] if key.isdigit() else target[key]
        target[leaf] = value
    return MissionArtifact.model_validate(data)


def test_valid_mission_has_no_problems() -> None:
    assert validate_mission(valid()) == []


def test_defaults() -> None:
    defaults = mission_defaults()
    assert defaults.schema_version == 2
    assert defaults.criteria.uncertainty_margin == 10.0
    assert defaults.criteria.acceptance_margin == 5.0
    assert defaults.criteria.qualification_margin == 5.0


def test_empty_draft_reports_what_is_required() -> None:
    problems = codes(mission_defaults())
    assert problems == {
        ("general.launch_date", C.REQUIRED),
        ("general.design_life", C.REQUIRED),
        ("envelope.size_x", C.REQUIRED),
        ("envelope.size_y", C.REQUIRED),
        ("envelope.size_z", C.REQUIRED),
        ("envelope.mass", C.REQUIRED),
    }
    assert all(p.message for p in validate_mission(mission_defaults()))


def test_min_and_max() -> None:
    assert codes(with_(valid(), general__design_life=0)) == {("general.design_life", C.MIN)}
    assert codes(with_(valid(), envelope__mass=-1)) == {("envelope.mass", C.MIN)}
    assert codes(with_(valid(), criteria__acceptance_margin=-0.5)) == {
        ("criteria.acceptance_margin", C.MIN)
    }
    assert codes(with_(valid(), criteria__heater_power_budget=-1)) == {
        ("criteria.heater_power_budget", C.MIN)
    }
    assert codes(with_(valid(), criteria__uncertainty_margin=0)) == set()
    assert codes(with_(valid(), criteria__qualification_margin=None)) == {
        ("criteria.qualification_margin", C.REQUIRED)
    }


def test_radiator_faces() -> None:
    artifact = valid()
    artifact.criteria.radiator_faces = [Face.PX, Face.MY, Face.PX]
    assert codes(artifact) == {("criteria.radiator_faces[2]", C.DUPLICATE)}


def test_messages_are_in_spanish() -> None:
    problems = validate_mission(with_(valid(), envelope__mass=0))
    assert problems[0].message == "La masa tiene que ser mayor que 0."


def test_orbit_and_attitude_are_not_mission_fields() -> None:
    schema = MissionArtifact.model_json_schema()["properties"]
    assert "orbit" not in schema and "attitude_modes" not in schema


def test_json_schema_declares_units() -> None:
    schema = MissionArtifact.model_json_schema()
    general = schema["$defs"]["General"]["properties"]
    assert general["design_life"]["x-unit"] == "s"
    criteria = schema["$defs"]["Criteria"]["properties"]
    assert criteria["uncertainty_margin"]["x-unit"] == "K"
    assert criteria["uncertainty_margin"]["x-display-unit"] == "K"  # ΔT: never °C
    envelope = schema["$defs"]["Envelope"]["properties"]
    assert all(envelope[f]["x-unit"] for f in ("size_x", "size_y", "size_z", "mass"))


def test_roundtrip_json() -> None:
    artifact = valid()
    again = MissionArtifact.model_validate_json(artifact.model_dump_json())
    assert again == artifact
    assert again.general.launch_date == date(2028, 3, 1)
