import { useEffect, useMemo, useState } from "react";
import { CalendarDays, Satellite } from "lucide-react";
import { api, unwrap, type EnvironmentParameters, type OrbitPreviewResult } from "@/api/client";
import { KeyValue } from "@/components/data/readouts";
import { Notice } from "@/components/feedback/notice";
import { Tag } from "@/components/feedback/tag";
import { fieldBoxClass } from "@/components/forms/field-box";
import { Segmented } from "@/components/forms/segmented";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { JsonObject } from "@/lib/json";
import { isIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { DRAFT_DEBOUNCE_MS } from "@/project/editor";
import { useProject } from "@/project/store";
import { date as isoDate, deg, fmt, minutes } from "./format";
import { OrbitTimeline } from "./orbit-timeline";
import { useOrbitClock } from "./use-orbit-clock";
import { instantAt } from "./orbit-profile";
import { OrbitScene, type CameraMode } from "./orbit-scene";

const CAMERAS: { value: CameraMode; label: string }[] = [
  { value: "global", label: "Global" },
  { value: "local", label: "Local" },
];

/**
 * «Vista previa» of the environment parameters (ADR 0023): the nominal orbit of the draft (or the
 * applied parameters) on a date, as the API computes it (`preview_orbit`), without fluxes. It
 * stores nothing; the view only interpolates between samples to animate.
 */
export function OrbitPreview({
  cellId,
  parameters,
  isDraft,
  revision,
}: {
  cellId: string;
  parameters: JsonObject;
  isDraft: boolean;
  /** Project revision: the mission (launch date) may change upstream. */
  revision: number;
}) {
  const { fail } = useProject();
  const [on, setOn] = useState<string | null>(null);
  const [modeId, setModeId] = useState<string | null>(null);
  const [camera, setCamera] = useState<CameraMode>("global");
  const [answer, setAnswer] = useState<OrbitPreviewResult | null>(null);
  /** The last orbit drawn, kept (dimmed) while the draft has problems. */
  const [shown, setShown] = useState<OrbitPreviewResult["preview"]>(null);

  useEffect(() => {
    let live = true;
    const timer = window.setTimeout(() => {
      unwrap(
        api.POST("/project/cells/{cell_id}/orbit-preview", {
          params: { path: { cell_id: cellId } },
          body: {
            parameters: parameters as unknown as EnvironmentParameters,
            date: on,
            mode_id: modeId,
          },
        }),
      )
        .then((next) => {
          if (!live) return;
          setAnswer(next);
          if (next.preview) setShown(next.preview);
        })
        .catch(fail);
    }, DRAFT_DEBOUNCE_MS);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [cellId, parameters, on, modeId, revision, fail]);

  const orbit = useOrbitClock(shown?.period ?? 0);
  const instant = useMemo(() => (shown ? instantAt(shown, orbit.time) : null), [shown, orbit.time]);
  const stale = answer !== null && answer.preview === null;
  const launch = shown !== null && !on;

  return (
    <aside className="flex w-110 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border bg-surface p-4">
      <header className="flex items-center gap-2">
        <h2 className="text-ui font-medium">Vista previa</h2>
        {isDraft && <Tag>borrador</Tag>}
        <span className="flex-1" />
        <span className="font-mono text-2xs text-subtle-foreground">sin guardar · sin flujos</span>
      </header>
      <div className="grid grid-cols-2 gap-2">
        <Select
          items={(shown?.attitude_modes ?? []).map((m) => ({ value: m.id, label: m.name }))}
          value={shown?.mode_id ?? null}
          onValueChange={(next) => typeof next === "string" && setModeId(next)}
          disabled={!shown?.attitude_modes.length}
        >
          <SelectTrigger
            size="sm"
            aria-label="Modo de actitud"
            className="w-full bg-background text-ui"
          >
            <Satellite aria-hidden className="text-subtle-foreground" />
            <SelectValue placeholder="Sin modos de actitud" />
          </SelectTrigger>
          <SelectContent>
            {shown?.attitude_modes.map((m) => (
              <SelectItem key={m.id} value={m.id} className="text-ui">
                {m.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <OrbitDate
          value={on ?? (shown ? isoDate(shown.date) : "")}
          isLaunch={!!launch}
          onChange={setOn}
        />
      </div>
      {answer && answer.problems.length > 0 && (
        <Notice tone="warning" title="No se puede dibujar la órbita del borrador">
          {answer.problems.map((p) => p.message).join(" ")}
        </Notice>
      )}
      <div
        className={cn(
          "relative h-56 shrink-0 overflow-hidden rounded-lg border border-border bg-background",
          stale && "opacity-50",
        )}
      >
        {shown && instant ? (
          <OrbitScene
            track={shown}
            instant={instant}
            mode={camera}
            onOpenLocal={() => setCamera("local")}
          />
        ) : (
          <p className="p-4 text-xs text-subtle-foreground">
            {answer ? "Sin órbita para dibujar." : "Calculando…"}
          </p>
        )}
        <Segmented
          aria-label="Vista"
          options={CAMERAS}
          value={camera}
          onValueChange={setCamera}
          className="absolute top-2 right-2"
        />
      </div>
      {shown && (
        <>
          <OrbitTimeline clock={orbit} period={shown.period} />
          <div className="grid grid-cols-2 gap-x-4">
            <div>
              <KeyValue label="Ángulo β" value={`${deg(shown.beta)}°`} />
              <KeyValue
                label="Inclinación"
                value={`${deg(shown.inclination)}°${shown.orbit_type === "sso" ? " calc." : ""}`}
              />
            </div>
            <div>
              <KeyValue label="Período" value={`${minutes(shown.period)} min`} />
              <KeyValue
                label="Eclipse"
                value={`${fmt(shown.eclipse_fraction * 100)} % · ${minutes(shown.eclipse_duration)} min`}
              />
            </div>
          </div>
          <p className="text-xs leading-relaxed text-subtle-foreground">
            {shown.node_assumed
              ? "En LEO/MEO el plano orbital no está fijo: la vista previa lo dibuja con RAAN 0° en la fecha elegida. La envolvente de β en toda la misión y los flujos salen de Actualizar."
              : "Órbita nominal en la fecha elegida, calculada con el mismo proveedor que Actualizar. No guarda nada ni cambia el estado de la celda; los flujos salen de Actualizar."}
          </p>
        </>
      )}
    </aside>
  );
}

/** The date of the orbit, typed as aaaa-mm-dd; only complete dates are sent. Empty: launch. */
function OrbitDate({
  value,
  isLaunch,
  onChange,
}: {
  value: string;
  isLaunch: boolean;
  onChange: (value: string | null) => void;
}) {
  const [text, setText] = useState(value);
  const [shown, setShown] = useState(value);
  if (value !== shown) {
    setShown(value);
    setText(value);
  }
  const invalid = text !== "" && !isIsoDate(text);
  return (
    <label className={cn(fieldBoxClass({ error: invalid }), "h-7")}>
      <CalendarDays aria-hidden className="size-3.5 shrink-0 text-subtle-foreground" />
      <input
        aria-label="Fecha de la órbita"
        aria-invalid={invalid || undefined}
        placeholder="aaaa-mm-dd"
        value={text}
        onChange={(e) => {
          const next = e.target.value.trim();
          setText(e.target.value);
          if (next === "") onChange(null);
          else if (isIsoDate(next)) onChange(next);
        }}
        className="min-w-0 flex-1 bg-transparent font-mono text-xs tabular-nums outline-none"
      />
      {isLaunch && <span className="shrink-0 text-2xs text-subtle-foreground">lanzamiento</span>}
    </label>
  );
}
