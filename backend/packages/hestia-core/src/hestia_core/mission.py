"""Mission stage artifact (``docs/etapas/mission.md``, ADR 0017).

The orbit and the attitude modes are parameters of the environment stage (ADR 0023,
``hestia_core.environment.orbit``).

A form stage: the artifact is what the user enters, validated. Every field is optional so a
draft can be incomplete; ``validate_mission`` reports what is missing or inconsistent and never
produces new values. SI units, temperatures in K. Each physical field declares its SI unit and
its display unit in the JSON Schema (``x-unit``, ``x-display-unit``).

JSON Schema extensions read by the UI to build the form (presentation only):

- ``x-unit`` / ``x-display-unit``: stored unit and the unit shown to people.
- ``x-enum-labels``: label of each enum value.
- ``x-show-if``: ``{sibling field: [values]}``; the field only applies for those values. A
  dotted key is a path from the artifact's root (``orbit.type``). When a change makes a field
  stop applying, the form clears it.
- ``x-carry-from``: ``[sibling fields]``; when the field starts applying empty, it takes the
  value of the first of them that stops applying (the perigee becomes the SSO altitude).
- ``x-notes``: ``{enum value: note}`` shown when that value is selected.
- ``x-input``: ``textarea`` or ``time`` for text fields.
- ``x-placeholder``: text shown while the field is empty.
- ``x-default``: library default of the field (its provenance is ``default`` until changed).
- ``x-default-source``: where the library default comes from (e.g. a standard).
- ``x-column-title``: short title of a field shown as a table column.
- ``x-add-label``: label of the action that adds an item to a list.
"""

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.config import JsonDict

from hestia_core.forms import Problem, ProblemCode, Problems, capitalize, unit

MISSION_SCHEMA_VERSION = 2
"""Version of ``MissionArtifact``. Bump on any incompatible change. v2: the orbit and the
attitude modes moved to the environment parameters (ADR 0023)."""

MARGINS_SOURCE = "ECSS-E-ST-31C"
"""Standard the default margins come from."""
DEFAULT_UNCERTAINTY_MARGIN_K = 10.0
"""ECSS-E-ST-31C, uncorrelated model. To be verified against the standard."""
DEFAULT_ACCEPTANCE_MARGIN_K = 5.0
DEFAULT_QUALIFICATION_MARGIN_K = 5.0


class Face(StrEnum):
    PX = "+X"
    MX = "-X"
    PY = "+Y"
    MY = "-Y"
    PZ = "+Z"
    MZ = "-Z"


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
        json_schema_extra=unit("s", "años"),
    )


class Envelope(BaseModel):
    size_x: float | None = Field(default=None, title="Dimensión X", json_schema_extra=unit("m"))
    size_y: float | None = Field(default=None, title="Dimensión Y", json_schema_extra=unit("m"))
    size_z: float | None = Field(default=None, title="Dimensión Z", json_schema_extra=unit("m"))
    mass: float | None = Field(
        default=None,
        title="Masa",
        description="Masa total del satélite en órbita, al inicio de vida.",
        json_schema_extra=unit("kg"),
    )


def _margin_default(value: float) -> JsonDict:
    return {"x-default": value, "x-default-source": MARGINS_SOURCE}


class Criteria(BaseModel):
    uncertainty_margin: float | None = Field(
        default=DEFAULT_UNCERTAINTY_MARGIN_K,
        title="Margen de incertidumbre",
        description="Incertidumbre de las predicciones (ΔT).",
        json_schema_extra=unit("K", extra=_margin_default(DEFAULT_UNCERTAINTY_MARGIN_K)),
    )
    acceptance_margin: float | None = Field(
        default=DEFAULT_ACCEPTANCE_MARGIN_K,
        title="Margen de aceptación",
        description="ΔT.",
        json_schema_extra=unit("K", extra=_margin_default(DEFAULT_ACCEPTANCE_MARGIN_K)),
    )
    qualification_margin: float | None = Field(
        default=DEFAULT_QUALIFICATION_MARGIN_K,
        title="Margen de calificación",
        description="Sobre el de aceptación (ΔT).",
        json_schema_extra=unit("K", extra=_margin_default(DEFAULT_QUALIFICATION_MARGIN_K)),
    )
    heater_power_budget: float | None = Field(
        default=None,
        title="Potencia para heaters",
        description="Promedio orbital disponible.",
        json_schema_extra=unit("W"),
    )
    tcs_mass_budget: float | None = Field(
        default=None, title="Masa para el TCS", json_schema_extra=unit("kg")
    )
    radiator_faces: list[Face] = Field(
        default_factory=list[Face],
        title="Caras permitidas para radiador",
        description="Caras donde se permite ubicar radiadores. Vacío: sin restricción.",
    )


class MissionArtifact(BaseModel):
    """Artifact of the mission stage: mission window, envelope and criteria."""

    model_config = ConfigDict(extra="forbid")
    """Unknown sections are an error, so a request body can tell it from other artifacts."""

    schema_version: int = MISSION_SCHEMA_VERSION
    general: General = Field(default_factory=General, title="General")
    envelope: Envelope = Field(default_factory=Envelope, title="Envolvente")
    criteria: Criteria = Field(default_factory=Criteria, title="Criterios y restricciones")


def mission_defaults() -> MissionArtifact:
    """A new mission: library defaults (margins), nothing else."""
    return MissionArtifact()


MOVED_TO_ENVIRONMENT = ("orbit", "attitude_modes")
"""Sections of mission v1 that are environment parameters since v2 (ADR 0023)."""


def upgrade_mission(data: dict[str, Any]) -> dict[str, Any]:
    """A mission artifact of any version (JSON) as the current version. From v1 the sections in
    ``MOVED_TO_ENVIRONMENT`` are dropped: the project migration moves them first."""
    kept = {k: v for k, v in data.items() if k not in MOVED_TO_ENVIRONMENT}
    current = kept | {"schema_version": MISSION_SCHEMA_VERSION}
    return MissionArtifact.model_validate(current).model_dump(mode="json")


# ---------------------------------------------------------------- validation


def validate_mission(artifact: MissionArtifact) -> list[Problem]:
    """Completeness and consistency of a mission (``docs/etapas/mission.md``).

    Deterministic; returns the problems in form order. An empty list means valid.
    """
    p = Problems()
    _validate_general(p, artifact.general)
    _validate_envelope(p, artifact.envelope)
    _validate_criteria(p, artifact.criteria)
    return p.items


def _validate_general(p: Problems, general: General) -> None:
    p.required("general.launch_date", general.launch_date, "la fecha de lanzamiento")
    if p.required("general.design_life", general.design_life, "la vida útil"):
        p.positive("general.design_life", general.design_life, "La vida útil")


def _validate_envelope(p: Problems, envelope: Envelope) -> None:
    for name, label in (
        ("size_x", "la dimensión X"),
        ("size_y", "la dimensión Y"),
        ("size_z", "la dimensión Z"),
        ("mass", "la masa"),
    ):
        value = getattr(envelope, name)
        if p.required(f"envelope.{name}", value, label):
            p.positive(f"envelope.{name}", value, capitalize(label))


def _validate_criteria(p: Problems, criteria: Criteria) -> None:
    for name, label in (
        ("uncertainty_margin", "el margen de incertidumbre"),
        ("acceptance_margin", "el margen de aceptación"),
        ("qualification_margin", "el margen de calificación"),
    ):
        value = getattr(criteria, name)
        if p.required(f"criteria.{name}", value, label):
            p.non_negative(f"criteria.{name}", value, capitalize(label))
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
