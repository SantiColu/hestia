import { useCallback, useMemo } from "react";
import type { ProjectView } from "@/api/client";
import { SectionLabel } from "@/components/navigation/section-label";
import { setAt, type Json, type JsonObject, type JsonPath } from "@/lib/json";
import { cn } from "@/lib/utils";
import { DraftStatusBadge, EditorHeader, EditorLoading, type Title } from "../cell-editor";
import { DraftBar, DraftErrors } from "../draft-bar";
import { changedLeaves } from "../schema";
import { useArtifactDraft } from "../use-artifact-draft";
import type { EquipmentForm } from "./cells";
import { dissipationScale } from "./dissipation";
import { asEquipment, toDraft } from "./edits";
import { equipmentSchema } from "./equipment-schema";
import { ItemsTable } from "./items-table";
import { OperatingModes } from "./operating-modes";

/** The editor and its draft bar use the whole width (docs/etapas/equipment.md, «Pantalla»). */
const BODY = "flex w-full flex-col";

/**
 * Tab of an equipment cell: the items with their own modes and the operating modes as a matrix
 * (docs/etapas/equipment.md). Its own
 * editor, not the generated form, over the same draft, dry validation and Apply (ADR 0017): the
 * API validates and derives everything; this view only edits the draft and shows what it gets.
 */
export function EquipmentEditor({
  cellId,
  title,
  view,
}: {
  cellId: string;
  title: Title;
  view: ProjectView;
}) {
  const draft = useArtifactDraft(cellId, "equipment", view.document.revision);
  const { schema, cellArtifact, applied, current, problems, change } = draft;
  const fields = useMemo(() => (schema ? equipmentSchema(schema) : null), [schema]);

  const set = useCallback(
    (path: JsonPath, value: Json) => current && change(setAt(current, path, value) as JsonObject),
    [current, change],
  );

  const changes = useMemo(
    () => (schema && applied && draft.draft ? changedLeaves(schema, applied, draft.draft) : []),
    [schema, applied, draft.draft],
  );

  if (!schema || !fields || !cellArtifact || !current || !applied) return <EditorLoading />;

  const artifact = asEquipment(current);
  const scale = dissipationScale(draft.derived, artifact);
  const form: EquipmentForm = { schema: fields, current, applied, problems, scale, set };
  const onEdit = (next: typeof artifact) => change(toDraft(next));

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        <div className={cn(BODY, "gap-7")}>
          <EditorHeader
            title={title}
            badge={<DraftStatusBadge form={draft} status={cellArtifact.status} />}
          />
          <DraftErrors schema={schema} problems={problems} hasDraft={draft.draft !== null} />
          <section className="flex flex-col gap-3.5">
            <SectionLabel>{schema.properties?.items?.title}</SectionLabel>
            <ItemsTable form={form} artifact={artifact} onEdit={onEdit} />
          </section>
          <section className="flex flex-col gap-3.5">
            <SectionLabel>{schema.properties?.operating_modes?.title}</SectionLabel>
            <OperatingModes form={form} artifact={artifact} onEdit={onEdit} />
          </section>
        </div>
      </div>
      {(draft.draft !== null || !cellArtifact.applied) && (
        <DraftBar
          hasDraft={draft.draft !== null}
          problems={problems}
          changes={changes}
          applying={draft.applying}
          onDiscard={draft.discard}
          onApply={() => void draft.apply()}
          className={BODY}
        />
      )}
    </div>
  );
}
