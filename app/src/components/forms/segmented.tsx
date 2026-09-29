import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

type SegmentedProps<T extends string> = {
  options: { value: T; label: string }[];
  value?: T;
  defaultValue?: T;
  onValueChange?: (value: T) => void;
  "aria-label": string;
  className?: string;
};

/** Single-choice segmented control (e.g. steady state / transient). */
export function Segmented<T extends string>({
  options,
  value,
  defaultValue,
  onValueChange,
  className,
  ...props
}: SegmentedProps<T>) {
  return (
    <ToggleGroup
      aria-label={props["aria-label"]}
      spacing={0}
      value={value !== undefined ? [value] : undefined}
      defaultValue={defaultValue !== undefined ? [defaultValue] : undefined}
      onValueChange={(next) => {
        const [selected] = next as T[];
        if (selected !== undefined) onValueChange?.(selected);
      }}
      className={cn("gap-0.5 border border-border bg-background p-0.5", className)}
    >
      {options.map((option) => (
        <ToggleGroupItem
          key={option.value}
          value={option.value}
          className={cn(
            "h-6 rounded-md! border border-transparent px-2.5 text-xs font-normal text-muted-foreground hover:bg-transparent",
            "aria-pressed:border-border-strong aria-pressed:bg-surface aria-pressed:font-medium aria-pressed:text-foreground",
          )}
        >
          {option.label}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
