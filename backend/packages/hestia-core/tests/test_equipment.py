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
