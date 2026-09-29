import { RefreshCw } from "lucide-react";
import type { CellResult } from "@/api/client";
import { EmptyState } from "@/components/data/empty-state";
import { Notice } from "@/components/feedback/notice";
import { Button } from "@/components/ui/button";

/**
 * What the result section says about the cell's state (ADR 0021): no result yet, failed with
 * problems, or outdated. Returns whether there is a result to show.
 */
export function ResultState({
  result,
  updating,
  onUpdate,
}: {
  result: CellResult | null;
  updating: boolean;
  onUpdate: () => void;
}) {
  if (!result) return <p className="text-xs text-subtle-foreground">Cargando…</p>;
  return (
    <>
      {result.status === "failed" && (
        <Notice tone="error" title="La última actualización falló">
          <ul className="list-disc pl-4">
            {result.problems.map((p) => (
              <li key={`${p.path}:${p.code}`}>{p.message}</li>
            ))}
          </ul>
          {result.environment && "Se muestra el resultado anterior."}
        </Notice>
      )}
      {result.status === "outdated" && result.environment && (
        <Notice tone="warning" title="Resultado desactualizado">
          Cambió algo aguas arriba o se aplicaron parámetros nuevos. Actualizá para recalcular.
        </Notice>
      )}
      {!result.environment && (
        <EmptyState
          icon={RefreshCw}
          title="Sin resultado"
          description="La celda todavía no se actualizó. Actualizar calcula el entorno con los parámetros aplicados y la Misión de su contexto."
          action={
            <Button size="sm" onClick={onUpdate} disabled={updating}>
              <RefreshCw data-icon="inline-start" /> Actualizar
            </Button>
          }
        />
      )}
    </>
  );
}
