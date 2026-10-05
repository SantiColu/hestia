import { Pencil, Trash2 } from "lucide-react";
import type { EquipmentArtifact, EquipmentItem, OperatingMode } from "@/api/client";
import { TableTextInput } from "@/components/forms/table-inputs";
import { SegmentMeter } from "@/components/data/segment-meter";
import { Button } from "@/components/ui/button";
import { formatPath } from "@/lib/json";
import { cn } from "@/lib/utils";
import { fmtUpTo } from "../format";
import { FieldCell, type EquipmentForm } from "./cells";
import { itemName, operatingModeName, removeOperatingMode } from "./edits";
import { appliedAt, errorAt, fieldOf } from "./equipment-schema";
import { StateSelect } from "./state-select";

/** «Rueda de reacción × 4»: the quantity always beside the name (identical items, one mode). */
export function ItemHeader({ item, index }: { item: EquipmentItem; index: number }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span className="truncate">{itemName(item, index)}</span>
      <span className="shrink-0 font-mono text-xs text-subtle-foreground">
        × {item.quantity ?? "—"}
      </span>
    </span>
  );
}

/** Header of an operating mode: its name with a pencil to rename it in place and, below, its
 * total dissipation from the API with a meter against the largest total. */
export function ModeHeader({
  form,
  mode,
  index,
  editing,
  onEditing,
}: {
  form: EquipmentForm;
  mode: OperatingMode;
  index: number;
  editing: boolean;
  onEditing: (editing: boolean) => void;
}) {
  const path = ["operating_modes", index, "name"];
  const error = errorAt(form.problems, formatPath(path));
  const name = operatingModeName(mode, index);
  return (
    <span className="flex flex-col gap-0.5">
      {editing ? (
        <RenameInput
          label={`Nombre de ${name}`}
          value={mode.name ?? null}
          error={error}
          onChange={(next) => form.set(path, next)}
          onDone={() => onEditing(false)}
        />
      ) : (
        <span className="flex min-w-0 items-center gap-1">
          <span
            title={error}
            className={cn(
              "flex-1 truncate text-2xs font-semibold text-muted-foreground",
              !mode.name && "text-subtle-foreground",
              error && "text-error",
            )}
          >
            {name}
          </span>
          <Button
            size="icon-xs"
            variant="ghost"
            aria-label={`Renombrar ${name}`}
            title="Renombrar"
            className="size-5.5 text-subtle-foreground"
            onClick={() => onEditing(true)}
          >
            <Pencil />
          </Button>
        </span>
      )}
      <ModeTotal total={form.scale.totalOf(mode.id)} max={form.scale.maxTotal} />
    </span>
  );
}

/** «Σ 45 W» with its meter; «Σ — W» while the API cannot add it up. */
function ModeTotal({ total, max }: { total: number | null | undefined; max: number }) {
  return (
    <span
      className={cn(
        "flex items-center gap-1.5 font-mono text-2xs font-semibold tabular-nums",
        typeof total === "number" ? "text-hot" : "text-subtle-foreground",
      )}
      title={typeof total === "number" ? undefined : "Sin total: faltan datos o hay errores"}
    >
      Σ {typeof total === "number" ? fmtUpTo(total) : "—"} W
      {typeof total === "number" && <SegmentMeter value={total} max={max} />}
    </span>
  );
}

/** The name being typed; Enter or leaving the field ends the rename (it is already in the
 * draft). */
function RenameInput({
  label,
  value,
  error,
  onChange,
  onDone,
}: {
  label: string;
  value: string | null;
  error?: string;
  onChange: (value: string | null) => void;
  onDone: () => void;
}) {
  return (
    <span className="block h-5.5">
      <TableTextInput
        // Renaming starts from the pencil: the name is what the user is about to type.
        autoFocus
        label={label}
        value={value}
        error={error}
        onChange={onChange}
        onBlur={onDone}
        onKeyDown={(event) => event.key === "Enter" && onDone()}
      />
    </span>
  );
}

export function DurationCell({
  form,
  mode,
  index,
}: {
  form: EquipmentForm;
  mode: OperatingMode;
  index: number;
}) {
  const f = fieldOf(form.schema.operatingMode, "max_duration");
  return (
    <FieldCell
      form={form}
      f={f}
      path={["operating_modes", index, "max_duration"]}
      label={`${f.meta.title ?? "Duración"} de ${operatingModeName(mode, index)}`}
    />
  );
}

/** The mode of an item in an operating mode (a missing entry shows «—»). */
export function StateCell({
  form,
  item,
  itemIndex,
  mode,
  modeIndex,
}: {
  form: EquipmentForm;
  item: EquipmentItem;
  itemIndex: number;
  mode: OperatingMode;
  modeIndex: number;
}) {
  if (!item.id) return <span className="px-2.5 text-xs text-subtle-foreground">—</span>;
  const path = ["operating_modes", modeIndex, "states", item.id];
  const states = mode.states ?? {};
  const applied = appliedAt(form.current, form.applied, path);
  return (
    <StateSelect
      label={`${itemName(item, itemIndex)} en ${operatingModeName(mode, modeIndex)}`}
      item={item}
      value={item.id in states ? states[item.id] : undefined}
      applied={typeof applied === "string" || applied === null ? applied : undefined}
      error={errorAt(form.problems, formatPath(path))}
      maxPerItem={form.scale.maxPerItem}
      onChange={(next) => form.set(path, next)}
    />
  );
}

export function DeleteModeButton({
  artifact,
  mode,
  index,
  onEdit,
}: {
  artifact: EquipmentArtifact;
  mode: OperatingMode;
  index: number;
  onEdit: (next: EquipmentArtifact) => void;
}) {
  return (
    <Button
      size="icon-sm"
      variant="ghost"
      aria-label={`Eliminar ${operatingModeName(mode, index)}`}
      title="Eliminar modo operativo"
      className="text-subtle-foreground"
      onClick={() => onEdit(removeOperatingMode(artifact, index))}
    >
      <Trash2 />
    </Button>
  );
}
