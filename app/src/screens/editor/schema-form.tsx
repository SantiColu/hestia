import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { Problem } from "@/api/client";
import { Tag } from "@/components/feedback/tag";
import { fieldBoxClass } from "@/components/forms/field-box";
import { FieldFootnote, FieldLabel } from "@/components/forms/field-label";
import { NumberField } from "@/components/forms/number-field";
import { Segmented } from "@/components/forms/segmented";
import { SelectField } from "@/components/forms/select-field";
import { TextField } from "@/components/forms/text-field";
import { SectionLabel } from "@/components/navigation/section-label";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  deepEqual,
  formatPath,
  getAt,
  type Json,
  type JsonObject,
  type JsonPath,
} from "@/lib/json";
import { isIsoDate } from "@/lib/format";
import { fromDisplay, toDisplay } from "@/lib/units";
import { cn } from "@/lib/utils";
import { applies, field, formatValue, resolve, type Field, type JsonSchema } from "./schema";

/**
 * A form generated from the JSON Schema of an artifact (ADR 0017, `workspace.pen` frames
 * «Workspace · Misión (…)»). Presentation only: which fields exist, their units, labels and
 * which apply to each option come from the schema's `x-` extensions; problems come from the
 * API's dry validation.
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

/** Grid of a row by its number of fields: at most MAX_COLUMNS side by side. */
const ROW_GRID = ["grid-cols-1", "grid-cols-2", "grid-cols-3", "grid-cols-4"] as const;
const MAX_COLUMNS = ROW_GRID.length;

function problemsAt(ctx: FormContext, path: JsonPath): Problem[] {
  const key = formatPath(path);
  return ctx.problems.filter((p) => p.path === key);
}

// ---------------------------------------------------------------- form

/** Sections of the artifact (top-level properties) in schema order. */
export function SchemaForm(ctx: FormContext) {
  return Object.entries(ctx.root.properties ?? {}).map(([key, meta]) => {
    if (key === "schema_version") return null;
    const f = field(meta, ctx.root);
    return (
      <section key={key} className="flex flex-col gap-3.5">
        <SectionLabel>{meta.title ?? f.node.title ?? key}</SectionLabel>
        {f.node.type === "array" ? (
          <TableField ctx={ctx} path={[key]} f={f} />
        ) : (
          <ObjectFields ctx={ctx} schema={f.node} path={[key]} />
        )}
      </section>
    );
  });
}

function enumOptions(f: Field): { value: string; label: string }[] {
  const labels = f.meta["x-enum-labels"] ?? {};
  return (f.node.enum ?? []).map((value) => ({ value, label: labels[value] ?? value }));
}

/** Fields that take a whole row: option selectors and free text. */
function takesRow(f: Field): boolean {
  if (f.node.enum) return enumOptions(f).length <= 3;
  return f.node.type === "string" && !f.node.format && f.meta["x-input"] !== "time";
}

/** Splits `n` fields into rows of at most MAX_COLUMNS, as even as possible (6 → 3 + 3). */
function balancedRows<T>(items: T[]): T[][] {
  const rows = Math.ceil(items.length / MAX_COLUMNS);
  const size = Math.ceil(items.length / rows);
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
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
  // A field of another option stays visible while it has a value (e.g. one an agent left), so
  // the problem the API reports on it (`not_allowed`) can be fixed.
  const visible = Object.entries(schema.properties ?? {}).filter(
    ([key, meta]) => (getAt(parent, [key]) ?? null) !== null || applies(meta, ctx.current, path),
  );

  // Consecutive fields share rows; selectors and free text take a row of their own.
  const rows: [string, JsonSchema][][] = [];
  let group: [string, JsonSchema][] = [];
  const flush = () => {
    rows.push(...balancedRows(group));
    group = [];
  };
  for (const entry of visible) {
    if (takesRow(field(entry[1], ctx.root))) {
      flush();
      rows.push([entry]);
    } else {
      group.push(entry);
    }
  }
  flush();

  const notes = visible.flatMap(([key, meta]) => {
    const value = getAt(parent, [key]);
    const note = typeof value === "string" ? meta["x-notes"]?.[value] : undefined;
    return note ? [note] : [];
  });

  return (
    <div className="flex flex-col gap-3.5">
      {rows.map((row) => (
        <div
          key={row.map(([key]) => key).join()}
          className={cn("grid items-start gap-4", ROW_GRID[row.length - 1])}
        >
          {row.map(([key, meta]) => (
            <LeafField key={key} ctx={ctx} path={[...path, key]} f={field(meta, ctx.root)} />
          ))}
        </div>
      ))}
      {notes.map((note) => (
        <p key={note} className="text-xs text-subtle-foreground">
          {note}
        </p>
      ))}
    </div>
  );
}

/** One field with its label, unit, error and the applied value (or the default's source). */
function LeafField({ ctx, path, f }: { ctx: FormContext; path: JsonPath; f: Field }) {
  const value = getAt(ctx.current, path) ?? null;
  const applied = getAt(ctx.applied, path) ?? null;
  const modified = !deepEqual(value, applied);
  const key = formatPath(path);
  const errors = problemsAt(ctx, path).concat(
    Array.isArray(value) ? ctx.problems.filter((p) => p.path.startsWith(`${key}[`)) : [],
  );
  const error = errors.map((p) => p.message).join(" ") || undefined;
  const source = f.meta["x-default-source"];
  const hint = modified
    ? `Aplicado: ${formatValue(applied, f)}`
    : source && ctx.sources[key] === "default"
      ? `default · ${source}`
      : undefined;
  const label = f.meta.title ?? String(path[path.length - 1]);
  const placeholder = f.meta["x-placeholder"] ?? "—";
  const set = (next: Json) => ctx.onChange(path, next);
  const common = { label, error, modified, hint };

  if (f.node.enum) {
    const options = enumOptions(f);
    if (options.length > 3) {
      return (
        <div className="flex flex-col gap-1.5">
          <SelectField
            label={label}
            options={[{ value: "", label: "—" }, ...options]}
            value={typeof value === "string" ? value : ""}
            onValueChange={(next) => set(next === "" ? null : next)}
          />
          <FieldFootnote error={error} hint={hint} />
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-1.5">
        <FieldLabel modified={modified}>{label}</FieldLabel>
        <Segmented
          aria-label={label}
          options={options}
          value={typeof value === "string" ? value : undefined}
          onValueChange={set}
          className="w-fit"
        />
        <FieldFootnote error={error} hint={hint} />
      </div>
    );
  }
  if (f.node.type === "number" || f.node.type === "integer") {
    const unit = f.meta["x-unit"];
    const display = f.meta["x-display-unit"];
    return (
      <NumberField
        {...common}
        unit={display}
        placeholder={placeholder}
        format={{ maximumFractionDigits: 6, useGrouping: false }}
        value={typeof value === "number" ? toDisplay(value, unit, display) : null}
        onValueChange={(next) => set(next === null ? null : fromDisplay(next, unit, display))}
      />
    );
  }
  if (f.node.type === "array") {
    return <ChoicesField {...common} f={f} root={ctx.root} value={value} onChange={set} />;
  }
  if (f.node.format === "date") {
    return (
      <DateField {...common} value={typeof value === "string" ? value : null} onChange={set} />
    );
  }
  const time = f.meta["x-input"] === "time";
  return (
    <TextField
      {...common}
      mono={time}
      suffix={time ? "hh:mm" : undefined}
      placeholder={placeholder}
      value={typeof value === "string" ? value : ""}
      onChange={(event) => set(event.target.value === "" ? null : event.target.value)}
    />
  );
}

type FieldProps = { label: string; error?: string; modified: boolean; hint?: string };

/** A date typed as aaaa-mm-dd. Only complete dates reach the draft (like a number being typed). */
function DateField({
  value,
  onChange,
  error,
  ...props
}: FieldProps & { value: string | null; onChange: (value: Json) => void }) {
  const [text, setText] = useState(value ?? "");
  const [shown, setShown] = useState(value);
  if (value !== shown) {
    setShown(value);
    setText(value ?? "");
  }
  const incomplete = text !== "" && !isIsoDate(text);
  return (
    <TextField
      {...props}
      mono
      placeholder="aaaa-mm-dd"
      error={incomplete ? "Fecha con el formato aaaa-mm-dd." : error}
      value={text}
      onChange={(event) => {
        const next = event.target.value.trim();
        setText(event.target.value);
        if (next === "") onChange(null);
        else if (isIsoDate(next)) onChange(next);
      }}
    />
  );
}

/** Several options of a list (e.g. radiator faces): tags in the box, a menu to pick them. */
function ChoicesField({
  label,
  error,
  modified,
  hint,
  f,
  root,
  value,
  onChange,
}: FieldProps & { f: Field; root: JsonSchema; value: Json; onChange: (value: Json) => void }) {
  const item = resolve(f.node.items ?? {}, root);
  const labels = f.node.items?.["x-enum-labels"] ?? {};
  const selected = Array.isArray(value) ? value.map(String) : [];
  const options = item.enum ?? [];
  return (
    <div className="flex flex-col gap-1.5">
      <FieldLabel modified={modified}>{label}</FieldLabel>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={label}
          aria-invalid={error ? true : undefined}
          className={cn(fieldBoxClass({ error: !!error, modified }), "w-full gap-1.5 px-2")}
        >
          {selected.length === 0 ? (
            <span className="px-0.5 text-ui text-subtle-foreground">—</span>
          ) : (
            options
              .filter((option) => selected.includes(option))
              .map((option) => (
                <Tag key={option} className="h-4.75 font-normal tracking-normal">
                  {labels[option] ?? option}
                </Tag>
              ))
          )}
        </DropdownMenuTrigger>
        <DropdownMenuContent className="font-mono">
          {options.map((option) => {
            const on = selected.includes(option);
            return (
              <DropdownMenuCheckboxItem
                key={option}
                checked={on}
                closeOnClick={false}
                onCheckedChange={() =>
                  onChange(
                    on
                      ? selected.filter((v) => v !== option)
                      : options.filter((o) => o === option || selected.includes(o)),
                  )
                }
              >
                {labels[option] ?? option}
              </DropdownMenuCheckboxItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
      <FieldFootnote error={error} hint={hint} />
    </div>
  );
}

// ---------------------------------------------------------------- table

const cellClass = "h-8 border-b border-border px-2.5";
const cellInput =
  "h-full w-full bg-transparent text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-inset aria-invalid:ring-1 aria-invalid:ring-error aria-invalid:ring-inset";

/** Width of an option column: short codes (axes) or labels (directions). */
function columnWidth(f: Field): string {
  const labels = enumOptions(f).map((o) => o.label.length);
  return Math.max(...labels) <= 3 ? "w-26" : "w-30";
}

/** A list of objects as an editable table (`Table/*`): one row per item, add and delete rows. */
function TableField({ ctx, path, f }: { ctx: FormContext; path: JsonPath; f: Field }) {
  const item = resolve(f.node.items ?? {}, ctx.root);
  const columns = Object.entries(item.properties ?? {}).filter(([key]) => key !== "id");
  const rows = getAt(ctx.current, path);
  const list = Array.isArray(rows) ? rows : [];
  const appliedRows = getAt(ctx.applied, path);
  const key = formatPath(path);
  const listProblems = problemsAt(ctx, path);
  const rowProblems = ctx.problems.filter((p) => p.path.startsWith(`${key}[`));
  const modified = !deepEqual(list, Array.isArray(appliedRows) ? appliedRows : []);

  const emptyRow = (): JsonObject => Object.fromEntries(columns.map(([name]) => [name, null]));

  return (
    <div className="flex flex-col gap-3.5">
      <div
        className={cn(
          "overflow-hidden rounded-lg border border-border",
          modified && "border-primary",
          listProblems.length > 0 && "border-error",
        )}
      >
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-surface-2 text-left">
              {columns.map(([name, meta]) => {
                const cf = field(meta, ctx.root);
                return (
                  <th
                    key={name}
                    className={cn(
                      "h-7 border-b border-border px-2.5 text-2xs font-medium text-subtle-foreground",
                      cf.node.enum && columnWidth(cf),
                    )}
                  >
                    {meta["x-column-title"] ?? meta.title ?? name}
                  </th>
                );
              })}
              <th className="h-7 w-11 border-b border-border" />
            </tr>
          </thead>
          <tbody className="[&>tr:last-child>td]:border-b-0">
            {list.map((_, row) => (
              <tr key={row}>
                {columns.map(([name, meta]) => {
                  const cellPath = [...path, row, name];
                  const cf = field(meta, ctx.root);
                  const value = getAt(ctx.current, cellPath) ?? null;
                  const errors = problemsAt(ctx, cellPath);
                  const invalid = errors.length > 0 || undefined;
                  const title = errors.map((p) => p.message).join(" ") || undefined;
                  const label = meta.title ?? name;
                  const set = (next: string) => ctx.onChange(cellPath, next === "" ? null : next);
                  return (
                    <td key={name} className={cn(cellClass, "px-0")}>
                      {cf.node.enum ? (
                        <select
                          aria-label={label}
                          aria-invalid={invalid}
                          title={title}
                          className={cn(
                            cellInput,
                            "cursor-pointer appearance-none px-2.5 font-mono [&>option]:bg-surface",
                            value === null && "text-subtle-foreground",
                          )}
                          value={typeof value === "string" ? value : ""}
                          onChange={(e) => set(e.target.value)}
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
                          aria-label={label}
                          aria-invalid={invalid}
                          title={title}
                          placeholder="—"
                          className={cn(cellInput, "px-2.5 placeholder:text-subtle-foreground")}
                          value={typeof value === "string" ? value : ""}
                          onChange={(e) => set(e.target.value)}
                        />
                      )}
                    </td>
                  );
                })}
                <td className={cn(cellClass, "px-0 text-center")}>
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    aria-label="Eliminar fila"
                    title="Eliminar fila"
                    className="text-subtle-foreground"
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
      </div>
      {problemLines(key, [...listProblems, ...rowProblems]).map((line) => (
        <p key={line} className="-mt-1.5 text-xs text-error">
          {line}
        </p>
      ))}
      {modified && (
        <p className="-mt-1.5 font-mono text-2xs text-subtle-foreground">
          Aplicado: {Array.isArray(appliedRows) ? appliedRows.length : 0} fila(s)
        </p>
      )}
      <Button
        variant="ghost"
        className="w-fit"
        onClick={() => ctx.onChange(path, [...list, emptyRow()])}
      >
        <Plus data-icon="inline-start" /> {f.meta["x-add-label"] ?? "Agregar fila"}
      </Button>
    </div>
  );
}

/** Problems of a table, one line per row: "Fila 3: Falta el nombre. Falta el eje primario." */
function problemLines(listKey: string, problems: Problem[]): string[] {
  const rows = new Map<string, string[]>();
  for (const p of problems) {
    const match = p.path.slice(listKey.length).match(/^\[(\d+)\]/);
    const row = match ? `Fila ${Number(match[1]) + 1}: ` : "";
    rows.set(row, [...(rows.get(row) ?? []), p.message]);
  }
  return [...rows].map(([row, messages]) => row + messages.join(" "));
}
