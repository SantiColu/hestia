"""Analytic environment provider (ADR 0020): closed-form geometry, no propagation.

Envelope: geocentric circular (or near-circular, e <= ``MAX_ECCENTRICITY``) orbits without
thrust. Outside it, ``InputRejectedError`` with ``eccentricity_out_of_range``.

Model (``docs/etapas/environment.md``, «Qué calcula»):

- Sun: low-precision Astronomical Almanac position and distance (``hestia_core.sun``); the
  irradiance of each date is ``S / r²``.
- Orbital plane: SSO follows the mean Sun from its LTAN, drifting with the J2 nodal rate
  (``orbits.nodal_precession_rate``, equal to the mean motion of the Sun); the LTAN dispersion
  widens the node to ``±Δ``. LEO/MEO (``keplerian``): the orbit fixes no node, so β is the
  envelope over every node. GEO: equatorial (nominal β = solar declination), up to
  ``geo_max_inclination`` with any node.
- β: ``sin β = ĥ · ŝ``; over an interval of nodes it is ``A sin(Ω - alpha☉) + C`` with
  ``A = sin i cos δ☉`` and ``C = cos i sin δ☉``, so its extremes are closed-form.
- Eclipse: cylindrical or conical shadow (``hestia_core.eclipse``) on the circular orbit.
- Attitude: body frame from the two axis → direction pairs (``hestia_core.attitude``).
- Fluxes on each face: direct solar ``S nu max(0, n·ŝ)`` (nu the visible part of the Sun),
  albedo ``S a F max(0, r̂·ŝ)`` (F the plate-to-Earth view factor, the cosine the solar zenith
  angle at the subsatellite point, zero on the night side) and Earth IR ``OLR F``.

Conditions, not cases: the extreme conditions are the β of largest and of smallest eclipse
at the nominal and end-of-life altitudes; each flux is given at its minimum and maximum
design values. The Sun is fixed during one orbit.
"""

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np
from numpy.typing import NDArray

from hestia_core.attitude import AXIS_VECTORS, quaternion_from_matrix, target_directions, triad
from hestia_core.eclipse import eclipse_fraction, visible_sun_fraction
from hestia_core.environment.orbit import (
    AttitudeMode,
    Axis,
    OrbitType,
    Target,
    nominal_altitude_m,
    nominal_inclination_rad,
    validate_attitude_modes,
)
from hestia_core.environment.parameters import (
    DEFAULT_ORBIT_SAMPLES,
    MAX_ORBIT_SAMPLES,
    MIN_ORBIT_SAMPLES,
    EclipseModel,
    EnvironmentParameters,
    ResolvedDesignValue,
    ResolvedDesignValues,
    resolve_design_values,
)
from hestia_core.environment.result import (
    AttitudeModeRef,
    Condition,
    ConditionOrigin,
    DesignValue,
    DesignValuesUsed,
    EnvironmentResult,
    FaceFluxes,
    FaceProfile,
    FluxStats,
    MissionSeries,
    OrbitPreview,
    OrbitProfile,
    OrbitSummary,
    ProviderInfo,
    RangeEntry,
    RangeQuantity,
)
from hestia_core.forms import InputRejectedError, Problem, ProblemCode, Problems
from hestia_core.mission import Face, MissionArtifact
from hestia_core.orbits import (
    EARTH_MU_M3_PER_S2,
    EARTH_RADIUS_M,
    eccentricity,
    nodal_precession_rate,
    orbital_period_s,
)
from hestia_core.sun import (
    SECONDS_PER_DAY,
    FloatArray,
    earth_rotation_angle,
    julian_date,
    mean_sun_right_ascension,
    solar_irradiance,
    sun_position,
)
from hestia_core.view_factors import plate_to_earth_view_factor

PROVIDER_NAME = "analytic"
PROVIDER_VERSION = "1"
"""Bump whenever the same inputs would give a different result."""

MAX_ECCENTRICITY = 0.01
"""*(propuesta)* Envelope of the circular model (ADR 0020). Pending a definitive threshold."""
MAX_SERIES_POINTS = 200_000
"""Guard against a mission step so small the series would not fit in the project file."""

_TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------- orbital plane


def orbit_normal(raan_rad: float | FloatArray, inclination_rad: float) -> FloatArray:
    """Unit orbit normal ``(sin i sin Ω, -sin i cos Ω, cos i)`` for node(s) Ω."""
    raan = np.asarray(raan_rad, dtype=np.float64)
    s = math.sin(inclination_rad)
    return np.stack(
        [s * np.sin(raan), -s * np.cos(raan), np.full_like(raan, math.cos(inclination_rad))],
        axis=-1,
    )


def beta_angle(normal: FloatArray, sun_unit: FloatArray) -> FloatArray:
    """β = asin(ĥ · ŝ), rad; positive with the Sun on the side of the orbit normal."""
    return np.arcsin(np.clip(np.sum(normal * sun_unit, axis=-1), -1.0, 1.0))


def _sun_angles(sun_unit: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Right ascension and declination of the Sun (rad)."""
    return np.arctan2(sun_unit[..., 1], sun_unit[..., 0]), np.arcsin(
        np.clip(sun_unit[..., 2], -1.0, 1.0)
    )


def beta_envelope(
    sun_unit: FloatArray,
    inclination_rad: float,
    raan_low: FloatArray | None = None,
    raan_high: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Minimum and maximum β over nodes in ``[raan_low, raan_high]`` (every node if None).

    ``sin β(Ω) = A sin(Ω - alpha) + C`` with ``A = sin i cos δ`` and ``C = cos i sin δ``
    (alpha, δ the Sun's right ascension and declination): the extremes are at the ends of
    the interval or at ``Ω = alpha ± π/2`` when inside it. Over every node,
    ``β ∈ [asin(C - A), asin(C + A)]``.
    """
    alpha, delta = _sun_angles(sun_unit)
    a = math.sin(inclination_rad) * np.cos(delta)
    c = math.cos(inclination_rad) * np.sin(delta)
    if raan_low is None or raan_high is None:
        low, high = c - a, c + a
    else:
        width = raan_high - raan_low
        ends = [a * np.sin(raan_low - alpha) + c, a * np.sin(raan_high - alpha) + c]
        low = np.minimum(ends[0], ends[1])
        high = np.maximum(ends[0], ends[1])
        crest = np.mod(alpha + math.pi / 2 - raan_low, _TWO_PI) <= width
        trough = np.mod(alpha - math.pi / 2 - raan_low, _TWO_PI) <= width
        high = np.where(crest, c + a, high)
        low = np.where(trough, c - a, low)
    return np.arcsin(np.clip(low, -1.0, 1.0)), np.arcsin(np.clip(high, -1.0, 1.0))


def normal_for_beta(
    sun_unit: FloatArray,
    beta_rad: float,
    inclination_rad: float,
    raan_ref: float | None,
) -> FloatArray:
    """An orbit normal with inclination ``inclination_rad`` whose β is ``beta_rad``.

    Solves ``sin(Ω - alpha) = (sin β - cos i sin δ) / (sin i cos δ)`` and keeps the node nearest
    ``raan_ref``. If no node of that inclination gives β (e.g. equatorial orbit, custom β), the
    normal closest to that of ``raan_ref`` is tilted to β about the Sun direction.
    """
    alpha, delta = (float(x) for x in _sun_angles(sun_unit))
    sin_i = math.sin(inclination_rad)
    denominator = sin_i * math.cos(delta)
    if abs(denominator) > 1e-9:
        k = (math.sin(beta_rad) - math.cos(inclination_rad) * math.sin(delta)) / denominator
        if abs(k) <= 1.0 + 1e-9:
            k = max(-1.0, min(1.0, k))
            candidates = [alpha + math.asin(k), alpha + math.pi - math.asin(k)]
            if raan_ref is not None:
                candidates.sort(key=lambda raan: abs(math.remainder(raan - raan_ref, _TWO_PI)))
            return orbit_normal(candidates[0], inclination_rad)
    reference = orbit_normal(raan_ref if raan_ref is not None else alpha, inclination_rad)
    across = reference - float(np.dot(reference, sun_unit)) * sun_unit
    norm = float(np.linalg.norm(across))
    if norm < 1e-9:  # reference along the Sun: any perpendicular direction
        helper = np.array([0.0, 0.0, 1.0]) if abs(sun_unit[2]) < 0.9 else np.array([1.0, 0, 0])
        across = np.cross(sun_unit, helper)
        norm = float(np.linalg.norm(across))
    return math.sin(beta_rad) * sun_unit + math.cos(beta_rad) * across / norm


# ---------------------------------------------------------------- provider


@dataclass(frozen=True)
class _Orbit:
    type: OrbitType
    epoch: datetime
    """Launch, 00:00 UTC: start of the mission window."""
    inclination: float
    """Nominal inclination (rad)."""
    solve_inclination: float
    """Inclination used to place the orbit of a condition (GEO: the maximum)."""
    altitude: float
    eol_altitude: float | None
    eccentricity: float
    semi_major_axis: float
    """m. Sets the nominal period (with an apogee it is above the perigee radius)."""
    raan0: float | None
    """SSO: node at the launch epoch."""
    raan_rate: float
    raan_dispersion: float
    """SSO: ± node spread from the LTAN dispersion (rad)."""
    geo_max_inclination: float


@dataclass(frozen=True)
class _Extreme:
    beta: float
    date_index: int


class AnalyticEnvironmentProvider:
    """Environment provider with closed-form geometry (ADR 0020)."""

    name = PROVIDER_NAME
    version = PROVIDER_VERSION

    def compute(
        self, mission: MissionArtifact, parameters: EnvironmentParameters
    ) -> EnvironmentResult:
        orbit = _orbit(mission, parameters)
        values = resolve_design_values(parameters.design_values, orbit.inclination)
        conical = parameters.sampling.eclipse_model is EclipseModel.CONICAL
        assert mission.general.design_life is not None
        assert parameters.sampling.mission_step is not None
        epoch = orbit.epoch
        seconds = _mission_times(mission.general.design_life, parameters.sampling.mission_step)
        dates = [epoch + timedelta(seconds=float(s)) for s in seconds]
        jd = julian_date(epoch) + seconds / SECONDS_PER_DAY
        sun, distance = sun_position(jd)
        irradiance = solar_irradiance(values.solar_constant.value, distance)

        # β along the mission: nominal and envelope.
        beta_nominal: FloatArray | None = None
        if orbit.type is OrbitType.SSO:
            assert orbit.raan0 is not None
            raan = orbit.raan0 + orbit.raan_rate * seconds
            beta_nominal = beta_angle(orbit_normal(raan, orbit.inclination), sun)
            beta_min, beta_max = beta_envelope(
                sun,
                orbit.inclination,
                raan - orbit.raan_dispersion,
                raan + orbit.raan_dispersion,
            )
        elif orbit.type is OrbitType.GEO:
            beta_nominal = beta_angle(np.array([0.0, 0.0, 1.0]), sun)
            beta_min, beta_max = beta_envelope(sun, orbit.geo_max_inclination)
        else:
            beta_min, beta_max = beta_envelope(sun, orbit.inclination)

        # Eclipse along the mission: over the |β| extremes of the envelope and the altitudes.
        crosses = (beta_min <= 0) & (beta_max >= 0)
        abs_low = np.where(crosses, 0.0, np.minimum(np.abs(beta_min), np.abs(beta_max)))
        abs_high = np.maximum(np.abs(beta_min), np.abs(beta_max))
        altitudes = _altitudes(orbit)
        fractions: list[FloatArray] = []
        durations: list[FloatArray] = []
        for altitude in altitudes:
            radius = EARTH_RADIUS_M + altitude
            period = _period(orbit, altitude)
            for beta in (abs_low, abs_high):
                fraction = eclipse_fraction(beta, radius, conical, distance)
                fractions.append(fraction)
                durations.append(fraction * period)
        series = MissionSeries(
            dates=dates,
            beta_nominal=_optional_list(beta_nominal, len(dates)),
            beta_min=_round(beta_min, 7),
            beta_max=_round(beta_max, 7),
            eclipse_fraction_min=_round(np.min(fractions, axis=0), 6),
            eclipse_fraction_max=_round(np.max(fractions, axis=0), 6),
            eclipse_duration_min=_round(np.min(durations, axis=0), 2),
            eclipse_duration_max=_round(np.max(durations, axis=0), 2),
            irradiance=_round(irradiance, 3),
        )

        largest_eclipse, smallest_eclipse = _beta_extremes(beta_min, beta_max, crosses)
        irradiance_min = float(np.min(irradiance))
        irradiance_max = float(np.max(irradiance))
        ranges = _ranges(orbit, values, dates, irradiance, beta_min, beta_max)
        conditions = _conditions(
            orbit,
            parameters,
            dates,
            (sun, distance),
            (beta_min, beta_max),
            conical,
            (largest_eclipse, smallest_eclipse),
        )
        modes = [
            (mode, _mode_id(mode, i), mode.name or f"Modo {i + 1}")
            for i, mode in enumerate(parameters.attitude_modes)
        ]
        fluxes: list[FaceFluxes] = []
        profiles: list[OrbitProfile] = []
        for condition in conditions:
            for mode, mode_id, _ in modes:
                profile = _profile(
                    orbit,
                    condition,
                    mode,
                    mode_id,
                    parameters.sampling.orbit_samples or DEFAULT_ORBIT_SAMPLES,
                    conical,
                    values,
                    irradiance_min,
                    irradiance_max,
                )
                profiles.append(profile)
                fluxes.extend(_face_fluxes(profile))

        return EnvironmentResult(
            provider=ProviderInfo(name=self.name, version=self.version),
            design_values=DesignValuesUsed(
                solar_constant=_used(values.solar_constant),
                albedo_min=_used(values.albedo_min),
                albedo_max=_used(values.albedo_max),
                olr_min=_used(values.olr_min),
                olr_max=_used(values.olr_max),
            ),
            orbit=OrbitSummary(
                type=orbit.type,
                inclination=orbit.inclination,
                altitude=orbit.altitude,
                eol_altitude=orbit.eol_altitude,
                eccentricity=orbit.eccentricity,
                period=_period(orbit, orbit.altitude),
                raan_swept=orbit.type is not OrbitType.SSO
                and not (orbit.type is OrbitType.GEO and orbit.geo_max_inclination == 0),
                eclipse_model=EclipseModel.CONICAL if conical else EclipseModel.CYLINDRICAL,
            ),
            mission_series=series,
            ranges=ranges,
            conditions=conditions,
            attitude_modes=[AttitudeModeRef(id=mode_id, name=name) for _, mode_id, name in modes],
            faces=list(Face),
            fluxes=fluxes,
            orbit_profiles=profiles,
        )

    def preview(
        self,
        mission: MissionArtifact,
        parameters: EnvironmentParameters,
        on: date | None,
        mode_id: str | None,
    ) -> OrbitPreview:
        orbit = _orbit(mission, parameters)
        when = _midnight(on) if on is not None else orbit.epoch
        sun, distance = sun_position(julian_date(when))
        if orbit.type is OrbitType.GEO:
            normal = np.array([0.0, 0.0, 1.0])
        else:
            raan = _raan_at(orbit, when)
            normal = orbit_normal(raan if raan is not None else 0.0, orbit.inclination)
        beta = float(beta_angle(normal, sun))
        conical = parameters.sampling.eclipse_model is EclipseModel.CONICAL
        samples = parameters.sampling.orbit_samples
        if samples is None or not MIN_ORBIT_SAMPLES <= samples <= MAX_ORBIT_SAMPLES:
            samples = DEFAULT_ORBIT_SAMPLES
        track = _track(normal, orbit.altitude, when, samples, conical)
        fraction = float(eclipse_fraction(beta, track.radius, conical, float(distance)))
        drawable = _drawable_modes(parameters.attitude_modes)
        chosen = next((m for m in drawable if m[0] == mode_id), drawable[0] if drawable else None)
        quaternion = None
        if chosen is not None:
            matrix = _body_to_inertial(track, chosen[1])
            quaternion = np.round(quaternion_from_matrix(matrix), 7).tolist()
        return OrbitPreview.model_validate(
            {
                **_track_fields(track),
                "orbit_type": orbit.type,
                "date": when,
                "beta": beta,
                "inclination": orbit.inclination,
                "altitude": orbit.altitude,
                "eclipse_fraction": round(fraction, 6),
                "eclipse_duration": round(fraction * _period(orbit, orbit.altitude), 2),
                "node_assumed": orbit.type is OrbitType.KEPLERIAN,
                "attitude_modes": [
                    AttitudeModeRef(id=mode_id, name=mode.name or mode_id)
                    for mode_id, mode in drawable
                ],
                "mode_id": chosen[0] if chosen is not None else None,
                "quaternion": quaternion,
            }
        )


def _mode_id(mode: AttitudeMode, index: int) -> str:
    """Id of an attitude mode in the result: its own, or a positional one for an unapplied
    draft."""
    return mode.id or f"mode_{index + 1}"


def _drawable_modes(modes: list[AttitudeMode]) -> list[tuple[str, AttitudeMode]]:
    """The complete and consistent attitude modes, with the id the result gives them."""

    def drawable(mode: AttitudeMode) -> bool:
        p = Problems()
        validate_attitude_modes(p, [mode])
        return not p.items

    return [(_mode_id(mode, i), mode) for i, mode in enumerate(modes) if drawable(mode)]


# ---------------------------------------------------------------- inputs


def _orbit(mission: MissionArtifact, parameters: EnvironmentParameters) -> _Orbit:
    orbit = parameters.orbit
    assert orbit.type is not None and mission.general.launch_date is not None
    epoch = _midnight(mission.general.launch_date)
    altitude = nominal_altitude_m(orbit)
    inclination = nominal_inclination_rad(orbit)
    assert altitude is not None and inclination is not None
    e = 0.0
    if orbit.type is OrbitType.KEPLERIAN and orbit.apogee_altitude is not None:
        e = eccentricity(altitude, orbit.apogee_altitude)
    if e > MAX_ECCENTRICITY:
        raise InputRejectedError(
            [
                Problem(
                    path="orbit.apogee_altitude",
                    code=ProblemCode.ECCENTRICITY_OUT_OF_RANGE,
                    message=f"La órbita tiene excentricidad {e:.4f}: el proveedor analítico "
                    f"solo admite órbitas casi circulares (e ≤ {MAX_ECCENTRICITY}).",
                )
            ]
        )
    dispersion = parameters.dispersion
    raan0: float | None = None
    raan_rate = 0.0
    raan_dispersion = 0.0
    if orbit.type is OrbitType.SSO:
        assert orbit.ltan is not None
        hours, minutes = (int(part) for part in orbit.ltan.split(":"))
        ltan_h = hours + minutes / 60
        jd0 = julian_date(epoch)
        # Local mean time of the node = 12 h + (Ω - alpha_mean☉) / 15°/h.
        raan0 = float(mean_sun_right_ascension(jd0)) + (ltan_h - 12.0) * math.pi / 12.0
        raan_rate = nodal_precession_rate(EARTH_RADIUS_M + altitude, inclination)
        raan_dispersion = (dispersion.ltan_dispersion or 0.0) * _TWO_PI / SECONDS_PER_DAY
    geo_max = 0.0
    if orbit.type is OrbitType.GEO and dispersion.geo_max_inclination is not None:
        geo_max = dispersion.geo_max_inclination
    return _Orbit(
        type=orbit.type,
        epoch=epoch,
        inclination=inclination,
        solve_inclination=geo_max if orbit.type is OrbitType.GEO else inclination,
        altitude=altitude,
        eol_altitude=dispersion.eol_altitude if orbit.type is not OrbitType.GEO else None,
        eccentricity=e,
        semi_major_axis=EARTH_RADIUS_M
        + (
            (altitude + orbit.apogee_altitude) / 2
            if orbit.type is OrbitType.KEPLERIAN and orbit.apogee_altitude is not None
            else altitude
        ),
        raan0=raan0,
        raan_rate=raan_rate,
        raan_dispersion=raan_dispersion,
        geo_max_inclination=geo_max,
    )


def _midnight(day: date) -> datetime:
    """00:00 UTC of a day: the launch epoch and the date of a preview."""
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC)


def _raan_at(orbit: _Orbit, when: datetime) -> float | None:
    """SSO: the nominal node at ``when``, drifting from the launch node. None otherwise."""
    if orbit.raan0 is None:
        return None
    return orbit.raan0 + orbit.raan_rate * (when - orbit.epoch).total_seconds()


def _mission_times(design_life_s: float, step_s: float) -> FloatArray:
    """Seconds from launch: every ``step_s`` and the end of life."""
    count = math.floor(design_life_s / step_s + 1e-9) + 1
    if count > MAX_SERIES_POINTS:
        raise InputRejectedError(
            [
                Problem(
                    path="sampling.mission_step",
                    code=ProblemCode.MAX,
                    message=f"Con este paso la serie tendría {count} puntos; el máximo es "
                    f"{MAX_SERIES_POINTS}. Usá un paso más grande.",
                )
            ]
        )
    times = np.arange(count, dtype=np.float64) * step_s
    if design_life_s - times[-1] > 1e-6:
        times = np.append(times, design_life_s)
    return times


def _period(orbit: _Orbit, altitude: float) -> float:
    """Period at an altitude: the nominal one uses the semi-major axis of the mission's orbit;
    the others (end of life, custom) are circular."""
    if altitude == orbit.altitude:
        return orbital_period_s(orbit.semi_major_axis)
    return orbital_period_s(EARTH_RADIUS_M + altitude)


def _altitudes(orbit: _Orbit) -> list[float]:
    if orbit.eol_altitude is None or orbit.eol_altitude == orbit.altitude:
        return [orbit.altitude]
    return [orbit.altitude, orbit.eol_altitude]


# ---------------------------------------------------------------- extremes and ranges


def _beta_extremes(
    beta_min: FloatArray, beta_max: FloatArray, crosses: NDArray[np.bool_]
) -> tuple[_Extreme, _Extreme]:
    """β of the largest eclipse (smallest |β|) and of the smallest eclipse (largest |β|).

    The envelope is continuous in time, so if its overall range holds 0, β = 0 happens.
    """
    low, high = float(np.min(beta_min)), float(np.max(beta_max))
    if low <= 0 <= high:
        nearest = np.where(crosses, 0.0, np.minimum(np.abs(beta_min), np.abs(beta_max)))
        largest = _Extreme(0.0, int(np.argmin(nearest)))
    elif low > 0:
        largest = _Extreme(low, int(np.argmin(beta_min)))
    else:
        largest = _Extreme(high, int(np.argmax(beta_max)))
    if abs(high) >= abs(low):
        smallest = _Extreme(high, int(np.argmax(beta_max)))
    else:
        smallest = _Extreme(low, int(np.argmin(beta_min)))
    return largest, smallest


def _ranges(
    orbit: _Orbit,
    values: ResolvedDesignValues,
    dates: list[datetime],
    irradiance: FloatArray,
    beta_min: FloatArray,
    beta_max: FloatArray,
) -> list[RangeEntry]:
    last = len(dates) - 1

    def when(index: int, inner: str) -> str:
        return inner if 0 < index < last else "Borde de la ventana de la misión"

    i_min, i_max = int(np.argmin(irradiance)), int(np.argmax(irradiance))
    b_min, b_max = int(np.argmin(beta_min)), int(np.argmax(beta_max))
    beta_note = {
        OrbitType.SSO: "Nodo nominal con la deriva de la hora del nodo",
        OrbitType.KEPLERIAN: "Barrido completo del nodo",
        OrbitType.GEO: "Ecuatorial, o inclinada hasta la inclinación máxima",
    }[orbit.type]
    eol = orbit.eol_altitude
    return [
        RangeEntry(
            quantity=RangeQuantity.IRRADIANCE,
            unit="W/m²",
            min=round(float(irradiance[i_min]), 3),
            max=round(float(irradiance[i_max]), 3),
            min_at=dates[i_min],
            max_at=dates[i_max],
            min_note=when(i_min, "Afelio"),
            max_note=when(i_max, "Perihelio"),
        ),
        RangeEntry(
            quantity=RangeQuantity.BETA,
            unit="rad",
            min=float(beta_min[b_min]),
            max=float(beta_max[b_max]),
            min_at=dates[b_min],
            max_at=dates[b_max],
            min_note=beta_note,
            max_note=beta_note,
        ),
        RangeEntry(
            quantity=RangeQuantity.ALTITUDE,
            unit="m",
            min=eol if eol is not None else orbit.altitude,
            max=orbit.altitude,
            min_note="Fin de vida (decaimiento)" if eol is not None else "Nominal, sin decaimiento",
            max_note="Nominal",
        ),
        _design_range(RangeQuantity.ALBEDO, "", values.albedo_min, values.albedo_max),
        _design_range(RangeQuantity.OLR, "W/m²", values.olr_min, values.olr_max),
    ]


def _note(value: ResolvedDesignValue) -> str:
    return value.reference or "Valor de diseño ingresado"


def _design_range(
    quantity: RangeQuantity, unit: str, low: ResolvedDesignValue, high: ResolvedDesignValue
) -> RangeEntry:
    return RangeEntry(
        quantity=quantity,
        unit=unit,
        min=low.value,
        max=high.value,
        min_note=_note(low),
        max_note=_note(high),
    )


def _deg(beta: float) -> str:
    return f"{math.degrees(beta):.1f}°"


def _conditions(
    orbit: _Orbit,
    parameters: EnvironmentParameters,
    dates: list[datetime],
    sun: tuple[FloatArray, FloatArray],
    envelope: tuple[FloatArray, FloatArray],
    conical: bool,
    extremes: tuple[_Extreme, _Extreme],
) -> list[Condition]:
    """Extreme conditions (β of largest and smallest eclipse x nominal and end-of-life
    altitude, without repeats) and then the custom ones.

    A custom condition is placed at the first date whose β envelope holds its β (the launch
    date if none does, with a note saying how its orbit is drawn).
    """
    sun_unit, distance = sun
    beta_min, beta_max = envelope
    largest, smallest = extremes
    altitudes = [(orbit.altitude, "", "altitud nominal")]
    if orbit.eol_altitude is not None and orbit.eol_altitude != orbit.altitude:
        altitudes.append((orbit.eol_altitude, "_eol", "fin de vida"))
    geometries = [(largest, "max_eclipse", "Eclipse máximo")]
    if smallest.beta != largest.beta:
        geometries.append((smallest, "min_eclipse", "Eclipse mínimo"))

    def condition(
        cid: str,
        name: str,
        origin: ConditionOrigin,
        beta: float,
        altitude: float,
        index: int,
        note: str | None = None,
    ) -> Condition:
        radius = EARTH_RADIUS_M + altitude
        period = _period(orbit, altitude)
        fraction = float(eclipse_fraction(beta, radius, conical, float(distance[index])))
        return Condition(
            id=cid,
            name=name,
            origin=origin,
            beta=beta,
            altitude=altitude,
            date=dates[index],
            period=round(period, 3),
            eclipse_fraction=round(fraction, 6),
            eclipse_duration=round(fraction * period, 2),
            note=note,
        )

    result: list[Condition] = []
    for extreme, cid, label in geometries:
        for altitude, suffix, altitude_label in altitudes:
            result.append(
                condition(
                    f"{cid}{suffix}",
                    f"{label} · β {_deg(extreme.beta)} · {altitude_label}",
                    ConditionOrigin.EXTREME,
                    extreme.beta,
                    altitude,
                    extreme.date_index,
                )
            )
    tolerance = 1e-9
    for i, custom in enumerate(parameters.custom_conditions):
        assert custom.beta is not None
        index = _first_date_with(custom.beta, beta_min, beta_max)
        note = None
        if index is None:
            index = 0
            low, high = beta_envelope(sun_unit[index], orbit.solve_inclination)
            if float(low) - tolerance <= custom.beta <= float(high) + tolerance:
                note = (
                    "El β no ocurre en la misión: se dibuja con otro nodo de la misma "
                    "inclinación, en la fecha de lanzamiento."
                )
            else:
                note = (
                    "Ninguna órbita con esta inclinación tiene este β: se dibuja con el "
                    "plano inclinado hasta alcanzarlo, en la fecha de lanzamiento."
                )
        result.append(
            condition(
                custom.id or f"custom_{i + 1}",
                custom.name or f"Condición {i + 1}",
                ConditionOrigin.CUSTOM,
                custom.beta,
                custom.altitude if custom.altitude is not None else orbit.altitude,
                index,
                note,
            )
        )
    return result


def _first_date_with(beta: float, beta_min: FloatArray, beta_max: FloatArray) -> int | None:
    """First date whose β envelope holds ``beta``, or None. The envelope is continuous in time,
    so a β between two consecutive samples happens between them: the nearer one is taken."""
    tolerance = 1e-9

    def distance(k: int) -> float:
        return max(float(beta_min[k]) - beta, beta - float(beta_max[k]), 0.0)

    if beta_min.size == 1:
        return 0 if distance(0) <= tolerance else None
    low = np.minimum(beta_min[:-1], beta_min[1:])
    high = np.maximum(beta_max[:-1], beta_max[1:])
    crossing = np.flatnonzero((low - tolerance <= beta) & (beta <= high + tolerance))
    if not crossing.size:
        return None
    k = int(crossing[0])
    return k if distance(k) <= distance(k + 1) else k + 1


# ---------------------------------------------------------------- orbit profiles and fluxes


@dataclass(frozen=True)
class _Track:
    """One circular orbit sampled uniformly from the ascending node, the Sun fixed."""

    epoch: datetime
    radius: float
    mean_motion: float
    time: FloatArray
    position: FloatArray
    velocity: FloatArray
    sun: FloatArray
    """Unit vector to the Sun at each sample."""
    sunlit: FloatArray

    @property
    def r_hat(self) -> FloatArray:
        return self.position / self.radius


def _track(
    normal: FloatArray, altitude: float, epoch: datetime, samples: int, conical: bool
) -> _Track:
    """Sample the circular orbit of plane ``normal`` at ``altitude`` from its ascending node."""
    sun, distance_au = sun_position(julian_date(epoch))
    node = np.cross(np.array([0.0, 0.0, 1.0]), normal)
    if np.linalg.norm(node) < 1e-9:
        node = np.array([1.0, 0.0, 0.0])
    x_axis = node / np.linalg.norm(node)
    y_axis = np.cross(normal, x_axis)

    radius = EARTH_RADIUS_M + altitude
    mean_motion = math.sqrt(EARTH_MU_M3_PER_S2 / radius**3)
    u = np.arange(samples, dtype=np.float64) * _TWO_PI / samples
    cos_u, sin_u = np.cos(u)[:, None], np.sin(u)[:, None]
    position = radius * (cos_u * x_axis + sin_u * y_axis)
    sun_b = np.broadcast_to(sun, position.shape).copy()
    return _Track(
        epoch=epoch,
        radius=radius,
        mean_motion=mean_motion,
        time=u / mean_motion,
        position=position,
        velocity=radius * mean_motion * (-sin_u * x_axis + cos_u * y_axis),
        sun=sun_b,
        sunlit=visible_sun_fraction(position, sun_b, float(distance_au), conical),
    )


def _body_to_inertial(track: _Track, mode: AttitudeMode) -> FloatArray:
    """Rotation matrices body → inertial of a valid attitude mode at each sample."""
    samples = track.time.size
    directions = target_directions(track.position, track.velocity, track.sun)
    primary, secondary = (
        directions[_target(mode.primary_target)],
        directions[_target(mode.secondary_target)],
    )
    candidates = np.stack(
        [directions[Target.ORBIT_NORMAL], directions[Target.VELOCITY], directions[Target.ZENITH]]
    )
    least_parallel = np.argmin(np.abs(np.sum(candidates * primary, axis=-1)), axis=0)
    fallback = candidates[least_parallel, np.arange(samples)]
    assert mode.primary_axis is not None and mode.secondary_axis is not None
    return triad(
        np.array(AXIS_VECTORS[mode.primary_axis]),
        primary,
        np.array(AXIS_VECTORS[mode.secondary_axis]),
        secondary,
        fallback,
    )


def _track_fields(track: _Track) -> dict[str, object]:
    """The ``OrbitTrack`` fields of a sampled orbit, rounded for storage."""
    jd = julian_date(track.epoch)
    return {
        "epoch": track.epoch,
        "period": round(_TWO_PI / track.mean_motion, 3),
        "time": _round(track.time, 3),
        "position": np.round(track.position, 1).tolist(),
        "velocity": np.round(track.velocity, 4).tolist(),
        "sun": np.round(track.sun, 7).tolist(),
        "sunlit": _round(track.sunlit, 6),
        "earth_rotation_angle": _round(earth_rotation_angle(jd + track.time / SECONDS_PER_DAY), 7),
    }


def _profile(
    orbit: _Orbit,
    condition: Condition,
    mode: AttitudeMode,
    mode_id: str,
    samples: int,
    conical: bool,
    values: ResolvedDesignValues,
    irradiance_min: float,
    irradiance_max: float,
) -> OrbitProfile:
    sun, _ = sun_position(julian_date(condition.date))
    normal = normal_for_beta(
        sun, condition.beta, orbit.solve_inclination, _raan_at(orbit, condition.date)
    )
    track = _track(normal, condition.altitude, condition.date, samples, conical)
    matrix = _body_to_inertial(track, mode)

    r_hat = track.r_hat
    sun_b = track.sun
    cos_zenith = np.maximum(np.sum(r_hat * sun_b, axis=-1), 0.0)
    faces: list[FaceProfile] = []
    for face in Face:
        normal_i: FloatArray = matrix @ np.array(AXIS_VECTORS[Axis(face.value)])
        solar = track.sunlit * np.maximum(np.sum(normal_i * sun_b, axis=-1), 0.0)
        view = plate_to_earth_view_factor(np.sum(normal_i * -r_hat, axis=-1), track.radius)
        albedo = view * cos_zenith
        low = (
            irradiance_min * solar,
            irradiance_min * values.albedo_min.value * albedo,
            values.olr_min.value * view,
        )
        high = (
            irradiance_max * solar,
            irradiance_max * values.albedo_max.value * albedo,
            values.olr_max.value * view,
        )
        faces.append(
            FaceProfile(
                face=face,
                solar_min=_round(low[0], 3),
                solar_max=_round(high[0], 3),
                albedo_min=_round(low[1], 3),
                albedo_max=_round(high[1], 3),
                ir_min=_round(low[2], 3),
                ir_max=_round(high[2], 3),
                total_min=_round(low[0] + low[1] + low[2], 3),
                total_max=_round(high[0] + high[1] + high[2], 3),
            )
        )
    return OrbitProfile.model_validate(
        {
            **_track_fields(track),
            "condition_id": condition.id,
            "mode_id": mode_id,
            "quaternion": np.round(quaternion_from_matrix(matrix), 7).tolist(),
            "faces": faces,
        }
    )


def _target(target: Target | None) -> Target:
    assert target is not None
    return target


def _stats(low: list[float], high: list[float]) -> FluxStats:
    lo, hi = np.asarray(low), np.asarray(high)
    return FluxStats(
        average_min=round(float(np.mean(lo)), 3),
        average_max=round(float(np.mean(hi)), 3),
        peak_min=round(float(np.max(lo)), 3),
        peak_max=round(float(np.max(hi)), 3),
    )


def _face_fluxes(profile: OrbitProfile) -> list[FaceFluxes]:
    return [
        FaceFluxes(
            condition_id=profile.condition_id,
            mode_id=profile.mode_id,
            face=face.face,
            solar=_stats(face.solar_min, face.solar_max),
            albedo=_stats(face.albedo_min, face.albedo_max),
            ir=_stats(face.ir_min, face.ir_max),
            total=_stats(face.total_min, face.total_max),
        )
        for face in profile.faces
    ]


# ---------------------------------------------------------------- helpers


def _used(value: ResolvedDesignValue) -> DesignValue:
    return DesignValue(value=value.value, source=value.source, reference=value.reference)


def _round(values: FloatArray, decimals: int) -> list[float]:
    return np.round(np.asarray(values, dtype=np.float64), decimals).tolist()


def _optional_list(values: FloatArray | None, count: int) -> list[float | None]:
    if values is None:
        return [None] * count
    return list(_round(values, 7))
