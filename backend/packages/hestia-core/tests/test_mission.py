"""Mission artifact and its validation (docs/etapas/mission.md, ADR 0017)."""

import math
from datetime import date
from typing import Any

from hestia_core.forms import ProblemCode
from hestia_core.mission import (
    AttitudeMode,
    Axis,
    Face,
    MissionArtifact,
    OrbitType,
    Target,
    mission_defaults,
    validate_mission,
)

C = ProblemCode


def valid() -> MissionArtifact:
    return MissionArtifact.model_validate(
        {
            "general": {"launch_date": "2028-03-01", "design_life": 5 * 365.25 * 86400},
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
    assert defaults.schema_version == 1
    assert defaults.orbit.type is OrbitType.SSO
    assert defaults.criteria.uncertainty_margin == 10.0
    assert defaults.criteria.acceptance_margin == 5.0
    assert defaults.criteria.qualification_margin == 5.0
    assert defaults.attitude_modes == []


def test_empty_draft_reports_what_is_required() -> None:
    problems = codes(mission_defaults())
    assert problems == {
        ("general.launch_date", C.REQUIRED),
        ("general.design_life", C.REQUIRED),
        ("orbit.altitude", C.REQUIRED),
        ("orbit.ltan", C.REQUIRED),
        ("envelope.size_x", C.REQUIRED),
        ("envelope.size_y", C.REQUIRED),
        ("envelope.size_z", C.REQUIRED),
        ("envelope.mass", C.REQUIRED),
        ("attitude_modes", C.REQUIRED),
    }
    assert all(p.message for p in validate_mission(mission_defaults()))


def test_missing_orbit_type() -> None:
    assert codes(with_(valid(), orbit__type=None)) == {("orbit.type", C.REQUIRED)}


def test_min_and_max() -> None:
    assert codes(with_(valid(), general__design_life=0)) == {("general.design_life", C.MIN)}
    assert codes(with_(valid(), orbit__altitude=99e3)) == {("orbit.altitude", C.MIN)}
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


def test_sso_altitude() -> None:
    assert codes(with_(valid(), orbit__altitude=5_900e3)) == set()
    assert codes(with_(valid(), orbit__altitude=6_000e3)) == {("orbit.altitude", C.SSO_ALTITUDE)}


def test_ltan_format() -> None:
    assert codes(with_(valid(), orbit__ltan="25:00")) == {("orbit.ltan", C.FORMAT)}
    assert codes(with_(valid(), orbit__ltan="  ")) == {("orbit.ltan", C.REQUIRED)}


def keplerian(**orbit: Any) -> MissionArtifact:
    return with_(
        valid(),
        orbit={"type": "keplerian", "perigee_altitude": 500e3, "inclination": 0.9, **orbit},
    )


def test_keplerian() -> None:
    assert codes(keplerian()) == set()
    assert codes(keplerian(apogee_altitude=20_000e3)) == set()
    assert codes(keplerian(apogee_altitude=400e3)) == {("orbit.apogee_altitude", C.ORDER)}
    assert codes(keplerian(inclination=None)) == {("orbit.inclination", C.REQUIRED)}
    assert codes(keplerian(inclination=-0.1)) == {("orbit.inclination", C.MIN)}
    assert codes(keplerian(inclination=math.pi + 0.01)) == {("orbit.inclination", C.MAX)}
    assert codes(keplerian(inclination=math.pi)) == set()
    assert codes(keplerian(perigee_altitude=50e3)) == {("orbit.perigee_altitude", C.MIN)}


def test_fields_of_other_orbit_types_are_not_allowed() -> None:
    assert codes(keplerian(altitude=600e3, ltan="10:30")) == {
        ("orbit.altitude", C.NOT_ALLOWED),
        ("orbit.ltan", C.NOT_ALLOWED),
    }
    assert codes(with_(valid(), orbit__perigee_altitude=500e3)) == {
        ("orbit.perigee_altitude", C.NOT_ALLOWED)
    }
    assert codes(with_(valid(), orbit={"type": "geo"})) == set()
    assert codes(with_(valid(), orbit={"type": "geo", "inclination": 0.0})) == {
        ("orbit.inclination", C.NOT_ALLOWED)
    }


def mode(name: str, pa: str, pt: str, sa: str, st: str) -> AttitudeMode:
    return AttitudeMode(
        name=name,
        primary_axis=Axis(pa),
        primary_target=Target(pt),
        secondary_axis=Axis(sa),
        secondary_target=Target(st),
    )


def test_attitude_modes() -> None:
    artifact = valid()
    artifact.attitude_modes = [
        mode("Nadir", "+Z", "nadir", "+X", "velocity"),
        mode(" nadir ", "+Z", "nadir", "-Z", "velocity"),
        mode("Sol", "-Y", "sun", "+X", "sun"),
        mode("Inercial", "+X", "nadir", "+Y", "zenith"),
        AttitudeMode(),
    ]
    assert codes(artifact) == {
        ("attitude_modes[1].name", C.DUPLICATE_NAME),
        ("attitude_modes[1].secondary_axis", C.PARALLEL),
        ("attitude_modes[2].secondary_target", C.PARALLEL),
        ("attitude_modes[3].secondary_target", C.PARALLEL),
        ("attitude_modes[4].name", C.REQUIRED),
        ("attitude_modes[4].primary_axis", C.REQUIRED),
        ("attitude_modes[4].primary_target", C.REQUIRED),
        ("attitude_modes[4].secondary_axis", C.REQUIRED),
        ("attitude_modes[4].secondary_target", C.REQUIRED),
    }


def test_radiator_faces() -> None:
    artifact = valid()
    artifact.criteria.radiator_faces = [Face.PX, Face.MY, Face.PX]
    assert codes(artifact) == {("criteria.radiator_faces[2]", C.DUPLICATE)}


def test_messages_are_in_spanish() -> None:
    problems = validate_mission(with_(valid(), orbit__altitude=6_000e3))
    assert problems[0].message == "No hay órbitas heliosincrónicas por encima de 5 974 km."


def test_json_schema_declares_units() -> None:
    schema = MissionArtifact.model_json_schema()
    orbit = schema["$defs"]["Orbit"]["properties"]
    assert orbit["altitude"]["x-unit"] == "m" and orbit["altitude"]["x-display-unit"] == "km"
    assert orbit["inclination"]["x-display-unit"] == "°"
    assert orbit["type"]["x-enum-labels"]["keplerian"] == "LEO/MEO"
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
