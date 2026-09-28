import { useId, type ComponentProps } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

type WithLabel<T> = T & { label: string };

export function CheckboxField({
  label,
  className,
  id,
  ...props
}: WithLabel<ComponentProps<typeof Checkbox>>) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Checkbox id={inputId} className="bg-background" {...props} />
      <label htmlFor={inputId} className="text-[13px]">
        {label}
      </label>
    </div>
  );
}

export function SwitchField({
  label,
  className,
  id,
  ...props
}: WithLabel<ComponentProps<typeof Switch>>) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Switch id={inputId} size="sm" {...props} />
      <label htmlFor={inputId} className="text-[13px]">
        {label}
      </label>
    </div>
  );
}
