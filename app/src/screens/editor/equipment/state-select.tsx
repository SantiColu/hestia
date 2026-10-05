import type { EquipmentItem } from "@/api/client";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SegmentMeter } from "@/components/data/segment-meter";
import { cn } from "@/lib/utils";
import { fmtUpTo } from "../format";
import { modesOf } from "./edits";

/** The option of Off, which is `null` in the artifact. Not an id: ids have `<prefix>_<hex>`. */
const OFF = "off";
const OFF_LABEL = "Apagado";

type Option = { value: string; label: string; dissipation?: number | null };

function optionsOf(item: EquipmentItem): Option[] {
  const modes = modesOf(item).flatMap((mode, i) =>
    mode.id
      ? [
          {
            value: mode.id,
            label: mode.name?.trim() || `Modo ${i + 1}`,
            dissipation: mode.dissipation,
          },
        ]
      : [],
  );
  return [...modes, { value: OFF, label: OFF_LABEL }];
}

/** «Nominal  8 W ▮▮▯▯▯»: a mode with its dissipation per item and a meter against the largest
 * of the table; Off has neither. */
function OptionLabel({ option, maxPerItem }: { option: Option; maxPerItem: number }) {
  if (option.value === OFF) return <span className="text-subtle-foreground">{option.label}</span>;
  const watts = option.dissipation;
  return (
    <span className="flex min-w-0 flex-1 items-center gap-2">
      <span className="flex-1 truncate">{option.label}</span>
      <span className="font-mono text-subtle-foreground tabular-nums">
        {typeof watts === "number" ? fmtUpTo(watts) : "—"} W
      </span>
      <SegmentMeter value={watts ?? 0} max={maxPerItem} />
    </span>
  );
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
  maxPerItem,
  onChange,
}: {
  /** Accessible name, e.g. «Rueda de reacción en Adquisición». */
  label: string;
  item: EquipmentItem;
  value: string | null | undefined;
  applied: string | null | undefined;
  error?: string;
  /** Largest dissipation per item of the table, W: what the meters compare against. */
  maxPerItem: number;
  onChange: (value: string | null) => void;
}) {
  const options = optionsOf(item);
  const asOption = (state: string | null | undefined) =>
    state === undefined ? null : (state ?? OFF);
  const find = (option: string | null) => options.find((o) => o.value === option);
  const labelOf = (option: string | null) =>
    option === null ? "—" : (find(option)?.label ?? "Modo inexistente");
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
        <SelectValue>
          {(value: string | null) => {
            const option = find(value);
            return option ? (
              <OptionLabel option={option} maxPerItem={maxPerItem} />
            ) : (
              labelOf(value)
            );
          }}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value} className="min-w-56 text-xs">
            <OptionLabel option={option} maxPerItem={maxPerItem} />
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
