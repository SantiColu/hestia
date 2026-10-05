import type { Problem } from "@/api/client";
import { deepEqual, getAt, type Json, type JsonPath } from "@/lib/json";
import { field, formatValue, resolve, type Field, type JsonSchema } from "../schema";

/** Fields of one level of the equipment artifact, by key, from its JSON Schema. */
export type Fields = Record<string, Field>;

/** What the equipment editor reads from the artifact's JSON Schema: titles, units, enum labels
 * and the prefixes of the ids it proposes (ADR 0025). */
export type EquipmentSchema = {
  root: JsonSchema;
  item: Fields;
  mode: Fields;
  operatingMode: Fields;
  prefixes: { item: string; mode: string; operatingMode: string };
};

const NO_FIELD: Field = { node: {}, meta: {} };

export function equipmentSchema(root: JsonSchema): EquipmentSchema {
  const listItem = (meta: JsonSchema | undefined) =>
    resolve(field(meta ?? {}, root).node.items ?? {}, root);
  const fieldsOf = (node: JsonSchema): Fields =>
    Object.fromEntries(
      Object.entries(node.properties ?? {}).map(([key, meta]) => [key, field(meta, root)]),
    );
  const prefixOf = (node: JsonSchema) => node.properties?.id?.["x-id-prefix"] ?? "";
  const item = listItem(root.properties?.items);
  const mode = listItem(item.properties?.modes);
  const operatingMode = listItem(root.properties?.operating_modes);
  return {
    root,
    item: fieldsOf(item),
    mode: fieldsOf(mode),
    operatingMode: fieldsOf(operatingMode),
    prefixes: {
      item: prefixOf(item),
      mode: prefixOf(mode),
      operatingMode: prefixOf(operatingMode),
    },
  };
}

/** A field of `fields` (an empty one if the schema lacks it). */
export function fieldOf(fields: Fields, key: string): Field {
  return fields[key] ?? NO_FIELD;
}

/** «T op. mín [°C]»: the short title of a field as a column, with its display unit. */
export function columnTitle(f: Field): string {
  const title = f.meta["x-column-title"] ?? f.meta.title ?? "";
  const unit = f.meta["x-display-unit"];
  return unit ? `${title} [${unit}]` : title;
}

/** The messages of the problems at exactly `path`, joined; undefined without problems. */
export function errorAt(problems: Problem[], path: string): string | undefined {
  const messages = problems.filter((p) => p.path === path).map((p) => p.message);
  return messages.length > 0 ? messages.join(" ") : undefined;
}

type CellState = { error?: string; modified: boolean; hint?: string };

/** Error, «modified» mark and the applied value of a field of the draft. */
export function cellState(
  f: Field,
  problems: Problem[],
  path: string,
  value: Json | undefined,
  applied: Json | undefined,
): CellState {
  const modified = !deepEqual(value ?? null, applied ?? null);
  return {
    error: errorAt(problems, path),
    modified,
    hint: modified ? `Aplicado: ${formatValue(applied, f)}` : undefined,
  };
}

/** The applied value of a draft field. List items are matched by id, so adding or deleting
 * rows does not mark the others as modified; a new item has no applied value. */
export function appliedAt(current: Json, applied: Json, path: JsonPath): Json | undefined {
  let draft: Json | undefined = current;
  let value: Json | undefined = applied;
  for (const key of path) {
    if (typeof key === "number" && Array.isArray(draft) && Array.isArray(value)) {
      const id = getAt(draft[key], ["id"]);
      value = id === undefined ? value[key] : value.find((item) => getAt(item, ["id"]) === id);
    } else {
      value = getAt(value, [key]);
    }
    draft = getAt(draft, [key]);
    if (value === undefined) return undefined;
  }
  return value;
}
