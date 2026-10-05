"""Catalog of stage types and system templates (phases 0 and 1).

Source of truth for the schematic rules (``docs/workflow-fases-0-1.md``, ADR 0016): each stage
type declares its class (root, form, computation, collector), the stage types it requires in its
context and its place in the catalog order. Links are validated against the context, not against
per-input sources (``schematic.check_link``).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from hestia_project.base import Schema


class Phase(StrEnum):
    PHASE_0 = "phase_0"
    PHASE_1 = "phase_1"


class StageType(StrEnum):
    """Stage types in catalog order (0.1 < 0.2 < … < 0.5 < 1.1 < … < 1.6)."""

    MISSION = "mission"
    ENVIRONMENT = "environment"
    EQUIPMENT = "equipment"
    GLOBAL_BALANCE = "global_balance"
    TCS_CONCEPT = "tcs_concept"
    DISCRETIZATION = "discretization"
    COUPLINGS = "couplings"
    LOAD_CASES = "load_cases"
    SOLUTION = "solution"
    MARGINS = "margins"
    SENSITIVITY = "sensitivity"


class StageKind(StrEnum):
    """How a stage produces its artifact."""

    FORM = "form"
    """The artifact is what the user enters, validated (ADR 0017). «Running» is validating."""
    COMPUTATION = "computation"
    """The artifact is computed from the context."""
    COLLECTOR = "collector"
    """Post-processing: accepts several parents of the same type, passes no context on."""


class TemplateId(StrEnum):
    PHASE_0 = "phase_0"
    PHASE_1 = "phase_1"


@dataclass(frozen=True)
class StageSpec:
    stage: StageType
    phase: Phase
    number: str
    """Stage number (0.1, 1.3…). Metadata only: never part of an id, never shown in the UI."""
    default_name: str
    kind: StageKind
    root: bool
    """Roots never have parents (``mission``, ``equipment``)."""
    requires: tuple[StageType, ...]
    """Stage types that must be in the context of a cell of this type for it to run."""
    implemented: bool
    """Whether the stage has an editor or a computation. Unimplemented stages still work in the
    schematic (create, link, branch)."""

    @property
    def order(self) -> int:
        """Position in the catalog order (link rule 5)."""
        return ORDER[self.stage]


S = StageType
K = StageKind

ORDER: Mapping[StageType, int] = {stage: i for i, stage in enumerate(StageType)}

STAGES: dict[StageType, StageSpec] = {
    spec.stage: spec
    for spec in (
        StageSpec(S.MISSION, Phase.PHASE_0, "0.1", "Misión", K.FORM, True, (), True),
        StageSpec(
            S.ENVIRONMENT,
            Phase.PHASE_0,
            "0.2",
            "Entorno",
            K.COMPUTATION,
            False,
            (S.MISSION,),
            True,
        ),
        StageSpec(S.EQUIPMENT, Phase.PHASE_0, "0.3", "Equipos", K.FORM, True, (), True),
        StageSpec(
            S.GLOBAL_BALANCE,
            Phase.PHASE_0,
            "0.4",
            "Balance global",
            K.COMPUTATION,
            False,
            (S.MISSION, S.ENVIRONMENT, S.EQUIPMENT),
            False,
        ),
        StageSpec(
            S.TCS_CONCEPT,
            Phase.PHASE_0,
            "0.5",
            "Concepto TCS",
            K.COMPUTATION,
            False,
            (S.GLOBAL_BALANCE,),
            False,
        ),
        StageSpec(
            S.DISCRETIZATION,
            Phase.PHASE_1,
            "1.1",
            "Discretización",
            K.COMPUTATION,
            False,
            (S.MISSION, S.EQUIPMENT, S.TCS_CONCEPT),
            False,
        ),
        StageSpec(
            S.COUPLINGS,
            Phase.PHASE_1,
            "1.2",
            "Acoplamientos",
            K.COMPUTATION,
            False,
            (S.DISCRETIZATION,),
            False,
        ),
        StageSpec(
            S.LOAD_CASES,
            Phase.PHASE_1,
            "1.3",
            "Casos de carga",
            K.COMPUTATION,
            False,
            (S.COUPLINGS, S.ENVIRONMENT, S.EQUIPMENT, S.MISSION),
            False,
        ),
        StageSpec(
            S.SOLUTION,
            Phase.PHASE_1,
            "1.4",
            "Solución",
            K.COMPUTATION,
            False,
            (S.LOAD_CASES, S.GLOBAL_BALANCE),
            False,
        ),
        StageSpec(
            S.MARGINS,
            Phase.PHASE_1,
            "1.5",
            "Márgenes",
            K.COMPUTATION,
            False,
            (S.SOLUTION, S.EQUIPMENT, S.MISSION),
            False,
        ),
        StageSpec(
            S.SENSITIVITY,
            Phase.PHASE_1,
            "1.6",
            "Sensibilidad",
            K.COMPUTATION,
            False,
            (S.MARGINS,),
            False,
        ),
    )
}


@dataclass(frozen=True)
class TemplateSpec:
    id: TemplateId
    phase: Phase
    default_name: str
    description: str
    stages: tuple[StageType, ...]
    """Cells in display (reading) order."""
    links: tuple[tuple[StageType, StageType], ...]
    """Links between the template's cells, as (source, target) stage types."""


def _chain(stages: tuple[StageType, ...]) -> tuple[tuple[StageType, StageType], ...]:
    return tuple(pairwise(stages))


_PHASE_1_STAGES = tuple(s for s in StageType if STAGES[s].phase is Phase.PHASE_1)

TEMPLATES: Mapping[TemplateId, TemplateSpec] = {
    spec.id: spec
    for spec in (
        TemplateSpec(
            TemplateId.PHASE_0,
            Phase.PHASE_0,
            "Fase 0 · Viabilidad",
            "Misión, entorno, equipos, balance global y concepto TCS, ya vinculados.",
            tuple(s for s in StageType if STAGES[s].phase is Phase.PHASE_0),
            (
                (S.MISSION, S.ENVIRONMENT),
                (S.ENVIRONMENT, S.GLOBAL_BALANCE),
                (S.EQUIPMENT, S.GLOBAL_BALANCE),
                (S.GLOBAL_BALANCE, S.TCS_CONCEPT),
            ),
        ),
        TemplateSpec(
            TemplateId.PHASE_1,
            Phase.PHASE_1,
            "Fase 1 · Modelo nodal",
            "Discretización a sensibilidad, en cadena.",
            _PHASE_1_STAGES,
            _chain(_PHASE_1_STAGES),
        ),
    )
}


def before(a: StageType, b: StageType) -> bool:
    """Whether ``a`` comes before ``b`` in the catalog order."""
    return ORDER[a] < ORDER[b]


# ---------------------------------------------------------------- public catalog (API)


class StageInfo(Schema):
    stage: StageType
    phase: Phase
    number: str
    """Metadata for documentation; never shown in the UI."""
    order: int
    name: str
    kind: StageKind
    root: bool
    requires: list[StageType]
    implemented: bool


class TemplateLink(Schema):
    source: StageType
    target: StageType


class TemplateInfo(Schema):
    id: TemplateId
    phase: Phase
    name: str
    description: str
    stages: list[StageType]
    links: list[TemplateLink]


class PhaseInfo(Schema):
    phase: Phase
    name: str
    template: TemplateId


class Catalog(Schema):
    phases: list[PhaseInfo]
    stages: list[StageInfo]
    """In catalog order."""
    templates: list[TemplateInfo]


def catalog() -> Catalog:
    return Catalog(
        phases=[
            PhaseInfo(phase=t.phase, name=t.default_name, template=t.id) for t in TEMPLATES.values()
        ],
        stages=[
            StageInfo(
                stage=s.stage,
                phase=s.phase,
                number=s.number,
                order=s.order,
                name=s.default_name,
                kind=s.kind,
                root=s.root,
                requires=list(s.requires),
                implemented=s.implemented,
            )
            for s in STAGES.values()
        ],
        templates=[
            TemplateInfo(
                id=t.id,
                phase=t.phase,
                name=t.default_name,
                description=t.description,
                stages=list(t.stages),
                links=[TemplateLink(source=a, target=b) for a, b in t.links],
            )
            for t in TEMPLATES.values()
        ],
    )
