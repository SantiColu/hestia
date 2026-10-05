import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";
import type { EquipmentArtifact, EquipmentItem } from "@/api/client";
import { tableCellClass, tableHeadClass } from "@/components/forms/table-inputs";
import { Button } from "@/components/ui/button";
import { plural } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FieldCell, type EquipmentForm } from "./cells";
import { addItem, itemName, itemsOf, modesOf, removeItem } from "./edits";
import { columnTitle, fieldOf } from "./equipment-schema";
import { ItemDetails } from "./item-details";
import { ProblemLines } from "./problem-lines";

/** Columns of the items table after the expander, with their widths and whether the value is
 * mono (numbers and the face codes of the location). Subsystem is wider than in the design: its
 * labels are full names («Computadora de a bordo»), not codes. */
const COLUMNS: { key: string; className?: string; mono?: boolean }[] = [
  { key: "name" },
  { key: "quantity", className: "w-14" },
  { key: "subsystem", className: "w-44" },
  { key: "mass", className: "w-20" },
  { key: "location", className: "w-21", mono: true },
  { key: "operating_min", className: "w-23" },
  { key: "operating_max", className: "w-23" },
];
/** Expander + columns + mode count + delete. */
const COLUMN_COUNT = COLUMNS.length + 3;

/**
 * The items (equipment) of the draft: one row per item with its main fields and how many modes
 * it has; a row expands to its modes and optional limits. Adding or deleting an item edits the
 * draft (`edits.ts`).
 */
export function ItemsTable({
  form,
  artifact,
  onEdit,
}: {
  form: EquipmentForm;
  /** The draft, typed. */
  artifact: EquipmentArtifact;
  onEdit: (next: EquipmentArtifact) => void;
}) {
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const items = itemsOf(artifact);
  const fields = form.schema.item;

  const toggle = (key: string) =>
    setExpanded((previous) => {
      const next = new Set(previous);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  const add = () => {
    const next = addItem(artifact, form.schema.prefixes);
    const added = itemsOf(next).at(-1)?.id;
    if (added) setExpanded((previous) => new Set(previous).add(added));
    onEdit(next);
  };

  return (
    <div className="flex flex-col gap-3.5">
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-surface-2">
              <th className={cn(tableHeadClass, "w-8")} />
              {COLUMNS.map(({ key, className }) => (
                <th key={key} className={cn(tableHeadClass, "whitespace-nowrap", className)}>
                  {columnTitle(fieldOf(fields, key))}
                </th>
              ))}
              <th className={cn(tableHeadClass, "w-24")}>{fieldOf(fields, "modes").meta.title}</th>
              <th className={cn(tableHeadClass, "w-11")} />
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => {
              const key = item.id ?? String(index);
              const open = expanded.has(key);
              const name = itemName(item, index);
              return (
                <ItemRows
                  key={key}
                  form={form}
                  artifact={artifact}
                  item={item}
                  index={index}
                  name={name}
                  open={open}
                  onToggle={() => toggle(key)}
                  onEdit={onEdit}
                />
              );
            })}
          </tbody>
        </table>
      </div>
      <ProblemLines
        problems={form.problems}
        list="items"
        nameOf={(i) => {
          const item = items[i];
          return item && itemName(item, i);
        }}
      />
      <Button variant="ghost" className="w-fit" onClick={add}>
        <Plus data-icon="inline-start" /> {form.schema.root.properties?.items?.["x-add-label"]}
      </Button>
    </div>
  );
}

function ItemRows({
  form,
  artifact,
  item,
  index,
  name,
  open,
  onToggle,
  onEdit,
}: {
  form: EquipmentForm;
  artifact: EquipmentArtifact;
  item: EquipmentItem;
  index: number;
  name: string;
  open: boolean;
  onToggle: () => void;
  onEdit: (next: EquipmentArtifact) => void;
}) {
  const fields = form.schema.item;
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <>
      <tr className={cn(open && "bg-surface-2")}>
        <td className={cn(tableCellClass, "px-0 text-center")}>
          <Button
            size="icon-sm"
            variant="ghost"
            aria-expanded={open}
            aria-label={open ? `Contraer ${name}` : `Expandir ${name}`}
            title={open ? "Contraer" : "Modos y límites opcionales"}
            className="text-subtle-foreground"
            onClick={onToggle}
          >
            <Chevron />
          </Button>
        </td>
        {COLUMNS.map(({ key, mono }) => {
          const f = fieldOf(fields, key);
          return (
            <td key={key} className={cn(tableCellClass, "px-0")}>
              <FieldCell
                form={form}
                f={f}
                path={["items", index, key]}
                label={`${f.meta.title ?? key} de ${name}`}
                className={cn(mono && "font-mono")}
              />
            </td>
          );
        })}
        <td className={cn(tableCellClass, "text-xs")}>
          {plural(modesOf(item).length, "modo", "modos")}
        </td>
        <td className={cn(tableCellClass, "px-0 text-center")}>
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={`Eliminar ${name}`}
            title="Eliminar equipo"
            className="text-subtle-foreground"
            onClick={() => onEdit(removeItem(artifact, index))}
          >
            <Trash2 />
          </Button>
        </td>
      </tr>
      {open && (
        <tr className="bg-surface-2">
          <td colSpan={COLUMN_COUNT} className="border-b border-border pt-3.5 pr-4 pb-4 pl-12">
            <ItemDetails form={form} artifact={artifact} index={index} onEdit={onEdit} />
          </td>
        </tr>
      )}
    </>
  );
}
