import {
  CircleCheck,
  CircleDashed,
  CircleX,
  LoaderCircle,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Stage state as reported by the API. `running` is transient (a run in progress).
 * TODO: replace with the type from the generated API client once it exists.
 */
export type StageStatus = "up_to_date" | "outdated" | "failed" | "never_run" | "running";

const STATUS: Record<StageStatus, { label: string; className: string; dot: string }> = {
  up_to_date: { label: "Actualizada", className: "bg-ok-soft text-ok", dot: "bg-ok" },
  outdated: { label: "Desactualizada", className: "bg-warn-soft text-warn", dot: "bg-warn" },
  failed: { label: "Fallida", className: "bg-error-soft text-error", dot: "bg-error" },
  never_run: { label: "Sin correr", className: "bg-idle-soft text-idle", dot: "bg-idle" },
  running: { label: "Corriendo", className: "bg-primary-soft text-primary", dot: "" },
};

export function StageStatusBadge({
  status,
  className,
}: {
  status: StageStatus;
  className?: string;
}) {
  const { label, className: tone, dot } = STATUS[status];
  return (
    <span
      className={cn(
        "inline-flex h-5 w-fit shrink-0 items-center gap-1.5 rounded-lg px-2 text-xs font-medium whitespace-nowrap",
        tone,
        className,
      )}
    >
      {status === "running" ? (
        <LoaderCircle className="size-3 animate-spin" aria-hidden />
      ) : (
        <span className={cn("size-1.5 rounded-full", dot)} aria-hidden />
      )}
      {label}
    </span>
  );
}

const ICON: Record<StageStatus, { icon: LucideIcon; className: string }> = {
  up_to_date: { icon: CircleCheck, className: "text-ok" },
  outdated: { icon: RefreshCw, className: "text-warn" },
  failed: { icon: CircleX, className: "text-error" },
  never_run: { icon: CircleDashed, className: "text-idle" },
  running: { icon: LoaderCircle, className: "animate-spin text-primary" },
};

/** Compact state of a schematic cell: a colored icon, labelled for tooltips and screen readers. */
export function StageStatusIcon({
  status,
  className,
}: {
  status: StageStatus;
  className?: string;
}) {
  const { icon: Icon, className: tone } = ICON[status];
  const { label } = STATUS[status];
  return (
    <Icon role="img" aria-label={label} className={cn("size-3.5 shrink-0", tone, className)}>
      <title>{label}</title>
    </Icon>
  );
}
