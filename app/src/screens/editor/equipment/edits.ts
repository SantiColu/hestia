import type { EquipmentArtifact, EquipmentItem, ItemMode } from "@/api/client";
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

export function modesOf(item: EquipmentItem): ItemMode[] {
  return item.modes ?? [];
}

function withItems(artifact: EquipmentArtifact, items: EquipmentItem[]): EquipmentArtifact {
  return { ...artifact, items };
}

export function updateItem(
  artifact: EquipmentArtifact,
  index: number,
  patch: Partial<EquipmentItem>,
): EquipmentArtifact {
  return withItems(
    artifact,
    itemsOf(artifact).map((item, i) => (i === index ? { ...item, ...patch } : item)),
  );
}

/** A new item with one empty mode (every item needs one) and the model's default quantity. */
export function addItem(artifact: EquipmentArtifact, prefixes: Prefixes): EquipmentArtifact {
  const item: EquipmentItem = {
    id: newId(prefixes.item),
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
  return withItems(artifact, [...itemsOf(artifact), item]);
}

export function removeItem(artifact: EquipmentArtifact, index: number): EquipmentArtifact {
  return withItems(
    artifact,
    itemsOf(artifact).filter((_, i) => i !== index),
  );
}

export function updateItemMode(
  artifact: EquipmentArtifact,
  itemIndex: number,
  modeIndex: number,
  patch: Partial<ItemMode>,
): EquipmentArtifact {
  const item = itemsOf(artifact)[itemIndex];
  if (!item) return artifact;
  const modes = modesOf(item).map((mode, i) => (i === modeIndex ? { ...mode, ...patch } : mode));
  return updateItem(artifact, itemIndex, { modes });
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

export function removeItemMode(
  artifact: EquipmentArtifact,
  itemIndex: number,
  modeIndex: number,
): EquipmentArtifact {
  const item = itemsOf(artifact)[itemIndex];
  if (!item) return artifact;
  return updateItem(artifact, itemIndex, {
    modes: modesOf(item).filter((_, i) => i !== modeIndex),
  });
}
