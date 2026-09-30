import type { ReactNode } from "react";
import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { clock } from "./format";
import type { OrbitClock } from "./use-orbit-clock";

/** Play/pause, the instant and a bar over one orbit (`Timeline` in the design). */
export function OrbitTimeline({
  clock: orbit,
  period,
  children,
}: {
  clock: OrbitClock;
  period: number;
  /** Extra controls after the total (e.g. the speed). */
  children?: ReactNode;
}) {
  return (
    <div className="flex h-9 shrink-0 items-center gap-2.5 rounded-lg border border-border bg-background px-2.5">
      <Button
        size="icon-xs"
        variant="ghost"
        aria-label={orbit.playing ? "Pausa" : "Reproducir"}
        title={orbit.playing ? "Pausa" : "Reproducir"}
        onClick={orbit.toggle}
      >
        {orbit.playing ? <Pause /> : <Play />}
      </Button>
      <span className="font-mono text-xs tabular-nums">{clock(orbit.time)}</span>
      <input
        type="range"
        aria-label="Instante de la órbita"
        min={0}
        max={period || 1}
        step={period / 1000 || 1}
        value={orbit.time}
        onChange={(e) => orbit.seek(Number(e.target.value))}
        className="min-w-0 flex-1 accent-primary"
      />
      <span className="font-mono text-xs text-subtle-foreground tabular-nums">{clock(period)}</span>
      {children}
    </div>
  );
}
