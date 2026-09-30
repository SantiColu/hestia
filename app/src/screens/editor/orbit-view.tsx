import { useEffect, useMemo, useState } from "react";
import { Satellite, Sun } from "lucide-react";
import { api, unwrap, type OrbitProfile } from "@/api/client";
import { CompactSelect } from "@/components/forms/compact-select";
import { Segmented } from "@/components/forms/segmented";
import { useProject } from "@/project/store";
import { cn } from "@/lib/utils";
import { column } from "./layout";
import { deg, fmt } from "./format";
import { FACES, instantAt, maxTotalFlux, type Instant, type Vec3 } from "./orbit-profile";
import { OrbitScene, type CameraMode } from "./orbit-scene";
import { OrbitTimeline } from "./orbit-timeline";
import { ResultState, type ResultStateProps } from "./result-state";
import { useOrbitClock } from "./use-orbit-clock";

const CAMERAS: { value: CameraMode; label: string }[] = [
  { value: "global", label: "Global" },
  { value: "local", label: "Local" },
];

const SPEEDS = [
  { value: "0.5", label: "×0.5" },
  { value: "1", label: "×1" },
  { value: "4", label: "×4" },
  { value: "16", label: "×16" },
];

/** What each camera shows and how to move it (`Label` and `Hint` in the design). */
const CAMERA_TEXT: Record<CameraMode, { title: string; subtitle: string; hint: string }> = {
  global: {
    title: "Global",
    subtitle: "Marco inercial · Tierra girando",
    hint: "Arrastrar para rotar · rueda para acercar · doble clic en el satélite: vista local",
  },
  local: {
    title: "Local",
    subtitle: "Sigue al satélite · envolvente fuera de escala · W/m²",
    hint: "La cámara sigue al satélite",
  },
};

/**
 * «Órbita 3D» of an environment cell: one orbit of a condition in an attitude mode, as the API
 * computed it (`get_orbit_profile`). The view only interpolates between samples to animate.
 */
export function OrbitView({
  cellId,
  state,
  envelope,
}: {
  cellId: string;
  state: ResultStateProps;
  /** Sizes of the mission's envelope, to draw the satellite with its shape. */
  envelope: Vec3 | null;
}) {
  const { fail } = useProject();
  const { result } = state;
  const environment = result?.environment ?? null;
  const [conditionId, setConditionId] = useState("");
  const [modeId, setModeId] = useState("");
  const condition =
    environment?.conditions.find((c) => c.id === conditionId) ?? environment?.conditions[0];
  const mode =
    environment?.attitude_modes.find((m) => m.id === modeId) ?? environment?.attitude_modes[0];
  const [profile, setProfile] = useState<OrbitProfile | null>(null);
  const [camera, setCamera] = useState<CameraMode>("global");
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

  const period = profile?.period ?? 0;
  const maxFlux = useMemo(() => (profile ? maxTotalFlux(profile) : 0), [profile]);
  const orbit = useOrbitClock(period);

  if (!environment || !condition || !mode) {
    return (
      <div className="h-full overflow-y-auto px-6 py-6">
        <div className={cn(column, "gap-7")}>
          <ResultState {...state} />
        </div>
      </div>
    );
  }

  const instant = profile ? instantAt(profile, orbit.time) : null;
  const text = CAMERA_TEXT[camera];

  return (
    <div className="flex h-full flex-col gap-3 px-4 py-3.5">
      {result?.status !== "up_to_date" && <ResultState {...state} />}
      <div className="flex shrink-0 items-center gap-2">
        <Segmented aria-label="Vista" options={CAMERAS} value={camera} onValueChange={setCamera} />
        <CompactSelect
          label="Condición"
          icon={Sun}
          options={environment.conditions.map((c) => ({ value: c.id, label: c.name }))}
          value={condition.id}
          onValueChange={setConditionId}
          className="max-w-64"
        />
        <CompactSelect
          label="Modo de actitud"
          icon={Satellite}
          options={environment.attitude_modes.map((m) => ({ value: m.id, label: m.name }))}
          value={mode.id}
          onValueChange={setModeId}
          className="max-w-48"
        />
        <span className="flex-1" />
        <span className="truncate text-xs text-subtle-foreground">{text.hint}</span>
      </div>
      {condition.note && <p className="text-2xs text-warn">{condition.note}</p>}
      <div className="relative min-h-0 flex-1 overflow-hidden rounded-lg border border-border bg-background">
        {profile && instant ? (
          <OrbitScene
            track={profile}
            instant={instant}
            mode={camera}
            maxFlux={maxFlux}
            envelope={envelope}
            onOpenLocal={() => setCamera("local")}
          />
        ) : (
          <p className="p-6 text-xs text-subtle-foreground">Cargando…</p>
        )}
        <div className="pointer-events-none absolute top-3 left-3.5 flex flex-col gap-0.5">
          <span className="font-mono text-2xs font-medium tracking-label text-subtle-foreground uppercase">
            {text.title}
          </span>
          <span className="text-2xs text-muted-foreground">{text.subtitle}</span>
        </div>
        {camera === "global" ? <OrbitLegend /> : <FluxScale max={maxFlux} />}
      </div>
      <OrbitTimeline clock={orbit} period={period}>
        <CompactSelect
          label="Velocidad"
          options={SPEEDS}
          value={String(orbit.speed)}
          onValueChange={(next) => orbit.setSpeed(Number(next))}
          className="w-18"
        />
        {instant && <InstantReadout beta={condition.beta} instant={instant} />}
      </OrbitTimeline>
    </div>
  );
}

/** «β 33.9° · en sol · +Y 1182 W/m²»: the face with the largest total incident flux now. */
function InstantReadout({ beta, instant }: { beta: number; instant: Instant }) {
  const { faces } = instant;
  const hottest = faces ? FACES.reduce((a, b) => (faces[b].total > faces[a].total ? b : a)) : null;
  const light =
    instant.sunlit >= 0.999
      ? "en sol"
      : instant.sunlit <= 0.001
        ? "en eclipse"
        : `penumbra ${fmt(instant.sunlit * 100, 0)} %`;
  return (
    <span className="flex shrink-0 items-center gap-2 font-mono text-xs tabular-nums">
      <span>β {deg(beta)}°</span>
      <span className="text-subtle-foreground">·</span>
      <span className={instant.sunlit > 0.5 ? "text-primary" : "text-muted-foreground"}>
        {light}
      </span>
      {faces && hottest && (
        <>
          <span className="text-subtle-foreground">·</span>
          <span className="text-hot">
            {hottest} {fmt(faces[hottest].total, 0)} W/m²
          </span>
        </>
      )}
    </span>
  );
}

function OrbitLegend() {
  return (
    <div className="pointer-events-none absolute bottom-3 left-3.5 flex items-center gap-3.5 text-2xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span aria-hidden className="h-0.5 w-3 bg-primary" />
        en sol
      </span>
      <span className="flex items-center gap-1.5">
        <span aria-hidden className="h-0.5 w-3 bg-idle" />
        eclipse
      </span>
      <span className="flex items-center gap-1.5">
        <span aria-hidden className="h-2 w-3 rounded-sm border border-border-strong bg-surface-2" />
        sombra
      </span>
    </div>
  );
}

/** Color scale of the faces in the local view: total incident flux, 0 to the profile's max. */
function FluxScale({ max }: { max: number }) {
  return (
    <div className="pointer-events-none absolute right-3 bottom-3 flex w-56 flex-col gap-1 rounded-lg bg-surface/90 px-2 py-1.5">
      <div
        aria-hidden
        className="h-1.5 rounded-sm"
        style={{ background: "linear-gradient(to right, var(--cold), var(--hot))" }}
      />
      <div className="flex justify-between font-mono text-3xs text-subtle-foreground">
        <span>0</span>
        <span>flujo incidente total</span>
        <span>{fmt(max, 0)} W/m²</span>
      </div>
    </div>
  );
}
