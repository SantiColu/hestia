import { ArrowDownToLine } from "lucide-react";
import { StageStatusBadge, type StageStatus } from "@/components/feedback/stage-status";
import { cn } from "@/lib/utils";

type ProvenanceRowProps = {
  /** Artifact reference, e.g. "environment.load_cases". */
  artifact: string;
  /** Where it comes from, e.g. "de 0.2 Entorno · esquema v3 · hace 5 min". */
  source: string;
  status: StageStatus;
  className?: string;
};

/** One input artifact of a stage and the upstream stage that produced it. */
export function ProvenanceRow({ artifact, source, status, className }: ProvenanceRowProps) {
  return (
    <div className={cn("flex items-center gap-2.5 border-b border-border py-2", className)}>
      <ArrowDownToLine className="size-3.5 shrink-0 text-subtle-foreground" aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-mono text-xs">{artifact}</span>
        <span className="truncate text-[11px] text-subtle-foreground">{source}</span>
      </div>
      <StageStatusBadge status={status} />
    </div>
  );
}
