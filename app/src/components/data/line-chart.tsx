import { useId } from "react";
import { cn } from "@/lib/utils";

export type ChartSeries = {
  label: string;
  /** CSS color (a token, e.g. `var(--primary)`). */
  color: string;
  /** One value per x; null leaves a gap. */
  values: (number | null)[];
};

export type ChartBand = {
  label: string;
  color: string;
  low: number[];
  high: number[];
};

type LineChartProps = {
  /** x values (e.g. timestamps in ms), increasing. */
  x: number[];
  series?: ChartSeries[];
  bands?: ChartBand[];
  /** Unit of the y axis, shown with the ticks. */
  unit: string;
  formatX: (x: number) => string;
  formatY: (y: number) => string;
  height?: number;
  className?: string;
};

const WIDTH = 720;
const PAD = { left: 52, right: 12, top: 10, bottom: 22 };

/**
 * Minimal SVG line chart with optional min–max bands. Draws the values it is given (computed by
 * the API); only maps them to pixels. TODO: move to Plotly (planned) when charts need zoom.
 */
export function LineChart({
  x,
  series = [],
  bands = [],
  unit,
  formatX,
  formatY,
  height = 180,
  className,
}: LineChartProps) {
  const id = useId();
  const all = [
    ...series.flatMap((s) => s.values.filter((v): v is number => v !== null)),
    ...bands.flatMap((b) => [...b.low, ...b.high]),
  ];
  if (x.length < 2 || all.length === 0) return null;
  let yMin = Math.min(...all);
  let yMax = Math.max(...all);
  if (yMax - yMin < 1e-9) {
    yMin -= 1;
    yMax += 1;
  }
  const margin = (yMax - yMin) * 0.05;
  yMin -= margin;
  yMax += margin;
  const x0 = x[0] ?? 0;
  const x1 = x[x.length - 1] ?? 1;
  const px = (v: number) => PAD.left + ((v - x0) / (x1 - x0)) * (WIDTH - PAD.left - PAD.right);
  const py = (v: number) =>
    PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (height - PAD.top - PAD.bottom);

  const path = (values: (number | null)[]) => {
    let d = "";
    let pen = false;
    values.forEach((v, i) => {
      if (v === null) {
        pen = false;
        return;
      }
      d += `${pen ? "L" : "M"}${px(x[i] ?? x0).toFixed(1)},${py(v).toFixed(1)}`;
      pen = true;
    });
    return d;
  };
  const band = (b: ChartBand) => {
    const top = b.high.map(
      (v, i) => `${i === 0 ? "M" : "L"}${px(x[i] ?? x0).toFixed(1)},${py(v).toFixed(1)}`,
    );
    const bottom = b.low
      .map((v, i) => `L${px(x[i] ?? x0).toFixed(1)},${py(v).toFixed(1)}`)
      .reverse();
    return `${top.join("")}${bottom.join("")}Z`;
  };
  const ticks = [yMin + margin, (yMin + yMax) / 2, yMax - margin];
  const xTicks = [x0, x0 + (x1 - x0) / 2, x1];

  return (
    <figure className={cn("flex flex-col gap-2", className)}>
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        className="w-full"
        role="img"
        aria-labelledby={`${id}-legend`}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={py(t)}
              y2={py(t)}
              stroke="var(--border)"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 6}
              y={py(t) + 3}
              textAnchor="end"
              className="fill-subtle-foreground font-mono text-[10px]"
            >
              {formatY(t)}
            </text>
          </g>
        ))}
        {xTicks.map((t, i) => (
          <text
            key={t}
            x={px(t)}
            y={height - 6}
            textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
            className="fill-subtle-foreground font-mono text-[10px]"
          >
            {formatX(t)}
          </text>
        ))}
        {bands.map((b) => (
          <path key={b.label} d={band(b)} fill={b.color} fillOpacity={0.22} stroke="none" />
        ))}
        {series.map((s) => (
          <path key={s.label} d={path(s.values)} fill="none" stroke={s.color} strokeWidth={1.5} />
        ))}
      </svg>
      <figcaption
        id={`${id}-legend`}
        className="flex flex-wrap gap-4 text-[11px] text-muted-foreground"
      >
        {bands.map((b) => (
          <span key={b.label} className="flex items-center gap-1.5">
            <span className="h-2 w-3 rounded-sm opacity-40" style={{ background: b.color }} />
            {b.label}
          </span>
        ))}
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className="h-0.5 w-3" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
        <span className="ml-auto font-mono">{unit}</span>
      </figcaption>
    </figure>
  );
}
