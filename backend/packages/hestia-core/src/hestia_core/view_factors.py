"""View factor from a flat plate to the spherical Earth, closed form.

Differential planar element at distance ``r`` from the centre of a sphere of radius ``R``, its
normal at angle λ from the direction to the centre (nadir). With ``H = r/R`` and
``X = √(H² - 1)`` (Howell, «A Catalog of Radiation Heat Transfer Configuration Factors»,
configuration «differential planar element to a sphere, element tilted»; the form used in
spacecraft thermal texts such as Gilmore, «Spacecraft Thermal Control Handbook», 2nd ed.,
2002, chapter 2). The tests check it against a direct numerical integration:

- the plate sees the whole visible cap, λ ≤ acos(1/H): ``F = cos λ / H²``;
- it sees none of it, λ ≥ π - acos(1/H): ``F = 0``;
- in between, with ``Y = -X cot λ``:
  ``F = [cos λ · acos Y - X sin λ √(1 - Y²)] / (π H²) + atan(sin λ √(1 - Y²) / X) / π``.

Assumptions: diffuse (Lambertian) Earth, uniform over the visible cap; the plate is small next
to its distance to the Earth and nothing shadows it (convex envelope).
"""

import math

import numpy as np

from hestia_core.orbits import EARTH_RADIUS_M
from hestia_core.sun import FloatArray


def plate_to_earth_view_factor(
    cos_nadir_angle: float | FloatArray, orbit_radius_m: float | FloatArray
) -> FloatArray:
    """View factor from a plate to the Earth; ``cos_nadir_angle`` = normal · nadir."""
    cos_l = np.clip(np.asarray(cos_nadir_angle, dtype=np.float64), -1.0, 1.0)
    h = np.asarray(orbit_radius_m, dtype=np.float64) / EARTH_RADIUS_M
    lam = np.arccos(cos_l)
    sin_l = np.sin(lam)
    full_limit = np.arccos(1.0 / h)
    x = np.sqrt(h**2 - 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.clip(-x * cos_l / sin_l, -1.0, 1.0)
        root = np.sqrt(1.0 - y**2)
        partial = (cos_l * np.arccos(y) - x * sin_l * root) / (math.pi * h**2) + np.arctan(
            sin_l * root / x
        ) / math.pi
    full = cos_l / h**2
    result = np.where(lam <= full_limit, full, np.where(lam >= math.pi - full_limit, 0.0, partial))
    return np.maximum(result, 0.0)
