import { StageStatusBadge, type StageStatus } from "@/components/feedback/stage-status";
import { cn } from "@/lib/utils";

type StageNodeProps = {
  /** Stage number metadata, e.g. "0.3". */
  number: string;
  title: string;
  /** Stage id in snake_case, e.g. "global_balance". */
  stageId: string;
  status: StageStatus;
  selected?: boolean;
  className?: string;
};

/** Workflow graph node. Presentational only: React Flow will wrap it as a custom node. */
export function StageNode({ number, title, stageId, status, selected, className }: StageNodeProps) {
  return (
    <div
      aria-selected={selected}
      className={cn(
        "flex w-44 flex-col rounded-lg border border-border-strong bg-surface",
        selected && "border-primary ring-1 ring-primary",
        className,
      )}
    >
      <div className="flex flex-col gap-1 px-3 py-2.5">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs text-subtle-foreground">{number}</span>
          <span className="truncate text-sm font-semibold">{title}</span>
        </div>
        <span className="truncate font-mono text-[11px] text-subtle-foreground">{stageId}</span>
      </div>
      <div className="border-t border-border px-3 py-2">
        <StageStatusBadge status={status} />
      </div>
    </div>
  );
}
