import { useId } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type SelectOption = { value: string; label: string };

type SelectFieldProps = {
  label: string;
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  className?: string;
};

export function SelectField({
  label,
  options,
  value,
  defaultValue,
  onValueChange,
  placeholder,
  className,
}: SelectFieldProps) {
  const id = useId();
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </label>
      <Select
        items={options}
        value={value}
        defaultValue={defaultValue}
        onValueChange={(next) => {
          if (typeof next === "string") onValueChange?.(next);
        }}
      >
        <SelectTrigger id={id} className="w-full bg-background text-[13px]">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value} className="text-[13px]">
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
