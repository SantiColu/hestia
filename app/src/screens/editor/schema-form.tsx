import { Plus, Trash2 } from "lucide-react";
import type { Problem } from "@/api/client";
import { NumberField } from "@/components/forms/number-field";
import { Segmented } from "@/components/forms/segmented";
import { SelectField } from "@/components/forms/select-field";
import { TextField } from "@/components/forms/text-field";
import { Button } from "@/components/ui/button";
import {
  deepEqual,
  formatPath,
  getAt,
  type Json,
  type JsonObject,
  type JsonPath,
} from "@/lib/json";
import { fromDisplay, toDisplay } from "@/lib/units";
import { field, formatValue, resolve, type Field, type JsonSchema } from "./schema";
import { cn } from "@/lib/utils";

/**
 * A form generated from the JSON Schema of an artifact (ADR 0017). Presentation only: which
 * fields exist, their units, labels and which apply to each option come from the schema's
 * `x-` extensions; problems come from the API's dry validation.
 */

export type FormContext = {
  root: JsonSchema;
  applied: JsonObject;
  current: JsonObject;
  problems: Problem[];
  /** Leaf path → source (`default`, `entered`, `imported`). */
  sources: Record<string, string>;
  onChange: (path: JsonPath, value: Json) => void;
};

function problemsAt(ctx: FormContext, path: JsonPath): Problem[] {
  const key = formatPath(path);
  return ctx.problems.filter((p) => p.path === key);
}

// ---------------------------------------------------------------- form

/** Sections of the artifact (top-level properties) in schema order, in one column. */
export function SchemaForm(ctx: FormContext) {
  return (
    <div className="flex flex-col gap-6">
      {Object.entries(ctx.root.properties ?? {}).map(([key, meta]) => {
        if (key === "schema_version") return null;
        const f = field(meta, ctx.root);
        return (
          <section key={key} className="flex flex-col gap-3">
            <h2 className="border-b border-border pb-1 text-sm font-semibold">
              {meta.title ?? f.node.title ?? key}
            </h2>
            {f.node.type === "array" ? (
              <TableField ctx={ctx} path={[key]} f={f} />
            ) : (
              <ObjectFields ctx={ctx} schema={f.node} path={[key]} />
            )}
          </section>
        );
      })}
    </div>
  );
}

function ObjectFields({
  ctx,
  schema,
  path,
}: {
  ctx: FormContext;
  schema: JsonSchema;
  path: JsonPath;
}) {
  const parent = getAt(ctx.current, path);
  return (
    <div className="flex flex-col gap-3">
      {Object.entries(schema.properties ?? {}).map(([key, meta]) => {
        const showIf = meta["x-show-if"];
        // A field of another option stays visible while it has a value, so the problem the
        // API reports on it (e.g. `not_allowed`) can be fixed.
        const filled = (getAt(parent, [key]) ?? null) !== null;
        if (showIf && !filled) {
          const visible = Object.entries(showIf).every(([sibling, values]) =>
            values.includes(String(getAt(parent, [sibling]) ?? "")),
          );
          if (!visible) return null;
        }
        return <LeafField key={key} ctx={ctx} path={[...path, key]} f={field(meta, ctx.root)} />;
      })}
    </div>
  );
}

function enumOptions(f: Field): { value: string; label: string }[] {
  const labels = f.meta["x-enum-labels"] ?? {};
  return (f.node.enum ?? []).map((value) => ({ value, label: labels[value] ?? value }));
}

/** One field with its label, unit, errors, note and the applied value when it changed. */
function LeafField({ ctx, path, f }: { ctx: FormContext; path: JsonPath; f: Field }) {
  const value = getAt(ctx.current, path) ?? null;
  const applied = getAt(ctx.applied, path) ?? null;
  const changed = !deepEqual(value, applied);
  const key = formatPath(path);
  const errors = problemsAt(ctx, path).concat(
    Array.isArray(value) ? ctx.problems.filter((p) => p.path.startsWith(`${key}[`)) : [],
  );
  const error = errors.map((p) => p.message).join(" ") || undefined;
  const isDefault = !changed && ctx.sources[key] === "default";
  const label = `${f.meta.title ?? String(path[path.length - 1])}${isDefault ? " · por defecto" : ""}`;
  const note = typeof value === "string" ? f.meta["x-notes"]?.[value] : undefined;
  const set = (next: Json) => ctx.onChange(path, next);

  let input;
  if (f.node.enum) {
    const options = enumOptions(f);
    input =
      options.length <= 3 ? (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-muted-foreground">{label}</span>
          <Segmented
            aria-label={label}
            options={options}
            value={typeof value === "string" ? value : undefined}
            onValueChange={set}
            className="w-fit"
          />
          {error && <p className="text-xs text-error">{error}</p>}
        </div>
      ) : (
        <SelectField
          label={label}
          options={[{ value: "", label: "—" }, ...options]}
          value={typeof value === "string" ? value : ""}
          onValueChange={(next) => set(next === "" ? null : next)}
        />
      );
  } else if (f.node.type === "number" || f.node.type === "integer") {
    const unit = f.meta["x-unit"];
    const display = f.meta["x-display-unit"];
    input = (
      <NumberField
        label={label}
        unit={display}
        error={error}
        format={{ maximumFractionDigits: 6, useGrouping: false }}
        value={typeof value === "number" ? toDisplay(value, unit, display) : null}
        onValueChange={(next) => set(next === null ? null : fromDisplay(next, unit, display))}
      />
    );
  } else if (f.node.type === "array") {
    const item = resolve(f.node.items ?? {}, ctx.root);
    const labels = f.node.items?.["x-enum-labels"] ?? {};
    const selected = Array.isArray(value) ? value.map(String) : [];
    input = (
      <div className="flex flex-col gap-1.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <div className="flex flex-wrap gap-1">
          {(item.enum ?? []).map((option) => {
            const on = selected.includes(option);
            return (
              <button
                key={option}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  set(on ? selected.filter((v) => v !== option) : [...selected, option])
                }
                className={cn(
                  "h-6 rounded-md border border-border px-2 font-mono text-xs text-muted-foreground",
                  on && "border-primary bg-primary-soft text-foreground",
                )}
              >
                {labels[option] ?? option}
              </button>
            );
          })}
        </div>
        {error && <p className="text-xs text-error">{error}</p>}
      </div>
    );
  } else if (f.meta["x-input"] === "textarea") {
    input = (
      <label className="flex flex-col gap-1.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <textarea
          rows={3}
          value={typeof value === "string" ? value : ""}
          onChange={(event) => set(event.target.value === "" ? null : event.target.value)}
          className="rounded-lg border border-input bg-background px-2.5 py-1.5 text-[13px] outline-none focus:border-ring"
        />
        {error && <p className="text-xs text-error">{error}</p>}
      </label>
    );
  } else {
    const type = f.node.format === "date" ? "date" : f.meta["x-input"] === "time" ? "time" : "text";
    input = (
      <TextField
        label={label}
        type={type}
        error={error}
        value={typeof value === "string" ? value : ""}
        onChange={(event) => set(event.target.value === "" ? null : event.target.value)}
        className={type === "text" ? undefined : "w-48"}
      />
    );
  }

  return (
    <div className="flex max-w-md flex-col gap-1">
      {input}
      {f.meta.description && (
        <p className="text-[11px] text-subtle-foreground">{f.meta.description}</p>
      )}
      {note && <p className="text-[11px] text-muted-foreground">{note}</p>}
      {changed && (
        <p className="font-mono text-[11px] text-subtle-foreground">
          Aplicado: {formatValue(applied, f)}
        </p>
      )}
    </div>
  );
}

const cellInput =
  "h-7 w-full rounded-md border border-input bg-background px-1.5 text-[13px] outline-none focus:border-ring aria-invalid:border-error";

/** A list of objects as an editable table: one row per item, add and delete rows. */
function TableField({ ctx, path, f }: { ctx: FormContext; path: JsonPath; f: Field }) {
  const item = resolve(f.node.items ?? {}, ctx.root);
  const columns = Object.entries(item.properties ?? {}).filter(([key]) => key !== "id");
  const rows = getAt(ctx.current, path);
  const list = Array.isArray(rows) ? rows : [];
  const appliedRows = getAt(ctx.applied, path);
  const key = formatPath(path);
  const listProblems = problemsAt(ctx, path);
  const rowProblems = ctx.problems.filter((p) => p.path.startsWith(`${key}[`));

  const emptyRow = (): JsonObject => Object.fromEntries(columns.map(([name]) => [name, null]));

  return (
    <div className="flex flex-col gap-2">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            {columns.map(([name, meta]) => (
              <th key={name} className="px-1 pb-1 font-normal">
                {meta.title ?? name}
              </th>
            ))}
            <th className="w-8" />
          </tr>
        </thead>
        <tbody>
          {list.map((_, row) => (
            <tr key={row}>
              {columns.map(([name, meta]) => {
                const cellPath = [...path, row, name];
                const cf = field(meta, ctx.root);
                const value = getAt(ctx.current, cellPath) ?? null;
                const errors = problemsAt(ctx, cellPath);
                const invalid = errors.length > 0 || undefined;
                const title = errors.map((p) => p.message).join(" ") || undefined;
                return (
                  <td key={name} className="px-1 py-0.5">
                    {cf.node.enum ? (
                      <select
                        aria-label={meta.title ?? name}
                        aria-invalid={invalid}
                        title={title}
                        className={cellInput}
                        value={typeof value === "string" ? value : ""}
                        onChange={(e) =>
                          ctx.onChange(cellPath, e.target.value === "" ? null : e.target.value)
                        }
                      >
                        <option value="">—</option>
                        {enumOptions(cf).map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        aria-label={meta.title ?? name}
                        aria-invalid={invalid}
                        title={title}
                        className={cellInput}
                        value={typeof value === "string" ? value : ""}
                        onChange={(e) =>
                          ctx.onChange(cellPath, e.target.value === "" ? null : e.target.value)
                        }
                      />
                    )}
                  </td>
                );
              })}
              <td className="px-1">
                <Button
                  size="icon-sm"
                  variant="ghost"
                  aria-label="Eliminar fila"
                  title="Eliminar fila"
                  onClick={() =>
                    ctx.onChange(
                      path,
                      list.filter((_, i) => i !== row),
                    )
                  }
                >
                  <Trash2 />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button
        size="sm"
        variant="ghost"
        className="w-fit"
        onClick={() => ctx.onChange(path, [...list, emptyRow()])}
      >
        <Plus data-icon="inline-start" /> Agregar fila
      </Button>
      {[...listProblems, ...rowProblems].map((p) => (
        <p key={`${p.path}:${p.code}`} className="text-xs text-error">
          {rowLabel(p.path, key)}
          {p.message}
        </p>
      ))}
      {!deepEqual(list, Array.isArray(appliedRows) ? appliedRows : []) && (
        <p className="font-mono text-[11px] text-subtle-foreground">
          Aplicado: {Array.isArray(appliedRows) ? appliedRows.length : 0} fila(s)
        </p>
      )}
    </div>
  );
}

function rowLabel(path: string, listKey: string): string {
  const match = path.slice(listKey.length).match(/^\[(\d+)\]/);
  return match ? `Fila ${Number(match[1]) + 1}: ` : "";
}
