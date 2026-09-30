"""Analytic environment provider: limit cases, hand calculations and consistency.

References: the closed forms are checked in test_sun, test_eclipse, test_view_factors and
test_attitude; here they are checked once assembled (ADR 0020).
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pytest

from hestia_core.eclipse import eclipse_fraction
from hestia_core.environment.analytic import (
    MAX_ECCENTRICITY,
    AnalyticEnvironmentProvider,
    beta_envelope,
    normal_for_beta,
)
from hestia_core.environment.orbit import OrbitType
from hestia_core.environment.parameters import DesignValueSource, EnvironmentParameters
from hestia_core.environment.provider import EnvironmentProvider
from hestia_core.environment.result import (
    ConditionOrigin,
    EnvironmentResult,
    FaceFluxes,
    OrbitProfile,
    RangeQuantity,
)
from hestia_core.forms import InputRejectedError, ProblemCode
from hestia_core.mission import MissionArtifact
from hestia_core.orbits import EARTH_RADIUS_M, orbital_period_s, sso_max_altitude_m
from hestia_core.sun import FloatArray, julian_date, sun_position

YEAR = 365.25 * 86_400.0
NADIR = {
    "id": "nadir",
    "name": "Apuntado nadir",
    "primary_axis": "+Z",
    "primary_target": "nadir",
    "secondary_axis": "+X",
    "secondary_target": "velocity",
}
SUN = {
    "id": "sun",
    "name": "Apuntado al Sol",
    "primary_axis": "-Z",
    "primary_target": "sun",
    "secondary_axis": "+Y",
    "secondary_target": "orbit_normal",
}


@dataclass(frozen=True)
class Case:
    """A mission window and an orbit; the attitude modes are always NADIR and SUN."""

    mission: MissionArtifact
    orbit: dict[str, Any]

    def parameters(self, **sections: Any) -> EnvironmentParameters:
        return EnvironmentParameters.model_validate(
            {"orbit": self.orbit, "attitude_modes": [NADIR, SUN], **sections}
        )


def case(orbit: dict[str, Any], life_years: float = 1.0, **general: Any) -> Case:
    mission = MissionArtifact.model_validate(
        {
            "general": {"launch_date": "2028-03-01", "design_life": life_years * YEAR, **general},
            "envelope": {"size_x": 1.0, "size_y": 1.0, "size_z": 1.0, "mass": 100.0},
        }
    )
    return Case(mission, orbit)


SSO = {"type": "sso", "altitude": 600e3, "ltan": "10:30"}
PROVIDER: EnvironmentProvider = AnalyticEnvironmentProvider()


def compute(c: Case, **parameters: Any) -> EnvironmentResult:
    return PROVIDER.compute(c.mission, c.parameters(**parameters))


def flux(result: EnvironmentResult, condition: str, mode: str, face: str) -> FaceFluxes:
    return next(
        f
        for f in result.fluxes
        if f.condition_id == condition and f.mode_id == mode and f.face.value == face
    )


def profile(result: EnvironmentResult, condition: str, mode: str) -> OrbitProfile:
    return next(
        p for p in result.orbit_profiles if p.condition_id == condition and p.mode_id == mode
    )


# ---------------------------------------------------------------- series, ranges, conditions


def test_series_cover_the_mission_window() -> None:
    result = compute(case(SSO, life_years=2))
    series = result.mission_series
    # Daily steps over 2 x 365.25 days: 731 dates, then the end of life.
    assert len(series.dates) == 732
    assert series.dates[0].isoformat() == "2028-03-01T00:00:00+00:00"
    assert (series.dates[-1] - series.dates[0]).total_seconds() == pytest.approx(2 * YEAR)
    assert all(b is not None for b in series.beta_nominal)
    assert result.provider.name == "analytic" and result.provider.version == "1"
    # Without dispersion the envelope is the nominal β.
    assert series.beta_min == pytest.approx(series.beta_nominal, abs=1e-6)  # type: ignore[arg-type]
    assert series.beta_max == pytest.approx(series.beta_nominal, abs=1e-6)  # type: ignore[arg-type]


def test_ranges_hold_perihelion_aphelion_and_design_values() -> None:
    result = compute(case(SSO, life_years=1), dispersion={"eol_altitude": 550e3})
    ranges = {r.quantity: r for r in result.ranges}
    irradiance = ranges[RangeQuantity.IRRADIANCE]
    # 1361 W/m² over 1.0167² and 0.9833² AU² (Astronomical Almanac distances).
    assert irradiance.min == pytest.approx(1316.6, abs=0.3)
    assert irradiance.max == pytest.approx(1407.6, abs=0.3)
    assert irradiance.min_note == "Afelio" and irradiance.max_note == "Perihelio"
    assert irradiance.min_at is not None and irradiance.min_at.month == 7
    altitude = ranges[RangeQuantity.ALTITUDE]
    assert (altitude.min, altitude.max) == (550e3, 600e3)
    albedo = ranges[RangeQuantity.ALBEDO]
    assert (albedo.min, albedo.max) == (0.25, 0.35)
    assert "NASA TM-2001-211221" in albedo.min_note
    olr = ranges[RangeQuantity.OLR]
    assert (olr.min, olr.max) == (218.0, 258.0)
    assert result.design_values.albedo_min.source is DesignValueSource.LIBRARY
    assert result.design_values.solar_constant.value == 1361.0


def test_extreme_and_custom_conditions() -> None:
    result = compute(
        case(SSO),
        dispersion={"eol_altitude": 550e3},
        custom_conditions=[{"id": "c1", "name": "β = 30°", "beta": math.radians(30)}],
    )
    ids = [c.id for c in result.conditions]
    assert ids == ["max_eclipse", "max_eclipse_eol", "min_eclipse", "min_eclipse_eol", "c1"]
    by_id = {c.id: c for c in result.conditions}
    series = result.mission_series
    # β of the largest eclipse is the smallest |β| of the mission; of the smallest, the largest.
    betas = np.abs(np.array(series.beta_min))
    assert abs(by_id["max_eclipse"].beta) == pytest.approx(float(np.min(betas)))
    assert abs(by_id["min_eclipse"].beta) == pytest.approx(float(np.max(betas)))
    assert by_id["max_eclipse"].eclipse_fraction >= by_id["min_eclipse"].eclipse_fraction
    # Lower altitude, longer eclipse fraction (same β).
    assert by_id["max_eclipse_eol"].eclipse_fraction > by_id["max_eclipse"].eclipse_fraction
    custom = by_id["c1"]
    assert custom.origin is ConditionOrigin.CUSTOM and custom.altitude == 600e3
    r = EARTH_RADIUS_M + 600e3
    expected = float(eclipse_fraction(math.radians(30), r, conical=False))
    assert custom.eclipse_fraction == pytest.approx(expected, abs=1e-6)
    assert custom.period == pytest.approx(orbital_period_s(r), abs=1e-3)
    assert custom.eclipse_duration == pytest.approx(expected * orbital_period_s(r), abs=0.01)
    # β = 30° never happens in this SSO (β between -29° and -11°): drawn at launch, with a note.
    assert custom.date == series.dates[0] and custom.note is not None
    assert "inclinación" in custom.note
    # Without end-of-life altitude there are only two extreme conditions.
    assert len(compute(case(SSO)).conditions) == 2


def test_custom_conditions_go_to_the_first_date_that_has_their_beta() -> None:
    # Without dispersion the envelope is the nominal line: β = -20° happens between two daily
    # samples, and the condition takes the nearer one (within one day of change of β).
    result = compute(
        case(SSO), custom_conditions=[{"id": "c", "name": "β -20°", "beta": math.radians(-20)}]
    )
    series = result.mission_series
    custom = next(c for c in result.conditions if c.id == "c")
    assert custom.note is None
    k = series.dates.index(custom.date)
    beta = np.array(series.beta_nominal, dtype=float)
    daily_change = float(np.max(np.abs(np.diff(beta))))
    assert abs(beta[k] - math.radians(-20)) <= daily_change
    earlier = beta[: max(k - 1, 0)]
    assert np.all(earlier > math.radians(-20)) or np.all(earlier < math.radians(-20))


def test_period_uses_the_semi_major_axis() -> None:
    # r_p = R + 500 km, r_a = R + 600 km (e = 0.0073): a = R + 550 km, T = 2π √(a³/μ).
    orbit = {
        "type": "keplerian",
        "perigee_altitude": 500e3,
        "apogee_altitude": 600e3,
        "inclination": 1.0,
    }
    result = compute(case(orbit))
    assert result.orbit.period == pytest.approx(orbital_period_s(EARTH_RADIUS_M + 550e3))
    assert result.conditions[0].period == pytest.approx(
        orbital_period_s(EARTH_RADIUS_M + 550e3), abs=1e-3
    )


def test_ltan_sets_the_node_against_the_sun_at_an_equinox() -> None:
    # Independent of the LTAN → node formula: at the March equinox (2028-03-20, δ ≈ 0) the
    # Sun is in the equator, so sin β = sin i sin(Ω - alpha☉) (hand calculation). LTAN 12:00
    # puts the node at the Sun: β ≈ 0. LTAN 06:00 puts it 90° west of the Sun:
    # β = -asin(sin i) = -(180° - i) ≈ -82.2° at 600 km (i = 97.8°). Tolerance 2.5°: the node
    # follows the mean Sun, which the true Sun leads by the equation of time (-7.5 min ≈ 1.9°
    # on 2028-03-20, Astronomical Almanac), plus δ ≈ 0.2° at 00:00 UTC.
    for ltan, expected in (("12:00", 0.0), ("06:00", -82.2), ("18:00", 82.2)):
        c = case({**SSO, "ltan": ltan}, launch_date="2028-03-20")
        beta = compute(c).mission_series.beta_nominal[0]
        assert beta is not None
        assert math.degrees(beta) == pytest.approx(expected, abs=2.5), ltan


def test_ltan_dispersion_widens_the_beta_envelope() -> None:
    nominal = compute(case(SSO)).mission_series
    spread = compute(case(SSO), dispersion={"ltan_dispersion": 1800}).mission_series
    assert spread.beta_nominal == nominal.beta_nominal
    low = np.array(spread.beta_min)
    high = np.array(spread.beta_max)
    beta = np.array(nominal.beta_nominal, dtype=float)
    assert np.all(low <= beta + 1e-9) and np.all(high >= beta - 1e-9)
    # ±30 min of node time is ±7.5° of node: β moves by up to ~sin(i)·7.5° ≈ 7.4°.
    assert math.degrees(float(np.max(high - low))) == pytest.approx(2 * 7.43, abs=0.3 * 2)


def test_beta_envelope_over_every_node_is_declination_plus_minus_inclination() -> None:
    # Hand calculation: sweeping every node, β ∈ [δ - i, δ + i] when |δ ± i| ≤ 90°.
    unit, _ = sun_position(julian_date(np.datetime64("2028-06-21").astype(object)))
    delta = math.asin(float(unit[2]))
    low, high = beta_envelope(unit, math.radians(40))
    assert float(low) == pytest.approx(delta - math.radians(40), abs=1e-12)
    assert float(high) == pytest.approx(delta + math.radians(40), abs=1e-12)


def test_keplerian_orbit_sweeps_the_node() -> None:
    orbit = {"type": "keplerian", "perigee_altitude": 500e3, "inclination": math.radians(51.6)}
    result = compute(case(orbit))
    assert result.orbit.raan_swept
    assert all(b is None for b in result.mission_series.beta_nominal)
    # Near the June solstice δ ≈ 23.4°: β reaches 23.4 + 51.6 = 75°.
    assert math.degrees(max(result.mission_series.beta_max)) == pytest.approx(75.0, abs=0.1)
    # |δ| < i every day: β = 0 is always possible, so the largest eclipse is at β = 0.
    assert result.conditions[0].beta == 0.0


# ---------------------------------------------------------------- limit cases


def test_beta_zero_eclipse_and_profile() -> None:
    # β = 0 at 600 km: the closed form gives f = asin(R/r)/π; the profile's shadow samples
    # agree within one sample.
    result = compute(case(SSO), custom_conditions=[{"id": "b0", "name": "β = 0", "beta": 0.0}])
    r = EARTH_RADIUS_M + 600e3
    expected = math.asin(EARTH_RADIUS_M / r) / math.pi
    condition = next(c for c in result.conditions if c.id == "b0")
    assert condition.eclipse_fraction == pytest.approx(expected, abs=1e-6)
    p = profile(result, "b0", "nadir")
    shadowed = float(np.mean(np.array(p.sunlit) < 1.0))
    assert shadowed == pytest.approx(expected, abs=1.0 / len(p.sunlit))
    # The orbit plane really has β = 0 (sun vector ⟂ orbit normal).
    h = np.cross(p.position[0], p.velocity[0])
    assert float(np.dot(h / np.linalg.norm(h), p.sun[0])) == pytest.approx(0.0, abs=1e-6)


def test_beta_above_the_critical_angle_has_no_eclipse() -> None:
    # At 600 km β* = asin(R/r) = 66.1°: at β = 80° the satellite is always in the Sun, so a
    # Sun-pointing face gets the full irradiance all the orbit and the albedo on the nadir face
    # follows the solar zenith angle.
    result = compute(
        case(SSO), custom_conditions=[{"id": "b80", "name": "β = 80°", "beta": math.radians(80)}]
    )
    condition = next(c for c in result.conditions if c.id == "b80")
    assert condition.eclipse_fraction == 0.0
    p = profile(result, "b80", "sun")
    assert min(p.sunlit) == 1.0
    sun_face = flux(result, "b80", "sun", "-Z")
    irradiance = {r.quantity: r for r in result.ranges}[RangeQuantity.IRRADIANCE]
    assert sun_face.solar.average_max == pytest.approx(irradiance.max, abs=1e-3)
    assert sun_face.solar.average_min == pytest.approx(irradiance.min, abs=1e-3)
    assert flux(result, "b80", "sun", "+Z").solar.peak_max == 0.0  # the opposite face


def test_nadir_face_ir_and_subsolar_albedo() -> None:
    # Nadir face: F = (R/r)², so IR = OLR (R/r)² all the orbit (Gilmore, ch. 2). At β = 0 the
    # satellite passes over the subsolar point: peak albedo = S a (R/r)² (cos θ = 1).
    result = compute(case(SSO), custom_conditions=[{"id": "b0", "name": "β0", "beta": 0.0}])
    r = EARTH_RADIUS_M + 600e3
    f_nadir = (EARTH_RADIUS_M / r) ** 2
    nadir = flux(result, "b0", "nadir", "+Z")
    assert nadir.ir.average_max == pytest.approx(258.0 * f_nadir, abs=1e-3)
    assert nadir.ir.average_min == pytest.approx(218.0 * f_nadir, abs=1e-3)
    irradiance = {q.quantity: q for q in result.ranges}[RangeQuantity.IRRADIANCE]
    # Samples every 3°: the peak is within 1 - cos(1.5°) of the subsolar value.
    assert nadir.albedo.peak_max == pytest.approx(irradiance.max * 0.35 * f_nadir, rel=4e-4)
    # The zenith face sees neither albedo nor IR; the nadir face never sees the Sun here.
    zenith = flux(result, "b0", "nadir", "-Z")
    assert zenith.ir.peak_max == 0.0 and zenith.albedo.peak_max == 0.0


def test_total_is_the_sum_of_the_three_fluxes() -> None:
    # Stored values are rounded to 1e-3 W/m² each: sums agree within 2e-3.
    result = compute(case(SSO))
    for f in result.fluxes:
        assert f.total.average_max == pytest.approx(
            f.solar.average_max + f.albedo.average_max + f.ir.average_max, abs=2e-3
        )
        assert f.total.peak_max <= f.solar.peak_max + f.albedo.peak_max + f.ir.peak_max + 2e-3
    for p in result.orbit_profiles:
        for face in p.faces:
            total = np.add(np.add(face.solar_max, face.albedo_max), face.ir_max)
            assert face.total_max == pytest.approx(total.tolist(), abs=2e-3)


def test_attitude_of_the_profiles() -> None:
    # The primary axis follows its direction exactly: +Z along nadir, -Z along the Sun.
    result = compute(case(SSO))
    for mode, axis, target in (("nadir", [0, 0, 1], "nadir"), ("sun", [0, 0, -1], "sun")):
        p = profile(result, "max_eclipse", mode)
        for k in range(0, len(p.time), 10):
            w, x, y, z = p.quaternion[k]
            v = np.array(axis, dtype=float)
            xyz = np.array([x, y, z])
            rotated = v + 2 * np.cross(xyz, np.cross(xyz, v) + w * v)
            expected = (
                -np.array(p.position[k]) / np.linalg.norm(p.position[k])
                if target == "nadir"
                else np.array(p.sun[k])
            )
            assert rotated == pytest.approx(expected, abs=1e-5)


def test_geo_beta_is_the_solar_declination() -> None:
    result = compute(case({"type": "geo"}), dispersion={"geo_max_inclination": 0.02})
    series = result.mission_series
    _, dates = sun_position(0.0), series.dates
    unit, _ = sun_position(np.array([julian_date(d) for d in dates]))
    declination = np.arcsin(unit[:, 2])
    assert np.array(series.beta_nominal, dtype=float) == pytest.approx(declination, abs=1e-6)
    # The envelope is the declination ± the maximum inclination.
    assert np.array(series.beta_max) == pytest.approx(declination + 0.02, abs=1e-6)
    # Eclipse seasons: about 69 min at the equinoxes, none at the solstices.
    duration = np.array(series.eclipse_duration_max) / 60
    assert float(np.max(duration)) == pytest.approx(69.4, abs=0.5)
    june = next(i for i, d in enumerate(dates) if (d.month, d.day) == (6, 21))
    assert duration[june] == 0.0
    assert result.orbit.altitude == 35_786e3 and result.orbit.eol_altitude is None


def test_sso_at_the_highest_altitude() -> None:
    # Near the highest SSO (i → 180°, retrograde equatorial) the provider still works: the
    # orbit is almost equatorial, so β ≈ -δ (the normal points south). 1 km below the limit
    # i = 178.6° (cos i varies as the square root of the distance to the limit), so β is
    # within 1.4° of -δ.
    altitude = sso_max_altitude_m() - 1e3
    result = compute(case({"type": "sso", "altitude": altitude, "ltan": "06:00"}))
    assert math.degrees(result.orbit.inclination) == pytest.approx(178.6, abs=0.1)
    series = result.mission_series
    unit, _ = sun_position(np.array([julian_date(d) for d in series.dates]))
    beta = np.array(series.beta_nominal, dtype=float)
    assert beta == pytest.approx(-np.arcsin(unit[:, 2]), abs=math.radians(1.4))
    assert all(math.isfinite(f.total.average_max) for f in result.fluxes)


def test_eccentric_orbits_are_rejected() -> None:
    near = {"type": "keplerian", "perigee_altitude": 500e3, "apogee_altitude": 600e3}
    compute(case({**near, "inclination": 1.0}))  # e = 0.0073: accepted
    far = {**near, "apogee_altitude": 700e3, "inclination": 1.0}  # e = 0.0145
    with pytest.raises(InputRejectedError) as raised:
        compute(case(far))
    (problem,) = raised.value.problems
    assert problem.code is ProblemCode.ECCENTRICITY_OUT_OF_RANGE
    assert str(MAX_ECCENTRICITY) in problem.message


def test_a_tiny_mission_step_is_rejected() -> None:
    with pytest.raises(InputRejectedError) as raised:
        compute(case(SSO, life_years=10), sampling={"mission_step": 60.0})
    assert raised.value.problems[0].path == "sampling.mission_step"


def test_same_inputs_same_result() -> None:
    c = case(SSO)
    assert compute(c) == compute(c)


def test_normal_for_beta_keeps_the_mission_inclination_when_possible() -> None:
    unit, _ = sun_position(2_462_000.5)
    for beta in (-0.5, 0.0, 0.3):
        normal = normal_for_beta(unit, beta, math.radians(98), raan_ref=1.0)
        assert math.asin(float(np.dot(normal, unit))) == pytest.approx(beta, abs=1e-9)
        assert math.acos(float(normal[2])) == pytest.approx(math.radians(98), abs=1e-9)
    # Equatorial orbit: only β = δ is possible; any other β tilts the normal.
    normal = normal_for_beta(unit, 0.1, 0.0, raan_ref=None)
    assert math.asin(float(np.dot(normal, unit))) == pytest.approx(0.1, abs=1e-9)
    assert OrbitType.GEO.value == "geo"


# ---------------------------------------------------------------- preview (ADR 0023)


def rotate(quaternion: list[float], vector: FloatArray) -> FloatArray:
    """Body → inertial rotation of ``vector`` by a unit quaternion ``[w, x, y, z]``."""
    w, xyz = quaternion[0], np.asarray(quaternion[1:])
    return vector + 2 * np.cross(xyz, np.cross(xyz, vector) + w * vector)


def test_preview_matches_the_nominal_series_of_the_result() -> None:
    # The preview draws the nominal orbit that the result's series describe: same β on the same
    # date (launch and 100 days later), for SSO and GEO.
    for orbit in (SSO, {"type": "geo"}):
        c = case(orbit)
        series = compute(c).mission_series
        for days in (0, 100):
            on = date(2028, 3, 1) + timedelta(days=days)
            preview = PROVIDER.preview(c.mission, c.parameters(), on, None)
            assert preview.date.date() == on and preview.node_assumed is False
            assert preview.beta == pytest.approx(series.beta_nominal[days], abs=1e-6)


def test_preview_of_leo_draws_node_zero_within_the_envelope() -> None:
    c = case({"type": "keplerian", "perigee_altitude": 500e3, "inclination": math.radians(51.6)})
    series = compute(c).mission_series
    preview = PROVIDER.preview(c.mission, c.parameters(), None, None)
    assert preview.node_assumed is True
    assert preview.date.date() == date(2028, 3, 1)  # the launch date by default
    assert series.beta_min[0] - 1e-9 <= preview.beta <= series.beta_max[0] + 1e-9
    # Node 0: the normal is (0, -sin i, cos i), so sin β = ŝ · ĥ (hand calculation).
    sun = np.asarray(preview.sun[0])
    i = math.radians(51.6)
    assert math.sin(preview.beta) == pytest.approx(-sun[1] * math.sin(i) + sun[2] * math.cos(i))


def test_preview_orbit_and_eclipse() -> None:
    c = case(SSO)
    preview = PROVIDER.preview(c.mission, c.parameters(sampling={"orbit_samples": 72}), None, None)
    radius = EARTH_RADIUS_M + 600e3
    assert len(preview.time) == 72
    # Positions are stored rounded to 0.1 m per component: the radius holds within 0.2 m.
    assert np.linalg.norm(preview.position, axis=1) == pytest.approx(radius, abs=0.2)
    assert preview.period == pytest.approx(orbital_period_s(radius), abs=1e-3)
    fraction = eclipse_fraction(preview.beta, radius, False, 1.0)
    assert preview.eclipse_fraction == pytest.approx(float(fraction), abs=2e-3)  # 1 AU vs r(t)
    # The duration is stored rounded to 0.01 s.
    assert preview.eclipse_duration == pytest.approx(
        preview.eclipse_fraction * preview.period, abs=0.01
    )
    assert preview.inclination == pytest.approx(compute(c).orbit.inclination)


def test_preview_attitude_of_the_chosen_mode() -> None:
    c = case(SSO)
    parameters = c.parameters()
    first = PROVIDER.preview(c.mission, parameters, None, None)
    assert first.mode_id == "nadir"
    sun_pointing = PROVIDER.preview(c.mission, parameters, None, "sun")
    assert sun_pointing.mode_id == "sun"
    assert sun_pointing.quaternion is not None
    for q, sun in zip(sun_pointing.quaternion, sun_pointing.sun, strict=True):
        # The primary pair of SUN: body -Z points at the Sun.
        assert rotate(q, np.array([0.0, 0.0, -1.0])) == pytest.approx(sun, abs=1e-6)


def test_preview_skips_incomplete_modes_and_draws_without_attitude() -> None:
    c = case(SSO)
    draft = c.parameters(attitude_modes=[{"name": "A medias", "primary_axis": "+Z"}, NADIR])
    preview = PROVIDER.preview(c.mission, draft, None, None)
    assert preview.mode_id == "nadir"
    assert [(m.id, m.name) for m in preview.attitude_modes] == [("nadir", "Apuntado nadir")]
    bare = PROVIDER.preview(c.mission, c.parameters(attitude_modes=[]), None, "nadir")
    assert bare.mode_id is None and bare.quaternion is None


def test_preview_rejects_what_the_result_rejects() -> None:
    far = {"type": "keplerian", "perigee_altitude": 500e3, "apogee_altitude": 700e3}
    c = case({**far, "inclination": 1.0})
    with pytest.raises(InputRejectedError) as raised:
        PROVIDER.preview(c.mission, c.parameters(), None, None)
    assert raised.value.problems[0].path == "orbit.apogee_altitude"
