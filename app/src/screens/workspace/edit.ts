import { useCallback, useMemo } from "react";
import { useEditActions } from "@/project/actions";
import { useProject } from "@/project/store";
import type { SchematicActions } from "./actions";
import { useWorkspaceUi, type Target } from "./context";

/**
 * The Edit menu and its shortcuts, acting on the selected system or cell. Items that need a
 * selection are disabled without one; Paste needs a fragment in the clipboard.
 */
export function useEditCommands(actions: SchematicActions) {
  const { view } = useProject();
  const { selection, select, canPaste, pointerRef } = useWorkspaceUi();
  const history = useEditActions();
  const project = view?.project;

  // The selection may point to something just deleted (by anyone).
  const target = useMemo<Target | null>(() => {
    if (!selection || !project) return null;
    const list = selection.kind === "system" ? project.systems : project.cells;
    return list.some((item) => item.id === selection.id) ? selection : null;
  }, [selection, project]);

  const targetSystemId = useMemo(() => {
    if (!target || !project) return undefined;
    if (target.kind === "system") return target.id;
    return project.cells.find((cell) => cell.id === target.id)?.system_id;
  }, [target, project]);

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
      target,
      canPaste,
      undo: history.undo,
      redo: history.redo,
      cut: withTarget(actions.cut),
      copy: withTarget(actions.copy),
      paste,
      duplicate: withTarget(actions.duplicate),
      rename: withTarget(actions.rename),
      remove: withTarget(actions.remove),
      clearSelection: () => select(null),
    }),
    [target, canPaste, history, withTarget, actions, paste, select],
  );
}
