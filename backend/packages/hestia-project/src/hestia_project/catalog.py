"""Catalog of stage types and system templates (phases 0 and 1).

Source of truth for which links are valid: each stage type declares which stage types can feed
its inputs (``docs/workflow-fases-0-1.md``, «Vínculos válidos»). Every stage type has a single
output, so an input is identified by the stage type that feeds it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from hestia_project.base import Schema


class Phase(StrEnum):
    PHASE_0 = "phase_0"
    PHASE_1 = "phase_1"


class StageType(StrEnum):
    MISSION = "mission"
    ENVIRONMENT = "environment"
    GLOBAL_BALANCE = "global_balance"
    TCS_CONCEPT = "tcs_concept"
    DISCRETIZATION = "discretization"
    COUPLINGS = "couplings"
    LOAD_CASES = "load_cases"
    SOLUTION = "solution"
    MARGINS = "margins"
    SENSITIVITY = "sensitivity"


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
    inputs: tuple[StageType, ...]
    """Stage types that can feed this stage, one input each."""


S = StageType

STAGES: Mapping[StageType, StageSpec] = {
    spec.stage: spec
    for spec in (
        StageSpec(S.MISSION, Phase.PHASE_0, "0.1", "Misión", ()),
        StageSpec(S.ENVIRONMENT, Phase.PHASE_0, "0.2", "Entorno", (S.MISSION,)),
        StageSpec(S.GLOBAL_BALANCE, Phase.PHASE_0, "0.3", "Balance global", (S.ENVIRONMENT,)),
        StageSpec(S.TCS_CONCEPT, Phase.PHASE_0, "0.4", "Concepto TCS", (S.GLOBAL_BALANCE,)),
        # Phase 1. Cross-phase transfers: mission → discretization (units → nodes),
        # environment → load_cases, global_balance → solution (sanity check) and
        # mission → margins (temperature limits).
        StageSpec(S.DISCRETIZATION, Phase.PHASE_1, "1.1", "Discretización", (S.MISSION,)),
        StageSpec(S.COUPLINGS, Phase.PHASE_1, "1.2", "Acoplamientos", (S.DISCRETIZATION,)),
        StageSpec(
            S.LOAD_CASES, Phase.PHASE_1, "1.3", "Casos de carga", (S.COUPLINGS, S.ENVIRONMENT)
        ),
        StageSpec(S.SOLUTION, Phase.PHASE_1, "1.4", "Solución", (S.LOAD_CASES, S.GLOBAL_BALANCE)),
        StageSpec(S.MARGINS, Phase.PHASE_1, "1.5", "Márgenes", (S.SOLUTION, S.MISSION)),
        StageSpec(S.SENSITIVITY, Phase.PHASE_1, "1.6", "Sensibilidad", (S.MARGINS,)),
    )
}


@dataclass(frozen=True)
class TemplateSpec:
    id: TemplateId
    phase: Phase
    default_name: str
    description: str
    stages: tuple[StageType, ...]


TEMPLATES: Mapping[TemplateId, TemplateSpec] = {
    spec.id: spec
    for spec in (
        TemplateSpec(
            TemplateId.PHASE_0,
            Phase.PHASE_0,
            "Fase 0 · Viabilidad",
            "Misión, entorno, balance global y concepto TCS, ya vinculados.",
            tuple(s for s in StageType if STAGES[s].phase is Phase.PHASE_0),
        ),
        TemplateSpec(
            TemplateId.PHASE_1,
            Phase.PHASE_1,
            "Fase 1 · Modelo nodal",
            "Discretización a sensibilidad, ya vinculadas.",
            tuple(s for s in StageType if STAGES[s].phase is Phase.PHASE_1),
        ),
    )
}


def accepts(target: StageType, source: StageType) -> bool:
    """Whether a cell of type ``source`` can feed an input of a cell of type ``target``."""
    return source in STAGES[target].inputs


# ---------------------------------------------------------------- public catalog (API)


class StageInfo(Schema):
    stage: StageType
    phase: Phase
    number: str
    name: str
    inputs: list[StageType]


class TemplateInfo(Schema):
    id: TemplateId
    phase: Phase
    name: str
    description: str
    stages: list[StageType]


class PhaseInfo(Schema):
    phase: Phase
    name: str
    template: TemplateId


class Catalog(Schema):
    phases: list[PhaseInfo]
    stages: list[StageInfo]
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
                name=s.default_name,
                inputs=list(s.inputs),
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
            )
            for t in TEMPLATES.values()
        ],
    )
