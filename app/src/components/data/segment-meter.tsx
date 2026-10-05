import { cn } from "@/lib/utils";

/** Segments of the meter (`docs/etapas/equipment.md`, «Pantalla»). */
const SEGMENTS = 5;

/**
 * How a value compares with the largest one shown next to it, in 5 segments of the heat color
 * (e.g. the dissipation of each operating mode). Presentation only: any positive value lights
 * at least one segment; zero or nothing to compare lights none.
 */
export function SegmentMeter({
  value,
  max,
  className,
}: {
  value: number;
  /** The largest value it is compared with. */
  max: number;
  className?: string;
}) {
  const lit = max > 0 && value > 0 ? Math.min(SEGMENTS, Math.ceil((value / max) * SEGMENTS)) : 0;
  return (
    <span
      role="img"
      aria-label={`${lit} de ${SEGMENTS}`}
      className={cn("inline-flex shrink-0 items-center gap-px", className)}
    >
      {Array.from({ length: SEGMENTS }, (_, i) => (
        <span
          key={i}
          className={cn("h-3 w-1 rounded-xs", i < lit ? "bg-hot" : "bg-border-strong")}
        />
      ))}
    </span>
  );
}
