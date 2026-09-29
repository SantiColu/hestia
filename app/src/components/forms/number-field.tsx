import { useId, type ReactNode } from "react";
import { NumberField as NumberFieldPrimitive } from "@base-ui/react/number-field";
import { cn } from "@/lib/utils";
import { fieldBoxClass } from "./field-box";
import { FieldFootnote, FieldLabel } from "./field-label";

type NumberFieldProps = Omit<NumberFieldPrimitive.Root.Props, "className" | "render"> & {
  label: string;
  /** Unit shown to the right of the value, e.g. "W", "m²", "°C". */
  unit?: string;
  /** Validation message; also marks the field as invalid. */
  error?: string;
  /** The value differs from the applied one (`Field/Number/Modified`). */
  modified?: boolean;
  /** Line under the input when there is no error, e.g. "Aplicado: 550 km". */
  hint?: ReactNode;
  placeholder?: string;
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
  modified,
  hint,
  placeholder,
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
      <FieldLabel htmlFor={inputId} modified={modified}>
        {label}
      </FieldLabel>
      <NumberFieldPrimitive.Group className={fieldBoxClass({ error: !!error, modified })}>
        <NumberFieldPrimitive.Input
          aria-invalid={error ? true : undefined}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent font-mono text-ui tabular-nums outline-none placeholder:font-sans placeholder:text-subtle-foreground"
        />
        {unit && <span className="shrink-0 font-mono text-xs text-subtle-foreground">{unit}</span>}
      </NumberFieldPrimitive.Group>
      <FieldFootnote error={error} hint={hint} />
    </NumberFieldPrimitive.Root>
  );
}
