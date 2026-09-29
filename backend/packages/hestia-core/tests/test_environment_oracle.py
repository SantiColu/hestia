# Skyfield and sgp4 ship without type information.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

"""The analytic provider against an independent propagator (ADR 0020): Skyfield + SGP4.

Development oracle only (Skyfield is a dev dependency, never a runtime one). Over one year, a
600 km SSO propagated with SGP4 (secular J2 and J4, WGS-72) from the same initial node, with
the Sun from the JPL DE421 ephemeris, gives β and the eclipse fraction to compare with.

The ephemeris (~17 MB) is downloaded once into ``HESTIA_SKYFIELD_CACHE`` (default
``~/.cache/hestia/skyfield``). Without network the tests are skipped.

Tolerances:
- Sun direction: 0.02° (Astronomical Almanac low precision, 0.01°, plus the nutation it
  ignores).
- Node: 0.8° after a year. The analytic node drifts with the secular J2 term only; SGP4 adds
  the J2² and J4 secular terms (~1e-3 of the J2 rate each).
- β: the Sun's error plus the node's at each date (|∂β/∂Ω| ≤ 1), and 0.8° over the year.
- Eclipse fraction: 0.005 (30 s of a 97 min orbit). SGP4's osculating radius oscillates by
  ~±10 km (J2 short-period terms), which moves the fraction by ~0.001; the samples every 5 s
  add 0.001; Skyfield's shadow (Sun centre hidden by the Earth) is the cylinder plus a
  negligible parallax.
"""

import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from hestia_core.environment.analytic import AnalyticEnvironmentProvider
from hestia_core.environment.parameters import EnvironmentParameters
from hestia_core.mission import MissionArtifact
from hestia_core.orbits import (
    EARTH_MU_M3_PER_S2,
    EARTH_RADIUS_M,
    nodal_precession_rate,
    sso_inclination_rad,
)
from hestia_core.sun import julian_date, mean_sun_right_ascension, sun_position

CACHE = Path(os.environ.get("HESTIA_SKYFIELD_CACHE", Path.home() / ".cache/hestia/skyfield"))
ALTITUDE_M = 600e3
LTAN = "10:30"
LAUNCH = datetime(2028, 3, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def skyfield() -> Any:
    api = pytest.importorskip("skyfield.api")
    CACHE.mkdir(parents=True, exist_ok=True)
    loader = api.Loader(str(CACHE), verbose=False)
    try:
        ephemeris = loader("de421.bsp")
    except Exception as exc:  # noqa: BLE001  # any download failure means «no network»
        pytest.skip(
            f"No se pudo descargar la efeméride de421.bsp de Skyfield ({exc}): sin red, el "
            f"oráculo de β y eclipse no corre. Se guarda en {CACHE} (HESTIA_SKYFIELD_CACHE)."
        )
    return api, ephemeris, loader.timescale(builtin=True)


def _analytic() -> Any:
    mission = MissionArtifact.model_validate(
        {
            "general": {"launch_date": LAUNCH.date().isoformat(), "design_life": 365.25 * 86400},
            "orbit": {"type": "sso", "altitude": ALTITUDE_M, "ltan": LTAN},
            "envelope": {"size_x": 1, "size_y": 1, "size_z": 1, "mass": 100},
            "attitude_modes": [
                {
                    "id": "n",
                    "name": "Nadir",
                    "primary_axis": "+Z",
                    "primary_target": "nadir",
                    "secondary_axis": "+X",
                    "secondary_target": "velocity",
                }
            ],
        }
    )
    return AnalyticEnvironmentProvider().compute(mission, EnvironmentParameters())


def _satellite(api: Any, timescale: Any) -> Any:
    from sgp4.api import WGS72, Satrec  # pyright: ignore[reportMissingTypeStubs]

    a = EARTH_RADIUS_M + ALTITUDE_M
    inclination = sso_inclination_rad(ALTITUDE_M)
    hours, minutes = (int(x) for x in LTAN.split(":"))
    jd = julian_date(LAUNCH)
    raan = float(mean_sun_right_ascension(jd)) + (hours + minutes / 60 - 12) * math.pi / 12
    satrec = Satrec()
    satrec.sgp4init(
        WGS72,
        "i",
        1,
        jd - 2_433_281.5,  # days since 1949-12-31 00:00 UT
        0.0,
        0.0,
        0.0,
        1e-6,
        0.0,
        inclination,
        0.0,
        math.sqrt(EARTH_MU_M3_PER_S2 / a**3) * 60.0,  # rad/min
        raan % (2 * math.pi),
    )
    return api.EarthSatellite.from_satrec(satrec, timescale)


def _oracle_states(skyfield: Any, dates: list[datetime]) -> tuple[Any, Any, Any]:
    """SGP4 position and velocity (TEME, true equator and mean equinox of date) and the DE421
    apparent Sun (true equator and equinox of date), as unit vectors."""
    api, ephemeris, timescale = skyfield
    from skyfield.framelib import (  # pyright: ignore[reportMissingTypeStubs]
        true_equator_and_equinox_of_date,
    )

    satellite = _satellite(api, timescale)
    jd = np.array([julian_date(d) for d in dates])
    _, r, v = satellite.model.sgp4_array(np.floor(jd - 0.5) + 0.5, jd - np.floor(jd - 0.5) - 0.5)
    times = timescale.from_datetimes(dates)
    apparent = ephemeris["earth"].at(times).observe(ephemeris["sun"]).apparent()
    sun = apparent.frame_xyz(true_equator_and_equinox_of_date).km.T
    return np.asarray(r), np.asarray(v), sun / np.linalg.norm(sun, axis=-1, keepdims=True)


def test_sun_direction_over_a_year(skyfield: Any) -> None:
    # Astronomical Almanac low precision: 0.01°; plus nutation (≤ 0.005°) it ignores.
    series = _analytic().mission_series
    _, _, oracle = _oracle_states(skyfield, series.dates)
    unit, _ = sun_position(np.array([julian_date(d) for d in series.dates]))
    angle = np.degrees(np.arccos(np.clip(np.sum(unit * oracle, axis=-1), -1, 1)))
    assert float(np.max(angle)) < 0.02


def test_beta_over_a_year(skyfield: Any) -> None:
    result = _analytic()
    series = result.mission_series
    r, v, sun = _oracle_states(skyfield, series.dates)
    normal = np.cross(r, v)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    oracle_beta = np.degrees(np.arcsin(np.sum(normal * sun, axis=-1)))
    beta = np.degrees(np.array(series.beta_nominal, dtype=float))

    # Node drift: the analytic model keeps only the secular J2 term; SGP4 adds the J2² and
    # J4 secular terms, each ~1e-3 of the J2 rate (J2 (R/a)² ≈ 8e-4, J4/J2 (R/a)² ≈ 1.2e-3),
    # i.e. up to ~0.8° of node after a year (360°/year of node). Same initial node.
    oracle_node = np.degrees(np.arctan2(normal[:, 0], -normal[:, 1]))
    jd0 = julian_date(LAUNCH)
    hours, minutes = (int(x) for x in LTAN.split(":"))
    raan0 = float(mean_sun_right_ascension(jd0)) + (hours + minutes / 60 - 12) * math.pi / 12
    rate = nodal_precession_rate(EARTH_RADIUS_M + ALTITUDE_M, result.orbit.inclination)
    seconds = np.array([(d - LAUNCH).total_seconds() for d in series.dates])
    node = np.degrees(raan0 + rate * seconds)
    node_error = np.abs((oracle_node - node + 180.0) % 360.0 - 180.0)
    assert float(node_error[0]) < 0.01
    assert float(np.max(node_error)) < 0.8

    # β error: the Sun's (≤ 0.02°) plus the node's, since |∂β/∂Ω| ≤ sin i ≤ 1. Also bounded by
    # 0.8° over the year.
    error = np.abs(beta - oracle_beta)
    assert np.all(error <= 0.02 + node_error)
    assert float(np.max(error)) < 0.8


def test_eclipse_fraction_over_a_year(skyfield: Any) -> None:
    api, ephemeris, timescale = skyfield
    result = _analytic()
    series = result.mission_series
    satellite = _satellite(api, timescale)
    period = result.orbit.period
    step = 5.0
    for k in range(0, len(series.dates), 30):
        start = series.dates[k]
        moments = [start + timedelta(seconds=s) for s in np.arange(0.0, period, step)]
        sunlit = satellite.at(timescale.from_datetimes(moments)).is_sunlit(ephemeris)
        oracle = 1.0 - float(np.mean(sunlit))
        assert series.eclipse_fraction_max[k] == pytest.approx(oracle, abs=0.005), start
