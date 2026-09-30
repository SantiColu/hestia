"""Parameters of the environment stage (``docs/etapas/environment.md``, ADR 0021).

Edited as a form, like the mission (same ``x-`` JSON Schema extensions, see
``hestia_core.mission``). They hold the orbit and the attitude modes (ADR 0023,
``hestia_core.environment.orbit``) and the parameters of the computation. Every field is
optional so a draft can be incomplete; ``validate_environment_parameters`` reports what is
missing or inconsistent. Only the mission step looks at the mission of the cell's context (its
design life). SI units.

Design albedo and Earth IR (OLR) left empty take the library default for the orbit's
inclination (``design_value_band``), resolved when the stage is updated and reported with its
source in the result.
"""

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.config import JsonDict

from hestia_core.environment.orbit import (
    MIN_ALTITUDE_M,
    ORBIT_TYPE_LABELS,
    AttitudeMode,
    Orbit,
    OrbitType,
    nominal_altitude_m,
    nominal_inclination_rad,
    validate_attitude_modes,
    validate_orbit,
)
from hestia_core.forms import Problem, ProblemCode, Problems, format_km, unit
from hestia_core.mission import MissionArtifact

ENVIRONMENT_PARAMETERS_SCHEMA_VERSION = 2
"""Version of ``EnvironmentParameters``. Bump on any incompatible change. v2: the orbit and the
attitude modes, from the mission (ADR 0023)."""

DEFAULT_SOLAR_CONSTANT_W_M2 = 1361.0
SOLAR_CONSTANT_SOURCE = "ECSS-E-ST-10-04C (a verificar)"
"""Where the default solar constant comes from. To be verified against the standard."""
DEFAULT_MISSION_STEP_S = 86_400.0
"""*(propuesta)* one day."""
DEFAULT_ORBIT_SAMPLES = 120
"""*(propuesta)* 3° per sample."""
MIN_ORBIT_SAMPLES = 36
MAX_ORBIT_SAMPLES = 3600


class EclipseModel(StrEnum):
    CYLINDRICAL = "cylindrical"
    """Shadow cylinder without penumbra."""
    CONICAL = "conical"
    """Umbra and penumbra of a finite Sun."""


DEFAULT_ECLIPSE_MODEL = EclipseModel.CYLINDRICAL
"""*(propuesta)*"""


# ---------------------------------------------------------------- library of design values


@dataclass(frozen=True)
class DesignValueBand:
    """Design albedo and OLR for orbits whose inclination falls in ``[min, max]`` (rad)."""

    min_inclination_rad: float
    max_inclination_rad: float
    albedo_min: float
    albedo_max: float
    olr_min_w_m2: float
    olr_max_w_m2: float
    source: str


DESIGN_VALUE_SOURCE = "Provisorio, a verificar contra NASA TM-2001-211221"

# TODO(environment): load the bands of NASA TM-2001-211221 (Anderson, Justus & Batts,
# «Guidelines for the Selection of Near-Earth Thermal Environment Parameters for Spacecraft
# Design», 2001), verified against the document, and choose its averaging time. Until then a
# single provisional band covers every inclination.
DESIGN_VALUE_BANDS: tuple[DesignValueBand, ...] = (
    DesignValueBand(
        min_inclination_rad=0.0,
        max_inclination_rad=math.pi,
        albedo_min=0.25,
        albedo_max=0.35,
        olr_min_w_m2=218.0,
        olr_max_w_m2=258.0,
        source=DESIGN_VALUE_SOURCE,
    ),
)
"""Design albedo and OLR by inclination band (library defaults)."""


def design_value_band(inclination_rad: float) -> DesignValueBand:
    """The band of ``DESIGN_VALUE_BANDS`` that holds an inclination (folded to [0, π])."""
    inclination = abs(inclination_rad) % (2 * math.pi)
    if inclination > math.pi:
        inclination = 2 * math.pi - inclination
    for band in DESIGN_VALUE_BANDS:
        if band.min_inclination_rad <= inclination <= band.max_inclination_rad:
            return band
    return DESIGN_VALUE_BANDS[-1]


# ---------------------------------------------------------------- model


_BY_INCLINATION: JsonDict = {
    "x-placeholder": "tabla por inclinación",
    "x-default-source": DESIGN_VALUE_SOURCE,
}

ECLIPSE_MODEL_LABELS: JsonDict = {"cylindrical": "Cilíndrico", "conical": "Cónico"}


class DesignValues(BaseModel):
    solar_constant: float | None = Field(
        default=DEFAULT_SOLAR_CONSTANT_W_M2,
        title="Constante solar",
        description="Irradiancia solar a 1 UA. La de cada fecha sale de la distancia Tierra-Sol.",
        json_schema_extra=unit(
            "W/m²",
            extra={
                "x-default": DEFAULT_SOLAR_CONSTANT_W_M2,
                "x-default-source": SOLAR_CONSTANT_SOURCE,
            },
        ),
    )
    albedo_min: float | None = Field(
        default=None,
        title="Albedo mínimo",
        description="Albedo de diseño mínimo. Vacío: tabla por inclinación.",
        json_schema_extra=_BY_INCLINATION,
    )
    albedo_max: float | None = Field(
        default=None,
        title="Albedo máximo",
        description="Albedo de diseño máximo. Vacío: tabla por inclinación.",
        json_schema_extra=_BY_INCLINATION,
    )
    olr_min: float | None = Field(
        default=None,
        title="IR terrestre mínima",
        description="Radiación de onda larga saliente mínima. Vacío: tabla por inclinación.",
        json_schema_extra=unit("W/m²", extra=_BY_INCLINATION),
    )
    olr_max: float | None = Field(
        default=None,
        title="IR terrestre máxima",
        description="Radiación de onda larga saliente máxima. Vacío: tabla por inclinación.",
        json_schema_extra=unit("W/m²", extra=_BY_INCLINATION),
    )


class Dispersion(BaseModel):
    """Long-term perturbations that are not propagated: their extremes are evaluated around
    the nominal orbit (ADR 0020)."""

    ltan_dispersion: float | None = Field(
        default=None,
        title="Deriva de la hora del nodo",
        description="Solo SSO. Deriva máxima (±) de la hora local del nodo a lo largo de la "
        "vida. Vacío: 0.",
        json_schema_extra=unit("s", "min", {"x-placeholder": "0"}),
    )
    eol_altitude: float | None = Field(
        default=None,
        title="Altitud al fin de vida",
        description="SSO y LEO/MEO. Altitud por decaimiento al fin de vida. Vacío: sin "
        "decaimiento.",
        json_schema_extra=unit("m", "km", {"x-placeholder": "sin decaimiento"}),
    )
    geo_max_inclination: float | None = Field(
        default=None,
        title="Inclinación máxima en GEO",
        description="Solo GEO. Inclinación máxima que alcanza la órbita. Vacío: 0.",
        json_schema_extra=unit("rad", "°", {"x-placeholder": "0"}),
    )


class Sampling(BaseModel):
    mission_step: float | None = Field(
        default=DEFAULT_MISSION_STEP_S,
        title="Paso a lo largo de la misión",
        description="Paso de las series de β, eclipse e irradiancia.",
        json_schema_extra=unit("s", "días", {"x-default": DEFAULT_MISSION_STEP_S}),
    )
    orbit_samples: int | None = Field(
        default=DEFAULT_ORBIT_SAMPLES,
        title="Puntos por órbita",
        description="Muestras de los perfiles orbitales.",
        json_schema_extra={"x-default": DEFAULT_ORBIT_SAMPLES},
    )
    eclipse_model: EclipseModel | None = Field(
        default=DEFAULT_ECLIPSE_MODEL,
        title="Modelo de sombra",
        json_schema_extra={
            "x-enum-labels": ECLIPSE_MODEL_LABELS,
            "x-default": DEFAULT_ECLIPSE_MODEL.value,
            "x-notes": {
                "cylindrical": "Sombra cilíndrica sin penumbra.",
                "conical": "Umbra y penumbra: el eclipse cuenta la penumbra.",
            },
        },
    )


class CustomCondition(BaseModel):
    """A geometry the user adds to the extreme conditions (e.g. an intermediate β)."""

    id: str | None = Field(
        default=None, description="Generated by the backend when applied. Immutable."
    )
    name: str | None = Field(
        default=None, title="Nombre", json_schema_extra={"x-placeholder": "β = 30°"}
    )
    beta: float | None = Field(default=None, title="Ángulo β", json_schema_extra=unit("rad", "°"))
    altitude: float | None = Field(
        default=None,
        title="Altitud",
        description="Vacío: la nominal.",
        json_schema_extra=unit("m", "km", {"x-placeholder": "nominal"}),
    )


class EnvironmentParameters(BaseModel):
    """Parameters of the environment stage: orbit, attitude modes, design values, dispersions,
    sampling and custom conditions."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = ENVIRONMENT_PARAMETERS_SCHEMA_VERSION
    orbit: Orbit = Field(default_factory=Orbit, title="Órbita")
    attitude_modes: list[AttitudeMode] = Field(
        default_factory=list[AttitudeMode],
        title="Modos de actitud",
        json_schema_extra={"x-add-label": "Agregar modo de actitud"},
    )
    design_values: DesignValues = Field(default_factory=DesignValues, title="Valores de diseño")
    dispersion: Dispersion = Field(default_factory=Dispersion, title="Dispersión de la órbita")
    sampling: Sampling = Field(default_factory=Sampling, title="Muestreo")
    custom_conditions: list[CustomCondition] = Field(
        default_factory=list[CustomCondition],
        title="Condiciones propias",
        json_schema_extra={"x-add-label": "Agregar condición"},
    )


def environment_defaults() -> EnvironmentParameters:
    """New parameters: the library defaults (orbit type, solar constant, sampling), nothing
    else."""
    return EnvironmentParameters()


def upgrade_environment_parameters(data: dict[str, Any]) -> dict[str, Any]:
    """Environment parameters of any version (JSON) as the current version. v1 had no orbit nor
    attitude modes: they take what ``data`` holds (the project migration merges the mission's
    in), else the defaults."""
    current = data | {"schema_version": ENVIRONMENT_PARAMETERS_SCHEMA_VERSION}
    return EnvironmentParameters.model_validate(current).model_dump(mode="json")


# ---------------------------------------------------------------- resolution


class DesignValueSource(StrEnum):
    ENTERED = "entered"
    """Set in the parameters."""
    LIBRARY = "library"
    """Library default (table by inclination, standard)."""


@dataclass(frozen=True)
class ResolvedDesignValue:
    value: float
    source: DesignValueSource
    reference: str | None
    """The library source of a default (e.g. the table)."""


@dataclass(frozen=True)
class ResolvedDesignValues:
    solar_constant: ResolvedDesignValue
    albedo_min: ResolvedDesignValue
    albedo_max: ResolvedDesignValue
    olr_min: ResolvedDesignValue
    olr_max: ResolvedDesignValue


def resolve_design_values(values: DesignValues, inclination_rad: float) -> ResolvedDesignValues:
    """Fill empty design values with the library defaults for the orbit's inclination."""
    band = design_value_band(inclination_rad)

    def pick(value: float | None, default: float, reference: str) -> ResolvedDesignValue:
        if value is None:
            return ResolvedDesignValue(default, DesignValueSource.LIBRARY, reference)
        return ResolvedDesignValue(value, DesignValueSource.ENTERED, None)

    return ResolvedDesignValues(
        solar_constant=pick(
            values.solar_constant, DEFAULT_SOLAR_CONSTANT_W_M2, SOLAR_CONSTANT_SOURCE
        ),
        albedo_min=pick(values.albedo_min, band.albedo_min, band.source),
        albedo_max=pick(values.albedo_max, band.albedo_max, band.source),
        olr_min=pick(values.olr_min, band.olr_min_w_m2, band.source),
        olr_max=pick(values.olr_max, band.olr_max_w_m2, band.source),
    )


# ---------------------------------------------------------------- validation


_DISPERSION_BY_ORBIT: dict[str, tuple[OrbitType, ...]] = {
    "ltan_dispersion": (OrbitType.SSO,),
    "eol_altitude": (OrbitType.SSO, OrbitType.KEPLERIAN),
    "geo_max_inclination": (OrbitType.GEO,),
}
_DISPERSION_LABELS = {
    "ltan_dispersion": "La deriva de la hora del nodo",
    "eol_altitude": "La altitud al fin de vida",
    "geo_max_inclination": "La inclinación máxima en GEO",
}


def validate_environment_parameters(
    parameters: EnvironmentParameters, mission: MissionArtifact | None = None
) -> list[Problem]:
    """Completeness and consistency of the parameters (``docs/etapas/environment.md``).

    The mission step within the design life only applies when ``mission`` is given.
    Deterministic; problems in form order. An empty list means valid.
    """
    p = Problems()
    validate_orbit(p, parameters.orbit)
    validate_attitude_modes(p, parameters.attitude_modes)
    _validate_design_values(p, parameters.design_values, parameters.orbit)
    _validate_dispersion(p, parameters.dispersion, parameters.orbit)
    _validate_sampling(p, parameters.sampling, mission)
    _validate_conditions(p, parameters.custom_conditions)
    return p.items


def _validate_design_values(p: Problems, values: DesignValues, orbit: Orbit) -> None:
    path = "design_values"
    if p.required(f"{path}.solar_constant", values.solar_constant, "la constante solar"):
        assert values.solar_constant is not None
        if not values.solar_constant > 0:
            p.add(
                f"{path}.solar_constant",
                ProblemCode.MIN,
                "La constante solar tiene que ser mayor que 0.",
            )
    for name, label in (("albedo_min", "El albedo mínimo"), ("albedo_max", "El albedo máximo")):
        value = getattr(values, name)
        if value is not None and value < 0:
            p.add(f"{path}.{name}", ProblemCode.MIN, f"{label} no puede ser negativo.")
        elif value is not None and value > 1:
            p.add(f"{path}.{name}", ProblemCode.MAX, f"{label} no puede superar 1.")
    for name, label in (("olr_min", "La IR mínima"), ("olr_max", "La IR máxima")):
        value = getattr(values, name)
        if value is not None and not value > 0:
            p.add(f"{path}.{name}", ProblemCode.MIN, f"{label} tiene que ser mayor que 0.")

    # Order of the bounds, with empty bounds taken from the table when the orbit is known.
    inclination = nominal_inclination_rad(orbit)
    band = design_value_band(inclination) if inclination is not None else None
    albedo_min = values.albedo_min if values.albedo_min is not None else None
    albedo_max = values.albedo_max
    olr_min, olr_max = values.olr_min, values.olr_max
    if band is not None:
        albedo_min = band.albedo_min if albedo_min is None else albedo_min
        albedo_max = band.albedo_max if albedo_max is None else albedo_max
        olr_min = band.olr_min_w_m2 if olr_min is None else olr_min
        olr_max = band.olr_max_w_m2 if olr_max is None else olr_max
    if albedo_min is not None and albedo_max is not None and albedo_min > albedo_max:
        p.add(
            f"{path}.albedo_max",
            ProblemCode.ORDER,
            "El albedo máximo no puede ser menor que el mínimo.",
        )
    if olr_min is not None and olr_max is not None and olr_min > olr_max:
        p.add(
            f"{path}.olr_max", ProblemCode.ORDER, "La IR máxima no puede ser menor que la mínima."
        )


def _validate_dispersion(p: Problems, dispersion: Dispersion, orbit: Orbit) -> None:
    path = "dispersion"
    orbit_type = orbit.type
    if orbit_type is not None:
        for name, allowed in _DISPERSION_BY_ORBIT.items():
            if orbit_type not in allowed and getattr(dispersion, name) is not None:
                p.add(
                    f"{path}.{name}",
                    ProblemCode.NOT_ALLOWED,
                    f"{_DISPERSION_LABELS[name]} no corresponde a una órbita "
                    f"{ORBIT_TYPE_LABELS[orbit_type.value]}: dejala vacía.",
                )
    if dispersion.ltan_dispersion is not None and dispersion.ltan_dispersion < 0:
        p.add(
            f"{path}.ltan_dispersion",
            ProblemCode.MIN,
            "La deriva de la hora del nodo no puede ser negativa.",
        )
    if dispersion.geo_max_inclination is not None and dispersion.geo_max_inclination < 0:
        p.add(
            f"{path}.geo_max_inclination",
            ProblemCode.MIN,
            "La inclinación máxima no puede ser negativa.",
        )
    eol = dispersion.eol_altitude
    if eol is not None:
        if eol < MIN_ALTITUDE_M:
            p.add(
                f"{path}.eol_altitude",
                ProblemCode.MIN,
                f"La altitud al fin de vida tiene que ser de al menos {format_km(MIN_ALTITUDE_M)}.",
            )
        nominal = nominal_altitude_m(orbit)
        if nominal is not None and eol > nominal:
            p.add(
                f"{path}.eol_altitude",
                ProblemCode.MAX,
                f"La altitud al fin de vida no puede superar la nominal ({format_km(nominal)}).",
            )


def _validate_sampling(p: Problems, sampling: Sampling, mission: MissionArtifact | None) -> None:
    path = "sampling"
    if p.required(f"{path}.mission_step", sampling.mission_step, "el paso de la misión"):
        assert sampling.mission_step is not None
        life = mission.general.design_life if mission is not None else None
        if not sampling.mission_step > 0:
            p.add(f"{path}.mission_step", ProblemCode.MIN, "El paso tiene que ser mayor que 0.")
        elif life is not None and life > 0 and sampling.mission_step > life:
            p.add(
                f"{path}.mission_step",
                ProblemCode.MAX,
                "El paso no puede superar la vida útil de la misión.",
            )
    if p.required(f"{path}.orbit_samples", sampling.orbit_samples, "los puntos por órbita"):
        assert sampling.orbit_samples is not None
        if sampling.orbit_samples < MIN_ORBIT_SAMPLES:
            p.add(
                f"{path}.orbit_samples",
                ProblemCode.MIN,
                f"Hacen falta al menos {MIN_ORBIT_SAMPLES} puntos por órbita.",
            )
        elif sampling.orbit_samples > MAX_ORBIT_SAMPLES:
            p.add(
                f"{path}.orbit_samples",
                ProblemCode.MAX,
                f"No puede haber más de {MAX_ORBIT_SAMPLES} puntos por órbita.",
            )
    p.required(f"{path}.eclipse_model", sampling.eclipse_model, "el modelo de sombra")


def _validate_conditions(p: Problems, conditions: list[CustomCondition]) -> None:
    seen: set[str] = set()
    for i, condition in enumerate(conditions):
        path = f"custom_conditions[{i}]"
        p.unique_name(
            f"{path}.name",
            condition.name,
            seen,
            "el nombre de la condición",
            "Ya hay una condición llamada",
        )
        if p.required(f"{path}.beta", condition.beta, "el ángulo β"):
            assert condition.beta is not None
            if condition.beta < -math.pi / 2:
                p.add(f"{path}.beta", ProblemCode.MIN, "El ángulo β no puede ser menor que -90°.")
            elif condition.beta > math.pi / 2:
                p.add(f"{path}.beta", ProblemCode.MAX, "El ángulo β no puede superar 90°.")
        if condition.altitude is not None and condition.altitude < MIN_ALTITUDE_M:
            p.add(
                f"{path}.altitude",
                ProblemCode.MIN,
                f"La altitud tiene que ser de al menos {format_km(MIN_ALTITUDE_M)}.",
            )
