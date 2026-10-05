import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Check, CircleDashed, Undo2 } from "lucide-react";
import {
  api,
  unwrap,
  type CellArtifact,
  type EnvironmentParameters,
  type MissionArtifact,
  type Problem,
  type ProjectView,
  type StageType,
} from "@/api/client";
import { EmptyState } from "@/components/data/empty-state";
import { Notice } from "@/components/feedback/notice";
import { StageStatusBadge, type StageStatus } from "@/components/feedback/stage-status";
import { SectionLabel } from "@/components/navigation/section-label";
import { Button } from "@/components/ui/button";
import { joinList, plural } from "@/lib/format";
import { deepEqual, getAt, setAt, type Json, type JsonObject, type JsonPath } from "@/lib/json";
import { cn } from "@/lib/utils";
import { useDialogs } from "@/project/dialogs";
import { DRAFT_DEBOUNCE_MS, useEditor } from "@/project/editor";
import { findCell, findSystem, stageName } from "@/project/lookup";
import { useProject } from "@/project/store";
import { ComputationEditor } from "./computation-editor";
import { column } from "./layout";
import { changedLeaves, problemsBySection, switchOption, type JsonSchema } from "./schema";
import { useCellContext } from "./use-cell-context";
import { SchemaForm } from "./schema-form";

/** Downstream cells named in the apply summary before "y N más". */
const MAX_NAMED_CELLS = 3;

/** Body of the generic artifact endpoints (ADR 0019): a form artifact or a computation's
 * parameters. The API validates it against the cell's stage. */
type Artifact = MissionArtifact | EnvironmentParameters;

/** The draft is plain JSON built from the stage's JSON Schema; the API validates its shape. */
function asArtifact(value: JsonObject): Artifact {
  return value as unknown as Artifact;
}

/** Schemas of form artifacts, fetched once per stage. */
const schemas = new Map<StageType, Promise<JsonSchema>>();

function artifactSchema(stage: StageType): Promise<JsonSchema> {
  let schema = schemas.get(stage);
  if (!schema) {
    schema = unwrap(
      api.GET("/catalog/stages/{stage}/artifact-schema", { params: { path: { stage } } }),
    ) as Promise<JsonSchema>;
    schema.catch(() => schemas.delete(stage));
    schemas.set(stage, schema);
  }
  return schema;
}

/**
 * The editor of a cell's tab: a form for implemented form stages, parameters + Update + results
 * for implemented computation stages (ADR 0021), a placeholder otherwise.
 */
export function CellEditor({ cellId, view }: { cellId: string; view: ProjectView }) {
  const { catalog } = useProject();
  const cell = findCell(view.project, cellId);
  if (!cell) return null;
  const stage = catalog?.stages.find((entry) => entry.stage === cell.stage);
  const title = { name: cell.name, system: findSystem(view.project, cell.system_id)?.name ?? "" };
  if (stage?.kind === "form" && stage.implemented) {
    return <FormEditor cellId={cellId} stage={cell.stage} title={title} view={view} />;
  }
  if (stage?.kind === "computation" && stage.implemented) {
    return <ComputationEditor cellId={cellId} status={cell.status} title={title} view={view} />;
  }
  return <NotImplemented cellId={cellId} title={title} status={cell.status} view={view} />;
}

export type Title = { name: string; system: string };

export function EditorHeader({
  title,
  source,
  badge,
}: {
  title: Title;
  /** What the cell reads from its context, after its system. */
  source?: ReactNode;
  badge: ReactNode;
}) {
  return (
    <header className="flex items-center gap-2.5">
      <h1 className="truncate text-lg font-semibold">{title.name}</h1>
      <span className="truncate text-ui text-subtle-foreground">{title.system}</span>
      {source}
      <span className="flex-1" />
      {badge}
    </header>
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
  const { catalog } = useProject();
  const context = useCellContext(cellId, view.document.revision);

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
            {context.missing.map((stage) => stageName(catalog, stage)).join(", ")}. Vinculá las
            celdas que los proveen.
          </Notice>
        )}
        {context && context.entries.length > 0 && (
          <section className="flex flex-col gap-3.5">
            <SectionLabel>Contexto</SectionLabel>
            {context.entries.map((entry) => (
              <p key={`${entry.stage}:${entry.cell_id}`} className="text-ui">
                {stageName(catalog, entry.stage)} ← «{entry.cell_name}»
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
 * validates it (debounced) and decides status and provenance. `computation`: the parameters of
 * a computation stage (ADR 0021), shown inside its editor (no header of its own), full width with
 * an optional panel beside the form (`aside`, given the current draft or applied artifact).
 */
export function FormEditor({
  cellId,
  stage,
  title,
  view,
  computation = false,
  aside,
}: {
  cellId: string;
  stage: StageType;
  title: Title;
  view: ProjectView;
  computation?: boolean;
  aside?: (current: JsonObject, isDraft: boolean) => ReactNode;
}) {
  const { fail, notify, setView } = useProject();
  const { drafts, setDraft } = useEditor();
  const dialogs = useDialogs();
  const [schema, setSchema] = useState<JsonSchema | null>(null);
  const [cellArtifact, setCellArtifact] = useState<CellArtifact | null>(null);
  /** Problems of the latest validated draft (kept while a newer one is being validated). */
  const [draftProblems, setDraftProblems] = useState<Problem[] | null>(null);
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
          body: { artifact: asArtifact(draft) },
        }),
      )
        .then(({ problems }) => {
          if (latestDraft.current === draft) setDraftProblems(problems);
        })
        .catch(fail);
    }, DRAFT_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [cellId, draft, fail]);

  const problems = draft && draftProblems ? draftProblems : (cellArtifact?.problems ?? []);

  const onChange = useCallback(
    (path: JsonPath, value: Json) => {
      if (!current || !applied) return;
      const changed = setAt(current, path, value) as JsonObject;
      // Fields that stop applying with this change are cleared or carried to their equivalent
      // (switchOption). Ask first when that loses values not applied yet.
      const { next, dropped } = schema
        ? switchOption(schema, current, changed)
        : { next: changed, dropped: [] };
      const commit = () => setDraft(cellId, deepEqual(next, applied) ? null : next);
      const unapplied = dropped.filter(
        (f) => !deepEqual(getAt(changed, f.path), getAt(applied, f.path) ?? null),
      );
      if (unapplied.length === 0) return commit();
      void dialogs
        .askConfirm({
          title: "Valores sin aplicar",
          description: `Con la opción elegida dejan de aplicar campos con valores sin aplicar: ${joinList(
            unapplied.map((f) => f.label),
          )}. Si continuás, se borran.`,
          confirmLabel: "Borrar y cambiar",
        })
        .then((confirmed) => confirmed && commit());
    },
    [current, applied, schema, cellId, setDraft, dialogs],
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

  if (!schema || !cellArtifact || !current || !applied) {
    return <p className="p-6 text-xs text-subtle-foreground">Cargando…</p>;
  }

  const errorCount = plural(problems.length, "error", "errores");
  /** What errors mean for this cell: a form cell fails; a computation cannot update. */
  const errorConsequence = computation
    ? "Actualizar falla hasta corregirlos."
    : "la celda queda Fallida hasta corregirlos.";

  /** Impact of applying: the downstream cells it outdates (from the API) and the errors. */
  const applySummary = () => {
    const outdated = cellArtifact.outdates.map((id) => findCell(view.project, id)?.name ?? id);
    return [
      outdated.length > 0
        ? `Desactualiza las celdas aguas abajo: ${joinList(outdated, MAX_NAMED_CELLS)}.`
        : "No desactualiza ninguna celda aguas abajo.",
      problems.length > 0 && `Con ${errorCount}: ${errorConsequence}`,
    ]
      .filter(Boolean)
      .join(" ");
  };

  /** Ask for the justification and apply the draft, or the untouched defaults (first apply). */
  const apply = async () => {
    const justification = await dialogs.askJustification(
      draft
        ? {
            title: `Aplicar cambios · ${title.name}`,
            summary: applySummary(),
            changes: changes.map((c) => ({
              field: c.path,
              from: c.from,
              to: c.to,
              value: c.change,
            })),
            confirmLabel: "Aplicar",
          }
        : {
            title: `Aplicar · ${title.name}`,
            summary: "Se aplica el contenido actual (valores por defecto) y se valida.",
            changes: [],
            confirmLabel: "Aplicar",
          },
    );
    if (justification === null) return;
    setApplying(true);
    try {
      const result = await unwrap(
        api.PUT("/project/cells/{cell_id}/artifact", {
          params: { path: { cell_id: cellId } },
          body: { artifact: asArtifact(draft ?? applied), justification },
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

  const sections = [...new Set(changes.map((c) => c.section))];
  /** Computation parameters use the whole width, as their header does. */
  const body = computation ? "flex w-full flex-col" : column;

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        <div className={cn("min-h-0 flex-1 overflow-y-auto px-6", computation ? "py-4" : "py-6")}>
          <div className={cn(body, "gap-7")}>
            {!computation && (
              <EditorHeader
                title={title}
                badge={
                  draft && problems.length > 0 ? (
                    <StageStatusBadge status="failed" label="Borrador con errores" />
                  ) : (
                    <StageStatusBadge status={cellArtifact.status} />
                  )
                }
              />
            )}
            {problems.length > 0 && (
              <Notice tone="error" title={`${errorCount} de validación`}>
                {problemsBySection(
                  schema,
                  problems.map((p) => p.path),
                )}
                .{" "}
                {computation || draft
                  ? `Podés aplicar igual: ${errorConsequence}`
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
        {aside?.(current, draft !== null)}
      </div>
      {(draft !== null || !cellArtifact.applied) && (
        <footer className="h-13 shrink-0 border-t border-border bg-surface px-6">
          <div className={cn(body, "h-full flex-row items-center gap-3")}>
            <span
              aria-hidden
              className={cn(
                "size-1.5 shrink-0 rounded-full",
                !draft ? "bg-idle" : problems.length > 0 ? "bg-error" : "bg-primary",
              )}
            />
            <span className="flex-1 truncate text-ui text-muted-foreground">
              {draft
                ? `${plural(changes.length, "cambio", "cambios")} sin aplicar · ${
                    problems.length > 0 ? errorCount : sections.join(", ")
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
            <Button disabled={applying} onClick={() => void apply()}>
              <Check data-icon="inline-start" /> Aplicar…
            </Button>
          </div>
        </footer>
      )}
    </div>
  );
}
