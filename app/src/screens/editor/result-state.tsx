import { CircleX, RefreshCw, SquareArrowOutUpRight } from "lucide-react";
import type { CellResult, Problem } from "@/api/client";
import { EmptyState } from "@/components/data/empty-state";
import { Notice } from "@/components/feedback/notice";
import { Button } from "@/components/ui/button";

export type ResultStateProps = {
  result: CellResult | null;
  updating: boolean;
  /** The cells the result reads from its context (`contextLabel`). */
  sources: string | null;
  onUpdate: () => void;
  onOpenParameters: () => void;
};

/**
 * What the result sections say about the cell's state (ADR 0021): no result yet, failed with
 * its problems (and the previous result, if any, below), or outdated.
 */
export function ResultState({
  result,
  updating,
  sources,
  onUpdate,
  onOpenParameters,
}: ResultStateProps) {
  if (!result) return <p className="text-xs text-subtle-foreground">Cargando…</p>;
  const failed = result.status === "failed";
  return (
    <>
      {failed && <Failure result={result} sources={sources} />}
      {result.status === "outdated" && result.environment && (
        <Notice tone="warning" title="Resultado desactualizado">
          Cambió algo aguas arriba o se aplicaron parámetros nuevos. Actualizá para recalcular.
        </Notice>
      )}
      {!result.environment &&
        (failed ? (
          <EmptyState
            icon={CircleX}
            title="Sin resultado"
            description="La última actualización no produjo resultado. Cuando corrijas el problema, actualizá la celda."
            action={
              <Button variant="secondary" onClick={onOpenParameters}>
                <SquareArrowOutUpRight data-icon="inline-start" /> Ir a Parámetros
              </Button>
            }
          />
        ) : (
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
        ))}
    </>
  );
}

/** The problems of the last update, each with its code and field, and what it read. */
function Failure({ result, sources }: { result: CellResult; sources: string | null }) {
  const [first] = result.problems;
  const provider = result.provenance
    ? `${result.provenance.provider} ${result.provenance.provider_version}`
    : null;
  return (
    <>
      <Notice tone="error" title="No se pudo actualizar">
        {result.problems.length === 1 ? (
          first?.message
        ) : (
          <ul className="list-disc pl-4">
            {result.problems.map((p) => (
              <li key={`${p.path}:${p.code}`}>{p.message}</li>
            ))}
          </ul>
        )}
        {result.environment && " Se muestra el resultado anterior."}
      </Notice>
      <dl className="flex flex-col rounded-lg border border-border text-xs">
        {result.problems.map((p) => (
          <ProblemRows key={`${p.path}:${p.code}`} problem={p} stage={result.stage} />
        ))}
        {sources && <Row label="Contexto" value={sources} />}
        {provider && <Row label="Proveedor" value={provider} />}
      </dl>
    </>
  );
}

function ProblemRows({ problem, stage }: { problem: Problem; stage: string }) {
  return (
    <>
      <Row label="Código" value={problem.code} />
      <Row label="Campo" value={`${stage} · ${problem.path}`} />
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex h-8 items-center gap-4 border-b border-border px-3 last:border-b-0">
      <dt className="w-26 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="truncate font-mono">{value}</dd>
    </div>
  );
}
