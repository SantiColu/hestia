import { useId, type ComponentProps } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type TextFieldProps = ComponentProps<typeof Input> & {
  label: string;
  error?: string;
};

export function TextField({ label, error, className, id, ...props }: TextFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={inputId} className="text-xs text-muted-foreground">
        {label}
      </label>
      <Input
        id={inputId}
        aria-invalid={error ? true : undefined}
        className="bg-background text-[13px] md:text-[13px]"
        {...props}
      />
      {error && <p className="text-xs text-error">{error}</p>}
    </div>
  );
}
