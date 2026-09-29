"""Sun-synchronous orbit relations against published values."""

import math

import pytest

from hestia_core.orbits import sso_inclination_rad, sso_max_altitude_m


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
