import type { EquipmentItem } from "@/api/client";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { modesOf } from "./edits";

/** The option of Off, which is `null` in the artifact. Not an id: ids have `<prefix>_<hex>`. */
const OFF = "off";
const OFF_LABEL = "Apagado";

type Option = { value: string; label: string };

function optionsOf(item: EquipmentItem): Option[] {
  const modes = modesOf(item).flatMap((mode, i) =>
    mode.id ? [{ value: mode.id, label: mode.name?.trim() || `Modo ${i + 1}` }] : [],
  );
  return [...modes, { value: OFF, label: OFF_LABEL }];
}

/**
 * The state of an item in an operating mode, as a table cell: one of the item's own modes, or
 * Off (dimmed). `undefined` is a missing entry; an id that is not one of its modes shows as
 * such (the API reports both). A changed state shows the applied one on hover.
 */
export function StateSelect({
  label,
  item,
  value,
  applied,
  error,
  onChange,
}: {
  /** Accessible name, e.g. «Rueda de reacción en Adquisición». */
  label: string;
  item: EquipmentItem;
  value: string | null | undefined;
  applied: string | null | undefined;
  error?: string;
  onChange: (value: string | null) => void;
}) {
  const options = optionsOf(item);
  const asOption = (state: string | null | undefined) =>
    state === undefined ? null : (state ?? OFF);
  const labelOf = (option: string | null) =>
    option === null ? "—" : (options.find((o) => o.value === option)?.label ?? "Modo inexistente");
  const selected = asOption(value);
  const modified = selected !== asOption(applied);
  return (
    <Select
      items={options}
      value={selected}
      onValueChange={(next) => {
        if (typeof next === "string") onChange(next === OFF ? null : next);
      }}
    >
      <SelectTrigger
        size="sm"
        aria-label={label}
        aria-invalid={error ? true : undefined}
        title={error ?? (modified ? `Aplicado: ${labelOf(asOption(applied))}` : undefined)}
        className={cn(
          "h-8 w-full min-w-36 rounded-none border-0 bg-transparent px-2.5 text-xs dark:bg-transparent",
          "focus-visible:ring-1 focus-visible:ring-inset aria-invalid:ring-1 aria-invalid:ring-error aria-invalid:ring-inset",
          modified && "ring-1 ring-primary ring-inset",
          selected === OFF && "text-subtle-foreground",
        )}
      >
        <SelectValue>{(option: string | null) => labelOf(option)}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem
            key={option.value}
            value={option.value}
            className={cn("text-xs", option.value === OFF && "text-subtle-foreground")}
          >
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
