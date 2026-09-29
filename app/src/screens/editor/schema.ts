import type { Json, JsonObject, JsonPath } from "@/lib/json";
import { deepEqual, formatPath, getAt } from "@/lib/json";
import { toDisplay } from "@/lib/units";

/** JSON Schema of an artifact as the API serves it (pydantic), with Hestia's `x-` hints. */
export type JsonSchema = {
  type?: string;
  $ref?: string;
  anyOf?: JsonSchema[];
  enum?: string[];
  items?: JsonSchema;
  properties?: Record<string, JsonSchema>;
  $defs?: Record<string, JsonSchema>;
  title?: string;
  description?: string;
  format?: string;
  default?: Json;
  "x-unit"?: string;
  "x-display-unit"?: string;
  "x-enum-labels"?: Record<string, string>;
  "x-show-if"?: Record<string, string[]>;
  "x-notes"?: Record<string, string>;
  "x-input"?: "textarea" | "time";
  "x-placeholder"?: string;
  "x-default"?: Json;
  "x-default-source"?: string;
  "x-column-title"?: string;
  "x-add-label"?: string;
};

/** A field's own schema (`type`, `enum`…) plus the field-level metadata (title, `x-`). */
export type Field = { node: JsonSchema; meta: JsonSchema };

export function resolve(schema: JsonSchema, root: JsonSchema): JsonSchema {
  if (schema.$ref) {
    const name = schema.$ref.split("/").pop() ?? "";
    return resolve(root.$defs?.[name] ?? {}, root);
  }
  if (schema.anyOf) {
    const option = schema.anyOf.find((s) => s.type !== "null") ?? {};
    return resolve(option, root);
  }
  return schema;
}

export function field(meta: JsonSchema, root: JsonSchema): Field {
  return { node: resolve(meta, root), meta };
}

// ---------------------------------------------------------------- value formatting

/** A value without its display unit (the unit is shown once, e.g. "550 → 600 km"). */
function formatBare(value: Json | undefined, f: Field): string {
  if (typeof value === "number") {
    return String(toDisplay(value, f.meta["x-unit"], f.meta["x-display-unit"]));
  }
  return formatValue(value, f);
}

/** "550 → 600 km": both values in display units, the unit once at the end. */
export function formatChange(from: Json | undefined, to: Json | undefined, f: Field): string {
  const unit =
    f.node.type === "number" || f.node.type === "integer" ? f.meta["x-display-unit"] : "";
  const text = `${formatBare(from, f)} → ${formatBare(to, f)}`;
  return unit ? `${text} ${unit}` : text;
}

export function formatValue(value: Json | undefined, f: Field): string {
  if (value === null || value === undefined || value === "") return "—";
  const labels = f.meta["x-enum-labels"] ?? f.node.items?.["x-enum-labels"];
  if (Array.isArray(value)) {
    return value.length === 0 ? "—" : value.map((v) => labels?.[String(v)] ?? String(v)).join(", ");
  }
  if (typeof value === "number") {
    const unit = f.meta["x-unit"];
    const display = f.meta["x-display-unit"];
    const shown = toDisplay(value, unit, display);
    return display ? `${shown} ${display}` : String(shown);
  }
  if (typeof value === "string") return labels?.[value] ?? value;
  return JSON.stringify(value);
}

export type LeafChange = {
  path: string;
  /** Title of the section (top-level property) the field belongs to. */
  section: string;
  label: string;
  from: string;
  to: string;
  /** Compact "from → to unit". */
  change: string;
};

/** Leaf fields that differ between two artifacts, with display values (for the diff). */
export function changedLeaves(
  root: JsonSchema,
  before: JsonObject,
  after: JsonObject,
): LeafChange[] {
  const changes: LeafChange[] = [];
  const walk = (
    schema: JsonSchema,
    a: Json | undefined,
    b: Json | undefined,
    path: JsonPath,
    label: string[],
  ) => {
    for (const [key, meta] of Object.entries(schema.properties ?? {})) {
      if (key === "schema_version" || key === "id") continue;
      const f = field(meta, root);
      const childPath = [...path, key];
      const childLabel = [...label, meta.title ?? key];
      const va = getAt(a, [key]);
      const vb = getAt(b, [key]);
      if (f.node.type === "object") {
        walk(f.node, va, vb, childPath, childLabel);
      } else if (
        f.node.type === "array" &&
        f.node.items &&
        resolve(f.node.items, root).type === "object"
      ) {
        const item = resolve(f.node.items, root);
        const length = Math.max(
          Array.isArray(va) ? va.length : 0,
          Array.isArray(vb) ? vb.length : 0,
        );
        for (let i = 0; i < length; i++) {
          const count = changes.length;
          walk(
            item,
            getAt(va, [i]),
            getAt(vb, [i]),
            [...childPath, i],
            [...childLabel, `fila ${i + 1}`],
          );
          const before = getAt(va, [i]);
          const after = getAt(vb, [i]);
          if (count === changes.length && (before === undefined) !== (after === undefined)) {
            // A row added or deleted empty is still a change.
            const from = before === undefined ? "—" : "fila";
            const to = after === undefined ? "eliminada" : "nueva";
            changes.push({
              path: formatPath([...childPath, i]),
              section: childLabel[0] ?? "",
              label: [...childLabel, `fila ${i + 1}`].join(" · "),
              from,
              to,
              change: `${from} → ${to}`,
            });
          }
        }
      } else if (!deepEqual(va ?? null, vb ?? null)) {
        changes.push({
          path: formatPath(childPath),
          section: childLabel[0] ?? "",
          label: childLabel.join(" · "),
          from: formatValue(va, f),
          to: formatValue(vb, f),
          change: formatChange(va, vb, f),
        });
      }
    }
  };
  walk(root, before, after, [], []);
  return changes;
}

// ---------------------------------------------------------------- problems summary

function lowerFirst(text: string): string {
  // Keep acronyms ("LTAN") as they are.
  return /^.[A-ZÁÉÍÓÚÑ]/.test(text) ? text : text.charAt(0).toLowerCase() + text.slice(1);
}

function joinList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}

/**
 * Which fields have problems, by section: "Órbita: altitud y hora local del nodo ascendente".
 * Only names the fields (from the schema titles); the messages come from the API.
 */
export function problemsBySection(root: JsonSchema, paths: string[]): string {
  const sections = new Map<string, string[]>();
  for (const path of paths) {
    const [sectionKey, ...rest] = path.split(/[.[\]]+/).filter(Boolean);
    if (!sectionKey) continue;
    const sectionMeta = root.properties?.[sectionKey];
    if (!sectionMeta) continue;
    const section = sectionMeta.title ?? sectionKey;
    const fields = sections.get(section) ?? [];
    sections.set(section, fields);
    const node = resolve(sectionMeta, root);
    const container = node.type === "array" ? resolve(node.items ?? {}, root) : node;
    const leaf = rest.filter((part) => !/^\d+$/.test(part))[0];
    const meta = leaf ? container.properties?.[leaf] : undefined;
    const name = meta ? lowerFirst(meta.title ?? leaf ?? "") : "";
    if (name && !fields.includes(name)) fields.push(name);
  }
  return [...sections]
    .map(([section, fields]) => (fields.length ? `${section}: ${joinList(fields)}` : section))
    .join("; ");
}
