import { useId, type ComponentProps } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type JustificationFieldProps = Omit<ComponentProps<typeof Textarea>, "required"> & {
  label?: string;
  error?: string;
};

/** Required rationale for every write operation (author + justification). */
export function JustificationField({
  label = "Justificación",
  error,
  className,
  id,
  placeholder = "Por qué se hace este cambio…",
  ...props
}: JustificationFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={inputId} className="flex gap-1 text-xs text-muted-foreground">
        {label}
        <span className="text-primary" aria-hidden>
          *
        </span>
      </label>
      <Textarea
        id={inputId}
        required
        placeholder={placeholder}
        aria-invalid={error ? true : undefined}
        className="min-h-20 bg-background text-ui placeholder:text-subtle-foreground md:text-ui"
        {...props}
      />
      <p className={cn("text-xs", error ? "text-error" : "text-subtle-foreground")}>
        {error ?? "Queda en el historial junto con el autor. Obligatoria para todo cambio."}
      </p>
    </div>
  );
}
