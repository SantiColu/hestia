"""Low-precision Sun position, distance and Earth rotation against published values."""

import math
from datetime import UTC, date, datetime

import numpy as np
import pytest

from hestia_core.sun import (
    earth_rotation_angle,
    julian_date,
    mean_sun_right_ascension,
    solar_irradiance,
    sun_position,
)


def test_julian_date_of_j2000_and_of_a_date() -> None:
    # J2000.0 is JD 2451545.0 by definition (2000-01-01 12:00). Meeus, «Astronomical
    # Algorithms», 2nd ed., ex. 7.a: 1957-10-04.81 is JD 2436116.31.
    assert julian_date(datetime(2000, 1, 1, 12, tzinfo=UTC)) == 2_451_545.0
    assert julian_date(date(2000, 1, 1)) == 2_451_544.5
    sputnik = datetime(1957, 10, 4, 19, 26, 24, tzinfo=UTC)  # .81 of a day
    assert julian_date(sputnik) == pytest.approx(2_436_116.31, abs=1e-6)


def test_sun_position_against_meeus_example() -> None:
    # Meeus, «Astronomical Algorithms», 2nd ed., ex. 25.a, 1992-10-13 0h TD (JD 2448908.5):
    # apparent alpha = 198.38083°, δ = -7.78507°, R = 0.99766 AU. The Astronomical Almanac's
    # low-precision formula is good to 0.01° (plus ~0.005° of nutation it ignores) and to
    # 1e-4 AU, so the tolerance is 0.02° and 2e-4 AU.
    unit, distance = sun_position(2_448_908.5)
    ra = math.degrees(math.atan2(unit[1], unit[0])) % 360
    dec = math.degrees(math.asin(unit[2]))
    assert ra == pytest.approx(198.38083, abs=0.02)
    assert dec == pytest.approx(-7.78507, abs=0.02)
    assert float(distance) == pytest.approx(0.99766, abs=2e-4)
    assert float(np.linalg.norm(unit)) == pytest.approx(1.0, abs=1e-12)


def test_perihelion_and_aphelion_of_2028() -> None:
    # Earth's orbit: e ≈ 0.0167, perihelion early January (~0.9833 AU), aphelion early July
    # (~1.0167 AU) (Astronomical Almanac). Daily samples; tolerance 2 days and 2e-4 AU.
    start = julian_date(date(2028, 1, 1))
    days = np.arange(366.0)
    _, distance = sun_position(start + days)
    assert float(np.min(distance)) == pytest.approx(0.9833, abs=2e-4)
    assert float(np.max(distance)) == pytest.approx(1.0167, abs=2e-4)
    assert int(np.argmin(distance)) == pytest.approx(3, abs=2)  # ~ January 4
    assert int(np.argmax(distance)) == pytest.approx(184, abs=2)  # ~ July 3-5


def test_irradiance_scales_with_the_inverse_square() -> None:
    # S(r) = S / r²: 1361 W/m² at 1 AU; 1361 / 0.9833² = 1407.6 W/m² at perihelion.
    assert float(solar_irradiance(1361.0, 1.0)) == 1361.0
    assert float(solar_irradiance(1361.0, 0.9833)) == pytest.approx(1407.6, abs=0.1)


def test_mean_sun_and_earth_rotation_at_j2000() -> None:
    # Astronomical Almanac: L = 280.460° at J2000. IERS Conventions 2010, eq. 5.15:
    # ERA(J2000) = 2π · 0.7790572732640 = 280.46061837504°.
    assert math.degrees(float(mean_sun_right_ascension(2_451_545.0))) == pytest.approx(
        280.460, abs=1e-9
    )
    assert math.degrees(float(earth_rotation_angle(2_451_545.0))) == pytest.approx(
        280.46061837504, abs=1e-9
    )
    # One sidereal day later the Earth has turned exactly once more (tolerance: the float
    # resolution of a Julian date, ~5e-11 day, is ~3e-10 rad of rotation).
    sidereal_day = 1.0 / 1.00273781191135448
    assert float(earth_rotation_angle(2_451_545.0 + sidereal_day)) == pytest.approx(
        float(earth_rotation_angle(2_451_545.0)), abs=1e-8
    )
