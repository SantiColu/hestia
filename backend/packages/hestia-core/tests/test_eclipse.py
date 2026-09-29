"""Eclipse of a circular orbit: closed form, shadow function and limit cases."""

import math

import numpy as np
import pytest

from hestia_core.eclipse import (
    earth_angular_radius,
    eclipse_fraction,
    shadow_angular_radius,
    sun_angular_radius,
    visible_sun_fraction,
)
from hestia_core.orbits import EARTH_RADIUS_M, GEO_ALTITUDE_M, orbital_period_s

R = EARTH_RADIUS_M


def test_eclipse_at_beta_zero_500_km() -> None:
    # Gilmore, «Spacecraft Thermal Control Handbook», 2nd ed., eq. 2.4 with β = 0:
    # f = acos(√(h² + 2Rh) / (R + h)) / π. Hand calculation at h = 500 km:
    # √(500² + 2·6378.137·500) / 6878.137 = 2574.517 / 6878.137 = 0.374304 → acos = 1.187150
    # rad → f = 0.377882 (35.75 min of a 94.6 min orbit). Tolerance 1e-6 (hand rounding).
    r = R + 500e3
    fraction = float(eclipse_fraction(0.0, r, conical=False))
    assert fraction == pytest.approx(0.377882, abs=1e-6)
    assert fraction * orbital_period_s(r) / 60 == pytest.approx(35.75, abs=0.01)


def test_no_eclipse_above_the_critical_beta() -> None:
    # β* = asin(R / (R + h)): 68.0° at 500 km (Gilmore, table 2.2 gives ≈ 68°).
    r = R + 500e3
    critical = float(earth_angular_radius(r))
    assert math.degrees(critical) == pytest.approx(68.0, abs=0.05)
    assert float(eclipse_fraction(critical + 1e-6, r, conical=False)) == 0.0
    assert float(eclipse_fraction(math.radians(80), r, conical=False)) == 0.0
    assert float(eclipse_fraction(critical - 1e-3, r, conical=False)) > 0.0
    # Symmetric in β and decreasing with |β|.
    betas = np.radians(np.arange(-67.0, 68.0, 1.0))
    fractions = eclipse_fraction(betas, r, conical=False)
    assert np.allclose(fractions, fractions[::-1])
    assert np.all(np.diff(fractions[betas >= 0]) < 0)


def test_geo_eclipse_at_equinox() -> None:
    # GEO at equinox (β = 0): the cylindrical shadow gives 2·asin(R/a)/(2π) of a sidereal day
    # = 69.4 min; with the penumbra the longest eclipse is about 72 min (Wertz & Larson,
    # SMAD 3rd ed., section 5.1; Pisacane, «Fundamentals of Space Systems», 2nd ed.). The
    # tolerance of 1 min covers the textbook rounding.
    r = R + GEO_ALTITUDE_M
    period = orbital_period_s(r)
    cylindrical = float(eclipse_fraction(0.0, r, conical=False)) * period / 60
    conical = float(eclipse_fraction(0.0, r, conical=True)) * period / 60
    assert cylindrical == pytest.approx(69.4, abs=0.1)
    assert conical == pytest.approx(72.0, abs=1.0)
    # At a solstice (β ≈ 23.4°) there is no eclipse: β* = 8.7°.
    assert math.degrees(float(earth_angular_radius(r))) == pytest.approx(8.70, abs=0.01)
    assert float(eclipse_fraction(math.radians(23.4), r, conical=True)) == 0.0


def test_conical_shadow_adds_the_penumbra() -> None:
    # rho_S = asin(R☉ / 1 AU) = 0.2664° (IAU nominal radius 695 700 km).
    assert math.degrees(float(sun_angular_radius(1.0))) == pytest.approx(0.2664, abs=1e-4)
    r = R + 600e3
    assert float(shadow_angular_radius(r, conical=True)) == pytest.approx(
        float(earth_angular_radius(r) + sun_angular_radius(1.0)), abs=1e-15
    )
    assert float(eclipse_fraction(0.3, r, conical=True)) > float(
        eclipse_fraction(0.3, r, conical=False)
    )


def _circle(radius: float, beta: float, samples: int) -> tuple[np.ndarray, np.ndarray]:
    """Circular orbit whose plane is at β from the Sun (Sun along +x tilted by β)."""
    u = np.arange(samples) * 2 * math.pi / samples
    position = radius * np.stack([np.cos(u), np.sin(u), np.zeros_like(u)], axis=-1)
    sun = np.array([math.cos(beta), 0.0, math.sin(beta)])
    return position, np.broadcast_to(sun, position.shape).copy()


@pytest.mark.parametrize("conical", [False, True])
@pytest.mark.parametrize("beta_deg", [0.0, 30.0, 60.0, 67.0])
def test_shadow_function_agrees_with_the_closed_form(conical: bool, beta_deg: float) -> None:
    # Sampling the shadow function along the orbit gives the closed-form fraction within the
    # sampling step (1/N of the orbit, N = 36 000). The conical closed form takes the Sun's
    # direction from the Earth's centre (parallax r/d ≈ 5e-5 rad), which near the critical β
    # moves the fraction by up to ~2e-4: the conical tolerance adds 3e-4.
    r = R + 500e3
    samples = 36_000
    position, sun = _circle(r, math.radians(beta_deg), samples)
    nu = visible_sun_fraction(position, sun, 1.0, conical=conical)
    shadowed = float(np.mean(nu < 1.0))
    expected = float(eclipse_fraction(math.radians(beta_deg), r, conical=conical))
    assert shadowed == pytest.approx(expected, abs=2.0 / samples + (3e-4 if conical else 0.0))


def test_penumbra_is_a_smooth_transition() -> None:
    # Along the shadow entry nu goes from 1 to 0 monotonically; nu = 0 in umbra, where the
    # umbra (rho_E - rho_S) is shorter than the cylinder.
    r = R + 500e3
    position, sun = _circle(r, 0.0, 36_000)
    nu = visible_sun_fraction(position, sun, 1.0, conical=True)
    half = nu[9_000:18_001]  # from the terminator (u = 90°) to the anti-Sun point (u = 180°)
    assert np.all(np.diff(half) <= 1e-12)
    assert half[0] == 1.0 and half[-1] == 0.0
    partial = (nu > 0) & (nu < 1)
    assert 0 < int(np.sum(partial)) < 200
    umbra = float(np.mean(np.where(nu == 0.0, 1.0, 0.0)))
    assert umbra < float(eclipse_fraction(0.0, r, conical=False))
