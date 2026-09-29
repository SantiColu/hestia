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

export type LeafChange = { path: string; label: string; from: string; to: string };

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
          walk(
            item,
            getAt(va, [i]),
            getAt(vb, [i]),
            [...childPath, i],
            [...childLabel, `fila ${i + 1}`],
          );
        }
      } else if (!deepEqual(va ?? null, vb ?? null)) {
        changes.push({
          path: formatPath(childPath),
          label: childLabel.join(" · "),
          from: formatValue(va, f),
          to: formatValue(vb, f),
        });
      }
    }
  };
  walk(root, before, after, [], []);
  return changes;
}
