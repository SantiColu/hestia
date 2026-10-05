import { useCallback, useMemo } from "react";
import { useEditActions } from "@/project/actions";
import { findCell } from "@/project/lookup";
import { useProject } from "@/project/store";
import type { SchematicActions } from "./actions";
import { useWorkspaceUi } from "./context";
import type { Target } from "./target";

/**
 * The Edit menu and its shortcuts, acting on the selected systems and cells. Cut, copy and
 * delete take the whole selection; duplicate and rename need a single item. Paste needs a
 * fragment in the clipboard.
 */
export function useEditCommands(actions: SchematicActions) {
  const { view } = useProject();
  const { selection, select, canPaste, pointerRef } = useWorkspaceUi();
  const history = useEditActions();
  const project = view?.project;

  // The selection may point to something just deleted (by anyone).
  const targets = useMemo<Target[]>(
    () =>
      selection.filter((t) =>
        (t.kind === "system" ? project?.systems : project?.cells)?.some((item) => item.id === t.id),
      ),
    [selection, project],
  );
  const target = targets.length === 1 ? (targets[0] ?? null) : null;

  const targetSystemId = useMemo(() => {
    if (!target || !project) return undefined;
    if (target.kind === "system") return target.id;
    return findCell(project, target.id)?.system_id;
  }, [target, project]);

  const withTargets = useCallback(
    (run: (targets: Target[]) => unknown) => () => {
      if (targets.length > 0) void run(targets);
    },
    [targets],
  );

  const withTarget = useCallback(
    (run: (target: Target) => unknown) => () => {
      if (target) void run(target);
    },
    [target],
  );

  /**
   * From the keyboard, paste where the pointer is (if it is over the canvas). The keyboard
   * always tries: if the clipboard holds no fragment, Messages says so.
   */
  const paste = useCallback(
    (atPointer: boolean) => {
      const position = atPointer ? (pointerRef.current ?? undefined) : undefined;
      void actions.paste({ position, targetSystemId });
    },
    [pointerRef, actions, targetSystemId],
  );

  return useMemo(
    () => ({
      targets,
      target,
      canPaste,
      undo: history.undo,
      redo: history.redo,
      cut: withTargets(actions.cut),
      copy: withTargets(actions.copy),
      paste,
      duplicate: withTarget(actions.duplicate),
      rename: withTarget(actions.rename),
      remove: withTargets(actions.remove),
      clearSelection: () => select(null),
    }),
    [targets, target, canPaste, history, withTargets, withTarget, actions, paste, select],
  );
}
