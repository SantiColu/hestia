import { useCallback, useMemo, type ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import type { ProjectView, StageType } from "@/api/client";
import { EmptyState } from "@/components/data/empty-state";
import { Notice } from "@/components/feedback/notice";
import { StageStatusBadge, type StageStatus } from "@/components/feedback/stage-status";
import { SectionLabel } from "@/components/navigation/section-label";
import { joinList } from "@/lib/format";
import { deepEqual, getAt, setAt, type Json, type JsonObject, type JsonPath } from "@/lib/json";
import { cn } from "@/lib/utils";
import { useDialogs } from "@/project/dialogs";
import { findCell, findSystem, isComputation, stageInfo, stageName } from "@/project/lookup";
import { useProject } from "@/project/store";
import { ComputationEditor } from "./computation-editor";
import { DraftBar, DraftErrors } from "./draft-bar";
import { EquipmentEditor } from "./equipment/equipment-editor";
import { column } from "./layout";
import { changedLeaves, switchOption } from "./schema";
import { SchemaForm } from "./schema-form";
import { useArtifactDraft, type ArtifactDraft } from "./use-artifact-draft";
import { useCellContext } from "./use-cell-context";

/**
 * The editor of a cell's tab: a form for implemented form stages (equipment has its own),
 * parameters + Update + results for implemented computation stages (ADR 0021), a placeholder
 * otherwise.
 */
export function CellEditor({ cellId, view }: { cellId: string; view: ProjectView }) {
  const { catalog } = useProject();
  const cell = findCell(view.project, cellId);
  if (!cell) return null;
  const stage = stageInfo(catalog, cell.stage);
  const title = { name: cell.name, system: findSystem(view.project, cell.system_id)?.name ?? "" };
  if (stage?.kind === "form" && stage.implemented) {
    // Equipment has an editor of its own: its matrix does not fit the generated form.
    if (cell.stage === "equipment") {
      return <EquipmentEditor cellId={cellId} title={title} view={view} />;
    }
    return <FormEditor cellId={cellId} stage={cell.stage} title={title} view={view} />;
  }
  if (isComputation(catalog, cell.stage)) {
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
 * A form generated from the stage's JSON Schema, with the draft, dry validation and Apply of
 * `useArtifactDraft` (ADR 0017). `computation`: the parameters of a computation stage
 * (ADR 0021), shown inside its editor (no header of its own), full width with an optional panel
 * beside the form (`aside`, given the current draft or applied artifact).
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
  const dialogs = useDialogs();
  const form = useArtifactDraft(cellId, stage, view.document.revision);
  const { schema, cellArtifact, applied, draft, current, problems, change } = form;

  const onChange = useCallback(
    (path: JsonPath, value: Json) => {
      if (!current || !applied) return;
      const changed = setAt(current, path, value) as JsonObject;
      // Fields that stop applying with this change are cleared or carried to their equivalent
      // (switchOption). Ask first when that loses values not applied yet.
      const { next, dropped } = schema
        ? switchOption(schema, current, changed)
        : { next: changed, dropped: [] };
      const unapplied = dropped.filter(
        (f) => !deepEqual(getAt(changed, f.path), getAt(applied, f.path) ?? null),
      );
      if (unapplied.length === 0) return change(next);
      void dialogs
        .askConfirm({
          title: "Valores sin aplicar",
          description: `Con la opción elegida dejan de aplicar campos con valores sin aplicar: ${joinList(
            unapplied.map((f) => f.label),
          )}. Si continuás, se borran.`,
          confirmLabel: "Borrar y cambiar",
        })
        .then((confirmed) => confirmed && change(next));
    },
    [current, applied, schema, change, dialogs],
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

  if (!schema || !cellArtifact || !current || !applied) return <EditorLoading />;

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
                badge={<DraftStatusBadge form={form} status={cellArtifact.status} />}
              />
            )}
            <DraftErrors
              schema={schema}
              problems={problems}
              hasDraft={draft !== null}
              computation={computation}
            />
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
        <DraftBar
          hasDraft={draft !== null}
          problems={problems}
          changes={changes}
          applying={form.applying}
          onDiscard={form.discard}
          onApply={() => void form.apply()}
          className={body}
        />
      )}
    </div>
  );
}

export function EditorLoading() {
  return <p className="p-6 text-xs text-subtle-foreground">Cargando…</p>;
}

/** The cell's status, or «Borrador con errores» while the draft has problems. */
export function DraftStatusBadge({
  form,
  status,
}: {
  form: Pick<ArtifactDraft, "draft" | "problems">;
  status: StageStatus;
}) {
  return form.draft && form.problems.length > 0 ? (
    <StageStatusBadge status="failed" label="Borrador con errores" />
  ) : (
    <StageStatusBadge status={status} />
  );
}
