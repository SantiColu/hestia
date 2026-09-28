import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type MetricProps = {
  label: string;
  value: string;
  unit?: string;
  /** Secondary line, e.g. change vs. previous run. */
  detail?: string;
  className?: string;
};

/** Prominent read-only value. Formatting is the caller's job: values arrive computed from the API. */
export function Metric({ label, value, unit, detail, className }: MetricProps) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="flex items-baseline gap-1.5">
        <span className="font-mono text-2xl tabular-nums">{value}</span>
        {unit && <span className="font-mono text-[13px] text-subtle-foreground">{unit}</span>}
      </span>
      {detail && <span className="font-mono text-[11px] text-subtle-foreground">{detail}</span>}
    </div>
  );
}

type KeyValueProps = {
  label: ReactNode;
  value: ReactNode;
  className?: string;
};

export function KeyValue({ label, value, className }: KeyValueProps) {
  return (
    <div
      className={cn(
        "flex h-7 items-center justify-between gap-4 border-b border-border text-xs",
        className,
      )}
    >
      <span className="whitespace-nowrap text-muted-foreground">{label}</span>
      <span className="font-mono whitespace-nowrap tabular-nums">{value}</span>
    </div>
  );
}
