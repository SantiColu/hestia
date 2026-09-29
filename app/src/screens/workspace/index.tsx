import type { ProjectView } from "@/api/client";
import { useShortcuts } from "@/project/shortcuts";
import { useSchematicActions } from "./actions";
import { BottomPanel } from "./bottom-panel";
import { WorkspaceUiProvider } from "./context";
import { Dock } from "./dock";
import { useEditCommands } from "./edit";
import { Schematic } from "./schematic";
import { Toolbox } from "./toolbox";
import { TopBar } from "./top-bar";

/** Edit shortcuts on the selection (undo and redo live in the app shell). */
function EditShortcuts() {
  const edit = useEditCommands(useSchematicActions());
  useShortcuts({
    cut: edit.cut,
    copy: edit.copy,
    paste: () => edit.paste(true),
    duplicate: edit.duplicate,
    rename: edit.rename,
    delete: edit.remove,
    clearSelection: edit.clearSelection,
  });
  return null;
}

/** Open project: top bar, Toolbox, schematic, right dock and bottom panel. */
export function Workspace({ view }: { view: ProjectView }) {
  return (
    <WorkspaceUiProvider>
      <EditShortcuts />
      <div className="flex h-screen flex-col overflow-hidden">
        <TopBar view={view} />
        <div className="flex min-h-0 flex-1">
          <Toolbox />
          <main className="min-w-0 flex-1">
            <Schematic project={view.project} />
          </main>
          <Dock />
        </div>
        <BottomPanel />
      </div>
    </WorkspaceUiProvider>
  );
}
