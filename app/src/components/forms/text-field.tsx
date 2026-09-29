import { useId, type ComponentProps, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { fieldBoxClass } from "./field-box";
import { FieldFootnote, FieldLabel } from "./field-label";

type TextFieldProps = Omit<ComponentProps<"input">, "className"> & {
  label: string;
  error?: string;
  /** The value differs from the applied one. */
  modified?: boolean;
  /** Line under the input when there is no error, e.g. "Aplicado: 10:30". */
  hint?: ReactNode;
  /** Mono value, for dates, times and codes. */
  mono?: boolean;
  /** Text to the right of the value, e.g. the expected format "hh:mm". */
  suffix?: string;
  className?: string;
};

export function TextField({
  label,
  error,
  modified,
  hint,
  mono,
  suffix,
  className,
  id,
  ...props
}: TextFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <FieldLabel htmlFor={inputId} modified={modified}>
        {label}
      </FieldLabel>
      <div className={fieldBoxClass({ error: !!error, modified })}>
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          className={cn(
            "min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:font-sans placeholder:text-subtle-foreground",
            mono && "font-mono tabular-nums",
          )}
          {...props}
        />
        {suffix && (
          <span className="shrink-0 font-mono text-xs text-subtle-foreground">{suffix}</span>
        )}
      </div>
      <FieldFootnote error={error} hint={hint} />
    </div>
  );
}
