import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, CircleDashed, Undo2 } from "lucide-react";
import {
  api,
  unwrap,
  type CellArtifact,
  type CellContext,
  type MissionArtifact,
  type Problem,
  type ProjectView,
} from "@/api/client";
import { EmptyState } from "@/components/data/empty-state";
import { Notice } from "@/components/feedback/notice";
import { StageStatusBadge } from "@/components/feedback/stage-status";
import { Button } from "@/components/ui/button";
import { deepEqual, setAt, type Json, type JsonObject, type JsonPath } from "@/lib/json";
import { useDialogs } from "@/project/dialogs";
import { useEditor } from "@/project/editor";
import { useProject } from "@/project/store";
import { changedLeaves, type JsonSchema } from "./schema";
import { SchemaForm } from "./schema-form";

const VALIDATE_DEBOUNCE_MS = 300;

/** Schemas of form artifacts, fetched once per stage. */
const schemas = new Map<string, Promise<JsonSchema>>();

function artifactSchema(stage: string): Promise<JsonSchema> {
  let schema = schemas.get(stage);
  if (!schema) {
    schema = unwrap(
      api.GET("/catalog/stages/{stage}/artifact-schema", {
        params: { path: { stage: stage as never } },
      }),
    ) as Promise<JsonSchema>;
    schema.catch(() => schemas.delete(stage));
    schemas.set(stage, schema);
  }
  return schema;
}

/** The editor of a cell's tab: a form for implemented form stages, a placeholder otherwise. */
export function CellEditor({ cellId, view }: { cellId: string; view: ProjectView }) {
  const { catalog } = useProject();
  const cell = view.project.cells.find((c) => c.id === cellId);
  if (!cell) return null;
  const stage = catalog?.stages.find((s) => s.stage === cell.stage);
  const system = view.project.systems.find((s) => s.id === cell.system_id);
  const title = `${cell.name} · ${system?.name ?? ""}`;
  if (stage?.kind === "form" && stage.implemented) {
    return <FormEditor cellId={cellId} stage={cell.stage} title={title} view={view} />;
  }
  return <NotImplemented cellId={cellId} title={title} view={view} />;
}

function useStageNames() {
  const { catalog } = useProject();
  return useCallback(
    (stage: string) => catalog?.stages.find((s) => s.stage === stage)?.name ?? stage,
    [catalog],
  );
}

/** Stages without an editor yet: say so, and what their context lacks. */
function NotImplemented({
  cellId,
  title,
  view,
}: {
  cellId: string;
  title: string;
  view: ProjectView;
}) {
  const { fail } = useProject();
  const stageName = useStageNames();
  const [context, setContext] = useState<CellContext | null>(null);
  const revision = view.document.revision;

  useEffect(() => {
    let live = true;
    unwrap(api.GET("/project/cells/{cell_id}/context", { params: { path: { cell_id: cellId } } }))
      .then((result) => live && setContext(result))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [cellId, revision, fail]);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <h1 className="text-base font-semibold">{title}</h1>
      <EmptyState
        icon={CircleDashed}
        title="Sin implementar"
        description="Esta etapa todavía no tiene editor ni cálculo. Se puede vincular y ramificar en el esquemático."
        className="max-w-lg"
      />
      {context && context.missing.length > 0 && (
        <Notice tone="warning" title="Falta en su contexto" className="max-w-lg">
          {context.missing.map(stageName).join(", ")}. Vinculá las celdas que los proveen.
        </Notice>
      )}
      {context && context.entries.length > 0 && (
        <div className="flex max-w-lg flex-col gap-1">
          <h2 className="text-xs text-muted-foreground">Contexto</h2>
          {context.entries.map((entry) => (
            <p key={`${entry.stage}:${entry.cell_id}`} className="text-[13px]">
              {stageName(entry.stage)} ← «{entry.cell_name}»
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Draft + dry validation + Apply (ADR 0017). The draft lives in the editor store; the API
 * validates it (debounced) and decides status and provenance.
 */
function FormEditor({
  cellId,
  stage,
  title,
  view,
}: {
  cellId: string;
  stage: string;
  title: string;
  view: ProjectView;
}) {
  const { fail, notify, setView } = useProject();
  const { drafts, setDraft } = useEditor();
  const dialogs = useDialogs();
  const [schema, setSchema] = useState<JsonSchema | null>(null);
  const [cellArtifact, setCellArtifact] = useState<CellArtifact | null>(null);
  const [draftProblems, setDraftProblems] = useState<{
    draft: JsonObject;
    problems: Problem[];
  } | null>(null);
  const [applying, setApplying] = useState(false);
  const revision = view.document.revision;

  useEffect(() => {
    let live = true;
    artifactSchema(stage)
      .then((result) => live && setSchema(result))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [stage, fail]);

  // The applied artifact; refetched on every project change (undo, another actor).
  useEffect(() => {
    let live = true;
    unwrap(api.GET("/project/cells/{cell_id}/artifact", { params: { path: { cell_id: cellId } } }))
      .then((result) => live && setCellArtifact(result))
      .catch(fail);
    return () => {
      live = false;
    };
  }, [cellId, revision, fail]);

  const applied = useMemo(
    () => (cellArtifact?.artifact ?? null) as JsonObject | null,
    [cellArtifact],
  );
  const draft = drafts[cellId] ?? null;
  const current = draft ?? applied;

  // Dry validation of the draft, debounced. Without a draft, the applied problems count.
  const latestDraft = useRef(draft);
  useEffect(() => {
    latestDraft.current = draft;
    if (!draft) return;
    const timer = window.setTimeout(() => {
      unwrap(
        api.POST("/project/cells/{cell_id}/artifact/validate", {
          params: { path: { cell_id: cellId } },
          body: { artifact: draft as unknown as MissionArtifact },
        }),
      )
        .then(({ problems }) => {
          if (latestDraft.current === draft) setDraftProblems({ draft, problems });
        })
        .catch(fail);
    }, VALIDATE_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [cellId, draft, fail]);

  const problems =
    draft && draftProblems?.draft === draft
      ? draftProblems.problems
      : draft && draftProblems
        ? draftProblems.problems // previous answer while the new one is on its way
        : (cellArtifact?.problems ?? []);

  const onChange = useCallback(
    (path: JsonPath, value: Json) => {
      if (!current || !applied) return;
      const next = setAt(current, path, value) as JsonObject;
      setDraft(cellId, deepEqual(next, applied) ? null : next);
    },
    [current, applied, cellId, setDraft],
  );

  const sources = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(cellArtifact?.provenance ?? {}).map(([path, p]) => [path, p.source]),
      ),
    [cellArtifact],
  );

  const apply = async () => {
    if (!draft || !applied || !schema) return;
    const changes = changedLeaves(schema, applied, draft);
    const justification = await dialogs.askJustification({
      title: `Aplicar cambios en «${title}»`,
      summary:
        (problems.length > 0
          ? `Tiene ${problems.length} problema(s): la celda queda fallida hasta corregirlos. `
          : "") + "Todo lo que está aguas abajo de esta celda queda desactualizado.",
      changes: changes.map((c) => ({ field: c.label, from: c.from, to: c.to })),
      confirmLabel: "Aplicar",
    });
    if (justification === null) return;
    setApplying(true);
    try {
      const result = await unwrap(
        api.PUT("/project/cells/{cell_id}/artifact", {
          params: { path: { cell_id: cellId } },
          body: { artifact: draft as unknown as MissionArtifact, justification },
        }),
      );
      setView(result.view);
      setCellArtifact(result.cell);
      setDraft(cellId, null);
      setDraftProblems(null);
      if (!result.change) notify("Sin cambios: el contenido ya estaba aplicado.");
    } catch (error) {
      fail(error);
    } finally {
      setApplying(false);
    }
  };

  if (!schema || !cellArtifact || !current || !applied) {
    return <p className="p-6 text-xs text-subtle-foreground">Cargando…</p>;
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex shrink-0 items-center gap-3 border-b border-border px-6 py-3">
        <h1 className="flex-1 truncate text-base font-semibold">{title}</h1>
        <StageStatusBadge status={cellArtifact.status} />
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
        <div className="flex max-w-3xl flex-col gap-4">
          {problems.length > 0 && (
            <Notice
              tone={draft ? "warning" : "error"}
              title={`${problems.length} problema${problems.length === 1 ? "" : "s"}${draft ? " en el borrador" : ""}`}
            >
              <ul className="list-disc pl-4">
                {problems.map((p) => (
                  <li key={`${p.path}:${p.code}`}>
                    <span className="font-mono">{p.path}</span>: {p.message}
                  </li>
                ))}
              </ul>
            </Notice>
          )}
          <SchemaForm
            root={schema}
            applied={applied}
            current={current}
            problems={problems}
            sources={sources}
            onChange={onChange}
          />
        </div>
      </div>
      <footer className="flex shrink-0 items-center gap-2 border-t border-border bg-surface px-6 py-2">
        <span className="flex-1 text-xs text-muted-foreground">
          {draft
            ? "Borrador sin aplicar."
            : cellArtifact.applied
              ? "Sin cambios."
              : "Nunca aplicado."}
        </span>
        <Button
          size="sm"
          variant="ghost"
          disabled={!draft || applying}
          onClick={() => setDraft(cellId, null)}
        >
          <Undo2 data-icon="inline-start" /> Descartar
        </Button>
        <Button
          size="sm"
          disabled={(!draft && cellArtifact.applied) || applying}
          onClick={() => void (draft ? apply() : applyUnchanged())}
        >
          <Check data-icon="inline-start" /> Aplicar…
        </Button>
      </footer>
    </div>
  );

  /** First apply of an untouched artifact (the defaults): records it and validates it. */
  async function applyUnchanged() {
    if (!applied) return;
    const justification = await dialogs.askJustification({
      title: `Aplicar «${title}»`,
      summary: "Se aplica el contenido actual (valores por defecto) y se valida.",
      changes: [],
      confirmLabel: "Aplicar",
    });
    if (justification === null) return;
    try {
      const result = await unwrap(
        api.PUT("/project/cells/{cell_id}/artifact", {
          params: { path: { cell_id: cellId } },
          body: { artifact: applied as unknown as MissionArtifact, justification },
        }),
      );
      setView(result.view);
      setCellArtifact(result.cell);
    } catch (error) {
      fail(error);
    }
  }
}
