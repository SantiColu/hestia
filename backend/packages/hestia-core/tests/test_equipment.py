"""Equipment artifact and its validation (docs/etapas/equipment.md, ADR 0017)."""

from typing import Any

from hestia_core.equipment import (
    EquipmentArtifact,
    Location,
    equipment_defaults,
    validate_equipment,
)
from hestia_core.forms import ProblemCode

C = ProblemCode

WHEEL: dict[str, Any] = {
    "id": "item_a1",
    "name": "Rueda de reacción",
    "subsystem": "aocs",
    "quantity": 4,
    "mass": 0.9,
    "location": "internal",
    "modes": [
        {"id": "imode_a1", "name": "Standby", "dissipation": 3.0},
        {"id": "imode_a2", "name": "Nominal", "dissipation": 8.0},
    ],
    "operating_min": 253.15,
    "operating_max": 333.15,
}


def artifact(*items: dict[str, Any]) -> EquipmentArtifact:
    listed = list(items) or [WHEEL]
    return EquipmentArtifact.model_validate(
        {
            "items": listed,
            "operating_modes": [
                {"id": "opmode_1", "name": "Nominal", "states": {i["id"]: None for i in listed}}
            ],
        }
    )


def wheel(**changes: Any) -> dict[str, Any]:
    return WHEEL | changes


def codes(value: EquipmentArtifact) -> set[tuple[str, ProblemCode]]:
    return {(p.path, p.code) for p in validate_equipment(value)}


def test_valid_equipment_has_no_problems() -> None:
    assert validate_equipment(artifact()) == []


def test_defaults_are_one_aggregated_item_used_by_one_operating_mode() -> None:
    defaults = equipment_defaults()
    assert defaults.schema_version == 1
    [item] = defaults.items
    assert item.name == "Plataforma" and item.quantity == 1
    assert [m.name for m in item.modes] == ["Nominal"]
    [mode] = defaults.operating_modes
    assert mode.name == "Nominal"
    assert mode.states == {item.id: item.modes[0].id}


def test_defaults_report_what_is_required() -> None:
    assert codes(equipment_defaults()) == {
        ("items[0].subsystem", C.REQUIRED),
        ("items[0].mass", C.REQUIRED),
        ("items[0].location", C.REQUIRED),
        ("items[0].modes[0].dissipation", C.REQUIRED),
        ("items[0].operating_min", C.REQUIRED),
        ("items[0].operating_max", C.REQUIRED),
    }
    assert all(p.message for p in validate_equipment(equipment_defaults()))


def test_at_least_one_item_and_one_mode_per_item() -> None:
    assert ("items", C.REQUIRED) in codes(EquipmentArtifact())
    assert codes(artifact(wheel(modes=[]))) == {("items[0].modes", C.REQUIRED)}


def test_unique_names_of_items_and_of_modes_within_an_item() -> None:
    other = wheel(id="item_b1", name=" rueda de  REACCIÓN ")
    assert codes(artifact(WHEEL, other)) == {("items[1].name", C.DUPLICATE_NAME)}
    modes = [*WHEEL["modes"], {"id": "imode_a3", "name": "nominal", "dissipation": 1.0}]
    assert codes(artifact(wheel(modes=modes))) == {("items[0].modes[2].name", C.DUPLICATE_NAME)}
    # The same mode name in two items is fine.
    assert codes(artifact(WHEEL, wheel(id="item_b1", name="Transmisor"))) == set()


def test_quantity_mass_and_dissipation_bounds() -> None:
    assert codes(artifact(wheel(quantity=0))) == {("items[0].quantity", C.MIN)}
    assert codes(artifact(wheel(mass=-0.1))) == {("items[0].mass", C.MIN)}
    assert codes(artifact(wheel(mass=0.0))) == set()
    modes = [{"id": "imode_a1", "name": "Standby", "dissipation": -1.0}]
    assert codes(artifact(wheel(modes=modes))) == {("items[0].modes[0].dissipation", C.MIN)}
    zero = [{"id": "imode_a1", "name": "Standby", "dissipation": 0.0}]
    assert codes(artifact(wheel(modes=zero))) == set()


def test_operating_range_order() -> None:
    assert codes(artifact(wheel(operating_max=253.15))) == {("items[0].operating_max", C.ORDER)}


def test_non_operating_limits_come_in_pairs_and_contain_the_operating_range() -> None:
    assert codes(artifact(wheel(non_operating_min=233.15))) == {
        ("items[0].non_operating_max", C.REQUIRED)
    }
    assert codes(artifact(wheel(non_operating_max=353.15))) == {
        ("items[0].non_operating_min", C.REQUIRED)
    }
    assert codes(artifact(wheel(non_operating_min=233.15, non_operating_max=353.15))) == set()
    assert codes(artifact(wheel(non_operating_min=263.15, non_operating_max=323.15))) == {
        ("items[0].non_operating_min", C.ORDER),
        ("items[0].non_operating_max", C.ORDER),
    }


def test_switch_on_minimum_between_non_operating_minimum_and_operating_maximum() -> None:
    assert codes(artifact(wheel(switch_on_min=243.15))) == set()
    assert codes(artifact(wheel(switch_on_min=343.15))) == {("items[0].switch_on_min", C.ORDER)}
    limits = {"non_operating_min": 233.15, "non_operating_max": 353.15}
    assert codes(artifact(wheel(switch_on_min=223.15, **limits))) == {
        ("items[0].switch_on_min", C.ORDER)
    }
    assert codes(artifact(wheel(switch_on_min=233.15, **limits))) == set()


def test_location_is_a_face_or_internal() -> None:
    assert {location.value for location in Location} == {
        "+X",
        "-X",
        "+Y",
        "-Y",
        "+Z",
        "-Z",
        "internal",
    }


# ---------------------------------------------------------------- operating modes


TRANSMITTER: dict[str, Any] = WHEEL | {
    "id": "item_b1",
    "name": "Transmisor",
    "quantity": 1,
    "modes": [{"id": "imode_b1", "name": "Transmisión", "dissipation": 15.0}],
}


def configured(*modes: dict[str, Any]) -> EquipmentArtifact:
    return EquipmentArtifact.model_validate(
        {"items": [WHEEL, TRANSMITTER], "operating_modes": modes}
    )


def operating_mode(states: dict[str, str | None], **fields: Any) -> dict[str, Any]:
    return {"id": "opmode_1", "name": "Nominal", "states": states} | fields


BOTH = {"item_a1": "imode_a2", "item_b1": None}


def test_at_least_one_operating_mode_with_unique_names() -> None:
    assert codes(configured()) == {("operating_modes", C.REQUIRED)}
    second = operating_mode(BOTH, id="opmode_2", name=" nominal")
    assert codes(configured(operating_mode(BOTH), second)) == {
        ("operating_modes[1].name", C.DUPLICATE_NAME)
    }
    assert codes(configured(operating_mode(BOTH, name=None))) == {
        ("operating_modes[0].name", C.REQUIRED)
    }


def test_max_duration_is_optional_and_positive() -> None:
    assert codes(configured(operating_mode(BOTH, max_duration=3600.0))) == set()
    assert codes(configured(operating_mode(BOTH, max_duration=0.0))) == {
        ("operating_modes[0].max_duration", C.MIN)
    }


def test_states_have_exactly_one_entry_per_item() -> None:
    missing = operating_mode({"item_a1": "imode_a1"})
    assert codes(configured(missing)) == {("operating_modes[0].states.item_b1", C.REQUIRED)}
    extra = operating_mode(BOTH | {"item_zz": None})
    assert codes(configured(extra)) == {("operating_modes[0].states.item_zz", C.NOT_ALLOWED)}


def test_each_state_is_off_or_a_mode_of_that_item() -> None:
    assert codes(configured(operating_mode({"item_a1": None, "item_b1": None}))) == set()
    other_item = operating_mode({"item_a1": "imode_b1", "item_b1": None})
    assert codes(configured(other_item)) == {
        ("operating_modes[0].states.item_a1", C.INVALID_REFERENCE)
    }
    unknown = operating_mode({"item_a1": "imode_zz", "item_b1": None})
    problems = validate_equipment(configured(unknown))
    assert [(p.path, p.code) for p in problems] == [
        ("operating_modes[0].states.item_a1", C.INVALID_REFERENCE)
    ]
    assert "Rueda de reacción" in problems[0].message


def test_items_without_a_usable_id_have_no_state() -> None:
    # No id (or a repeated one, replaced when applied): no state can reference it yet.
    twin = TRANSMITTER | {"id": "item_a1", "name": "Gemelo"}
    value = EquipmentArtifact.model_validate(
        {"items": [WHEEL, twin], "operating_modes": [operating_mode({"item_a1": None})]}
    )
    assert codes(value) == {("operating_modes[0].states", C.REQUIRED)}
