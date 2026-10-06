import { Check, Undo2 } from "lucide-react";
import type { Problem } from "@/api/client";
import { Notice } from "@/components/feedback/notice";
import { Button } from "@/components/ui/button";
import { plural } from "@/lib/format";
import { cn } from "@/lib/utils";
import { problemsBySection, type JsonSchema, type LeafChange } from "./schema";

function errorCount(problems: Problem[]): string {
  return plural(problems.length, "error", "errores");
}

/**
 * Summary of the validation problems over a form: which fields, by section, and what applying
 * with errors means (a form cell fails; a computation cannot update).
 */
export function DraftErrors({
  schema,
  problems,
  hasDraft,
  computation = false,
}: {
  schema: JsonSchema;
  problems: Problem[];
  hasDraft: boolean;
  computation?: boolean;
}) {
  if (problems.length === 0) return null;
  const consequence = computation
    ? "Actualizar falla hasta corregirlos."
    : "la celda queda Fallida hasta corregirlos.";
  return (
    <Notice tone="error" title={`${errorCount(problems)} de validación`}>
      {problemsBySection(
        schema,
        problems.map((p) => p.path),
      )}
      .{" "}
      {computation || hasDraft
        ? `Podés aplicar igual: ${consequence}`
        : "La celda queda Fallida hasta corregirlos."}
    </Notice>
  );
}

/**
 * Bar under a form while there is a draft or the defaults were never applied: what changed
 * (or the errors), Discard and Apply. `className` lays out its content (centered column or the
 * whole width).
 */
export function DraftBar({
  hasDraft,
  problems,
  changes,
  applying,
  onDiscard,
  onApply,
  className,
}: {
  hasDraft: boolean;
  problems: Problem[];
  /** Fields of the draft that differ from the applied artifact. */
  changes: LeafChange[];
  applying: boolean;
  onDiscard: () => void;
  onApply: () => void;
  className?: string;
}) {
  return (
    <footer className="h-13 shrink-0 border-t border-border bg-surface px-6">
      <div className={cn(className, "h-full flex-row items-center gap-3")}>
        <span
          aria-hidden
          className={cn(
            "size-1.5 shrink-0 rounded-full",
            !hasDraft ? "bg-idle" : problems.length > 0 ? "bg-error" : "bg-primary",
          )}
        />
        <span className="flex-1 truncate text-ui text-muted-foreground">
          {hasDraft
            ? `${plural(changes.length, "cambio", "cambios")} sin aplicar · ${
                problems.length > 0
                  ? errorCount(problems)
                  : [...new Set(changes.map((c) => c.section))].join(", ")
              }`
            : "Sin aplicar · valores por defecto"}
        </span>
        <Button variant="ghost" disabled={!hasDraft || applying} onClick={onDiscard}>
          <Undo2 data-icon="inline-start" /> Descartar
        </Button>
        <Button disabled={applying} onClick={onApply}>
          <Check data-icon="inline-start" /> Aplicar
        </Button>
      </div>
    </footer>
  );
}
