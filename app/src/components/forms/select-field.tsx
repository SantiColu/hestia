import { useId } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { FieldLabel } from "./field-label";

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
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select
        items={options}
        value={value}
        defaultValue={defaultValue}
        onValueChange={(next) => {
          if (typeof next === "string") onValueChange?.(next);
        }}
      >
        <SelectTrigger id={id} className="w-full bg-background text-ui">
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
    </div>
  );
}
