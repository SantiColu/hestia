import { useState } from "react";
import { Plus } from "lucide-react";
import type { EquipmentArtifact, EquipmentItem, OperatingMode } from "@/api/client";
import { Segmented } from "@/components/forms/segmented";
import { tableCellClass, tableHeadClass } from "@/components/forms/table-inputs";
import { SectionLabel } from "@/components/navigation/section-label";
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

/** A column of the matrix (an operating mode, or an item when transposed). */
const columnClass = "w-45 border-l";
/** The narrow empty column that closes the rows of the matrix, as in the design. */
const endColumnClass = "w-11 border-l";
/** Padding of a cell holding a `ModeHeader` (name and total in two lines). */
const modeHeadPadding = "pt-1 pr-1 pb-1.5";
/** Row header of an item: its name with the quantity. */
const itemHeadClass = cn(tableCellClass, "min-w-60 px-3 text-left text-ui font-normal");
/** Row header of a shaded row: the duration, and the operating modes when transposed. */
const shadedHeadClass = cn(
  tableCellClass,
  "min-w-45 bg-surface-2 text-left text-xs font-normal text-muted-foreground",
);

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
    <section className="flex flex-col gap-3.5">
      <div className="flex items-center gap-3">
        <SectionLabel className="flex-1">
          {form.schema.root.properties?.operating_modes?.title}
        </SectionLabel>
        <span className="text-xs text-subtle-foreground">Filas</span>
        <Segmented
          aria-label="Filas de la matriz"
          options={ROWS}
          value={rows}
          onValueChange={setRows}
          className="border-0 bg-surface-2"
        />
      </div>
      <p className="text-xs text-subtle-foreground">
        Cada modo operativo es una configuración del satélite: en qué modo está cada equipo. Apagado
        usa los límites no operativos. Σ: disipación total del modo (cantidad × disipación, la
        calcula el backend); sus barras comparan los modos entre sí. Las barras de cada celda
        comparan la disipación por ítem con la mayor de la tabla.
      </p>
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
    </section>
  );
}

function durationTitle(form: EquipmentForm): string {
  return columnTitle(fieldOf(form.schema.operatingMode, "max_duration"));
}

/** Items in rows, operating modes in columns: duration first, delete last. */
function ByItems({ form, artifact, items, modes, renaming, onRenaming, onEdit }: MatrixProps) {
  const endCell = <td className={cn(tableCellClass, endColumnClass)} />;
  return (
    <table className="w-full border-collapse [&>tbody>tr:last-child>*]:border-b-0">
      <thead>
        <tr className="bg-surface-2">
          <th className={tableHeadClass}>Equipo \ Modo operativo</th>
          {modes.map((mode, k) => (
            <th key={mode.id ?? k} className={cn(tableHeadClass, columnClass, modeHeadPadding)}>
              <ModeHeader
                form={form}
                mode={mode}
                index={k}
                editing={renaming === mode.id}
                onEditing={(editing) => onRenaming(editing ? (mode.id ?? null) : null)}
              />
            </th>
          ))}
          <th className={cn(tableHeadClass, endColumnClass)} />
        </tr>
      </thead>
      <tbody>
        <tr className="bg-surface-2">
          <th className={shadedHeadClass}>{durationTitle(form)}</th>
          {modes.map((mode, k) => (
            <td key={mode.id ?? k} className={cn(tableCellClass, "border-l px-0")}>
              <DurationCell form={form} mode={mode} index={k} />
            </td>
          ))}
          {endCell}
        </tr>
        {items.map((item, i) => (
          <tr key={item.id ?? i}>
            <th className={itemHeadClass}>
              <ItemHeader item={item} index={i} />
            </th>
            {modes.map((mode, k) => (
              <td key={mode.id ?? k} className={cn(tableCellClass, "border-l px-0")}>
                <StateCell form={form} item={item} itemIndex={i} mode={mode} modeIndex={k} />
              </td>
            ))}
            {endCell}
          </tr>
        ))}
        <tr>
          <th className={tableCellClass} />
          {modes.map((mode, k) => (
            <td key={mode.id ?? k} className={cn(tableCellClass, "border-l text-center")}>
              <DeleteModeButton artifact={artifact} mode={mode} index={k} onEdit={onEdit} />
            </td>
          ))}
          {endCell}
        </tr>
      </tbody>
    </table>
  );
}

/** Operating modes in rows, items in columns: duration after the name, delete last. */
function ByModes({ form, artifact, items, modes, renaming, onRenaming, onEdit }: MatrixProps) {
  return (
    <table className="w-full border-collapse [&>tbody>tr:last-child>*]:border-b-0">
      <thead>
        <tr className="bg-surface-2">
          <th className={cn(tableHeadClass, "w-45")}>Modo operativo \ Equipo</th>
          <th className={cn(tableHeadClass, "w-32 border-l whitespace-nowrap")}>
            {durationTitle(form)}
          </th>
          {items.map((item, i) => (
            <th key={item.id ?? i} className={cn(tableHeadClass, columnClass)}>
              <ItemHeader item={item} index={i} />
            </th>
          ))}
          <th className={cn(tableHeadClass, endColumnClass)} />
        </tr>
      </thead>
      <tbody>
        {modes.map((mode, k) => (
          <tr key={mode.id ?? k}>
            <th className={cn(shadedHeadClass, modeHeadPadding)}>
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
