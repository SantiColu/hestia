"""Sun-synchronous orbit relations against published values."""

import math

import pytest

from hestia_core.orbits import (
    EARTH_RADIUS_M,
    SUN_MEAN_MOTION_RAD_PER_S,
    eccentricity,
    nodal_precession_rate,
    orbital_period_s,
    sso_inclination_rad,
    sso_max_altitude_m,
)


def test_sso_inclination_at_800_km() -> None:
    # Wertz & Larson, «Space Mission Analysis and Design», 3rd ed., fig. 6-7 / Vallado,
    # «Fundamentals of Astrodynamics and Applications», 4th ed., ex. 9-5: a circular SSO at
    # 800 km has i ≈ 98.6°. Tolerance 0.05° (J2-only secular model).
    assert math.degrees(sso_inclination_rad(800e3)) == pytest.approx(98.6, abs=0.05)


def test_sso_inclination_grows_with_altitude() -> None:
    low, high = sso_inclination_rad(400e3), sso_inclination_rad(1500e3)
    # SMAD fig. 6-7: ≈ 97.0° at 400 km, ≈ 102° at 1500 km.
    assert math.degrees(low) == pytest.approx(97.0, abs=0.1)
    assert math.degrees(high) == pytest.approx(102.0, abs=0.3)


def test_sso_max_altitude() -> None:
    # Boain, «A-B-Cs of Sun-Synchronous Orbit Mission Design», AAS 04-108 (2004): SSOs exist up
    # to ≈ 5 975 km (i = 180°). docs/etapas/mission.md: «hasta unos 5 970 km». Tolerance 10 km.
    assert sso_max_altitude_m() == pytest.approx(5_974e3, abs=10e3)
    assert math.degrees(sso_inclination_rad(sso_max_altitude_m() - 1.0)) == pytest.approx(
        180.0, abs=0.1
    )
    with pytest.raises(ValueError):
        sso_inclination_rad(sso_max_altitude_m() + 10e3)


def test_nodal_precession_of_a_sso_matches_the_mean_sun() -> None:
    # By construction of the SSO inclination (same J2 model): dΩ/dt = 360° per tropical year.
    a = EARTH_RADIUS_M + 700e3
    rate = nodal_precession_rate(a, sso_inclination_rad(700e3))
    assert rate == pytest.approx(SUN_MEAN_MOTION_RAD_PER_S, rel=1e-12)


def test_nodal_precession_of_the_iss() -> None:
    # Vallado, 4th ed., eq. 9-41; SMAD 3rd ed., fig. 6-5: a circular orbit at 400 km and
    # i = 51.6° regresses about 5.0°/day. Tolerance 0.05°/day (reading of the figure).
    rate = nodal_precession_rate(EARTH_RADIUS_M + 400e3, math.radians(51.6))
    assert math.degrees(rate) * 86_400 == pytest.approx(-5.0, abs=0.05)
    assert nodal_precession_rate(EARTH_RADIUS_M + 400e3, math.pi / 2) == pytest.approx(0.0)


def test_period_and_eccentricity() -> None:
    # A geostationary orbit (a = 42 164 km) has the sidereal day as its period, 86 164 s.
    # Tolerance 1 s (a is rounded to the km).
    assert orbital_period_s(42_164e3) == pytest.approx(86_164.1, abs=1.0)
    # Hand calculation: r_p = R + 500 km, r_a = R + 700 km → e = 200 / (2R + 1200 km).
    expected = 200e3 / (2 * EARTH_RADIUS_M + 1_200e3)
    assert eccentricity(500e3, 700e3) == pytest.approx(expected, rel=1e-12)
    assert eccentricity(600e3, 600e3) == 0.0
