import { useEffect, useRef } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { api, unwrap } from "@/api/client";
import { isTauri } from "@/lib/native";
import { fileLabel, useEditActions, useFileActions } from "@/project/actions";
import { DialogsProvider, useDialogs } from "@/project/dialogs";
import { useShortcuts } from "@/project/shortcuts";
import { ProjectProvider, useProject } from "@/project/store";
import { Home } from "./home";
import { Workspace } from "./workspace";

function Shell() {
  const { loaded, view } = useProject();
  const file = useFileActions();
  const edit = useEditActions();
  const dialogs = useDialogs();

  useShortcuts({
    new: () => void file.newProject(),
    open: () => void file.openProject(),
    save: () => void file.save(),
    saveAs: () => void file.saveAs(),
    close: () => void file.closeProject(),
    undo: edit.undo,
    redo: edit.redo,
  });

  // Closing the desktop window: ask about unsaved changes and release the file lock.
  const latest = useRef({ view, file, dialogs });
  useEffect(() => {
    latest.current = { view, file, dialogs };
  });
  useEffect(() => {
    if (!isTauri()) return;
    const window = getCurrentWindow();
    const unlisten = window.onCloseRequested(async (event) => {
      const { view: current, file: actions, dialogs: ask } = latest.current;
      if (!current) return;
      event.preventDefault();
      if (current.document.dirty) {
        const choice = await ask.askUnsaved(fileLabel(current));
        if (choice === "cancel") return;
        if (choice === "save" && !(await actions.save())) return;
      }
      await unwrap(api.POST("/project/close", { body: { discard_unsaved: true } })).catch(
        () => null,
      );
      await window.destroy();
    });
    return () => void unlisten.then((stop) => stop());
  }, []);

  if (!loaded) return null;
  return view ? <Workspace view={view} /> : <Home />;
}

export function App() {
  return (
    <ProjectProvider>
      <DialogsProvider>
        <Shell />
      </DialogsProvider>
    </ProjectProvider>
  );
}
