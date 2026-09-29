import { useMemo, useState } from "react";
import type {
  CellResult,
  EnvironmentCondition,
  EnvironmentSummary,
  FaceFluxes,
  ProjectView,
  RangeEntry,
} from "@/api/client";
import { DenseTable, type DenseColumn } from "@/components/data/dense-table";
import { LineChart } from "@/components/data/line-chart";
import { Metric } from "@/components/data/readouts";
import { SelectField } from "@/components/forms/select-field";
import { SectionLabel } from "@/components/navigation/section-label";
import { cn } from "@/lib/utils";
import { column } from "./layout";
import { date, deg, fmt, km, minutes } from "./format";
import { ResultState } from "./result-state";

/**
 * «Resultados» of an environment cell (docs/etapas/environment.md, «Vista de la celda»):
 * metrics, β and eclipse along the mission, ranges, conditions and incident fluxes per face.
 * Everything is computed by the API; this only formats it (SI → display units).
 */
export function EnvironmentResults({
  result,
  updating,
  onUpdate,
}: {
  result: CellResult | null;
  view: ProjectView;
  updating: boolean;
  onUpdate: () => void;
}) {
  const environment = result?.environment ?? null;
  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className={cn(column, "gap-7")}>
        <ResultState result={result} updating={updating} onUpdate={onUpdate} />
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
  const x = useMemo(() => series.dates.map((d) => Date.parse(d)), [series.dates]);
  const toDeg = (values: number[]) => values.map((v) => (v * 180) / Math.PI);

  return (
    <>
      <section className="grid grid-cols-3 gap-x-6 gap-y-5">
        {beta && <Metric label="Ángulo β" value={`${deg(beta.min)} … ${deg(beta.max)}`} unit="°" />}
        <Metric label="Eclipse más largo" value={minutes(longest)} unit="min" />
        {irradiance && (
          <Metric
            label="Irradiancia solar"
            value={`${fmt(irradiance.min, 0)} … ${fmt(irradiance.max, 0)}`}
            unit="W/m²"
          />
        )}
        <Metric label="Período" value={minutes(orbit.period)} unit="min" />
        <Metric
          label="Inclinación"
          value={deg(orbit.inclination, 2)}
          unit="°"
          detail={orbit.raan_swept ? "Nodo barrido completo" : undefined}
        />
        <Metric
          label="Altitud"
          value={km(orbit.altitude)}
          unit="km"
          detail={
            orbit.eol_altitude !== null ? `Fin de vida: ${km(orbit.eol_altitude)} km` : undefined
          }
        />
      </section>

      <section className="flex flex-col gap-3.5">
        <SectionLabel>Ángulo β a lo largo de la misión</SectionLabel>
        <LineChart
          x={x}
          unit="°"
          formatX={(t) => new Date(t).toISOString().slice(0, 7)}
          formatY={(v) => fmt(v, 0)}
          bands={[
            {
              label: "Envolvente",
              color: "var(--primary)",
              low: toDeg(series.beta_min),
              high: toDeg(series.beta_max),
            },
          ]}
          series={
            series.beta_nominal.some((b) => b !== null)
              ? [
                  {
                    label: "Nominal",
                    color: "var(--primary)",
                    values: series.beta_nominal.map((b) =>
                      b === null ? null : (b * 180) / Math.PI,
                    ),
                  },
                ]
              : []
          }
        />
      </section>

      <section className="flex flex-col gap-3.5">
        <SectionLabel>Eclipse por órbita</SectionLabel>
        <LineChart
          x={x}
          unit="min"
          height={140}
          formatX={(t) => new Date(t).toISOString().slice(0, 7)}
          formatY={(v) => fmt(v, 1)}
          bands={[
            {
              label: "Duración (mínima a máxima)",
              color: "var(--idle)",
              low: series.eclipse_duration_min.map((s) => s / 60),
              high: series.eclipse_duration_max.map((s) => s / 60),
            },
          ]}
          series={[
            {
              label: "Máxima",
              color: "var(--idle)",
              values: series.eclipse_duration_max.map((s) => s / 60),
            },
          ]}
        />
      </section>

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
      </section>

      {environment.conditions.some((c) => c.note) && (
        <p className="-mt-4 text-[11px] text-subtle-foreground">
          <span className="text-warn">*</span> La misión nunca tiene ese β: pasá el cursor por el
          nombre para ver cómo se dibuja su órbita.
        </p>
      )}

      <FluxTable environment={environment} />
    </>
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
    className: "max-w-[260px] truncate",
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
  Math.abs(high - low) < 0.05 ? fmt(high, 1) : `${fmt(low, 1)} – ${fmt(high, 1)}`;

const FLUX_COLUMNS: DenseColumn<FaceFluxes>[] = [
  { key: "face", header: "Cara", cell: (f) => <span className="font-mono">{f.face}</span> },
  {
    key: "solar",
    header: "Solar prom.",
    numeric: true,
    cell: (f) => pair(f.solar.average_min, f.solar.average_max),
  },
  {
    key: "albedo",
    header: "Albedo prom.",
    numeric: true,
    cell: (f) => pair(f.albedo.average_min, f.albedo.average_max),
  },
  {
    key: "ir",
    header: "IR prom.",
    numeric: true,
    cell: (f) => pair(f.ir.average_min, f.ir.average_max),
  },
  {
    key: "total",
    header: "Total prom.",
    numeric: true,
    cell: (f) => pair(f.total.average_min, f.total.average_max),
  },
  {
    key: "peak",
    header: "Total pico",
    numeric: true,
    cell: (f) => pair(f.total.peak_min, f.total.peak_max),
  },
];

function FluxTable({ environment }: { environment: EnvironmentSummary }) {
  const [conditionId, setConditionId] = useState(environment.conditions[0]?.id ?? "");
  const [modeId, setModeId] = useState(environment.attitude_modes[0]?.id ?? "");
  const condition = environment.conditions.some((c) => c.id === conditionId)
    ? conditionId
    : (environment.conditions[0]?.id ?? "");
  const mode = environment.attitude_modes.some((m) => m.id === modeId)
    ? modeId
    : (environment.attitude_modes[0]?.id ?? "");
  const rows = environment.fluxes.filter((f) => f.condition_id === condition && f.mode_id === mode);
  return (
    <section className="flex flex-col gap-3.5">
      <SectionLabel>Flujos incidentes por cara (W/m²)</SectionLabel>
      <div className="grid grid-cols-2 gap-4">
        <SelectField
          label="Condición"
          options={environment.conditions.map((c) => ({ value: c.id, label: c.name }))}
          value={condition}
          onValueChange={setConditionId}
        />
        <SelectField
          label="Modo de actitud"
          options={environment.attitude_modes.map((m) => ({ value: m.id, label: m.name }))}
          value={mode}
          onValueChange={setModeId}
        />
      </div>
      <DenseTable columns={FLUX_COLUMNS} rows={rows} rowKey={(f) => f.face} />
      <p className="text-[11px] text-subtle-foreground">
        Flujos incidentes (no absorbidos), con los valores de diseño mínimos y máximos: solar con la
        irradiancia mínima y máxima de la misión, albedo con irradiancia × albedo, IR con la IR
        terrestre mínima y máxima.
      </p>
    </section>
  );
}
