import { useCallback, useMemo } from "react";
import {
  api,
  unwrap,
  type Blueprint,
  type Link,
  type Position,
  type StageType,
} from "@/api/client";
import { useDialogs } from "@/project/dialogs";
import { readFragment, writeFragment } from "@/project/fragment";
import { findCell, findSystem, stageName as stageNameOf } from "@/project/lookup";
import { useProject } from "@/project/store";
import { useWorkspaceUi, type Target } from "./context";

export type PasteOptions = { position?: Position; targetSystemId?: string };

/**
 * Schematic writes. People are never asked for a justification (ADR 0024): every write runs
 * right away and is undone from the history. Copy and paste go through the system clipboard
 * as a fragment (ADR 0014).
 */
export function useSchematicActions() {
  const { view, catalog, mutate, notify, fail } = useProject();
  const { select, setCanPaste } = useWorkspaceUi();
  const dialogs = useDialogs();
  const project = view?.project;

  const stageName = useCallback((stage: StageType) => stageNameOf(catalog, stage), [catalog]);
  const blueprintName = useCallback(
    (blueprint: Blueprint) =>
      blueprint.template
        ? (catalog?.templates.find((t) => t.id === blueprint.template)?.name ?? blueprint.template)
        : blueprint.stage
          ? stageName(blueprint.stage)
          : "",
    [catalog, stageName],
  );
  const cellName = useCallback(
    (cellId: string) => findCell(project, cellId)?.name ?? cellId,
    [project],
  );

  const createSystem = useCallback(
    (blueprint: Blueprint, position?: Position) =>
      mutate(() =>
        unwrap(
          api.POST("/project/systems", {
            body: { ...blueprint, position: position ?? null },
          }),
        ),
      ),
    [mutate],
  );

  const branch = useCallback(
    (cellId: string, blueprint: Blueprint) =>
      mutate(() =>
        unwrap(
          api.POST("/project/cells/{cell_id}/branch", {
            params: { path: { cell_id: cellId } },
            body: blueprint,
          }),
        ),
      ),
    [mutate],
  );

  const addCell = useCallback(
    (systemId: string, stage: StageType) =>
      mutate(() =>
        unwrap(
          api.POST("/project/systems/{system_id}/cells", {
            params: { path: { system_id: systemId } },
            body: { stage },
          }),
        ),
      ),
    [mutate],
  );

  const moveSystem = useCallback(
    (systemId: string, position: Position) =>
      mutate(() =>
        unwrap(
          api.POST("/project/systems/{system_id}/move", {
            params: { path: { system_id: systemId } },
            body: { position },
          }),
        ),
      ),
    [mutate],
  );

  const link = useCallback(
    (sourceCellId: string, targetCellId: string) =>
      mutate(() =>
        unwrap(
          api.POST("/project/links", {
            body: { source_cell_id: sourceCellId, target_cell_id: targetCellId },
          }),
        ),
      ),
    [mutate],
  );

  const renameSystem = useCallback(
    async (systemId: string) => {
      const current = findSystem(project, systemId)?.name ?? "";
      const name = await dialogs.askRename({ title: "Renombrar sistema", current });
      if (!name || name === current) return;
      await mutate(() =>
        unwrap(
          api.PATCH("/project/systems/{system_id}", {
            params: { path: { system_id: systemId } },
            body: { name },
          }),
        ),
      );
    },
    [project, dialogs, mutate],
  );

  const renameCell = useCallback(
    async (cellId: string) => {
      const current = cellName(cellId);
      const name = await dialogs.askRename({ title: "Renombrar celda", current });
      if (!name || name === current) return;
      await mutate(() =>
        unwrap(
          api.PATCH("/project/cells/{cell_id}", {
            params: { path: { cell_id: cellId } },
            body: { name },
          }),
        ),
      );
    },
    [cellName, dialogs, mutate],
  );

  const duplicateSystem = useCallback(
    (systemId: string) =>
      mutate(() =>
        unwrap(
          api.POST("/project/systems/{system_id}/duplicate", {
            params: { path: { system_id: systemId } },
            body: {},
          }),
        ),
      ),
    [mutate],
  );

  const targetName = useCallback(
    (target: Target) =>
      target.kind === "system"
        ? (findSystem(project, target.id)?.name ?? target.id)
        : cellName(target.id),
    [project, cellName],
  );

  const removeWith = useCallback(
    (target: Target) =>
      mutate(() =>
        target.kind === "system"
          ? unwrap(
              api.DELETE("/project/systems/{system_id}", {
                params: { path: { system_id: target.id } },
                body: {},
              }),
            )
          : unwrap(
              api.DELETE("/project/cells/{cell_id}", {
                params: { path: { cell_id: target.id } },
                body: {},
              }),
            ),
      ),
    [mutate],
  );

  const remove = useCallback(
    async (target: Target) => {
      const result = await removeWith(target);
      if (result) select(null);
    },
    [removeWith, select],
  );

  const deleteSystem = useCallback(
    (systemId: string) => remove({ kind: "system", id: systemId }),
    [remove],
  );
  const deleteCell = useCallback(
    (cellId: string) => remove({ kind: "cell", id: cellId }),
    [remove],
  );

  const rename = useCallback(
    (target: Target) =>
      target.kind === "system" ? renameSystem(target.id) : renameCell(target.id),
    [renameSystem, renameCell],
  );

  const copyFragment = useCallback(
    (target: Target) =>
      unwrap(
        api.POST("/project/clipboard/copy", {
          body:
            target.kind === "system"
              ? { system_ids: [target.id], cell_ids: [] }
              : { system_ids: [], cell_ids: [target.id] },
        }),
      ),
    [],
  );

  /** Copy to the system clipboard. Resolves false if it failed (reported in Messages). */
  const copy = useCallback(
    async (target: Target): Promise<boolean> => {
      try {
        await writeFragment(await copyFragment(target));
        setCanPaste(true);
        notify(`Copió «${targetName(target)}».`);
        return true;
      } catch (error) {
        fail(error);
        return false;
      }
    },
    [copyFragment, setCanPaste, notify, targetName, fail],
  );

  /** Copy, then delete; nothing is deleted if copying failed. */
  const cut = useCallback(
    async (target: Target) => {
      if (!(await copy(target))) return;
      const result = await removeWith(target);
      if (result) select(null);
    },
    [copy, removeWith, select],
  );

  const pasteFragment = useCallback(
    async (run: () => ReturnType<typeof readFragment>, options: PasteOptions) => {
      const result = await mutate(async () => {
        const fragment = await run();
        if (!fragment) throw new Error("El portapapeles no tiene sistemas ni celdas de Hestia.");
        return unwrap(
          api.POST("/project/clipboard/paste", {
            body: {
              fragment,
              position: options.position ?? null,
              target_system_id: options.targetSystemId ?? null,
            },
          }),
        );
      });
      // Select what was pasted: the first new system, or else the first new cell.
      const created = result?.change.created_ids ?? [];
      const systems = new Set(result?.view.project.systems.map((s) => s.id));
      const first = created.find((id) => systems.has(id)) ?? created[0];
      if (first) select({ kind: systems.has(first) ? "system" : "cell", id: first });
    },
    [mutate, select],
  );

  const paste = useCallback(
    (options: PasteOptions = {}) => pasteFragment(readFragment, options),
    [pasteFragment],
  );

  /** Systems: the API's duplicate (keeps incoming links). Cells: copy and paste in place. */
  const duplicate = useCallback(
    async (target: Target) => {
      if (target.kind === "system") {
        await duplicateSystem(target.id);
        return;
      }
      const systemId = findCell(project, target.id)?.system_id;
      await pasteFragment(() => copyFragment(target), { targetSystemId: systemId });
    },
    [duplicateSystem, project, pasteFragment, copyFragment],
  );

  const unlink = useCallback(
    (target: Link) =>
      mutate(() =>
        unwrap(
          api.DELETE("/project/links/{link_id}", {
            params: { path: { link_id: target.id } },
            body: {},
          }),
        ),
      ),
    [mutate],
  );

  return useMemo(
    () => ({
      stageName,
      blueprintName,
      cellName,
      createSystem,
      branch,
      addCell,
      moveSystem,
      link,
      renameSystem,
      renameCell,
      duplicateSystem,
      deleteSystem,
      deleteCell,
      unlink,
      rename,
      remove,
      copy,
      cut,
      paste,
      duplicate,
    }),
    [
      stageName,
      blueprintName,
      cellName,
      createSystem,
      branch,
      addCell,
      moveSystem,
      link,
      renameSystem,
      renameCell,
      duplicateSystem,
      deleteSystem,
      deleteCell,
      unlink,
      rename,
      remove,
      copy,
      cut,
      paste,
      duplicate,
    ],
  );
}

export type SchematicActions = ReturnType<typeof useSchematicActions>;
