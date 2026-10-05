import { useCallback, useMemo } from "react";
import { api, isApiError, unwrap, type ProjectView, type UpdateCellResult } from "@/api/client";
import { pickProjectToOpen, pickProjectToSave } from "@/lib/native";
import { useDialogs } from "./dialogs";
import { useEditor } from "./editor";
import { useProject } from "./store";

export function fileLabel(view: ProjectView | null): string {
  if (!view) return "";
  return view.document.file_name ?? view.project.name;
}

/**
 * File menu actions. The API decides whether something would lose unsaved changes
 * (`unsaved_changes`) or is locked (`project_locked`); the UI only asks the user and retries.
 */
export function useFileActions() {
  const { view, setView, fail, refreshRecents } = useProject();
  const dialogs = useDialogs();
  const { confirmDiscardDrafts } = useEditor();

  const saveAs = useCallback(async (): Promise<boolean> => {
    if (!view) return false;
    try {
      const path = await pickProjectToSave(view.project.name);
      if (!path) return false;
      setView(await unwrap(api.POST("/project/save-as", { body: { path } })));
      void refreshRecents();
      return true;
    } catch (error) {
      fail(error);
      return false;
    }
  }, [view, setView, fail, refreshRecents]);

  const save = useCallback(async (): Promise<boolean> => {
    if (!view) return false;
    if (!view.document.path) return saveAs();
    try {
      setView(await unwrap(api.POST("/project/save")));
      return true;
    } catch (error) {
      if (isApiError(error, "no_path")) return saveAs();
      fail(error);
      return false;
    }
  }, [view, setView, fail, saveAs]);

  /** Run `run(false)`; if the API reports unsaved changes, ask and retry. */
  const guardUnsaved = useCallback(
    async <T>(run: (discard: boolean) => Promise<T | null>): Promise<T | null> => {
      try {
        return await run(false);
      } catch (error) {
        if (!isApiError(error, "unsaved_changes")) throw error;
        const choice = await dialogs.askUnsaved(fileLabel(view) || "El proyecto");
        if (choice === "cancel") return null;
        if (choice === "save") return (await save()) ? run(false) : null;
        return run(true);
      }
    },
    [dialogs, view, save],
  );

  const newProject = useCallback(async () => {
    if (!(await confirmDiscardDrafts())) return;
    try {
      const result = await guardUnsaved((discard) =>
        unwrap(api.POST("/project/new", { body: { discard_unsaved: discard } })),
      );
      if (result) setView(result);
    } catch (error) {
      fail(error);
    }
  }, [guardUnsaved, setView, fail, confirmDiscardDrafts]);

  const openProject = useCallback(
    async (knownPath?: string) => {
      try {
        const path = knownPath ?? (await pickProjectToOpen());
        if (!path) return;
        if (path !== view?.document.path && !(await confirmDiscardDrafts())) return;
        const open = (discard: boolean, force: boolean) =>
          unwrap(api.POST("/project/open", { body: { path, force, discard_unsaved: discard } }));
        const result = await guardUnsaved(async (discard) => {
          try {
            return await open(discard, false);
          } catch (error) {
            if (!isApiError(error, "project_locked")) throw error;
            return (await dialogs.askLocked(error.message)) ? open(discard, true) : null;
          }
        });
        if (result) setView(result);
      } catch (error) {
        fail(error);
      } finally {
        void refreshRecents();
      }
    },
    [guardUnsaved, dialogs, setView, fail, refreshRecents, view, confirmDiscardDrafts],
  );

  const closeProject = useCallback(async (): Promise<boolean> => {
    if (!(await confirmDiscardDrafts())) return false;
    try {
      const result = await guardUnsaved((discard) =>
        unwrap(api.POST("/project/close", { body: { discard_unsaved: discard } })),
      );
      if (!result) return false;
      setView(null);
      return true;
    } catch (error) {
      fail(error);
      return false;
    }
  }, [guardUnsaved, setView, fail, confirmDiscardDrafts]);

  const removeRecent = useCallback(
    async (path: string) => {
      try {
        await unwrap(api.DELETE("/recents", { body: { path } }));
      } catch (error) {
        fail(error);
      } finally {
        void refreshRecents();
      }
    },
    [fail, refreshRecents],
  );

  return useMemo(
    () => ({ newProject, openProject, save, saveAs, closeProject, removeRecent }),
    [newProject, openProject, save, saveAs, closeProject, removeRecent],
  );
}

export function useEditActions() {
  const { view, mutate } = useProject();
  const undo = useCallback(() => {
    if (!view?.document.can_undo) return;
    void mutate(() => unwrap(api.POST("/project/undo", { body: {} })));
  }, [view, mutate]);
  const redo = useCallback(() => {
    if (!view?.document.can_redo) return;
    void mutate(() => unwrap(api.POST("/project/redo", { body: {} })));
  }, [view, mutate]);
  return useMemo(() => ({ undo, redo }), [undo, redo]);
}

/** Update (run) a computation cell with its applied parameters. Says when nothing changed;
 * null when it failed (reported in Messages). */
export function useUpdateCell() {
  const { setView, notify, fail } = useProject();
  const { drafts } = useEditor();
  return useCallback(
    async (cellId: string): Promise<UpdateCellResult | null> => {
      if (drafts[cellId]) notify("Hay parámetros sin aplicar: Actualizar usa los aplicados.");
      try {
        const answer = await unwrap(
          api.POST("/project/cells/{cell_id}/update", {
            params: { path: { cell_id: cellId } },
            body: {},
          }),
        );
        setView(answer.view);
        if (!answer.change) {
          notify(
            answer.result.status === "up_to_date"
              ? "Sin cambios: la celda ya estaba actualizada."
              : "Sin cambios: falla por los mismos problemas.",
          );
        }
        return answer;
      } catch (error) {
        fail(error);
        return null;
      }
    },
    [drafts, setView, notify, fail],
  );
}
