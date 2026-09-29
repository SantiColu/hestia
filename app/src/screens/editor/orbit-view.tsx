import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { api, unwrap, type CellResult, type OrbitProfile } from "@/api/client";
import { KeyValue } from "@/components/data/readouts";
import { Segmented } from "@/components/forms/segmented";
import { SelectField } from "@/components/forms/select-field";
import { Button } from "@/components/ui/button";
import { useProject } from "@/project/store";
import { cn } from "@/lib/utils";
import { column } from "./layout";
import { deg, fmt, minutes } from "./format";
import { FACES, instantAt, maxTotalFlux, profilePeriod, type FaceName } from "./orbit-profile";
import { OrbitScene, type CameraMode } from "./orbit-scene";
import { ResultState } from "./result-state";

/** Seconds of animation for one orbit at speed ×1. */
const ORBIT_SECONDS = 30;

const SPEEDS = [
  { value: "1", label: "×1" },
  { value: "4", label: "×4" },
  { value: "16", label: "×16" },
];

/**
 * «Órbita 3D» of an environment cell: one orbit of a condition in an attitude mode, as the API
 * computed it (`get_orbit_profile`). The view only interpolates between samples to animate.
 */
export function OrbitView({
  cellId,
  result,
  updating,
  onUpdate,
}: {
  cellId: string;
  result: CellResult | null;
  updating: boolean;
  onUpdate: () => void;
}) {
  const { fail } = useProject();
  const environment = result?.environment ?? null;
  const [conditionId, setConditionId] = useState("");
  const [modeId, setModeId] = useState("");
  const condition =
    environment?.conditions.find((c) => c.id === conditionId) ?? environment?.conditions[0];
  const mode =
    environment?.attitude_modes.find((m) => m.id === modeId) ?? environment?.attitude_modes[0];
  const [profile, setProfile] = useState<OrbitProfile | null>(null);
  const [camera, setCamera] = useState<CameraMode>("global");
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState("1");
  const [time, setTime] = useState(0);
  const [face, setFace] = useState<FaceName>("+X");
  const resultId = result?.result_id ?? null;

  useEffect(() => {
    if (!resultId || !condition || !mode) return;
    let live = true;
    unwrap(
      api.GET("/project/cells/{cell_id}/result/orbit-profile", {
        params: {
          path: { cell_id: cellId },
          query: { condition_id: condition.id, mode_id: mode.id },
        },
      }),
    )
      .then((next) => live && setProfile(next))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [cellId, resultId, condition, mode, fail]);

  const period = profile ? profilePeriod(profile) : 0;
  const maxFlux = useMemo(() => (profile ? maxTotalFlux(profile) : 0), [profile]);

  // Animation: advance the instant while playing (the camera keeps it when switching views).
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (!playing || period <= 0) return;
    let frame = 0;
    const tick = (now: number) => {
      const previous = last.current ?? now;
      last.current = now;
      const rate = (period / ORBIT_SECONDS) * Number(speed);
      setTime((t) => (t + ((now - previous) / 1000) * rate) % period);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      last.current = null;
    };
  }, [playing, period, speed]);

  if (!environment || !condition || !mode) {
    return (
      <div className="h-full overflow-y-auto px-6 py-6">
        <div className={cn(column, "gap-7")}>
          <ResultState result={result} updating={updating} onUpdate={onUpdate} />
        </div>
      </div>
    );
  }

  const instant = profile ? instantAt(profile, time) : null;
  const flux = instant?.faces[face];

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-border px-6 py-3">
        <div className={cn(column, "gap-3")}>
          {result?.status !== "up_to_date" && (
            <ResultState result={result} updating={updating} onUpdate={onUpdate} />
          )}
          {condition.note && <p className="text-[11px] text-warn">{condition.note}</p>}
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="Condición"
              options={environment.conditions.map((c) => ({ value: c.id, label: c.name }))}
              value={condition.id}
              onValueChange={setConditionId}
            />
            <SelectField
              label="Modo de actitud"
              options={environment.attitude_modes.map((m) => ({ value: m.id, label: m.name }))}
              value={mode.id}
              onValueChange={setModeId}
            />
          </div>
        </div>
      </div>
      <div className="relative min-h-0 flex-1">
        {profile && instant ? (
          <OrbitScene
            profile={profile}
            instant={instant}
            mode={camera}
            maxFlux={maxFlux}
            onOpenLocal={() => setCamera("local")}
          />
        ) : (
          <p className="p-6 text-xs text-subtle-foreground">Cargando…</p>
        )}
        {instant && flux && (
          <div className="absolute top-3 right-3 w-72 rounded-lg border border-border bg-surface/90 px-3 py-2">
            <KeyValue label="Tiempo" value={`${minutes(instant.time)} / ${minutes(period)} min`} />
            <KeyValue label="β" value={`${deg(condition.beta)}°`} />
            <KeyValue
              label="Sol"
              value={
                instant.sunlit >= 0.999
                  ? "Sol"
                  : instant.sunlit <= 0.001
                    ? "Eclipse"
                    : `Penumbra (${fmt(instant.sunlit * 100, 0)} %)`
              }
            />
            <div className="flex items-center justify-between gap-2 py-1.5 text-xs text-muted-foreground">
              <span>Cara</span>
              <Segmented
                aria-label="Cara"
                options={FACES.map((f) => ({ value: f, label: f }))}
                value={face}
                onValueChange={setFace}
              />
            </div>
            <KeyValue label="Solar" value={`${fmt(flux.solar)} W/m²`} />
            <KeyValue label="Albedo" value={`${fmt(flux.albedo)} W/m²`} />
            <KeyValue label="IR" value={`${fmt(flux.ir)} W/m²`} />
            <KeyValue label="Total" value={`${fmt(flux.total)} W/m²`} className="border-b-0" />
            <div className="mt-2 flex flex-col gap-1">
              <div
                className="h-1.5 rounded-sm"
                style={{ background: "linear-gradient(to right, var(--cold), var(--hot))" }}
                aria-hidden
              />
              <div className="flex justify-between font-mono text-[10px] text-subtle-foreground">
                <span>0</span>
                <span>{fmt(maxFlux, 0)} W/m² · flujo total máx.</span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="shrink-0 border-t border-border bg-surface px-6 py-2">
        <div className="flex items-center gap-3">
          <Segmented
            aria-label="Vista"
            options={[
              { value: "global", label: "Global" },
              { value: "local", label: "Local" },
            ]}
            value={camera}
            onValueChange={setCamera}
          />
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={playing ? "Pausa" : "Reproducir"}
            onClick={() => setPlaying((p) => !p)}
          >
            {playing ? <Pause /> : <Play />}
          </Button>
          <input
            type="range"
            aria-label="Instante de la órbita"
            min={0}
            max={period || 1}
            step={period / 1000 || 1}
            value={time}
            onChange={(e) => {
              setPlaying(false);
              setTime(Number(e.target.value));
            }}
            className="min-w-0 flex-1 accent-primary"
          />
          <Segmented
            aria-label="Velocidad"
            options={SPEEDS}
            value={speed}
            onValueChange={setSpeed}
          />
        </div>
      </div>
    </div>
  );
}
