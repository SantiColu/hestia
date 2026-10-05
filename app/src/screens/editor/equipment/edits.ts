import type { EquipmentArtifact, EquipmentItem, ItemMode, OperatingMode } from "@/api/client";
import { newId } from "@/lib/ids";
import type { JsonObject } from "@/lib/json";
import type { EquipmentSchema } from "./equipment-schema";

/**
 * Edits of an equipment draft (docs/etapas/equipment.md, «Comportamiento al editar»). They only
 * keep the draft's own references whole when lists change; the API validates everything.
 */

type Prefixes = EquipmentSchema["prefixes"];

/** The draft as the contract types it: plain JSON from the API that the API validates. */
export function asEquipment(value: JsonObject): EquipmentArtifact {
  return value as unknown as EquipmentArtifact;
}

/** An edited equipment draft back as the JSON the draft store keeps. */
export function toDraft(value: EquipmentArtifact): JsonObject {
  return value as unknown as JsonObject;
}

export function itemsOf(artifact: EquipmentArtifact): EquipmentItem[] {
  return artifact.items ?? [];
}

/** «Rueda de reacción», or «Equipo 3» while it has no name. */
export function itemName(item: EquipmentItem, index: number): string {
  return item.name?.trim() || `Equipo ${index + 1}`;
}

/** «Adquisición», or «Modo operativo 2» while it has no name. */
export function operatingModeName(mode: OperatingMode, index: number): string {
  return mode.name?.trim() || `Modo operativo ${index + 1}`;
}

export function modesOf(item: EquipmentItem): ItemMode[] {
  return item.modes ?? [];
}

export function operatingModesOf(artifact: EquipmentArtifact): OperatingMode[] {
  return artifact.operating_modes ?? [];
}

function withItems(artifact: EquipmentArtifact, items: EquipmentItem[]): EquipmentArtifact {
  return { ...artifact, items };
}

type States = NonNullable<OperatingMode["states"]>;

/** Every operating mode with its states replaced by `edit`, which must not mutate them. */
function editStates(artifact: EquipmentArtifact, edit: (states: States) => States) {
  return {
    ...artifact,
    operating_modes: operatingModesOf(artifact).map((mode) => ({
      ...mode,
      states: edit(mode.states ?? {}),
    })),
  };
}

function updateItem(
  artifact: EquipmentArtifact,
  index: number,
  patch: Partial<EquipmentItem>,
): EquipmentArtifact {
  return withItems(
    artifact,
    itemsOf(artifact).map((item, i) => (i === index ? { ...item, ...patch } : item)),
  );
}

/** A new item with one empty mode (every item needs one) and the model's default quantity, Off
 * in every operating mode. */
export function addItem(artifact: EquipmentArtifact, prefixes: Prefixes): EquipmentArtifact {
  const id = newId(prefixes.item);
  const item: EquipmentItem = {
    id,
    name: null,
    subsystem: null,
    quantity: 1,
    mass: null,
    location: null,
    modes: [{ id: newId(prefixes.mode), name: null, dissipation: null }],
    operating_min: null,
    operating_max: null,
    non_operating_min: null,
    non_operating_max: null,
    switch_on_min: null,
  };
  const withItem = withItems(artifact, [...itemsOf(artifact), item]);
  return editStates(withItem, (states) => ({ ...states, [id]: null }));
}

/** Delete an item and its entry in every operating mode. */
export function removeItem(artifact: EquipmentArtifact, index: number): EquipmentArtifact {
  const id = itemsOf(artifact)[index]?.id;
  const without = withItems(
    artifact,
    itemsOf(artifact).filter((_, i) => i !== index),
  );
  if (!id) return without;
  return editStates(without, (states) =>
    Object.fromEntries(Object.entries(states).filter(([itemId]) => itemId !== id)),
  );
}

export function addItemMode(
  artifact: EquipmentArtifact,
  itemIndex: number,
  prefixes: Prefixes,
): EquipmentArtifact {
  const item = itemsOf(artifact)[itemIndex];
  if (!item) return artifact;
  const mode: ItemMode = { id: newId(prefixes.mode), name: null, dissipation: null };
  return updateItem(artifact, itemIndex, { modes: [...modesOf(item), mode] });
}

/** Delete a mode of an item; the operating modes that used it turn that item Off. */
export function removeItemMode(
  artifact: EquipmentArtifact,
  itemIndex: number,
  modeIndex: number,
): EquipmentArtifact {
  const item = itemsOf(artifact)[itemIndex];
  if (!item) return artifact;
  const without = updateItem(artifact, itemIndex, {
    modes: modesOf(item).filter((_, i) => i !== modeIndex),
  });
  const modeId = modesOf(item)[modeIndex]?.id;
  const itemId = item.id;
  if (!modeId || !itemId) return without;
  return editStates(without, (states) =>
    states[itemId] === modeId ? { ...states, [itemId]: null } : states,
  );
}

/** A new operating mode with every item Off. */
export function addOperatingMode(
  artifact: EquipmentArtifact,
  prefixes: Prefixes,
): EquipmentArtifact {
  const states: States = {};
  for (const item of itemsOf(artifact)) if (item.id) states[item.id] = null;
  const mode: OperatingMode = {
    id: newId(prefixes.operatingMode),
    name: null,
    max_duration: null,
    states,
  };
  return { ...artifact, operating_modes: [...operatingModesOf(artifact), mode] };
}

/** Delete an operating mode with its configuration. */
export function removeOperatingMode(artifact: EquipmentArtifact, index: number): EquipmentArtifact {
  return {
    ...artifact,
    operating_modes: operatingModesOf(artifact).filter((_, i) => i !== index),
  };
}
