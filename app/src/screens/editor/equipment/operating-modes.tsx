import { useState } from "react";
import { Plus } from "lucide-react";
import type { EquipmentArtifact, EquipmentItem, OperatingMode } from "@/api/client";
import { Segmented } from "@/components/forms/segmented";
import { tableCellClass, tableHeadClass } from "@/components/forms/table-inputs";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { EquipmentForm } from "./cells";
import { addOperatingMode, itemsOf, operatingModeName, operatingModesOf } from "./edits";
import { columnTitle, fieldOf } from "./equipment-schema";
import { DeleteModeButton, DurationCell, ItemHeader, ModeHeader, StateCell } from "./matrix-cells";
import { ProblemLines } from "./problem-lines";

/** What the rows of the matrix are; the other one goes in columns. Only a view. */
type Rows = "items" | "modes";

const ROWS: { value: Rows; label: string }[] = [
  { value: "items", label: "Equipos" },
  { value: "modes", label: "Modos" },
];

const rowHeadClass = cn(tableCellClass, "max-w-60 bg-surface-2 text-left text-xs font-normal");

type MatrixProps = {
  form: EquipmentForm;
  artifact: EquipmentArtifact;
  items: EquipmentItem[];
  modes: OperatingMode[];
  /** Id of the operating mode being renamed. */
  renaming: string | null;
  onRenaming: (id: string | null) => void;
  onEdit: (next: EquipmentArtifact) => void;
};

/**
 * The operating modes of the satellite: a matrix of items × operating modes where every cell
 * picks the mode of an item (or Off). Adding or deleting an operating mode edits the draft
 * (`edits.ts`); transposing only changes the view.
 */
export function OperatingModes({
  form,
  artifact,
  onEdit,
}: {
  form: EquipmentForm;
  artifact: EquipmentArtifact;
  onEdit: (next: EquipmentArtifact) => void;
}) {
  const [rows, setRows] = useState<Rows>("items");
  const [renaming, setRenaming] = useState<string | null>(null);
  const matrix: MatrixProps = {
    form,
    artifact,
    items: itemsOf(artifact),
    modes: operatingModesOf(artifact),
    renaming,
    onRenaming: setRenaming,
    onEdit,
  };
  const add = () => {
    const next = addOperatingMode(artifact, form.schema.prefixes);
    setRenaming(operatingModesOf(next).at(-1)?.id ?? null);
    onEdit(next);
  };

  return (
    <div className="flex flex-col gap-3.5">
      <div className="flex items-center gap-6">
        <p className="flex-1 text-xs text-subtle-foreground">
          Cada modo operativo es una configuración del satélite: elegí en qué modo está cada equipo.
          Apagado disipa 0 W y se verifica con los límites no operativos. Σ es la disipación total
          del modo (cantidad × W por ítem); sus barras lo comparan con el modo que más disipa, y las
          de cada celda, con la mayor disipación por ítem de la tabla.
        </p>
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          Filas:
          <Segmented
            aria-label="Filas de la matriz"
            options={ROWS}
            value={rows}
            onValueChange={setRows}
          />
        </span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border">
        {rows === "items" ? <ByItems {...matrix} /> : <ByModes {...matrix} />}
      </div>
      <ProblemLines
        problems={form.problems}
        list="operating_modes"
        nameOf={(k) => {
          const mode = matrix.modes[k];
          return mode && operatingModeName(mode, k);
        }}
      />
      <Button variant="ghost" className="w-fit" onClick={add}>
        <Plus data-icon="inline-start" />{" "}
        {form.schema.root.properties?.operating_modes?.["x-add-label"]}
      </Button>
    </div>
  );
}

function durationTitle(form: EquipmentForm): string {
  return columnTitle(fieldOf(form.schema.operatingMode, "max_duration"));
}

/** Items in rows, operating modes in columns: duration first, delete last. */
function ByItems({ form, artifact, items, modes, renaming, onRenaming, onEdit }: MatrixProps) {
  return (
    <table className="w-full border-collapse [&_tr:last-child>*]:border-b-0">
      <thead>
        <tr className="bg-surface-2">
          <th className={cn(tableHeadClass, "w-60")}>Equipo</th>
          {modes.map((mode, k) => (
            <th key={mode.id ?? k} className={cn(tableHeadClass, "border-l")}>
              <ModeHeader
                form={form}
                mode={mode}
                index={k}
                editing={renaming === mode.id}
                onEditing={(editing) => onRenaming(editing ? (mode.id ?? null) : null)}
              />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th className={rowHeadClass}>{durationTitle(form)}</th>
          {modes.map((mode, k) => (
            <td key={mode.id ?? k} className={cn(tableCellClass, "border-l px-0")}>
              <DurationCell form={form} mode={mode} index={k} />
            </td>
          ))}
        </tr>
        {items.map((item, i) => (
          <tr key={item.id ?? i}>
            <th className={rowHeadClass}>
              <ItemHeader item={item} index={i} />
            </th>
            {modes.map((mode, k) => (
              <td key={mode.id ?? k} className={cn(tableCellClass, "border-l px-0")}>
                <StateCell form={form} item={item} itemIndex={i} mode={mode} modeIndex={k} />
              </td>
            ))}
          </tr>
        ))}
        <tr>
          <th className={rowHeadClass} />
          {modes.map((mode, k) => (
            <td key={mode.id ?? k} className={cn(tableCellClass, "border-l text-center")}>
              <DeleteModeButton artifact={artifact} mode={mode} index={k} onEdit={onEdit} />
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

/** Operating modes in rows, items in columns: duration after the name, delete last. */
function ByModes({ form, artifact, items, modes, renaming, onRenaming, onEdit }: MatrixProps) {
  return (
    <table className="w-full border-collapse [&_tr:last-child>*]:border-b-0">
      <thead>
        <tr className="bg-surface-2">
          <th className={cn(tableHeadClass, "w-60")}>Modo operativo</th>
          <th className={cn(tableHeadClass, "w-32 border-l")}>{durationTitle(form)}</th>
          {items.map((item, i) => (
            <th key={item.id ?? i} className={cn(tableHeadClass, "border-l")}>
              <ItemHeader item={item} index={i} />
            </th>
          ))}
          <th className={cn(tableHeadClass, "w-11 border-l")} />
        </tr>
      </thead>
      <tbody>
        {modes.map((mode, k) => (
          <tr key={mode.id ?? k}>
            <th className={rowHeadClass}>
              <ModeHeader
                form={form}
                mode={mode}
                index={k}
                editing={renaming === mode.id}
                onEditing={(editing) => onRenaming(editing ? (mode.id ?? null) : null)}
              />
            </th>
            <td className={cn(tableCellClass, "border-l px-0")}>
              <DurationCell form={form} mode={mode} index={k} />
            </td>
            {items.map((item, i) => (
              <td key={item.id ?? i} className={cn(tableCellClass, "border-l px-0")}>
                <StateCell form={form} item={item} itemIndex={i} mode={mode} modeIndex={k} />
              </td>
            ))}
            <td className={cn(tableCellClass, "border-l px-0 text-center")}>
              <DeleteModeButton artifact={artifact} mode={mode} index={k} onEdit={onEdit} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
