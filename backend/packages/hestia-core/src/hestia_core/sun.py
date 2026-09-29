"""Position of the Sun and Earth rotation, low precision. Pure functions, SI units.

Sun: the low-precision formulae of the Astronomical Almanac (section C, «Low precision formulas
for the Sun»), valid 1950-2050 with an error of about 0.01° in direction and 1e-5 AU in
distance. Time is UTC treated as TT and UT1 (the ~70 s difference moves the Sun by 0.001°).

Frame: geocentric equatorial inertial, mean equator and equinox of date (``x`` to the vernal
equinox, ``z`` to the north pole). The precession since J2000 (≈ 0.35° by 2025) is ignored:
every vector of the environment is in this same frame.
"""

import math
from datetime import UTC, date, datetime

import numpy as np
from numpy.typing import NDArray

AU_M = 149_597_870_700.0
"""Astronomical unit (IAU 2012)."""
SUN_RADIUS_M = 695_700_000.0
"""Nominal solar radius (IAU 2015 Resolution B3)."""
JD_J2000 = 2_451_545.0
"""Julian date of J2000.0 (2000-01-01 12:00 TT)."""
_JD_UNIX_EPOCH = 2_440_587.5
SECONDS_PER_DAY = 86_400.0

FloatArray = NDArray[np.float64]


def julian_date(moment: datetime | date) -> float:
    """Julian date of a moment (naive datetimes are UTC; a date is its 00:00 UTC)."""
    if not isinstance(moment, datetime):
        moment = datetime(moment.year, moment.month, moment.day, tzinfo=UTC)
    elif moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return _JD_UNIX_EPOCH + moment.timestamp() / SECONDS_PER_DAY


def sun_position(jd: float | FloatArray) -> tuple[FloatArray, FloatArray]:
    """Unit vector Earth → Sun and Earth-Sun distance (AU) at Julian date(s) ``jd``.

    Astronomical Almanac, low precision: ``n = JD - 2451545.0``;
    ``L = 280.460° + 0.9856474° n`` (mean longitude, aberration included);
    ``g = 357.528° + 0.9856003° n`` (mean anomaly);
    ``λ = L + 1.915° sin g + 0.020° sin 2g`` (ecliptic longitude, latitude 0);
    ``ε = 23.439° - 0.0000004° n`` (obliquity);
    ``R = 1.00014 - 0.01671 cos g - 0.00014 cos 2g`` AU.

    Returns arrays of shape ``(…, 3)`` and ``(…)``.
    """
    n = np.asarray(jd, dtype=np.float64) - JD_J2000
    g = np.radians(357.528 + 0.9856003 * n)
    lam = np.radians(280.460 + 0.9856474 * n + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g))
    eps = np.radians(23.439 - 0.0000004 * n)
    unit = np.stack([np.cos(lam), np.cos(eps) * np.sin(lam), np.sin(eps) * np.sin(lam)], axis=-1)
    distance_au = 1.00014 - 0.01671 * np.cos(g) - 0.00014 * np.cos(2 * g)
    return unit, distance_au


def mean_sun_right_ascension(jd: float | FloatArray) -> FloatArray:
    """Right ascension of the mean (fictitious) Sun, rad in [0, 2π).

    It moves uniformly along the equator with the Sun's mean longitude ``L`` (Astronomical
    Almanac); local mean solar time is measured from it. The equation of time is the
    difference to the true Sun (up to ±16 min).
    """
    n = np.asarray(jd, dtype=np.float64) - JD_J2000
    return np.mod(np.radians(280.460 + 0.9856474 * n), 2 * math.pi)


def solar_irradiance(solar_constant_w_m2: float, distance_au: float | FloatArray) -> FloatArray:
    """Irradiance at ``distance_au`` from the Sun: the solar constant (at 1 AU) over r²."""
    return solar_constant_w_m2 / np.asarray(distance_au, dtype=np.float64) ** 2


def earth_rotation_angle(jd: float | FloatArray) -> FloatArray:
    """Earth rotation angle (IERS Conventions 2010, eq. 5.15), rad in [0, 2π).

    ``θ = 2π (0.7790572732640 + 1.00273781191135448 (JD_UT1 - 2451545.0))``. Angle between the
    Greenwich meridian and the x axis; only used to draw a rotating Earth.
    """
    n = np.asarray(jd, dtype=np.float64) - JD_J2000
    turns = 0.7790572732640 + 1.00273781191135448 * n
    return np.mod(2 * math.pi * np.mod(turns, 1.0), 2 * math.pi)
