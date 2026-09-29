from hestia_project.catalog import (
    ORDER,
    STAGES,
    TEMPLATES,
    StageKind,
    StageType,
    TemplateId,
    before,
    catalog,
)

S = StageType


def test_eleven_stage_types_with_unique_numbers_in_catalog_order() -> None:
    assert len(STAGES) == 11
    numbers = [s.number for s in STAGES.values()]
    assert numbers == sorted(numbers, key=lambda n: tuple(int(p) for p in n.split(".")))
    assert len(set(numbers)) == 11
    assert [ORDER[s] for s in STAGES] == list(range(11))


def test_phase0_numbering() -> None:
    # docs/workflow-fases-0-1.md, «Fase 0 · viabilidad».
    assert {s: STAGES[s].number for s in list(S)[:5]} == {
        S.MISSION: "0.1",
        S.ENVIRONMENT: "0.2",
        S.EQUIPMENT: "0.3",
        S.GLOBAL_BALANCE: "0.4",
        S.TCS_CONCEPT: "0.5",
    }


def test_classes() -> None:
    roots = {s for s, spec in STAGES.items() if spec.root}
    forms = {s for s, spec in STAGES.items() if spec.kind is StageKind.FORM}
    assert roots == forms == {S.MISSION, S.EQUIPMENT}
    assert all(STAGES[s].requires == () for s in roots)
    # Mission (form) and environment (computation) are implemented; equipment is registered
    # without a form.
    assert {s for s, spec in STAGES.items() if spec.implemented} == {S.MISSION, S.ENVIRONMENT}


def test_requirements_follow_the_doc_table() -> None:
    assert STAGES[S.ENVIRONMENT].requires == (S.MISSION,)
    assert set(STAGES[S.GLOBAL_BALANCE].requires) == {S.MISSION, S.ENVIRONMENT, S.EQUIPMENT}
    assert STAGES[S.TCS_CONCEPT].requires == (S.GLOBAL_BALANCE,)
    assert set(STAGES[S.DISCRETIZATION].requires) == {S.MISSION, S.EQUIPMENT, S.TCS_CONCEPT}
    assert STAGES[S.COUPLINGS].requires == (S.DISCRETIZATION,)
    assert set(STAGES[S.LOAD_CASES].requires) == {
        S.COUPLINGS,
        S.ENVIRONMENT,
        S.EQUIPMENT,
        S.MISSION,
    }
    assert set(STAGES[S.SOLUTION].requires) == {S.LOAD_CASES, S.GLOBAL_BALANCE}
    assert set(STAGES[S.MARGINS].requires) == {S.SOLUTION, S.EQUIPMENT, S.MISSION}
    assert STAGES[S.SENSITIVITY].requires == (S.MARGINS,)


def test_requirements_come_before_in_catalog_order() -> None:
    for stage, spec in STAGES.items():
        assert all(before(r, stage) for r in spec.requires), stage


def test_templates() -> None:
    phase0 = TEMPLATES[TemplateId.PHASE_0]
    assert phase0.stages == (
        S.MISSION,
        S.ENVIRONMENT,
        S.EQUIPMENT,
        S.GLOBAL_BALANCE,
        S.TCS_CONCEPT,
    )
    assert set(phase0.links) == {
        (S.MISSION, S.ENVIRONMENT),
        (S.ENVIRONMENT, S.GLOBAL_BALANCE),
        (S.EQUIPMENT, S.GLOBAL_BALANCE),
        (S.GLOBAL_BALANCE, S.TCS_CONCEPT),
    }
    phase1 = TEMPLATES[TemplateId.PHASE_1]
    assert len(phase1.stages) == 6
    assert phase1.links == tuple(zip(phase1.stages, phase1.stages[1:], strict=False))


def test_catalog_lists_everything() -> None:
    data = catalog()
    assert [s.stage for s in data.stages] == list(S)
    assert {t.id for t in data.templates} == set(TemplateId)
    assert [p.template for p in data.phases] == [TemplateId.PHASE_0, TemplateId.PHASE_1]
    equipment = next(s for s in data.stages if s.stage is S.EQUIPMENT)
    assert equipment.root and equipment.kind is StageKind.FORM and not equipment.implemented
    assert equipment.order == 2
