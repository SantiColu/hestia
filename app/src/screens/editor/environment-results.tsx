import { useMemo, useState } from "react";
import { Satellite, Sun } from "lucide-react";
import type {
  EnvironmentCondition,
  EnvironmentSummary,
  FaceFluxes,
  RangeEntry,
} from "@/api/client";
import { DenseTable, type DenseColumn } from "@/components/data/dense-table";
import {
  ChartLegend,
  LineChart,
  type ChartBand,
  type ChartSeries,
} from "@/components/data/line-chart";
import { Metric } from "@/components/data/readouts";
import { CompactSelect } from "@/components/forms/compact-select";
import { Segmented } from "@/components/forms/segmented";
import { SectionLabel } from "@/components/navigation/section-label";
import { cn } from "@/lib/utils";
import { column } from "./layout";
import { date, deg, fmt, km, minutes } from "./format";
import { ResultState, type ResultStateProps } from "./result-state";

/**
 * «Resultados» of an environment cell (docs/etapas/environment.md, «Vista de la celda»):
 * metrics, β and eclipse along the mission, ranges, conditions and incident fluxes per face.
 * Everything is computed by the API; this only formats it (SI → display units).
 */
export function EnvironmentResults({ state }: { state: ResultStateProps }) {
  const environment = state.result?.environment ?? null;
  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className={cn(column, "gap-7")}>
        <ResultState {...state} />
        {environment && <Summary environment={environment} />}
      </div>
    </div>
  );
}

function Summary({ environment }: { environment: EnvironmentSummary }) {
  const { orbit, mission_series: series } = environment;
  const ranges = Object.fromEntries(environment.ranges.map((r) => [r.quantity, r]));
  const beta = ranges.beta;
  const irradiance = ranges.irradiance;
  const longest = Math.max(...series.eclipse_duration_max);
  const longestFraction = Math.max(...series.eclipse_fraction_max);
  const endOfLife = environment.conditions.find(
    (c) => c.origin === "extreme" && c.altitude === orbit.eol_altitude,
  );

  return (
    <>
      <section className="grid grid-cols-4 gap-6">
        {beta && (
          <Metric
            label="Ángulo β"
            value={`${deg(beta.min)}…${deg(beta.max)}`}
            unit="°"
            detail={orbit.raan_swept ? "envolvente · nodo barrido" : "envolvente"}
          />
        )}
        <Metric
          label="Eclipse máximo"
          value={minutes(longest)}
          unit="min"
          detail={`${fmt(longestFraction * 100, 0)} % de la órbita`}
        />
        {irradiance && (
          <Metric
            label="Irradiancia solar"
            value={`${fmt(irradiance.min, 0)}…${fmt(irradiance.max, 0)}`}
            unit="W/m²"
            detail="afelio · perihelio"
          />
        )}
        <Metric
          label="Período"
          value={minutes(orbit.period)}
          unit="min"
          detail={endOfLife ? `${minutes(endOfLife.period)} al fin de vida` : undefined}
        />
      </section>

      <MissionChart series={series} />

      <FluxTable environment={environment} />

      <section className="flex flex-col gap-3.5">
        <SectionLabel>Rangos</SectionLabel>
        <DenseTable columns={RANGE_COLUMNS} rows={environment.ranges} rowKey={(r) => r.quantity} />
      </section>

      <section className="flex flex-col gap-3.5">
        <SectionLabel>Condiciones</SectionLabel>
        <DenseTable
          columns={CONDITION_COLUMNS}
          rows={environment.conditions}
          rowKey={(c) => c.id}
        />
        {environment.conditions.some((c) => c.note) && (
          <p className="text-2xs text-subtle-foreground">
            <span className="text-warn">*</span> La misión nunca tiene ese β: pasá el cursor por el
            nombre para ver cómo se dibuja su órbita.
          </p>
        )}
      </section>
    </>
  );
}

// ---------------------------------------------------------------- β and eclipse

const toDeg = (values: number[]) => values.map((v) => (v * 180) / Math.PI);
const yearMonth = (t: number) => new Date(t).toISOString().slice(0, 7);

/** β (nominal and envelope) over the eclipse duration along the mission, on one time axis
 * (`Chart β y eclipse` in the design). */
function MissionChart({ series }: { series: EnvironmentSummary["mission_series"] }) {
  const x = useMemo(() => series.dates.map((d) => Date.parse(d)), [series.dates]);
  const envelope: ChartBand = {
    label: "envolvente",
    color: "var(--primary)",
    low: toDeg(series.beta_min),
    high: toDeg(series.beta_max),
  };
  const nominal: ChartSeries[] = series.beta_nominal.some((b) => b !== null)
    ? [
        {
          label: "β nominal",
          color: "var(--primary)",
          values: series.beta_nominal.map((b) => (b === null ? null : (b * 180) / Math.PI)),
        },
      ]
    : [];
  const eclipseMax = series.eclipse_duration_max.map((s) => s / 60);
  const eclipse: ChartBand = {
    label: "eclipse (mín. a máx.)",
    color: "var(--idle)",
    low: series.eclipse_duration_min.map((s) => s / 60),
    high: eclipseMax,
  };
  const longest: ChartSeries = { label: "eclipse máx.", color: "var(--idle)", values: eclipseMax };
  return (
    <section className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-3">
      <header className="flex items-center gap-4">
        <h2 className="text-xs font-medium">β y eclipse a lo largo de la misión</h2>
        <ChartLegend
          series={[...nominal, longest]}
          bands={[envelope, eclipse]}
          className="ml-auto"
        />
      </header>
      <LineChart
        x={x}
        unit="°"
        height={130}
        legend={false}
        xAxis={false}
        formatX={yearMonth}
        formatY={(v) => `${fmt(v, 0)}°`}
        bands={[envelope]}
        series={nominal}
      />
      <LineChart
        x={x}
        unit="min"
        height={80}
        legend={false}
        formatX={yearMonth}
        formatY={(v) => `${fmt(v, 1)} min`}
        bands={[eclipse]}
        series={[longest]}
      />
    </section>
  );
}

// ---------------------------------------------------------------- ranges

const RANGE_LABELS: Record<RangeEntry["quantity"], { label: string; unit: string }> = {
  irradiance: { label: "Irradiancia solar", unit: "W/m²" },
  beta: { label: "Ángulo β", unit: "°" },
  altitude: { label: "Altitud", unit: "km" },
  albedo: { label: "Albedo", unit: "" },
  olr: { label: "IR terrestre", unit: "W/m²" },
};

function rangeValue(entry: RangeEntry, value: number): string {
  switch (entry.quantity) {
    case "beta":
      return deg(value);
    case "altitude":
      return km(value);
    case "albedo":
      return fmt(value, 2);
    default:
      return fmt(value, 1);
  }
}

function why(note: string, at: string | null | undefined): string {
  return at ? `${note} · ${date(at)}` : note;
}

const RANGE_COLUMNS: DenseColumn<RangeEntry>[] = [
  { key: "quantity", header: "Magnitud", cell: (r) => RANGE_LABELS[r.quantity].label },
  { key: "min", header: "Mínimo", numeric: true, cell: (r) => rangeValue(r, r.min) },
  { key: "max", header: "Máximo", numeric: true, cell: (r) => rangeValue(r, r.max) },
  { key: "unit", header: "Unidad", cell: (r) => RANGE_LABELS[r.quantity].unit },
  {
    key: "notes",
    header: "Motivo",
    className: "max-w-65 truncate",
    cell: (r) => (
      <span title={`${why(r.min_note, r.min_at)} / ${why(r.max_note, r.max_at)}`}>
        {r.min_note === r.max_note && !r.min_at
          ? r.min_note
          : `${why(r.min_note, r.min_at)} / ${why(r.max_note, r.max_at)}`}
      </span>
    ),
  },
];

// ---------------------------------------------------------------- conditions

const CONDITION_COLUMNS: DenseColumn<EnvironmentCondition>[] = [
  {
    key: "name",
    header: "Condición",
    cell: (c) => (
      <span title={c.note ?? undefined}>
        {c.name}
        {c.note && <span className="text-warn"> *</span>}
      </span>
    ),
  },
  { key: "beta", header: "β (°)", numeric: true, cell: (c) => deg(c.beta) },
  { key: "altitude", header: "Altitud (km)", numeric: true, cell: (c) => km(c.altitude) },
  { key: "period", header: "Período (min)", numeric: true, cell: (c) => minutes(c.period) },
  {
    key: "fraction",
    header: "Eclipse (%)",
    numeric: true,
    cell: (c) => fmt(c.eclipse_fraction * 100, 1),
  },
  {
    key: "duration",
    header: "Eclipse (min)",
    numeric: true,
    cell: (c) => minutes(c.eclipse_duration),
  },
  { key: "date", header: "Fecha", numeric: true, cell: (c) => date(c.date) },
];

// ---------------------------------------------------------------- fluxes

const pair = (low: number, high: number) =>
  Math.abs(high - low) < 0.05 ? fmt(high, 0) : `${fmt(low, 0)} – ${fmt(high, 0)}`;

type FluxStat = "average" | "peak";

const FLUX_STATS: { value: FluxStat; label: string }[] = [
  { value: "average", label: "Promedio" },
  { value: "peak", label: "Pico" },
];

const FLUX_PARTS = [
  { key: "solar", header: "Solar" },
  { key: "albedo", header: "Albedo" },
  { key: "ir", header: "IR terrestre" },
  { key: "total", header: "Total" },
] as const;

function fluxColumns(stat: FluxStat): DenseColumn<FaceFluxes>[] {
  return [
    { key: "face", header: "Cara", cell: (f) => <span className="font-mono">{f.face}</span> },
    ...FLUX_PARTS.map(({ key, header }): DenseColumn<FaceFluxes> => ({
      key,
      header,
      numeric: true,
      cell: (f) =>
        stat === "average"
          ? pair(f[key].average_min, f[key].average_max)
          : pair(f[key].peak_min, f[key].peak_max),
    })),
  ];
}

function FluxTable({ environment }: { environment: EnvironmentSummary }) {
  const [conditionId, setConditionId] = useState(environment.conditions[0]?.id ?? "");
  const [modeId, setModeId] = useState(environment.attitude_modes[0]?.id ?? "");
  const [stat, setStat] = useState<FluxStat>("average");
  const condition = environment.conditions.some((c) => c.id === conditionId)
    ? conditionId
    : (environment.conditions[0]?.id ?? "");
  const mode = environment.attitude_modes.some((m) => m.id === modeId)
    ? modeId
    : (environment.attitude_modes[0]?.id ?? "");
  const rows = environment.fluxes.filter((f) => f.condition_id === condition && f.mode_id === mode);
  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex items-center gap-2">
        <SectionLabel className="mr-auto whitespace-nowrap">
          Flujos incidentes por cara · W/m²
        </SectionLabel>
        <CompactSelect
          label="Condición"
          icon={Sun}
          options={environment.conditions.map((c) => ({ value: c.id, label: c.name }))}
          value={condition}
          onValueChange={setConditionId}
          className="max-w-52"
        />
        <CompactSelect
          label="Modo de actitud"
          icon={Satellite}
          options={environment.attitude_modes.map((m) => ({ value: m.id, label: m.name }))}
          value={mode}
          onValueChange={setModeId}
          className="max-w-40"
        />
        <Segmented
          aria-label="Estadística"
          options={FLUX_STATS}
          value={stat}
          onValueChange={setStat}
        />
      </div>
      <DenseTable columns={fluxColumns(stat)} rows={rows} rowKey={(f) => f.face} />
      <p className="text-2xs text-subtle-foreground">
        Flujos incidentes (no absorbidos), {stat === "average" ? "promedio orbital" : "pico"} con
        los valores de diseño mínimos y máximos: solar con la irradiancia mínima y máxima de la
        misión, albedo con irradiancia × albedo, IR con la IR terrestre mínima y máxima.
      </p>
    </section>
  );
}
