import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
import { StageStatusBadge, type StageStatus } from "@/components/feedback/stage-status";
import { SectionLabel } from "@/components/navigation/section-label";
import { Button } from "@/components/ui/button";
import { deepEqual, setAt, type Json, type JsonObject, type JsonPath } from "@/lib/json";
import { useDialogs } from "@/project/dialogs";
import { useEditor } from "@/project/editor";
import { useProject } from "@/project/store";
import { cn } from "@/lib/utils";
import { changedLeaves, problemsBySection, type JsonSchema } from "./schema";
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
  const system = view.project.systems.find((s) => s.id === cell.system_id)?.name ?? "";
  const title = { name: cell.name, system };
  if (stage?.kind === "form" && stage.implemented) {
    return <FormEditor cellId={cellId} stage={cell.stage} title={title} view={view} />;
  }
  return <NotImplemented cellId={cellId} title={title} status={cell.status} view={view} />;
}

type Title = { name: string; system: string };

/** Centered column of the editor (`Form` in the design: 760 px). */
const column = "mx-auto flex w-full max-w-[760px] flex-col";

function EditorHeader({ title, badge }: { title: Title; badge: ReactNode }) {
  return (
    <header className="flex items-center gap-2.5">
      <h1 className="truncate text-lg font-semibold">{title.name}</h1>
      <span className="truncate text-[13px] text-subtle-foreground">{title.system}</span>
      <span className="flex-1" />
      {badge}
    </header>
  );
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** "A, B, C y 6 más" / "A y B". */
function listNames(names: string[], shown = 3): string {
  if (names.length > shown) {
    return `${names.slice(0, shown).join(", ")} y ${names.length - shown} más`;
  }
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} y ${names[names.length - 1]}`;
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
  status,
  view,
}: {
  cellId: string;
  title: Title;
  status: StageStatus;
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
    <div className="h-full overflow-y-auto px-6 py-6">
      <div className={cn(column, "gap-7")}>
        <EditorHeader title={title} badge={<StageStatusBadge status={status} />} />
        <EmptyState
          icon={CircleDashed}
          title="Sin implementar"
          description="Esta etapa todavía no tiene editor ni cálculo. Se puede vincular y ramificar en el esquemático."
        />
        {context && context.missing.length > 0 && (
          <Notice tone="warning" title="Falta en su contexto">
            {context.missing.map(stageName).join(", ")}. Vinculá las celdas que los proveen.
          </Notice>
        )}
        {context && context.entries.length > 0 && (
          <section className="flex flex-col gap-3.5">
            <SectionLabel>Contexto</SectionLabel>
            {context.entries.map((entry) => (
              <p key={`${entry.stage}:${entry.cell_id}`} className="text-[13px]">
                {stageName(entry.stage)} ← «{entry.cell_name}»
              </p>
            ))}
          </section>
        )}
      </div>
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
  title: Title;
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

  const changes = useMemo(
    () => (schema && applied && draft ? changedLeaves(schema, applied, draft) : []),
    [schema, applied, draft],
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
    const justification = await dialogs.askJustification({
      title: `Aplicar cambios · ${title.name}`,
      summary: [outdatesText(), failedText()].filter(Boolean).join(" "),
      changes: changes.map((c) => ({ field: c.path, from: c.from, to: c.to, value: c.change })),
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

  const errorsText = plural(problems.length, "error", "errores");
  const badge =
    draft && problems.length > 0 ? (
      <StageStatusBadge status="failed" label="Borrador con errores" />
    ) : (
      <StageStatusBadge status={cellArtifact.status} />
    );
  const showBar = draft !== null || !cellArtifact.applied;
  const sections = [...new Set(changes.map((c) => c.section))];

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        <div className={cn(column, "gap-7")}>
          <EditorHeader title={title} badge={badge} />
          {problems.length > 0 && (
            <Notice
              tone="error"
              title={`${plural(problems.length, "error", "errores")} de validación`}
            >
              {problemsBySection(
                schema,
                problems.map((p) => p.path),
              )}
              .{" "}
              {draft
                ? "Podés aplicar igual: la celda queda Fallida hasta corregirlos."
                : "La celda queda Fallida hasta corregirlos."}
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
      {showBar && (
        <footer className="h-[52px] shrink-0 border-t border-border bg-surface px-6">
          <div className={cn(column, "h-full flex-row items-center gap-3")}>
            <span
              aria-hidden
              className={cn(
                "size-1.5 shrink-0 rounded-full",
                !draft ? "bg-idle" : problems.length > 0 ? "bg-error" : "bg-primary",
              )}
            />
            <span className="flex-1 truncate text-[13px] text-muted-foreground">
              {draft
                ? `${plural(changes.length, "cambio", "cambios")} sin aplicar · ${
                    problems.length > 0 ? errorsText : sections.join(", ")
                  }`
                : "Sin aplicar · valores por defecto"}
            </span>
            <Button
              variant="ghost"
              disabled={!draft || applying}
              onClick={() => setDraft(cellId, null)}
            >
              <Undo2 data-icon="inline-start" /> Descartar
            </Button>
            <Button disabled={applying} onClick={() => void (draft ? apply() : applyUnchanged())}>
              <Check data-icon="inline-start" /> Aplicar…
            </Button>
          </div>
        </footer>
      )}
    </div>
  );

  /** Downstream cells the apply outdates (preview from the API). */
  function outdatesText(): string {
    const names = (cellArtifact?.outdates ?? []).map(
      (id) => view.project.cells.find((c) => c.id === id)?.name ?? id,
    );
    return names.length > 0
      ? `Desactualiza las celdas aguas abajo: ${listNames(names)}.`
      : "No desactualiza ninguna celda aguas abajo.";
  }

  function failedText(): string {
    return problems.length > 0
      ? `Con ${plural(problems.length, "error", "errores")}: la celda queda Fallida hasta corregirlos.`
      : "";
  }

  /** First apply of an untouched artifact (the defaults): records it and validates it. */
  async function applyUnchanged() {
    if (!applied) return;
    const justification = await dialogs.askJustification({
      title: `Aplicar · ${title.name}`,
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
