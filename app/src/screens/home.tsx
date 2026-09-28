import { FilePlus2, FolderOpen, FileX2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SectionLabel } from "@/components/navigation/section-label";
import { Notice } from "@/components/feedback/notice";
import { API_URL } from "@/api/client";
import { useFileActions } from "@/project/actions";
import { useProject } from "@/project/store";

const dateFormat = new Intl.DateTimeFormat("es-AR", { dateStyle: "medium", timeStyle: "short" });

/** Start screen: New, Open and recent projects. */
export function Home() {
  const { recents, offline } = useProject();
  const { newProject, openProject, removeRecent } = useFileActions();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="flex items-center gap-3">
        <img src="/favicon.svg" alt="" className="size-10" />
        <h1 className="text-3xl font-semibold tracking-tight">Hestia</h1>
      </div>
      {offline && (
        <Notice tone="error" title="Sin conexión con la API" className="w-full max-w-xl">
          No responde {API_URL}. Levantala con <code className="font-mono">make dev-api</code>.
        </Notice>
      )}
      <div className="flex gap-2">
        <Button onClick={() => void newProject()}>
          <FilePlus2 data-icon="inline-start" />
          Nuevo proyecto
        </Button>
        <Button variant="secondary" onClick={() => void openProject()}>
          <FolderOpen data-icon="inline-start" />
          Abrir…
        </Button>
      </div>
      {recents.length > 0 && (
        <section className="flex w-full max-w-xl flex-col gap-2">
          <SectionLabel>Recientes</SectionLabel>
          <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
            {recents.map((recent) => (
              <li key={recent.path} className="flex items-center gap-3 px-3 py-2">
                <button
                  type="button"
                  disabled={!recent.exists}
                  onClick={() => void openProject(recent.path)}
                  className="flex min-w-0 flex-1 flex-col items-start text-left disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
                    {!recent.exists && <FileX2 className="size-3.5 text-error" aria-hidden />}
                    {recent.name}
                    {!recent.exists && <span className="text-xs text-error">no existe</span>}
                  </span>
                  <span className="w-full truncate font-mono text-[11px] text-subtle-foreground">
                    {recent.path}
                  </span>
                </button>
                <span className="font-mono text-[11px] text-subtle-foreground">
                  {dateFormat.format(new Date(recent.opened_at))}
                </span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Quitar de recientes"
                  title="Quitar de recientes"
                  onClick={() => void removeRecent(recent.path)}
                >
                  <X />
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
