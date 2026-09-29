"""Result of the environment stage (``docs/etapas/environment.md``, section «Resultado»).

Geometry (β, eclipses) and incident fluxes (W/m², not absorbed) on each face of the envelope,
for every attitude mode, in the extreme and custom conditions. SI units; angles in rad; times
in s; dates in UTC. Series and profiles are stored by columns (one list per quantity).

Frames and signs: vectors are geocentric equatorial inertial, mean equator of date (see
``hestia_core.sun``). β is positive when the Sun is on the side of the orbit normal
``h = r x v``. Quaternions are body → inertial, ``[w, x, y, z]``.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from hestia_core.environment.parameters import DesignValueSource, EclipseModel
from hestia_core.mission import Face, OrbitType

ENVIRONMENT_RESULT_SCHEMA_VERSION = 1
"""Version of ``EnvironmentResult``. Bump on any incompatible change."""


class ProviderInfo(BaseModel):
    name: str
    version: str


class DesignValue(BaseModel):
    """A design value as used, with where it comes from."""

    value: float
    source: DesignValueSource
    reference: str | None = None
    """Library source of a default (standard, table)."""


class DesignValuesUsed(BaseModel):
    solar_constant: DesignValue
    """W/m² at 1 AU."""
    albedo_min: DesignValue
    albedo_max: DesignValue
    olr_min: DesignValue
    """W/m²."""
    olr_max: DesignValue


class OrbitSummary(BaseModel):
    """The orbit as the provider models it: circular at ``altitude`` (ADR 0020)."""

    type: OrbitType
    inclination: float
    """rad. SSO: from J2 and the altitude. GEO: the nominal (0)."""
    altitude: float
    """m. Nominal: SSO altitude, LEO/MEO perigee, GEO altitude."""
    eol_altitude: float | None
    """m. Null: no decay."""
    eccentricity: float
    """Of the mission's orbit (the provider treats it as circular)."""
    period: float
    """s, from the semi-major axis of the mission's orbit."""
    raan_swept: bool
    """True when the mission does not fix the node (LEO/MEO, inclined GEO): β is given as the
    envelope over every node."""
    eclipse_model: EclipseModel


class MissionSeries(BaseModel):
    """Along the mission, one value per date (every ``mission_step``)."""

    dates: list[datetime]
    beta_nominal: list[float | None]
    """rad. Null in LEO/MEO (the node is not fixed)."""
    beta_min: list[float]
    """rad, envelope with the dispersions."""
    beta_max: list[float]
    eclipse_fraction_min: list[float]
    """Fraction of the orbit in shadow, over the β envelope and the altitudes."""
    eclipse_fraction_max: list[float]
    eclipse_duration_min: list[float]
    """s."""
    eclipse_duration_max: list[float]
    irradiance: list[float]
    """Solar irradiance at the date's Earth-Sun distance, W/m²."""


class RangeQuantity(StrEnum):
    IRRADIANCE = "irradiance"
    BETA = "beta"
    ALTITUDE = "altitude"
    ALBEDO = "albedo"
    OLR = "olr"


class RangeEntry(BaseModel):
    """Minimum and maximum of a quantity, with the date or the reason of each extreme."""

    quantity: RangeQuantity
    unit: str
    """SI unit (``W/m²``, ``rad``, ``m``; empty for the albedo)."""
    min: float
    max: float
    min_at: datetime | None = None
    max_at: datetime | None = None
    min_note: str
    max_note: str


class ConditionOrigin(StrEnum):
    EXTREME = "extreme"
    CUSTOM = "custom"


class Condition(BaseModel):
    """A geometry of the environment: β and altitude, with its orbit and eclipse."""

    id: str
    name: str
    origin: ConditionOrigin
    beta: float
    """rad."""
    altitude: float
    """m."""
    date: datetime
    """Date the geometry happens (extremes), or the first date whose β envelope holds it
    (custom; the launch date if none does)."""
    period: float
    """s. The nominal altitude uses the semi-major axis of the mission's orbit."""
    eclipse_fraction: float
    eclipse_duration: float
    """s."""
    note: str | None = None
    """How the geometry is drawn when the mission never has it (custom conditions)."""


class AttitudeModeRef(BaseModel):
    id: str
    name: str


class FluxStats(BaseModel):
    """Orbit average and peak of a flux, each with the minimum and maximum design values
    (W/m²)."""

    average_min: float
    average_max: float
    peak_min: float
    peak_max: float


class FaceFluxes(BaseModel):
    """Incident fluxes on one face, in one condition and attitude mode (W/m²)."""

    condition_id: str
    mode_id: str
    face: Face
    solar: FluxStats
    """Direct Sun: minimum and maximum irradiance of the mission window."""
    albedo: FluxStats
    """Irradiance x albedo, both minimum or both maximum."""
    ir: FluxStats
    """Earth IR: minimum and maximum OLR."""
    total: FluxStats
    """Sum of the three at each instant, all minimum or all maximum."""


class FaceProfile(BaseModel):
    """Incident fluxes on one face along the orbit (W/m²)."""

    face: Face
    solar_min: list[float]
    solar_max: list[float]
    albedo_min: list[float]
    albedo_max: list[float]
    ir_min: list[float]
    ir_max: list[float]
    total_min: list[float]
    """Solar + albedo + IR, all at their minimum."""
    total_max: list[float]
    """Solar + albedo + IR, all at their maximum."""


class OrbitProfile(BaseModel):
    """One orbit of a condition in an attitude mode, ``orbit_samples`` points from the
    ascending node. For charts, the 3D view and later the transients of ``load_cases``."""

    condition_id: str
    mode_id: str
    epoch: datetime
    """Time of the first sample."""
    period: float
    """s. The samples cover one period of the drawn circular orbit uniformly."""
    time: list[float]
    """s from the epoch."""
    position: list[list[float]]
    """Inertial, m."""
    velocity: list[list[float]]
    """Inertial, m/s."""
    sun: list[list[float]]
    """Unit vector to the Sun, inertial."""
    sunlit: list[float]
    """Visible fraction of the solar disk: 0 in umbra, 1 in full Sun."""
    quaternion: list[list[float]]
    """Body → inertial, ``[w, x, y, z]``."""
    earth_rotation_angle: list[float]
    """rad: Greenwich meridian from the x axis, to draw a rotating Earth."""
    faces: list[FaceProfile]


class OrbitProfileRef(BaseModel):
    """An orbit profile of the result, read on its own (profiles are the bulk of the result)."""

    condition_id: str
    mode_id: str


class _EnvironmentBase(BaseModel):
    schema_version: int = ENVIRONMENT_RESULT_SCHEMA_VERSION
    provider: ProviderInfo
    design_values: DesignValuesUsed
    orbit: OrbitSummary
    mission_series: MissionSeries
    ranges: list[RangeEntry]
    conditions: list[Condition]
    attitude_modes: list[AttitudeModeRef]
    faces: list[Face]
    """Faces of the envelope, in order."""
    fluxes: list[FaceFluxes]
    """By condition x attitude mode x face."""


class EnvironmentResult(_EnvironmentBase):
    """Result of the environment stage. Conditions, not cases: which combination is hot or cold
    is decided downstream (``global_balance``, ``load_cases``)."""

    orbit_profiles: list[OrbitProfile]
    """By condition x attitude mode."""


class EnvironmentSummary(_EnvironmentBase):
    """The result without the orbit profiles, which are read one at a time."""

    orbit_profiles: list[OrbitProfileRef]
    """Profiles available, by condition x attitude mode."""


def summarize(result: EnvironmentResult) -> EnvironmentSummary:
    data = result.model_dump(exclude={"orbit_profiles"})
    refs = [
        OrbitProfileRef(condition_id=p.condition_id, mode_id=p.mode_id)
        for p in result.orbit_profiles
    ]
    return EnvironmentSummary.model_validate({**data, "orbit_profiles": refs})
