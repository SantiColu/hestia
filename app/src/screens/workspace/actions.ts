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
import { useProject } from "@/project/store";

/**
 * Schematic writes. Small operations (create, branch, move, rename, link, duplicate) send an
 * empty or optional justification; deletions and unlinking always ask for one (ADR 0011).
 */
export function useSchematicActions() {
  const { view, catalog, mutate } = useProject();
  const dialogs = useDialogs();
  const project = view?.project;

  const stageName = useCallback(
    (stage: StageType) => catalog?.stages.find((s) => s.stage === stage)?.name ?? stage,
    [catalog],
  );
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
    (cellId: string) => project?.cells.find((c) => c.id === cellId)?.name ?? cellId,
    [project],
  );

  const createSystem = useCallback(
    (blueprint: Blueprint, position?: Position) =>
      mutate(() =>
        unwrap(
          api.POST("/project/systems", {
            body: { ...blueprint, position: position ?? null, justification: "" },
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
            body: { ...blueprint, justification: "" },
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
            body: { stage, justification: "" },
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
            body: { position, justification: "" },
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
            body: { source_cell_id: sourceCellId, target_cell_id: targetCellId, justification: "" },
          }),
        ),
      ),
    [mutate],
  );

  const renameSystem = useCallback(
    async (systemId: string) => {
      const current = project?.systems.find((s) => s.id === systemId)?.name ?? "";
      const answer = await dialogs.askRename({ title: "Renombrar sistema", current });
      if (!answer || answer.name === current) return;
      await mutate(() =>
        unwrap(
          api.PATCH("/project/systems/{system_id}", {
            params: { path: { system_id: systemId } },
            body: answer,
          }),
        ),
      );
    },
    [project, dialogs, mutate],
  );

  const renameCell = useCallback(
    async (cellId: string) => {
      const current = cellName(cellId);
      const answer = await dialogs.askRename({ title: "Renombrar celda", current });
      if (!answer || answer.name === current) return;
      await mutate(() =>
        unwrap(
          api.PATCH("/project/cells/{cell_id}", {
            params: { path: { cell_id: cellId } },
            body: answer,
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
            body: { justification: "" },
          }),
        ),
      ),
    [mutate],
  );

  const deleteSystem = useCallback(
    async (systemId: string) => {
      const system = project?.systems.find((s) => s.id === systemId);
      if (!system) return;
      const justification = await dialogs.askJustification({
        title: "Eliminar sistema",
        summary: "Se eliminan sus celdas y vínculos; lo que dependa de ellas queda desactualizado.",
        changes: [{ field: "sistema", from: system.name, to: "—" }],
        confirmLabel: "Eliminar",
      });
      if (justification === null) return;
      await mutate(() =>
        unwrap(
          api.DELETE("/project/systems/{system_id}", {
            params: { path: { system_id: systemId } },
            body: { justification },
          }),
        ),
      );
    },
    [project, dialogs, mutate],
  );

  const deleteCell = useCallback(
    async (cellId: string) => {
      const justification = await dialogs.askJustification({
        title: "Eliminar celda",
        summary: "Se eliminan sus vínculos; lo que dependa de ella queda desactualizado.",
        changes: [{ field: "celda", from: cellName(cellId), to: "—" }],
        confirmLabel: "Eliminar",
      });
      if (justification === null) return;
      await mutate(() =>
        unwrap(
          api.DELETE("/project/cells/{cell_id}", {
            params: { path: { cell_id: cellId } },
            body: { justification },
          }),
        ),
      );
    },
    [cellName, dialogs, mutate],
  );

  const unlink = useCallback(
    async (target: Link) => {
      const justification = await dialogs.askJustification({
        title: "Desvincular",
        summary: "La celda de destino y todo lo que depende de ella queda desactualizado.",
        changes: [
          {
            field: "vínculo",
            from: `${cellName(target.source_cell_id)} → ${cellName(target.target_cell_id)}`,
            to: "—",
          },
        ],
        confirmLabel: "Desvincular",
      });
      if (justification === null) return;
      await mutate(() =>
        unwrap(
          api.DELETE("/project/links/{link_id}", {
            params: { path: { link_id: target.id } },
            body: { justification },
          }),
        ),
      );
    },
    [cellName, dialogs, mutate],
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
    ],
  );
}

export type SchematicActions = ReturnType<typeof useSchematicActions>;
