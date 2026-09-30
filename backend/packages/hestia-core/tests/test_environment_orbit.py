"""Orbit and attitude modes of the environment parameters and their validation
(docs/etapas/environment.md, ADR 0023)."""

import math
from typing import Any

from hestia_core.environment.orbit import (
    AttitudeMode,
    Axis,
    Orbit,
    OrbitType,
    Target,
    validate_attitude_modes,
    validate_orbit,
)
from hestia_core.forms import ProblemCode, Problems

C = ProblemCode


def sso(**changes: Any) -> Orbit:
    return Orbit.model_validate({"type": "sso", "altitude": 600e3, "ltan": "10:30", **changes})


def keplerian(**changes: Any) -> Orbit:
    return Orbit.model_validate(
        {"type": "keplerian", "perigee_altitude": 500e3, "inclination": 0.9, **changes}
    )


def codes(orbit: Orbit) -> set[tuple[str, ProblemCode]]:
    p = Problems()
    validate_orbit(p, orbit)
    return {(problem.path, problem.code) for problem in p.items}


def test_valid_orbits_have_no_problems() -> None:
    assert codes(sso()) == set()
    assert codes(keplerian()) == set()
    assert codes(Orbit(type=OrbitType.GEO)) == set()


def test_defaults() -> None:
    orbit = Orbit()
    assert orbit.type is OrbitType.SSO
    assert codes(orbit) == {("orbit.altitude", C.REQUIRED), ("orbit.ltan", C.REQUIRED)}


def test_missing_orbit_type() -> None:
    assert codes(sso(type=None)) == {("orbit.type", C.REQUIRED)}


def test_sso_altitude() -> None:
    assert codes(sso(altitude=99e3)) == {("orbit.altitude", C.MIN)}
    assert codes(sso(altitude=5_900e3)) == set()
    assert codes(sso(altitude=6_000e3)) == {("orbit.altitude", C.SSO_ALTITUDE)}


def test_ltan_format() -> None:
    assert codes(sso(ltan="25:00")) == {("orbit.ltan", C.FORMAT)}
    assert codes(sso(ltan="  ")) == {("orbit.ltan", C.REQUIRED)}


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
    assert codes(sso(perigee_altitude=500e3)) == {("orbit.perigee_altitude", C.NOT_ALLOWED)}
    assert codes(Orbit(type=OrbitType.GEO, inclination=0.0)) == {
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


def mode_codes(modes: list[AttitudeMode]) -> set[tuple[str, ProblemCode]]:
    p = Problems()
    validate_attitude_modes(p, modes)
    return {(problem.path, problem.code) for problem in p.items}


def test_attitude_modes() -> None:
    assert mode_codes([]) == {("attitude_modes", C.REQUIRED)}
    assert mode_codes(
        [
            mode("Nadir", "+Z", "nadir", "+X", "velocity"),
            mode(" nadir ", "+Z", "nadir", "-Z", "velocity"),
            mode("Sol", "-Y", "sun", "+X", "sun"),
            mode("Inercial", "+X", "nadir", "+Y", "zenith"),
            AttitudeMode(),
        ]
    ) == {
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


def test_messages_are_in_spanish() -> None:
    p = Problems()
    validate_orbit(p, sso(altitude=6_000e3))
    assert p.items[0].message == "No hay órbitas heliosincrónicas por encima de 5 974 km."


def test_json_schema_declares_units() -> None:
    schema = Orbit.model_json_schema()["properties"]
    assert schema["altitude"]["x-unit"] == "m" and schema["altitude"]["x-display-unit"] == "km"
    assert schema["inclination"]["x-display-unit"] == "°"
    assert schema["type"]["x-enum-labels"]["keplerian"] == "LEO/MEO"
