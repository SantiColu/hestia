"""Earth shadow on a circular orbit: closed-form eclipse fraction and the shadow function.

Two models (``docs/etapas/environment.md``), selected with ``conical``:

- cylindrical: the shadow is a cylinder of the Earth's radius behind the Earth, without
  penumbra (Sun at infinity, point source).
- conical: the Sun is a disk of finite size; umbra and penumbra (Montenbruck & Gill,
  «Satellite Orbits», 2000, section 3.4.2). The eclipse fraction counts any occultation
  (umbra and penumbra); the shadow function gives the visible part of the solar disk.

Geometry: for a circular orbit of radius r and a Sun at angle β from the orbital plane, the
satellite is occulted where the angle θ between the directions to the Sun and to the Earth's
centre is below rho (rho_E for the cylinder, rho_E + rho_S for the penumbra cone, with the
Earth and Sun apparent radii rho_E = asin(R/r), rho_S = asin(R☉/d)). Along the orbit
``cos θ = -cos β cos Δu`` (Δu from the point nearest the Sun), so the shadow half-arc φ from
the anti-Sun point obeys ``cos φ = cos rho / cos β`` and the fraction is ``φ/π`` when |β| < rho.
The Sun's direction is taken from the Earth's centre (parallax r/d: 5e-5 rad in LEO, 3e-4 rad
in GEO, negligible). With rho = rho_E this is the usual
``acos(√(h² + 2Rh) / ((R + h) cos β)) / π`` (Gilmore, «Spacecraft Thermal Control Handbook»,
2nd ed., 2002, eq. 2.4).
"""

import math

import numpy as np

from hestia_core.orbits import EARTH_RADIUS_M
from hestia_core.sun import AU_M, SUN_RADIUS_M, FloatArray


def earth_angular_radius(orbit_radius_m: float | FloatArray) -> FloatArray:
    """rho_E = asin(R/r): apparent radius of the Earth seen from the satellite."""
    return np.arcsin(EARTH_RADIUS_M / np.asarray(orbit_radius_m, dtype=np.float64))


def sun_angular_radius(sun_distance_au: float | FloatArray) -> FloatArray:
    """rho_S = asin(R☉/d): apparent radius of the Sun (≈ 0.267° at 1 AU)."""
    return np.arcsin(SUN_RADIUS_M / (np.asarray(sun_distance_au, dtype=np.float64) * AU_M))


def shadow_angular_radius(
    orbit_radius_m: float | FloatArray,
    conical: bool,
    sun_distance_au: float | FloatArray = 1.0,
) -> FloatArray:
    """rho: angle between Sun and Earth centre below which the satellite is (partly) occulted.
    It is also the critical β above which there is no eclipse."""
    rho = earth_angular_radius(orbit_radius_m)
    if conical:
        rho = rho + sun_angular_radius(sun_distance_au)
    return rho


def eclipse_fraction(
    beta_rad: float | FloatArray,
    orbit_radius_m: float | FloatArray,
    conical: bool,
    sun_distance_au: float | FloatArray = 1.0,
) -> FloatArray:
    """Fraction of a circular orbit in shadow (umbra and penumbra if ``conical``), in [0, ½).

    ``acos(cos rho / cos β) / π`` if |β| < rho, else 0. Broadcasts over its arguments.
    """
    rho = shadow_angular_radius(orbit_radius_m, conical, sun_distance_au)
    cos_beta = np.cos(np.asarray(beta_rad, dtype=np.float64))
    ratio = np.cos(rho) / np.maximum(cos_beta, 1e-12)
    return np.where(ratio < 1.0, np.arccos(np.minimum(ratio, 1.0)) / math.pi, 0.0)


def visible_sun_fraction(
    position_m: FloatArray,
    sun_unit: FloatArray,
    sun_distance_au: float | FloatArray,
    conical: bool,
) -> FloatArray:
    """Shadow function nu: visible fraction of the solar disk, 0 (umbra) to 1 (full Sun).

    ``position_m`` (…, 3) is the geocentric satellite position and ``sun_unit`` (…, 3) the
    Earth → Sun direction. Cylindrical: 0 inside the cylinder behind the Earth, else 1.
    Conical: overlap of the two apparent disks (Montenbruck & Gill, eqs. 3.85-3.89), with
    ``a = rho_S``, ``b = rho_E``, ``c = θ``: nu = 1 if c ≥ a + b, 0 if c ≤ b - a, else
    ``1 - A/(π a²)`` with ``x = (c² + a² - b²)/(2c)``, ``y = √(a² - x²)`` and
    ``A = a² acos(x/a) + b² acos((c - x)/b) - c y``.
    """
    r = np.asarray(position_m, dtype=np.float64)
    s = np.asarray(sun_unit, dtype=np.float64)
    radius = np.linalg.norm(r, axis=-1)
    if not conical:
        along = np.sum(r * s, axis=-1)
        across = np.linalg.norm(r - along[..., None] * s, axis=-1)
        return np.where((along < 0) & (across < EARTH_RADIUS_M), 0.0, 1.0)

    d = np.asarray(sun_distance_au, dtype=np.float64) * AU_M
    to_sun = d[..., None] * s - r if np.ndim(d) else d * s - r
    to_sun_norm = np.linalg.norm(to_sun, axis=-1)
    a = np.arcsin(SUN_RADIUS_M / to_sun_norm)
    b = np.arcsin(EARTH_RADIUS_M / radius)
    cos_c = np.sum(to_sun * (-r), axis=-1) / (to_sun_norm * radius)
    c = np.arccos(np.clip(cos_c, -1.0, 1.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        x = (c**2 + a**2 - b**2) / (2 * c)
        y = np.sqrt(np.maximum(a**2 - x**2, 0.0))
        area = (
            a**2 * np.arccos(np.clip(x / a, -1.0, 1.0))
            + b**2 * np.arccos(np.clip((c - x) / b, -1.0, 1.0))
            - c * y
        )
        partial = 1.0 - area / (math.pi * a**2)
    nu = np.where(c >= a + b, 1.0, np.where(c <= b - a, 0.0, partial))
    return np.clip(nu, 0.0, 1.0)
