"""Mission stage artifact (``docs/etapas/mission.md``, ADR 0017).

A form stage: the artifact is what the user enters, validated. Every field is optional so a
draft can be incomplete; ``validate_mission`` reports what is missing or inconsistent and never
produces new values. SI units, temperatures in K. Each physical field declares its SI unit and
its display unit in the JSON Schema (``x-unit``, ``x-display-unit``).

JSON Schema extensions read by the UI to build the form (presentation only):

- ``x-unit`` / ``x-display-unit``: stored unit and the unit shown to people.
- ``x-enum-labels``: label of each enum value.
- ``x-show-if``: ``{sibling field: [values]}``; the field only applies for those values.
- ``x-notes``: ``{enum value: note}`` shown when that value is selected.
- ``x-input``: ``textarea`` or ``time`` for text fields.
- ``x-placeholder``: text shown while the field is empty.
- ``x-default``: library default of the field (its provenance is ``default`` until changed).
- ``x-default-source``: where the library default comes from (e.g. a standard).
- ``x-column-title``: short title of a field shown as a table column.
- ``x-add-label``: label of the action that adds an item to a list.
"""

import math
import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic.config import JsonDict

from hestia_core.forms import Problem, ProblemCode
from hestia_core.orbits import sso_max_altitude_m

MISSION_SCHEMA_VERSION = 1
"""Version of ``MissionArtifact``. Bump on any incompatible change."""

MIN_ALTITUDE_M = 100_000.0
"""Lowest altitude accepted for an orbit (Kármán line)."""

MARGINS_SOURCE = "ECSS-E-ST-31C"
"""Standard the default margins come from."""
DEFAULT_UNCERTAINTY_MARGIN_K = 10.0
"""ECSS-E-ST-31C, uncorrelated model. To be verified against the standard."""
DEFAULT_ACCEPTANCE_MARGIN_K = 5.0
DEFAULT_QUALIFICATION_MARGIN_K = 5.0


class OrbitType(StrEnum):
    SSO = "sso"
    KEPLERIAN = "keplerian"
    """LEO/MEO: defined by its elements (also elliptical)."""
    GEO = "geo"


class Axis(StrEnum):
    PX = "+X"
    MX = "-X"
    PY = "+Y"
    MY = "-Y"
    PZ = "+Z"
    MZ = "-Z"


class Face(StrEnum):
    PX = "+X"
    MX = "-X"
    PY = "+Y"
    MY = "-Y"
    PZ = "+Z"
    MZ = "-Z"


class Target(StrEnum):
    NADIR = "nadir"
    ZENITH = "zenith"
    SUN = "sun"
    VELOCITY = "velocity"
    ANTI_VELOCITY = "anti_velocity"
    ORBIT_NORMAL = "orbit_normal"
    ANTI_ORBIT_NORMAL = "anti_orbit_normal"


ORBIT_TYPE_LABELS: JsonDict = {"sso": "SSO", "keplerian": "LEO/MEO", "geo": "GEO"}
TARGET_LABELS: JsonDict = {
    "nadir": "Nadir",
    "zenith": "Cénit",
    "sun": "Sol",
    "velocity": "Velocidad",
    "anti_velocity": "Antivelocidad",
    "orbit_normal": "Normal a la órbita",
    "anti_orbit_normal": "Antinormal a la órbita",
}
_OPPOSITE_TARGETS = {
    frozenset({Target.NADIR, Target.ZENITH}),
    frozenset({Target.VELOCITY, Target.ANTI_VELOCITY}),
    frozenset({Target.ORBIT_NORMAL, Target.ANTI_ORBIT_NORMAL}),
}


def _unit(si: str, display: str | None = None, extra: JsonDict | None = None) -> JsonDict:
    return {"x-unit": si, "x-display-unit": display or si, **(extra or {})}


# ---------------------------------------------------------------- sections


class General(BaseModel):
    description: str | None = Field(
        default=None,
        title="Descripción",
        description="Objetivo y notas generales.",
    )
    launch_date: date | None = Field(
        default=None,
        title="Fecha de lanzamiento",
        description="Define las estaciones que recorre la misión (flujo solar, historia de β).",
    )
    design_life: float | None = Field(
        default=None,
        title="Vida útil",
        description="Define el fin de vida (degradación de recubrimientos, EOL).",
        json_schema_extra=_unit("s", "años"),
    )


_SSO_ONLY: JsonDict = {"x-show-if": {"type": ["sso"]}}
_KEPLERIAN_ONLY: JsonDict = {"x-show-if": {"type": ["keplerian"]}}


class Orbit(BaseModel):
    type: OrbitType | None = Field(
        default=OrbitType.SSO,
        title="Tipo de órbita",
        json_schema_extra={
            "x-enum-labels": ORBIT_TYPE_LABELS,
            "x-default": OrbitType.SSO.value,
            "x-notes": {
                "sso": "En una SSO la inclinación la fija la altitud: se calcula en Entorno.",
                "geo": "Altitud 35 786 km, circular y ecuatorial.",
            },
        },
    )
    altitude: float | None = Field(
        default=None,
        title="Altitud",
        description="Órbita circular.",
        json_schema_extra=_unit("m", "km", _SSO_ONLY),
    )
    ltan: str | None = Field(
        default=None,
        title="Hora local del nodo ascendente",
        description="Hora local (solar media) del nodo ascendente, HH:MM.",
        json_schema_extra={"x-input": "time", **_SSO_ONLY},
    )
    perigee_altitude: float | None = Field(
        default=None,
        title="Altitud del perigeo",
        json_schema_extra=_unit("m", "km", _KEPLERIAN_ONLY),
    )
    apogee_altitude: float | None = Field(
        default=None,
        title="Altitud del apogeo",
        description="Vacío: órbita circular (igual al perigeo).",
        json_schema_extra=_unit(
            "m", "km", {**_KEPLERIAN_ONLY, "x-placeholder": "vacío = circular"}
        ),
    )
    inclination: float | None = Field(
        default=None,
        title="Inclinación",
        json_schema_extra=_unit("rad", "°", _KEPLERIAN_ONLY),
    )


class Envelope(BaseModel):
    size_x: float | None = Field(default=None, title="Dimensión X", json_schema_extra=_unit("m"))
    size_y: float | None = Field(default=None, title="Dimensión Y", json_schema_extra=_unit("m"))
    size_z: float | None = Field(default=None, title="Dimensión Z", json_schema_extra=_unit("m"))
    mass: float | None = Field(
        default=None,
        title="Masa",
        description="Masa total del satélite en órbita, al inicio de vida.",
        json_schema_extra=_unit("kg"),
    )


_TARGET_EXTRA: JsonDict = {"x-enum-labels": TARGET_LABELS, "x-column-title": "Dirección"}


class AttitudeMode(BaseModel):
    """Attitude from two body axis → direction pairs: the primary holds exactly, the secondary
    sets the rotation about the primary."""

    id: str | None = Field(
        default=None, description="Generated by the backend when applied. Immutable."
    )
    name: str | None = Field(default=None, title="Nombre")
    primary_axis: Axis | None = Field(default=None, title="Eje primario")
    primary_target: Target | None = Field(
        default=None, title="Dirección primaria", json_schema_extra=_TARGET_EXTRA
    )
    secondary_axis: Axis | None = Field(default=None, title="Eje secundario")
    secondary_target: Target | None = Field(
        default=None,
        title="Dirección secundaria",
        json_schema_extra=_TARGET_EXTRA,
    )


def _margin_default(value: float) -> JsonDict:
    return {"x-default": value, "x-default-source": MARGINS_SOURCE}


class Criteria(BaseModel):
    uncertainty_margin: float | None = Field(
        default=DEFAULT_UNCERTAINTY_MARGIN_K,
        title="Margen de incertidumbre",
        description="Incertidumbre de las predicciones (ΔT).",
        json_schema_extra=_unit("K", extra=_margin_default(DEFAULT_UNCERTAINTY_MARGIN_K)),
    )
    acceptance_margin: float | None = Field(
        default=DEFAULT_ACCEPTANCE_MARGIN_K,
        title="Margen de aceptación",
        description="ΔT.",
        json_schema_extra=_unit("K", extra=_margin_default(DEFAULT_ACCEPTANCE_MARGIN_K)),
    )
    qualification_margin: float | None = Field(
        default=DEFAULT_QUALIFICATION_MARGIN_K,
        title="Margen de calificación",
        description="Sobre el de aceptación (ΔT).",
        json_schema_extra=_unit("K", extra=_margin_default(DEFAULT_QUALIFICATION_MARGIN_K)),
    )
    heater_power_budget: float | None = Field(
        default=None,
        title="Potencia para heaters",
        description="Promedio orbital disponible.",
        json_schema_extra=_unit("W"),
    )
    tcs_mass_budget: float | None = Field(
        default=None, title="Masa para el TCS", json_schema_extra=_unit("kg")
    )
    radiator_faces: list[Face] = Field(
        default_factory=list[Face],
        title="Caras permitidas para radiador",
        description="Caras donde se permite ubicar radiadores. Vacío: sin restricción.",
    )


class MissionArtifact(BaseModel):
    """Artifact of the mission stage: orbit, attitude, envelope and criteria."""

    schema_version: int = MISSION_SCHEMA_VERSION
    general: General = Field(default_factory=General, title="General")
    orbit: Orbit = Field(default_factory=Orbit, title="Órbita")
    envelope: Envelope = Field(default_factory=Envelope, title="Envolvente")
    attitude_modes: list[AttitudeMode] = Field(
        default_factory=list[AttitudeMode],
        title="Modos de actitud",
        json_schema_extra={"x-add-label": "Agregar modo de actitud"},
    )
    criteria: Criteria = Field(default_factory=Criteria, title="Criterios y restricciones")


def mission_defaults() -> MissionArtifact:
    """A new mission: library defaults (margins, ``orbit.type = sso``), nothing else."""
    return MissionArtifact()


# ---------------------------------------------------------------- validation

_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class _Problems:
    def __init__(self) -> None:
        self.items: list[Problem] = []

    def add(self, path: str, code: ProblemCode, message: str) -> None:
        self.items.append(Problem(path=path, code=code, message=message))

    def required(self, path: str, value: object, label: str) -> bool:
        """Report a missing value. Returns whether the value is present."""
        if value is None or (isinstance(value, str) and not value.strip()):
            self.add(path, ProblemCode.REQUIRED, f"Falta {label}.")
            return False
        return True

    def positive(self, path: str, value: float | None, label: str) -> None:
        if value is not None and not value > 0:
            self.add(path, ProblemCode.MIN, f"{label} tiene que ser mayor que 0.")

    def non_negative(self, path: str, value: float | None, label: str) -> None:
        if value is not None and value < 0:
            self.add(path, ProblemCode.MIN, f"{label} no puede ser negativo.")


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _km(value_m: float) -> str:
    return f"{value_m / 1000:,.0f}".replace(",", " ") + " km"


def validate_mission(artifact: MissionArtifact) -> list[Problem]:
    """Completeness and consistency of a mission (``docs/etapas/mission.md``).

    Deterministic; returns the problems in form order. An empty list means valid.
    """
    p = _Problems()
    _validate_general(p, artifact.general)
    _validate_orbit(p, artifact.orbit)
    _validate_envelope(p, artifact.envelope)
    _validate_modes(p, artifact.attitude_modes)
    _validate_criteria(p, artifact.criteria)
    return p.items


def _validate_general(p: _Problems, general: General) -> None:
    p.required("general.launch_date", general.launch_date, "la fecha de lanzamiento")
    if p.required("general.design_life", general.design_life, "la vida útil"):
        p.positive("general.design_life", general.design_life, "La vida útil")


_ORBIT_FIELDS: dict[OrbitType, tuple[str, ...]] = {
    OrbitType.SSO: ("altitude", "ltan"),
    OrbitType.KEPLERIAN: ("perigee_altitude", "apogee_altitude", "inclination"),
    OrbitType.GEO: (),
}
_ORBIT_LABELS = {
    "altitude": "la altitud",
    "ltan": "la hora local del nodo ascendente",
    "perigee_altitude": "la altitud del perigeo",
    "apogee_altitude": "la altitud del apogeo",
    "inclination": "la inclinación",
}


def _validate_orbit(p: _Problems, orbit: Orbit) -> None:
    if not p.required("orbit.type", orbit.type, "el tipo de órbita"):
        return
    assert orbit.type is not None
    allowed = _ORBIT_FIELDS[orbit.type]
    for name in _ORBIT_LABELS:
        if name not in allowed and getattr(orbit, name) is not None:
            p.add(
                f"orbit.{name}",
                ProblemCode.NOT_ALLOWED,
                f"{_cap(_ORBIT_LABELS[name])} no corresponde a una órbita "
                f"{ORBIT_TYPE_LABELS[orbit.type.value]}: dejalo vacío.",
            )

    if orbit.type is OrbitType.SSO:
        if p.required("orbit.altitude", orbit.altitude, "la altitud"):
            assert orbit.altitude is not None
            _min_altitude(p, "orbit.altitude", orbit.altitude, "La altitud")
            max_altitude = sso_max_altitude_m()
            if orbit.altitude > max_altitude:
                p.add(
                    "orbit.altitude",
                    ProblemCode.SSO_ALTITUDE,
                    f"No hay órbitas heliosincrónicas por encima de {_km(max_altitude)}.",
                )
        ltan = orbit.ltan
        if p.required("orbit.ltan", ltan, _ORBIT_LABELS["ltan"]) and not _TIME.match(ltan or ""):
            p.add(
                "orbit.ltan", ProblemCode.FORMAT, "La hora local tiene que tener el formato HH:MM."
            )
    elif orbit.type is OrbitType.KEPLERIAN:
        perigee = orbit.perigee_altitude
        if p.required("orbit.perigee_altitude", perigee, "la altitud del perigeo"):
            assert perigee is not None
            _min_altitude(p, "orbit.perigee_altitude", perigee, "La altitud del perigeo")
        if orbit.apogee_altitude is not None:
            _min_altitude(
                p, "orbit.apogee_altitude", orbit.apogee_altitude, "La altitud del apogeo"
            )
            if perigee is not None and orbit.apogee_altitude < perigee:
                p.add(
                    "orbit.apogee_altitude",
                    ProblemCode.ORDER,
                    "El apogeo no puede estar por debajo del perigeo.",
                )
        if p.required("orbit.inclination", orbit.inclination, "la inclinación"):
            assert orbit.inclination is not None
            if orbit.inclination < 0:
                p.add("orbit.inclination", ProblemCode.MIN, "La inclinación no puede ser negativa.")
            elif orbit.inclination > math.pi:
                p.add("orbit.inclination", ProblemCode.MAX, "La inclinación no puede superar 180°.")


def _min_altitude(p: _Problems, path: str, value_m: float, label: str) -> None:
    if value_m < MIN_ALTITUDE_M:
        p.add(path, ProblemCode.MIN, f"{label} tiene que ser de al menos {_km(MIN_ALTITUDE_M)}.")


def _validate_envelope(p: _Problems, envelope: Envelope) -> None:
    for name, label in (
        ("size_x", "la dimensión X"),
        ("size_y", "la dimensión Y"),
        ("size_z", "la dimensión Z"),
        ("mass", "la masa"),
    ):
        value = getattr(envelope, name)
        if p.required(f"envelope.{name}", value, label):
            p.positive(f"envelope.{name}", value, _cap(label))


def _parallel_axes(a: Axis, b: Axis) -> bool:
    return a.value[1] == b.value[1]


def _validate_modes(p: _Problems, modes: list[AttitudeMode]) -> None:
    if not modes:
        p.add("attitude_modes", ProblemCode.REQUIRED, "Falta al menos un modo de actitud.")
    seen: set[str] = set()
    for i, mode in enumerate(modes):
        path = f"attitude_modes[{i}]"
        if p.required(f"{path}.name", mode.name, "el nombre del modo"):
            assert mode.name is not None
            key = " ".join(mode.name.split()).casefold()
            if key in seen:
                p.add(
                    f"{path}.name",
                    ProblemCode.DUPLICATE_NAME,
                    f"Ya hay un modo de actitud llamado «{mode.name.strip()}».",
                )
            seen.add(key)
        p.required(f"{path}.primary_axis", mode.primary_axis, "el eje primario")
        p.required(f"{path}.primary_target", mode.primary_target, "la dirección primaria")
        p.required(f"{path}.secondary_axis", mode.secondary_axis, "el eje secundario")
        p.required(f"{path}.secondary_target", mode.secondary_target, "la dirección secundaria")
        if (
            mode.primary_axis is not None
            and mode.secondary_axis is not None
            and _parallel_axes(mode.primary_axis, mode.secondary_axis)
        ):
            p.add(
                f"{path}.secondary_axis",
                ProblemCode.PARALLEL,
                "El eje secundario no puede ser paralelo al primario.",
            )
        if (
            mode.primary_target is not None
            and mode.secondary_target is not None
            and (
                mode.primary_target is mode.secondary_target
                or frozenset({mode.primary_target, mode.secondary_target}) in _OPPOSITE_TARGETS
            )
        ):
            p.add(
                f"{path}.secondary_target",
                ProblemCode.PARALLEL,
                "La dirección secundaria no puede ser la misma ni la opuesta a la primaria.",
            )


def _validate_criteria(p: _Problems, criteria: Criteria) -> None:
    for name, label in (
        ("uncertainty_margin", "el margen de incertidumbre"),
        ("acceptance_margin", "el margen de aceptación"),
        ("qualification_margin", "el margen de calificación"),
    ):
        value = getattr(criteria, name)
        if p.required(f"criteria.{name}", value, label):
            p.non_negative(f"criteria.{name}", value, _cap(label))
    p.non_negative(
        "criteria.heater_power_budget", criteria.heater_power_budget, "La potencia para heaters"
    )
    p.non_negative("criteria.tcs_mass_budget", criteria.tcs_mass_budget, "La masa para el TCS")
    faces: set[Face] = set()
    for i, face in enumerate(criteria.radiator_faces):
        if face in faces:
            p.add(
                f"criteria.radiator_faces[{i}]",
                ProblemCode.DUPLICATE,
                f"La cara {face.value} está repetida.",
            )
        faces.add(face)
