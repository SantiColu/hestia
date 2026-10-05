"""Equipment stage artifact (``docs/etapas/equipment.md``, ADR 0017).

A form stage with two levels: the items (equipment) with their own modes (what a data sheet
says: a reaction wheel dissipates 3 W in standby, 8 W nominal, 20 W at peak) and the operating
modes of the satellite, each a configuration that picks the mode of every item. Every item is
also implicitly Off (0 W, non-operating limits), which is never entered: ``null`` in a state.

Every field is optional so a draft can be incomplete; ``validate_equipment`` reports what is
missing or inconsistent and never produces new values. Values are per item: with a
``quantity`` > 1 all the identical items are in the same mode. SI units, temperatures in K.
The ``x-`` extensions of the JSON Schema are those of ``hestia_core.mission``.
"""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.config import JsonDict

from hestia_core.forms import Problem, ProblemCode, Problems, unit

EQUIPMENT_SCHEMA_VERSION = 1
"""Version of ``EquipmentArtifact``. Bump on any incompatible change."""


class Subsystem(StrEnum):
    PAYLOAD = "payload"
    POWER = "power"
    OBDH = "obdh"
    TTC = "ttc"
    AOCS = "aocs"
    PROPULSION = "propulsion"
    THERMAL = "thermal"
    STRUCTURE = "structure"
    OTHER = "other"


SUBSYSTEM_LABELS: JsonDict = {
    "payload": "Carga útil",
    "power": "Potencia",
    "obdh": "Computadora de a bordo",
    "ttc": "Comunicaciones",
    "aocs": "Control de actitud",
    "propulsion": "Propulsión",
    "thermal": "Térmico",
    "structure": "Estructura",
    "other": "Otro",
}


class Location(StrEnum):
    """Where an item is mounted: a face of the body (``mission.Face``) or inside it."""

    PX = "+X"
    MX = "-X"
    PY = "+Y"
    MY = "-Y"
    PZ = "+Z"
    MZ = "-Z"
    INTERNAL = "internal"


LOCATION_LABELS: JsonDict = {
    location.value: "Interno" if location is Location.INTERNAL else location.value
    for location in Location
}

ITEM_ID_PREFIX = "item"
ITEM_MODE_ID_PREFIX = "imode"
OPERATING_MODE_ID_PREFIX = "opmode"

ID_DESCRIPTION = "Proposed by the client (`<prefix>_<hex>`) or generated when applied. Immutable."


def _id(prefix: str) -> JsonDict:
    """Extensions of an item id: the prefix of the ids a client may propose (ADR 0025)."""
    return {"x-id-prefix": prefix}


def _temperature(column: str) -> JsonDict:
    """Extensions of an absolute temperature: stored in K, shown in °C, short column title."""
    return unit("K", "°C", {"x-column-title": column})


class ItemMode(BaseModel):
    """A mode of an item's own (on): its dissipation, per item."""

    id: str | None = Field(
        default=None, description=ID_DESCRIPTION, json_schema_extra=_id(ITEM_MODE_ID_PREFIX)
    )
    name: str | None = Field(default=None, title="Nombre")
    dissipation: float | None = Field(
        default=None,
        title="Disipación",
        description="Disipación media en este modo, por ítem.",
        json_schema_extra=unit("W"),
    )


class Item(BaseModel):
    """An item of equipment (``quantity`` identical items, always in the same mode)."""

    id: str | None = Field(
        default=None, description=ID_DESCRIPTION, json_schema_extra=_id(ITEM_ID_PREFIX)
    )
    name: str | None = Field(default=None, title="Nombre")
    subsystem: Subsystem | None = Field(
        default=None, title="Subsistema", json_schema_extra={"x-enum-labels": SUBSYSTEM_LABELS}
    )
    quantity: int | None = Field(
        default=1,
        title="Cantidad",
        description="Ítems idénticos, siempre en el mismo modo.",
        json_schema_extra={"x-column-title": "Cant."},
    )
    mass: float | None = Field(
        default=None, title="Masa", description="Por ítem.", json_schema_extra=unit("kg")
    )
    location: Location | None = Field(
        default=None,
        title="Ubicación",
        description="Cara donde va montado, o interno.",
        json_schema_extra={"x-enum-labels": LOCATION_LABELS},
    )
    modes: list[ItemMode] = Field(
        default_factory=list[ItemMode],
        title="Modos",
        description="Modos propios del equipo (encendido). Apagado está siempre disponible.",
        json_schema_extra={"x-add-label": "Agregar modo"},
    )
    operating_min: float | None = Field(
        default=None,
        title="Temperatura operativa mínima",
        json_schema_extra=_temperature("T op. mín"),
    )
    operating_max: float | None = Field(
        default=None,
        title="Temperatura operativa máxima",
        json_schema_extra=_temperature("T op. máx"),
    )
    non_operating_min: float | None = Field(
        default=None,
        title="Temperatura no operativa mínima",
        description="Apagado. Opcional: con la máxima no operativa.",
        json_schema_extra=_temperature("T no op. mín"),
    )
    non_operating_max: float | None = Field(
        default=None,
        title="Temperatura no operativa máxima",
        description="Apagado. Opcional: con la mínima no operativa.",
        json_schema_extra=_temperature("T no op. máx"),
    )
    switch_on_min: float | None = Field(
        default=None,
        title="Temperatura mínima de encendido",
        description="Opcional.",
        json_schema_extra=_temperature("T encendido mín"),
    )


class OperatingMode(BaseModel):
    """A configuration of the whole satellite: the mode of every item, or Off (``null``)."""

    id: str | None = Field(
        default=None, description=ID_DESCRIPTION, json_schema_extra=_id(OPERATING_MODE_ID_PREFIX)
    )
    name: str | None = Field(default=None, title="Nombre")
    max_duration: float | None = Field(
        default=None,
        title="Duración máxima",
        description="Vacío: puede durar indefinidamente (estacionario).",
        json_schema_extra=unit("s", "h"),
    )
    states: dict[str, str | None] = Field(
        default_factory=dict[str, str | None],
        title="Estados",
        description="Id de cada equipo → id de uno de sus modos, o null (Apagado).",
    )


class EquipmentArtifact(BaseModel):
    """Artifact of the equipment stage: the items with their modes and the operating modes."""

    model_config = ConfigDict(extra="forbid")
    """Unknown sections are an error, so a request body can tell it from other artifacts."""

    schema_version: int = EQUIPMENT_SCHEMA_VERSION
    items: list[Item] = Field(
        default_factory=list[Item],
        title="Equipos",
        json_schema_extra={"x-add-label": "Agregar equipo"},
    )
    operating_modes: list[OperatingMode] = Field(
        default_factory=list[OperatingMode],
        title="Modos operativos",
        json_schema_extra={"x-add-label": "Agregar modo operativo"},
    )


DEFAULT_ITEM_ID = f"{ITEM_ID_PREFIX}_1"
DEFAULT_ITEM_MODE_ID = f"{ITEM_MODE_ID_PREFIX}_1"
DEFAULT_OPERATING_MODE_ID = f"{OPERATING_MODE_ID_PREFIX}_1"
"""Ids of the defaults: fixed (ids only need to be unique within an artifact)."""


def equipment_defaults() -> EquipmentArtifact:
    """A new equipment list: one aggregated item «Plataforma» with a «Nominal» mode, used by a
    «Nominal» operating mode. Enough at the start of phase 0, without a list of equipment."""
    return EquipmentArtifact(
        items=[
            Item(
                id=DEFAULT_ITEM_ID,
                name="Plataforma",
                modes=[ItemMode(id=DEFAULT_ITEM_MODE_ID, name="Nominal")],
            )
        ],
        operating_modes=[
            OperatingMode(
                id=DEFAULT_OPERATING_MODE_ID,
                name="Nominal",
                states={DEFAULT_ITEM_ID: DEFAULT_ITEM_MODE_ID},
            )
        ],
    )


# ---------------------------------------------------------------- validation


def validate_equipment(artifact: EquipmentArtifact) -> list[Problem]:
    """Completeness and consistency of the equipment (``docs/etapas/equipment.md``).

    Deterministic; returns the problems in form order. An empty list means valid.
    """
    p = Problems()
    _validate_items(p, artifact.items)
    _validate_operating_modes(p, artifact.items, artifact.operating_modes)
    return p.items


def _validate_items(p: Problems, items: list[Item]) -> None:
    if not items:
        p.add("items", ProblemCode.REQUIRED, "Falta al menos un equipo.")
    seen: set[str] = set()
    for i, item in enumerate(items):
        path = f"items[{i}]"
        p.unique_name(
            f"{path}.name", item.name, seen, "el nombre del equipo", "Ya hay un equipo llamado"
        )
        p.required(f"{path}.subsystem", item.subsystem, "el subsistema")
        if p.required(f"{path}.quantity", item.quantity, "la cantidad"):
            assert item.quantity is not None
            if item.quantity < 1:
                p.add(f"{path}.quantity", ProblemCode.MIN, "La cantidad tiene que ser al menos 1.")
        if p.required(f"{path}.mass", item.mass, "la masa"):
            p.non_negative(f"{path}.mass", item.mass, "La masa")
        p.required(f"{path}.location", item.location, "la ubicación")
        _validate_item_modes(p, path, item.modes)
        _validate_temperatures(p, path, item)


def _validate_item_modes(p: Problems, item_path: str, modes: list[ItemMode]) -> None:
    if not modes:
        p.add(f"{item_path}.modes", ProblemCode.REQUIRED, "Falta al menos un modo del equipo.")
    seen: set[str] = set()
    for j, mode in enumerate(modes):
        path = f"{item_path}.modes[{j}]"
        p.unique_name(
            f"{path}.name", mode.name, seen, "el nombre del modo", "El equipo ya tiene un modo"
        )
        if p.required(f"{path}.dissipation", mode.dissipation, "la disipación"):
            p.non_negative(f"{path}.dissipation", mode.dissipation, "La disipación")


def _validate_temperatures(p: Problems, path: str, item: Item) -> None:
    """Operating range, optional non-operating limits (both or none, containing the operating
    range) and the switch-on minimum (``docs/etapas/equipment.md``)."""
    op_min, op_max = item.operating_min, item.operating_max
    p.required(f"{path}.operating_min", op_min, "la temperatura mínima operativa")
    p.required(f"{path}.operating_max", op_max, "la temperatura máxima operativa")
    if op_min is not None and op_max is not None and not op_min < op_max:
        p.add(
            f"{path}.operating_max",
            ProblemCode.ORDER,
            "La máxima operativa tiene que ser mayor que la mínima.",
        )

    non_min, non_max = item.non_operating_min, item.non_operating_max
    if (non_min is None) != (non_max is None):
        missing, label = (
            ("non_operating_min", "la mínima")
            if non_min is None
            else ("non_operating_max", "la máxima")
        )
        p.add(
            f"{path}.{missing}",
            ProblemCode.REQUIRED,
            f"Falta {label} no operativa: los límites no operativos van de a pares.",
        )
    if non_min is not None and op_min is not None and non_min > op_min:
        p.add(
            f"{path}.non_operating_min",
            ProblemCode.ORDER,
            "La mínima no operativa no puede superar la mínima operativa.",
        )
    if non_max is not None and op_max is not None and non_max < op_max:
        p.add(
            f"{path}.non_operating_max",
            ProblemCode.ORDER,
            "La máxima no operativa no puede ser menor que la máxima operativa.",
        )

    switch_on = item.switch_on_min
    if switch_on is None:
        return
    if op_max is not None and switch_on > op_max:
        p.add(
            f"{path}.switch_on_min",
            ProblemCode.ORDER,
            "La mínima de encendido no puede superar la máxima operativa.",
        )
    if non_min is not None and switch_on < non_min:
        p.add(
            f"{path}.switch_on_min",
            ProblemCode.ORDER,
            "La mínima de encendido no puede ser menor que la mínima no operativa.",
        )


def _item_label(item: Item, index: int) -> str:
    return (item.name or "").strip() or f"Equipo {index + 1}"


def _validate_operating_modes(
    p: Problems, items: list[Item], operating_modes: list[OperatingMode]
) -> None:
    """At least one operating mode, unique names, an optional positive duration and exactly one
    state per item that is Off or one of that item's modes."""
    if not operating_modes:
        p.add("operating_modes", ProblemCode.REQUIRED, "Falta al menos un modo operativo.")
    referable, unreferable = _referable_items(items)
    seen: set[str] = set()
    for k, mode in enumerate(operating_modes):
        path = f"operating_modes[{k}]"
        p.unique_name(
            f"{path}.name",
            mode.name,
            seen,
            "el nombre del modo operativo",
            "Ya hay un modo operativo llamado",
        )
        p.positive(f"{path}.max_duration", mode.max_duration, "La duración máxima")
        _validate_states(p, f"{path}.states", mode.states, referable)
        for i, item in unreferable:
            p.add(
                f"{path}.states",
                ProblemCode.REQUIRED,
                f"Falta el modo de «{_item_label(item, i)}»: su id falta o está repetido.",
            )


@dataclass(frozen=True)
class _Referable:
    """An item that states can reference: its position and the ids of its referable modes."""

    index: int
    item: Item
    mode_ids: frozenset[str]


def _referable_items(items: list[Item]) -> tuple[dict[str, _Referable], list[tuple[int, Item]]]:
    """Items (and modes) by id, and the items no state can reference. Only the first item or mode
    with an id counts: a missing or repeated id gets a new one when applied (ADR 0025)."""
    referable: dict[str, _Referable] = {}
    unreferable: list[tuple[int, Item]] = []
    seen_modes: set[str] = set()
    for i, item in enumerate(items):
        mode_ids = {m.id for m in item.modes if m.id is not None and m.id not in seen_modes}
        seen_modes |= mode_ids
        if item.id is None or item.id in referable:
            unreferable.append((i, item))
        else:
            referable[item.id] = _Referable(i, item, frozenset(mode_ids))
    return referable, unreferable


def _validate_states(
    p: Problems, path: str, states: dict[str, str | None], referable: dict[str, _Referable]
) -> None:
    for item_id, entry in referable.items():
        label = _item_label(entry.item, entry.index)
        if item_id not in states:
            p.add(
                f"{path}.{item_id}",
                ProblemCode.REQUIRED,
                f"Falta el modo de «{label}» (o Apagado).",
            )
            continue
        mode_id = states[item_id]
        if mode_id is not None and mode_id not in entry.mode_ids:
            p.add(
                f"{path}.{item_id}",
                ProblemCode.INVALID_REFERENCE,
                f"El modo elegido para «{label}» no es uno de sus modos.",
            )
    for key in states:
        if key not in referable:
            p.add(f"{path}.{key}", ProblemCode.NOT_ALLOWED, f"«{key}» no es un equipo de la lista.")
