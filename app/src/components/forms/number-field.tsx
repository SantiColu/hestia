import { useId } from "react";
import { NumberField as NumberFieldPrimitive } from "@base-ui/react/number-field";
import { cn } from "@/lib/utils";

type NumberFieldProps = Omit<NumberFieldPrimitive.Root.Props, "className" | "render"> & {
  label: string;
  /** Unit shown to the right of the value, e.g. "W", "m²", "°C". */
  unit?: string;
  /** Validation message; also marks the field as invalid. */
  error?: string;
  className?: string;
};

/**
 * Numeric input with a unit suffix. Values render in mono with a fixed "en-US"
 * locale so technical numbers always use a decimal point.
 */
export function NumberField({
  label,
  unit,
  error,
  className,
  id,
  locale = "en-US",
  format = { maximumFractionDigits: 6 },
  ...props
}: NumberFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <NumberFieldPrimitive.Root
      id={inputId}
      locale={locale}
      format={format}
      className={cn("flex flex-col gap-1.5", className)}
      {...props}
    >
      <label htmlFor={inputId} className="text-xs text-muted-foreground">
        {label}
      </label>
      <NumberFieldPrimitive.Group
        className={cn(
          "flex h-8 items-center gap-2 rounded-lg border border-input bg-background px-2.5 transition-colors",
          "focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30",
          "data-disabled:opacity-50",
          error && "border-error focus-within:border-error focus-within:ring-error/20",
        )}
      >
        <NumberFieldPrimitive.Input
          aria-invalid={error ? true : undefined}
          className="min-w-0 flex-1 bg-transparent font-mono text-[13px] tabular-nums outline-none"
        />
        {unit && <span className="shrink-0 font-mono text-xs text-subtle-foreground">{unit}</span>}
      </NumberFieldPrimitive.Group>
      {error && <p className="text-xs text-error">{error}</p>}
    </NumberFieldPrimitive.Root>
  );
}
