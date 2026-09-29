"""Registry of implemented forms (ADR 0017, 0021) and helpers on their stored state.

A form stage's artifact is what the user enters, validated: the model, its library defaults and
its validation live in ``hestia_core``. The parameters of a computation stage are edited the
same way. Operations on artifacts are in ``artifacts``.
"""

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from pydantic import BaseModel

from hestia_core.forms import Problem
from hestia_core.mission import MissionArtifact, mission_defaults, validate_mission
from hestia_project.catalog import STAGES, StageKind, StageType
from hestia_project.errors import StageNotImplementedError
from hestia_project.model import CellStatus, FieldProvenance, FieldSource, FormState

PENDING_CHANGE = "__pending__"
"""Placeholder ``change_id`` for provenance set by an operation; ``ProjectDocument`` replaces it
with the id of the change that records the operation."""


FormContext = Mapping[StageType, BaseModel]
"""Upstream inputs a form is validated against: the artifacts of the form stages in the cell's
context, by stage type. Empty for roots and when nothing is linked."""


@dataclass(frozen=True)
class FormSpec:
    model: type[BaseModel]
    defaults: Callable[[], BaseModel]
    validate: Callable[[Any, FormContext], list[Problem]]
    id_prefixes: dict[str, str] = field(default_factory=dict[str, str])
    """Lists whose items get a backend id (list path → id prefix)."""


FORMS: dict[StageType, FormSpec] = {
    StageType.MISSION: FormSpec(
        model=MissionArtifact,
        defaults=mission_defaults,
        validate=lambda artifact, _context: validate_mission(artifact),
        id_prefixes={"attitude_modes": "mode"},
    ),
}
"""Implemented forms: form stages (``mission``; ``equipment`` has no editor yet) and the
parameters of computation stages (registered by ``computations``)."""


def is_form_stage(stage: StageType) -> bool:
    """Form stages: the artifact is the form. Computation stages only edit parameters."""
    return STAGES[stage].kind is StageKind.FORM


def form_spec(stage: StageType) -> FormSpec:
    spec = FORMS.get(stage)
    if spec is None:
        name = STAGES[stage].default_name
        if STAGES[stage].kind is StageKind.FORM:
            raise StageNotImplementedError(
                f"La etapa «{name}» todavía no tiene formulario.", stage=stage
            )
        raise StageNotImplementedError(
            f"La etapa «{name}» todavía no tiene parámetros ni cálculo.", stage=stage
        )
    return spec


def artifact_schema(stage: StageType) -> dict[str, Any]:
    """JSON Schema of a form stage's artifact (or a computation stage's parameters), with the
    ``x-`` extensions the UI builds the form from (units, labels, conditional fields)."""
    return form_spec(stage).model.model_json_schema()


def status_for(problems: list[Problem]) -> CellStatus:
    return CellStatus.FAILED if problems else CellStatus.UP_TO_DATE


def new_form_state(stage: StageType, change_id: str | None = PENDING_CHANGE) -> FormState | None:
    """State of a new cell: library defaults with ``default`` provenance. None if not a form."""
    spec = FORMS.get(stage)
    if spec is None:
        return None
    artifact = spec.defaults()
    data = artifact.model_dump(mode="json")
    return FormState(
        artifact=data,
        problems=spec.validate(artifact, {}),
        provenance={
            leaf.path: FieldProvenance(source=FieldSource.DEFAULT, change_id=change_id)
            for leaf in leaves(data)
            if not _is_empty(leaf.value)
        },
    )


def form_from_artifact(
    stage: StageType, data: dict[str, Any], sources: dict[str, FieldSource], applied: bool
) -> FormState:
    """State for a copied artifact (paste): revalidated without context, provenance from
    ``sources``."""
    spec = form_spec(stage)
    artifact = spec.model.model_validate(data)
    dumped = artifact.model_dump(mode="json")
    return FormState(
        artifact=dumped,
        applied_change_id=PENDING_CHANGE if applied else None,
        problems=spec.validate(artifact, {}),
        provenance={
            leaf.path: FieldProvenance(
                source=sources.get(leaf.path, FieldSource.ENTERED), change_id=PENDING_CHANGE
            )
            for leaf in leaves(dumped)
            if not _is_empty(leaf.value)
        },
    )


# ---------------------------------------------------------------- leaf fields


@dataclass(frozen=True)
class Leaf:
    path: str
    """Path shown to people and used by problems and provenance: ``attitude_modes[0].name``."""
    key: str
    """Stable key for diffs: list items by id when they have one (``attitude_modes[#m1].name``)."""
    value: Any


_SKIPPED = {"schema_version", "id"}


def leaves(data: dict[str, Any], path: str = "", key: str = "") -> Iterator[Leaf]:
    """Leaf fields of an artifact (JSON). Lists of scalars are one leaf; ids are not leaves."""
    for name, value in data.items():
        if name in _SKIPPED:
            continue
        p = f"{path}.{name}" if path else name
        k = f"{key}.{name}" if key else name
        if isinstance(value, dict):
            yield from leaves(cast(dict[str, Any], value), p, k)
        elif _is_object_list(value):
            for i, item in enumerate(cast(list[dict[str, Any]], value)):
                item_id = item.get("id")
                yield from leaves(item, f"{p}[{i}]", f"{k}[#{item_id}]" if item_id else f"{k}[{i}]")
        else:
            yield Leaf(p, k, value)


def _is_object_list(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(v, dict) for v in cast(list[Any], value))


def _is_empty(value: Any) -> bool:
    return value is None or value == []
