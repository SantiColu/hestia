import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { CornerDownRight, RefreshCw } from "lucide-react";
import { api, unwrap, type CellResult, type CellStatus, type ProjectView } from "@/api/client";
import { StageStatusBadge } from "@/components/feedback/stage-status";
import { PanelTabs, PanelTabsList, PanelTabsTrigger } from "@/components/navigation/panel-tabs";
import { Button } from "@/components/ui/button";
import { useUpdateCell } from "@/project/actions";
import { useProject } from "@/project/store";
import { EditorHeader, FormEditor, type Title } from "./cell-editor";
import { EnvironmentResults } from "./environment-results";
import type { ResultStateProps } from "./result-state";
import { contextLabel, useCellContext } from "./use-cell-context";
import { useMissionEnvelope } from "./use-mission-envelope";

// three.js is large: the 3D views load when first shown.
const OrbitView = lazy(() => import("./orbit-view").then((m) => ({ default: m.OrbitView })));
const OrbitPreview = lazy(() =>
  import("./orbit-preview").then((m) => ({ default: m.OrbitPreview })),
);

const LOADING = <p className="p-6 text-xs text-subtle-foreground">Cargando…</p>;

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
  const { fail } = useProject();
  const updateCell = useUpdateCell();
  const [section, setSection] = useState<Section>(
    status === "never_run" ? "parameters" : "results",
  );
  const [result, setResult] = useState<CellResult | null>(null);
  const [updating, setUpdating] = useState(false);
  const revision = view.document.revision;
  const context = useCellContext(cellId, revision);
  const sources = contextLabel(context, view.project);
  const envelope = useMissionEnvelope(context, revision);

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
    setUpdating(true);
    const answer = await updateCell(cellId);
    setUpdating(false);
    if (!answer) return;
    setResult(answer.result);
    if (answer.result.status === "up_to_date" && section === "parameters") setSection("results");
  }, [cellId, updateCell, section]);

  const onUpdate = () => void update();
  const state: ResultStateProps = {
    result,
    updating,
    sources,
    onUpdate,
    onOpenParameters: () => setSection("parameters"),
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 flex-col gap-3 border-b border-border px-6 pt-5">
        <EditorHeader
          title={title}
          source={<ContextSources label={sources} />}
          badge={
            <div className="flex items-center gap-2.5">
              <StageStatusBadge status={updating ? "running" : status} />
              <Button variant="secondary" onClick={onUpdate} disabled={updating}>
                <RefreshCw data-icon="inline-start" /> Actualizar
              </Button>
            </div>
          }
        />
        <PanelTabs value={section} onValueChange={(next: Section) => setSection(next)}>
          <PanelTabsList aria-label="Sección de la celda" className="border-b-0 px-0">
            {SECTIONS.map((s) => (
              <PanelTabsTrigger key={s.value} value={s.value}>
                {s.label}
              </PanelTabsTrigger>
            ))}
          </PanelTabsList>
        </PanelTabs>
      </div>
      <div className="min-h-0 flex-1">
        {section === "parameters" && (
          <FormEditor
            cellId={cellId}
            stage="environment"
            title={title}
            view={view}
            computation
            aside={(current, isDraft) => (
              <Suspense fallback={LOADING}>
                <OrbitPreview
                  cellId={cellId}
                  parameters={current}
                  isDraft={isDraft}
                  revision={revision}
                  envelope={envelope}
                />
              </Suspense>
            )}
          />
        )}
        {section === "results" && <EnvironmentResults state={state} />}
        {section === "orbit" && (
          <Suspense fallback={LOADING}>
            <OrbitView cellId={cellId} state={state} envelope={envelope} />
          </Suspense>
        )}
      </div>
    </div>
  );
}

/** «usa Misión · Fase 0 · base»: the cells whose results or artifacts this one reads. */
function ContextSources({ label }: { label: string | null }) {
  if (!label) return null;
  return (
    <span className="flex min-w-0 items-center gap-1.5 pl-1.5 text-xs text-subtle-foreground">
      <CornerDownRight aria-hidden className="size-3 shrink-0" />
      <span className="truncate">usa {label}</span>
    </span>
  );
}
