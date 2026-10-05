import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  unwrap,
  type CellArtifact,
  type EnvironmentParameters,
  type EquipmentArtifact,
  type MissionArtifact,
  type Problem,
  type StageType,
  type ValidationResult,
} from "@/api/client";
import { deepEqual, type JsonObject } from "@/lib/json";
import { DRAFT_DEBOUNCE_MS, useEditor } from "@/project/editor";
import { useProject } from "@/project/store";
import type { JsonSchema } from "./schema";

/** Body of the generic artifact endpoints (ADR 0019): a form artifact or a computation's
 * parameters. The API validates it against the cell's stage. */
type Artifact = MissionArtifact | EquipmentArtifact | EnvironmentParameters;

/** The draft is plain JSON edited from the stage's JSON Schema; the API validates its shape. */
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

export type ArtifactDraft = {
  schema: JsonSchema | null;
  cellArtifact: CellArtifact | null;
  applied: JsonObject | null;
  /** The unapplied draft (null: nothing changed). */
  draft: JsonObject | null;
  /** The draft, or else the applied artifact. */
  current: JsonObject | null;
  /** Problems of the latest validated draft, or else of the applied artifact. */
  problems: Problem[];
  /** Values the API derives from the draft (or the applied artifact); null for stages without
   * them. */
  derived: CellArtifact["derived"];
  applying: boolean;
  /** Replace the draft; the same content as the applied artifact clears it. */
  change: (next: JsonObject) => void;
  discard: () => void;
  /** Apply the draft, or the untouched defaults (first apply). Undone from the history. */
  apply: () => Promise<void>;
};

/**
 * Draft + dry validation + Apply of a cell's artifact (ADR 0017). The draft lives in the editor
 * store; the API validates it (debounced) and decides problems, derived values, status and
 * provenance.
 */
export function useArtifactDraft(cellId: string, stage: StageType, revision: number) {
  const { fail, notify, setView } = useProject();
  const { drafts, setDraft } = useEditor();
  const [schema, setSchema] = useState<JsonSchema | null>(null);
  const [cellArtifact, setCellArtifact] = useState<CellArtifact | null>(null);
  /** Validation of the latest validated draft (kept while a newer one is being validated). */
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [applying, setApplying] = useState(false);

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

  // Dry validation of the draft, debounced. Without a draft, the applied artifact counts.
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
        .then((result) => {
          if (latestDraft.current === draft) setValidation(result);
        })
        .catch(fail);
    }, DRAFT_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [cellId, draft, fail]);

  const change = useCallback(
    (next: JsonObject) => setDraft(cellId, applied && deepEqual(next, applied) ? null : next),
    [cellId, applied, setDraft],
  );
  const discard = useCallback(() => setDraft(cellId, null), [cellId, setDraft]);

  const apply = async () => {
    if (!applied) return;
    setApplying(true);
    try {
      const result = await unwrap(
        api.PUT("/project/cells/{cell_id}/artifact", {
          params: { path: { cell_id: cellId } },
          body: { artifact: asArtifact(draft ?? applied) },
        }),
      );
      setView(result.view);
      setCellArtifact(result.cell);
      setDraft(cellId, null);
      setValidation(null);
      if (!result.change) notify("Sin cambios: el contenido ya estaba aplicado.");
    } catch (error) {
      fail(error);
    } finally {
      setApplying(false);
    }
  };

  const validated = draft ? validation : null;
  return {
    schema,
    cellArtifact,
    applied,
    draft,
    current: draft ?? applied,
    problems: validated?.problems ?? cellArtifact?.problems ?? [],
    derived: validated ? validated.derived : (cellArtifact?.derived ?? null),
    applying,
    change,
    discard,
    apply,
  } satisfies ArtifactDraft;
}
