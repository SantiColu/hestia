import type { LucideIcon } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { SelectOption } from "./select-field";

type CompactSelectProps = {
  /** Accessible name: the control has no visible label. */
  label: string;
  icon?: LucideIcon;
  options: SelectOption[];
  value: string | null;
  onValueChange: (value: string) => void;
  placeholder?: string;
  className?: string;
};

/** Toolbar selector with an icon and no label (condition, attitude mode over a view). */
export function CompactSelect({
  label,
  icon: Icon,
  options,
  value,
  onValueChange,
  placeholder,
  className,
}: CompactSelectProps) {
  return (
    <Select
      items={options}
      value={value}
      onValueChange={(next) => {
        if (typeof next === "string") onValueChange(next);
      }}
      disabled={options.length === 0}
    >
      <SelectTrigger
        size="sm"
        aria-label={label}
        title={label}
        className={cn("min-w-0 bg-background text-ui", className)}
      >
        {Icon && <Icon aria-hidden className="text-subtle-foreground" />}
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value} className="text-ui">
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
