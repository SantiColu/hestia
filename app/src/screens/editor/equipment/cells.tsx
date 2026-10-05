import type { Problem } from "@/api/client";
import { NumberField } from "@/components/forms/number-field";
import { TableNumberInput, TableSelect, TableTextInput } from "@/components/forms/table-inputs";
import { formatPath, getAt, type Json, type JsonObject, type JsonPath } from "@/lib/json";
import { fromDisplay, toDisplay } from "@/lib/units";
import { enumOptions, type Field } from "../schema";
import type { DissipationScale } from "./dissipation";
import { appliedAt, cellState, type EquipmentSchema } from "./equipment-schema";

/** What every field of the equipment editor needs: the draft, the applied artifact, the
 * problems and derived values of the latest validation and how to set a value. */
export type EquipmentForm = {
  schema: EquipmentSchema;
  current: JsonObject;
  applied: JsonObject;
  problems: Problem[];
  /** Totals from the API and the maxima the dissipation meters compare against. */
  scale: DissipationScale;
  set: (path: JsonPath, value: Json) => void;
};

function fieldState(form: EquipmentForm, f: Field, path: JsonPath) {
  const value = getAt(form.current, path);
  const applied = appliedAt(form.current, form.applied, path);
  return { value, ...cellState(f, form.problems, formatPath(path), value, applied) };
}

function isNumeric(f: Field): boolean {
  return f.node.type === "number" || f.node.type === "integer";
}

/** A number in its display unit (°C, h…) and back to SI; integers stay whole. */
function displayed(f: Field) {
  const unit = f.meta["x-unit"];
  const display = f.meta["x-display-unit"];
  return {
    show: (value: Json | undefined) =>
      typeof value === "number" ? toDisplay(value, unit, display) : null,
    read: (next: number | null) => {
      if (next === null) return null;
      return f.node.type === "integer" ? Math.round(next) : fromDisplay(next, unit, display);
    },
  };
}

/** A field of the draft as an editable table cell: text, number (display unit) or enum. */
export function FieldCell({
  form,
  f,
  path,
  label,
}: {
  form: EquipmentForm;
  f: Field;
  path: JsonPath;
  /** Accessible name, e.g. «Masa de Rueda de reacción». */
  label: string;
}) {
  const { value, ...state } = fieldState(form, f, path);
  const set = (next: Json) => form.set(path, next);
  if (f.node.enum) {
    return (
      <TableSelect
        {...state}
        label={label}
        value={typeof value === "string" ? value : null}
        options={enumOptions(f)}
        onChange={set}
      />
    );
  }
  if (isNumeric(f)) {
    const { show, read } = displayed(f);
    return (
      <TableNumberInput
        {...state}
        label={label}
        value={show(value)}
        onValueChange={(next) => set(read(next))}
      />
    );
  }
  return (
    <TableTextInput
      {...state}
      label={label}
      value={typeof value === "string" ? value : null}
      placeholder={f.meta["x-placeholder"] ?? "—"}
      onChange={set}
    />
  );
}

/** A number of the draft as a labeled field (title and display unit from the schema). */
export function NumberFieldOf({
  form,
  f,
  path,
}: {
  form: EquipmentForm;
  f: Field;
  path: JsonPath;
}) {
  const { value, ...state } = fieldState(form, f, path);
  const { show, read } = displayed(f);
  return (
    <NumberField
      {...state}
      label={f.meta.title ?? String(path[path.length - 1])}
      unit={f.meta["x-display-unit"]}
      placeholder="—"
      format={{ maximumFractionDigits: 6, useGrouping: false }}
      value={show(value)}
      onValueChange={(next) => form.set(path, read(next))}
    />
  );
}
