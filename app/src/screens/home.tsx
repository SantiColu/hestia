import type { CSSProperties } from "react";
import { File, FileX, FolderOpen, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SectionLabel } from "@/components/navigation/section-label";
import { API_URL, type RecentProject } from "@/api/client";
import { cn } from "@/lib/utils";
import { useFileActions } from "@/project/actions";
import { useProject } from "@/project/store";
import { version } from "../../package.json";

const timeFormat = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const dateFormat = new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" });

/** "hoy 14:32", "ayer 18:10" or "12 sep 2026". */
function formatOpened(iso: string): string {
  const date = new Date(iso);
  const days = Math.round(
    (new Date().setHours(0, 0, 0, 0) - new Date(date).setHours(0, 0, 0, 0)) / 86_400_000,
  );
  if (days === 0) return `hoy ${timeFormat.format(date)}`;
  if (days === 1) return `ayer ${timeFormat.format(date)}`;
  return dateFormat.format(date).replace(/\./g, "");
}

/** Split a file path into its directory (with the trailing separator) and file name. */
function splitPath(path: string): [string, string] {
  const cut = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\")) + 1;
  return [path.slice(0, cut), path.slice(cut)];
}

/** Start screen: New, Open and recent projects. Without recents, the brand as a blueprint. */
export function Home() {
  const { recents } = useProject();

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <header className="h-11 shrink-0 border-b border-border bg-surface" />
      {recents.length > 0 ? <WithRecents recents={recents} /> : <FirstUse />}
      <Footer />
    </div>
  );
}

function Actions() {
  const { newProject, openProject } = useFileActions();
  return (
    <div className="flex gap-3">
      <Button onClick={() => void newProject()}>
        <Plus data-icon="inline-start" />
        Nuevo proyecto
      </Button>
      <Button variant="secondary" onClick={() => void openProject()}>
        <FolderOpen data-icon="inline-start" />
        Abrir .hestia…
      </Button>
    </div>
  );
}

function WithRecents({ recents }: { recents: RecentProject[] }) {
  const { openProject, removeRecent } = useFileActions();
  return (
    <main className="flex min-h-0 flex-1 justify-center overflow-y-auto pt-24">
      <div className="flex w-[720px] flex-col gap-10">
        <div className="flex flex-col gap-4">
          <img src="/brand/hestia-logo.svg" alt="Hestia" className="h-10 w-fit" />
          <p className="text-sm text-muted-foreground">
            Prediseño del control térmico de satélites medianos · fases 0 y 1
          </p>
        </div>
        <Actions />
        <section className="flex flex-col gap-2 pb-8">
          <div className="flex items-center justify-between">
            <SectionLabel>Recientes</SectionLabel>
            <span className="font-mono text-[11px] text-subtle-foreground">
              {recents.length} {recents.length === 1 ? "proyecto" : "proyectos"}
            </span>
          </div>
          <ul className="flex flex-col border-t border-border">
            {recents.map((recent) => (
              <li
                key={recent.path}
                className="group/recent flex h-[52px] items-center gap-3 border-b border-border px-3 hover:bg-surface"
              >
                <button
                  type="button"
                  disabled={!recent.exists}
                  title={recent.path}
                  onClick={() => void openProject(recent.path)}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left disabled:cursor-default"
                >
                  {recent.exists ? (
                    <File className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  ) : (
                    <FileX className="size-4 shrink-0 text-subtle-foreground" aria-hidden />
                  )}
                  <span className="flex min-w-0 flex-col gap-[3px]">
                    <span
                      className={cn(
                        "truncate text-[13px] font-medium",
                        !recent.exists && "text-muted-foreground",
                      )}
                    >
                      {splitPath(recent.path)[1]}
                    </span>
                    <span className="truncate font-mono text-[11px] text-subtle-foreground">
                      {splitPath(recent.path)[0]}
                      {!recent.exists && " · archivo no encontrado"}
                    </span>
                  </span>
                </button>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  aria-label="Quitar de recientes"
                  title="Quitar de recientes"
                  className="invisible group-hover/recent:visible"
                  onClick={() => void removeRecent(recent.path)}
                >
                  <X />
                </Button>
                <span className="w-24 shrink-0 font-mono text-[11px] text-muted-foreground">
                  {formatOpened(recent.opened_at)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}

/** Absolute position relative to the horizontal center of the stage (design: 1440 wide). */
function at(dx: number, top: number, extra?: CSSProperties): CSSProperties {
  return { position: "absolute", left: `calc(50% + ${dx}px)`, top, ...extra };
}

const LINE = "bg-border";
const DIM = "bg-border-strong";
const DIM_LABEL = "font-mono text-[10px] tracking-[0.06em] text-subtle-foreground";

/** First use: the mark as a construction drawing (dimensions, axes, annotated core). */
function FirstUse() {
  const half = 105.6; // Half the mark's width (211.2 px).
  return (
    <main className="relative min-h-0 flex-1 overflow-hidden">
      <div className={cn("absolute inset-x-0 top-[132px] h-px", LINE)} />
      <div className={cn("absolute inset-x-0 top-[372px] h-px", LINE)} />
      <div className={LINE} style={at(-half, 40, { width: 1, height: 388 })} />
      <div className={LINE} style={at(half, 40, { width: 1, height: 388 })} />

      <div className={DIM} style={at(-half, 104, { width: 2 * half, height: 1 })} />
      <div className={DIM} style={at(-half, 100, { width: 1, height: 9 })} />
      <div className={DIM} style={at(half - 1, 100, { width: 1, height: 9 })} />
      <div className={cn(DIM_LABEL, "text-center")} style={at(-half, 84, { width: 2 * half })}>
        88
      </div>

      <div className={DIM} style={at(-half - 36, 132, { width: 1, height: 240 })} />
      <div className={DIM} style={at(-half - 40, 132, { width: 9, height: 1 })} />
      <div className={DIM} style={at(-half - 40, 371, { width: 9, height: 1 })} />
      <div className={cn(DIM_LABEL, "text-right")} style={at(-half - 76, 244, { width: 32 })}>
        100
      </div>

      <div className={DIM} style={at(half, 252, { width: 196, height: 1 })} />
      <div className={DIM} style={at(half + 196, 248, { width: 1, height: 9 })} />
      <div className="flex flex-col gap-1" style={at(half + 208, 237)}>
        <span className={DIM_LABEL}>NÚCLEO</span>
        <span className="font-mono text-[11px] text-muted-foreground">T 20 °C · 22 × 22</span>
      </div>

      <img
        src="/brand/hestia-mark.svg"
        alt="Hestia"
        style={at(-half, 132, { width: 2 * half, height: 240 })}
      />

      <div className="absolute inset-x-0 top-[444px] flex flex-col items-center gap-3.5 text-center">
        <h1 className="text-[30px] font-semibold tracking-[-0.01em]">Todo empieza por el núcleo</h1>
        <p className="w-[470px] text-[15px] text-muted-foreground">
          Creá un proyecto para dimensionar el control térmico de tu satélite: de la viabilidad al
          modelo nodal.
        </p>
        <div className="pt-[18px]">
          <Actions />
        </div>
        <p className="text-xs text-subtle-foreground">
          Cada proyecto es un archivo .hestia: guardalo junto a la documentación de la misión.
        </p>
      </div>

      <dl className="absolute right-6 bottom-[26px] flex w-[280px] flex-col border border-border">
        {[
          ["HESTIA", "TCS · prediseño"],
          ["FASES", "0 viabilidad · 1 nodal"],
          ["HOJA", "1 / 1"],
        ].map(([key, value]) => (
          <div
            key={key}
            className="flex h-7 items-center gap-3 border-b border-border px-2.5 last:border-b-0"
          >
            <dt className={cn(DIM_LABEL, "w-[52px]")}>{key}</dt>
            <dd className="font-mono text-[11px] text-muted-foreground">{value}</dd>
          </div>
        ))}
      </dl>
    </main>
  );
}

/** API status and app version. */
function Footer() {
  const { offline } = useProject();
  return (
    <footer className="flex h-8 shrink-0 items-center gap-2 border-t border-border px-4 font-mono text-[11px] text-subtle-foreground">
      <span className={cn("size-1.5 rounded-full", offline ? "bg-error" : "bg-ok")} aria-hidden />
      {offline ? (
        <span title={API_URL}>
          API local sin conexión · levantala con <code>make dev-api</code>
        </span>
      ) : (
        <span>API local conectada</span>
      )}
      <span className="flex-1" />
      <span>v{version}</span>
    </footer>
  );
}
