from hestia_project.catalog import STAGES, TEMPLATES, StageType, TemplateId, accepts, catalog


def test_ten_stage_types_with_unique_numbers() -> None:
    assert len(STAGES) == 10
    assert len({s.number for s in STAGES.values()}) == 10


def test_cross_phase_transfers_are_valid_links() -> None:
    # docs/workflow-fases-0-1.md, «Vínculos válidos».
    assert accepts(StageType.DISCRETIZATION, StageType.MISSION)
    assert accepts(StageType.LOAD_CASES, StageType.ENVIRONMENT)
    assert accepts(StageType.SOLUTION, StageType.GLOBAL_BALANCE)
    assert accepts(StageType.MARGINS, StageType.MISSION)
    assert not accepts(StageType.MISSION, StageType.SENSITIVITY)
    # Iterations are not links.
    assert not accepts(StageType.GLOBAL_BALANCE, StageType.TCS_CONCEPT)
    assert not accepts(StageType.DISCRETIZATION, StageType.SENSITIVITY)


def test_templates_cover_each_phase_in_order() -> None:
    assert [s.value for s in TEMPLATES[TemplateId.PHASE_0].stages] == [
        "mission",
        "environment",
        "global_balance",
        "tcs_concept",
    ]
    assert len(TEMPLATES[TemplateId.PHASE_1].stages) == 6


def test_catalog_lists_everything() -> None:
    data = catalog()
    assert len(data.stages) == 10
    assert {t.id for t in data.templates} == set(TemplateId)
    assert [p.template for p in data.phases] == [TemplateId.PHASE_0, TemplateId.PHASE_1]
