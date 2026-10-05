import { Plus, Trash2 } from "lucide-react";
import type { EquipmentArtifact } from "@/api/client";
import { tableCellClass, tableHeadClass } from "@/components/forms/table-inputs";
import { SectionLabel } from "@/components/navigation/section-label";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { FieldCell, NumberFieldOf, type EquipmentForm } from "./cells";
import { addItemMode, itemsOf, modesOf, removeItemMode } from "./edits";
import { columnTitle, fieldOf } from "./equipment-schema";

/** Optional limits of an item, beside its modes. */
const LIMITS = ["non_operating_min", "non_operating_max", "switch_on_min"] as const;

/**
 * The expanded row of an item: its own modes (name and dissipation per item) and its optional
 * limits. Off is never entered: every item has it.
 */
export function ItemDetails({
  form,
  artifact,
  index,
  onEdit,
}: {
  form: EquipmentForm;
  artifact: EquipmentArtifact;
  index: number;
  onEdit: (next: EquipmentArtifact) => void;
}) {
  const item = itemsOf(artifact)[index];
  if (!item) return null;
  const modeFields = form.schema.mode;
  const modesField = fieldOf(form.schema.item, "modes");
  const modes = modesOf(item);
  const name = item.name?.trim() || "este equipo";

  return (
    <div className="grid grid-cols-2 items-start gap-10">
      <div className="flex flex-col gap-2.5">
        <SectionLabel>{modesField.meta.title}</SectionLabel>
        <div className="overflow-hidden rounded-lg border border-border bg-background">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-surface-2">
                <th className={tableHeadClass}>{columnTitle(fieldOf(modeFields, "name"))}</th>
                <th className={cn(tableHeadClass, "w-32")}>
                  {columnTitle(fieldOf(modeFields, "dissipation"))}
                </th>
                <th className={cn(tableHeadClass, "w-11")} />
              </tr>
            </thead>
            <tbody className="[&>tr:last-child>td]:border-b-0">
              {modes.map((mode, modeIndex) => {
                const path = ["items", index, "modes", modeIndex];
                const modeName = mode.name?.trim() || `modo ${modeIndex + 1}`;
                return (
                  <tr key={mode.id ?? modeIndex}>
                    {(["name", "dissipation"] as const).map((key) => {
                      const f = fieldOf(modeFields, key);
                      return (
                        <td key={key} className={cn(tableCellClass, "px-0")}>
                          <FieldCell
                            form={form}
                            f={f}
                            path={[...path, key]}
                            label={`${f.meta.title ?? key} de ${modeName} (${name})`}
                          />
                        </td>
                      );
                    })}
                    <td className={cn(tableCellClass, "px-0 text-center")}>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label={`Eliminar ${modeName}`}
                        title="Eliminar modo"
                        className="text-subtle-foreground"
                        onClick={() => onEdit(removeItemMode(artifact, index, modeIndex))}
                      >
                        <Trash2 />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-fit"
            onClick={() => onEdit(addItemMode(artifact, index, form.schema.prefixes))}
          >
            <Plus data-icon="inline-start" /> {modesField.meta["x-add-label"]}
          </Button>
          <p className="text-xs text-subtle-foreground">
            Apagado está siempre disponible: 0 W, con los límites no operativos.
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-2.5">
        <SectionLabel>Límites opcionales</SectionLabel>
        <div className="grid grid-cols-3 gap-4">
          {LIMITS.map((key) => (
            <NumberFieldOf
              key={key}
              form={form}
              f={fieldOf(form.schema.item, key)}
              path={["items", index, key]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
