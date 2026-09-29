"""Closed-form orbit relations used to validate mission inputs. Pure functions, SI units.

Earth model: WGS-84 equatorial radius and GM, J2 from EGM2008. Only the secular J2 nodal
precession is modelled (circular orbits).
"""

import math

EARTH_MU_M3_PER_S2 = 3.986004418e14
"""Earth gravitational parameter (WGS-84)."""
EARTH_RADIUS_M = 6_378_137.0
"""Earth equatorial radius (WGS-84)."""
EARTH_J2 = 1.08262668e-3
"""Second zonal harmonic (EGM2008, unnormalized)."""
TROPICAL_YEAR_S = 365.2421897 * 86_400.0
SUN_MEAN_MOTION_RAD_PER_S = 2.0 * math.pi / TROPICAL_YEAR_S
"""Mean apparent motion of the Sun: the nodal precession rate of a sun-synchronous orbit."""
GEO_ALTITUDE_M = 35_786_000.0
"""Altitude of the geostationary orbit over the equator."""


def _j2_factor() -> float:
    return 3.0 * EARTH_J2 * EARTH_RADIUS_M**2 * math.sqrt(EARTH_MU_M3_PER_S2)


def sso_cos_inclination(altitude_m: float) -> float:
    """Cosine of the inclination of a circular sun-synchronous orbit at ``altitude_m``.

    From the secular J2 nodal precession (Vallado, eq. 9-41, circular orbit, e = 0):
    ``dΩ/dt = -3/2 · n · J2 · (R/a)² · cos i`` set equal to the Sun's mean motion, so
    ``cos i = -2 · ω☉ · a^(7/2) / (3 · J2 · R² · √μ)``. Values below -1 mean that no
    sun-synchronous orbit exists at that altitude.
    """
    a = EARTH_RADIUS_M + altitude_m
    return -2.0 * SUN_MEAN_MOTION_RAD_PER_S * a**3.5 / _j2_factor()


def sso_inclination_rad(altitude_m: float) -> float:
    """Inclination of a circular sun-synchronous orbit. Raises ``ValueError`` if none exists."""
    cos_i = sso_cos_inclination(altitude_m)
    if cos_i < -1.0:
        raise ValueError(f"no sun-synchronous orbit at {altitude_m} m")
    return math.acos(cos_i)


def sso_max_altitude_m() -> float:
    """Highest altitude of a circular sun-synchronous orbit (cos i = -1, i = 180°)."""
    a_max = (_j2_factor() / (2.0 * SUN_MEAN_MOTION_RAD_PER_S)) ** (2.0 / 7.0)
    return a_max - EARTH_RADIUS_M
