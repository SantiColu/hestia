import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";
import type { EquipmentArtifact, EquipmentItem, Problem } from "@/api/client";
import { tableCellClass, tableHeadClass } from "@/components/forms/table-inputs";
import { Button } from "@/components/ui/button";
import { plural } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FieldCell, type EquipmentForm } from "./cells";
import { addItem, itemName, itemsOf, modesOf, removeItem } from "./edits";
import { columnTitle, fieldOf } from "./equipment-schema";
import { ItemDetails } from "./item-details";

/** Columns of the items table after the expander, with their widths. */
const COLUMNS: { key: string; className?: string }[] = [
  { key: "name" },
  { key: "quantity", className: "w-16" },
  { key: "subsystem", className: "w-44" },
  { key: "mass", className: "w-24" },
  { key: "location", className: "w-26" },
  { key: "operating_min", className: "w-28" },
  { key: "operating_max", className: "w-28" },
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
                <th key={key} className={cn(tableHeadClass, className)}>
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
      <ProblemLines problems={form.problems} items={items} />
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
      <tr className={cn(open && "bg-surface")}>
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
        {COLUMNS.map(({ key }) => {
          const f = fieldOf(fields, key);
          return (
            <td key={key} className={cn(tableCellClass, "px-0")}>
              <FieldCell
                form={form}
                f={f}
                path={["items", index, key]}
                label={`${f.meta.title ?? key} de ${name}`}
              />
            </td>
          );
        })}
        <td className={cn(tableCellClass, "text-xs text-muted-foreground")}>
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
        <tr className="bg-surface">
          <td colSpan={COLUMN_COUNT} className="border-b border-border px-10 py-4">
            <ItemDetails form={form} artifact={artifact} index={index} onEdit={onEdit} />
          </td>
        </tr>
      )}
    </>
  );
}

/** The problems of the items, one line per item: «Rueda de reacción: Falta la masa. …». */
function ProblemLines({ problems, items }: { problems: Problem[]; items: EquipmentItem[] }) {
  const lines = new Map<string, string[]>();
  for (const problem of problems) {
    const match = /^items(?:\[(\d+)\])?/.exec(problem.path);
    if (!match) continue;
    const index = match[1] === undefined ? undefined : Number(match[1]);
    const item = index === undefined ? undefined : items[index];
    const prefix = item && index !== undefined ? `${itemName(item, index)}: ` : "";
    lines.set(prefix, [...(lines.get(prefix) ?? []), problem.message]);
  }
  return [...lines].map(([prefix, messages]) => (
    <p key={prefix} className="-mt-1.5 text-xs text-error">
      {prefix}
      {messages.join(" ")}
    </p>
  ));
}
