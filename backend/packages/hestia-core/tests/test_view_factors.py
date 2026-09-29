"""Plate-to-Earth view factor against hand values and a direct numerical integration."""

import math

import numpy as np
import pytest

from hestia_core.orbits import EARTH_RADIUS_M
from hestia_core.view_factors import plate_to_earth_view_factor

R = EARTH_RADIUS_M


def _integrated(cos_nadir: float, radius: float, n: int = 600) -> float:
    """F = (1/π) ∫ cos θ_plate cos θ_earth / d² dA over the part of the sphere the plate sees.

    Midpoint rule on the visible cap in (polar angle from the sub-plate point, azimuth).
    """
    lam = math.acos(cos_nadir)
    normal = np.array([math.sin(lam), 0.0, -math.cos(lam)])  # nadir is -z
    plate = np.array([0.0, 0.0, radius])
    cap = math.acos(R / radius)
    theta = (np.arange(n) + 0.5) * cap / n
    phi = (np.arange(2 * n) + 0.5) * 2 * math.pi / (2 * n)
    t, p = np.meshgrid(theta, phi, indexing="ij")
    points = R * np.stack([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)], axis=-1)
    area = R**2 * np.sin(t) * (cap / n) * (2 * math.pi / (2 * n))
    ray = points - plate
    d = np.linalg.norm(ray, axis=-1)
    cos_plate = np.sum(ray * normal, axis=-1) / d
    cos_earth = np.sum(-ray * points / R, axis=-1) / d
    kernel = np.where((cos_plate > 0) & (cos_earth > 0), cos_plate * cos_earth / d**2, 0.0)
    return float(np.sum(kernel * area) / math.pi)


def test_nadir_plate_sees_one_over_h_squared() -> None:
    # Plate facing nadir: F = (R / r)² (Gilmore, «Spacecraft Thermal Control Handbook», 2nd
    # ed., chapter 2). Hand calculation at 500 km: (6378.137 / 6878.137)² = 0.859896.
    r = R + 500e3
    assert float(plate_to_earth_view_factor(1.0, r)) == pytest.approx(0.859896, abs=1e-6)
    assert float(plate_to_earth_view_factor(-1.0, r)) == 0.0  # zenith
    # GEO: (6378.137 / 42164.137)² = 0.022883.
    assert float(plate_to_earth_view_factor(1.0, R + 35_786e3)) == pytest.approx(0.022883, abs=1e-6)


@pytest.mark.parametrize("altitude_km", [400.0, 1_000.0, 20_000.0])
@pytest.mark.parametrize("angle_deg", [0.0, 30.0, 60.0, 80.0, 90.0, 100.0, 120.0, 150.0])
def test_closed_form_matches_numerical_integration(altitude_km: float, angle_deg: float) -> None:
    # Independent check of the partial-view formula: direct integration of the view factor
    # kernel over the visible cap. Tolerance 1e-3 (quadrature error at the cap's edge).
    r = R + altitude_km * 1e3
    cos_nadir = math.cos(math.radians(angle_deg))
    expected = _integrated(cos_nadir, r)
    assert float(plate_to_earth_view_factor(cos_nadir, r)) == pytest.approx(expected, abs=1e-3)


def test_continuous_at_the_limits_of_the_partial_view() -> None:
    r = R + 600e3
    full = math.acos(R / r)
    for limit in (full, math.pi - full):
        below = float(plate_to_earth_view_factor(math.cos(limit - 1e-7), r))
        above = float(plate_to_earth_view_factor(math.cos(limit + 1e-7), r))
        assert below == pytest.approx(above, abs=1e-6)
    # Decreasing from nadir to zenith.
    angles = np.radians(np.linspace(0.0, 180.0, 181))
    values = plate_to_earth_view_factor(np.cos(angles), r)
    assert np.all(np.diff(values) <= 1e-12)
