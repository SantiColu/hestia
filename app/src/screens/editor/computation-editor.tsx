import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, unwrap, type CellResult, type CellStatus, type ProjectView } from "@/api/client";
import { StageStatusBadge } from "@/components/feedback/stage-status";
import { Segmented } from "@/components/forms/segmented";
import { Button } from "@/components/ui/button";
import { useEditor } from "@/project/editor";
import { useProject } from "@/project/store";
import { cn } from "@/lib/utils";
import { EditorHeader, FormEditor, type Title } from "./cell-editor";
import { column } from "./layout";
import { EnvironmentResults } from "./environment-results";

// three.js is large: the 3D view loads when first opened.
const OrbitView = lazy(() => import("./orbit-view").then((m) => ({ default: m.OrbitView })));

type Section = "parameters" | "results" | "orbit";

const SECTIONS: { value: Section; label: string }[] = [
  { value: "parameters", label: "Parámetros" },
  { value: "results", label: "Resultados" },
  { value: "orbit", label: "Órbita 3D" },
];

/**
 * Tab of a computation cell (ADR 0021): parameters as a form, Update and the result. The API
 * computes everything; this view only asks for it and draws it.
 */
export function ComputationEditor({
  cellId,
  status,
  title,
  view,
}: {
  cellId: string;
  status: CellStatus;
  title: Title;
  view: ProjectView;
}) {
  const { fail, notify, setView } = useProject();
  const { drafts } = useEditor();
  const [section, setSection] = useState<Section>(
    status === "never_run" ? "parameters" : "results",
  );
  const [result, setResult] = useState<CellResult | null>(null);
  const [updating, setUpdating] = useState(false);
  const revision = view.document.revision;

  // The result; refetched on every project change (undo, another actor, an upstream change).
  useEffect(() => {
    let live = true;
    unwrap(api.GET("/project/cells/{cell_id}/result", { params: { path: { cell_id: cellId } } }))
      .then((next) => live && setResult(next))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [cellId, revision, fail]);

  const update = useCallback(async () => {
    if (drafts[cellId]) notify("Hay parámetros sin aplicar: Actualizar usa los aplicados.");
    setUpdating(true);
    try {
      const answer = await unwrap(
        api.POST("/project/cells/{cell_id}/update", {
          params: { path: { cell_id: cellId } },
          body: { justification: "" },
        }),
      );
      setView(answer.view);
      setResult(answer.result);
      if (!answer.change) {
        notify(
          answer.result.status === "up_to_date"
            ? "Sin cambios: la celda ya estaba actualizada."
            : "Sin cambios: falla por los mismos problemas.",
        );
      }
      if (answer.result.status === "up_to_date" && section === "parameters") setSection("results");
    } catch (error) {
      fail(error);
    } finally {
      setUpdating(false);
    }
  }, [cellId, drafts, fail, notify, section, setView]);

  const onUpdate = () => void update();

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-border px-6 pt-5 pb-3">
        <div className={cn(column, "gap-3")}>
          <EditorHeader
            title={title}
            badge={
              <div className="flex items-center gap-2">
                <StageStatusBadge status={updating ? "running" : status} />
                <Button size="sm" onClick={onUpdate} disabled={updating}>
                  <RefreshCw data-icon="inline-start" /> Actualizar
                </Button>
              </div>
            }
          />
          <Segmented
            aria-label="Sección de la celda"
            options={SECTIONS}
            value={section}
            onValueChange={setSection}
            className="w-fit"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1">
        {section === "parameters" && (
          <FormEditor cellId={cellId} stage="environment" title={title} view={view} computation />
        )}
        {section === "results" && (
          <EnvironmentResults result={result} view={view} updating={updating} onUpdate={onUpdate} />
        )}
        {section === "orbit" && (
          <Suspense fallback={<p className="p-6 text-xs text-subtle-foreground">Cargando…</p>}>
            <OrbitView cellId={cellId} result={result} updating={updating} onUpdate={onUpdate} />
          </Suspense>
        )}
      </div>
    </div>
  );
}
