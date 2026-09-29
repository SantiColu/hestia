import type { ProjectView } from "@/api/client";
import { cn } from "@/lib/utils";
import { useEditor } from "@/project/editor";
import { useShortcuts } from "@/project/shortcuts";
import { CellEditor } from "../editor/cell-editor";
import { useSchematicActions } from "./actions";
import { BottomPanel } from "./bottom-panel";
import { WorkspaceUiProvider } from "./context";
import { Dock } from "./dock";
import { useEditCommands } from "./edit";
import { Schematic } from "./schematic";
import { TabBar } from "./tabs";
import { Toolbox } from "./toolbox";
import { TopBar } from "./top-bar";

/** Edit shortcuts on the schematic selection, only in the Workflow tab (undo and redo live in
 * the app shell). */
function EditShortcuts() {
  const edit = useEditCommands(useSchematicActions());
  const { active } = useEditor();
  useShortcuts(
    active !== null
      ? {}
      : {
          cut: edit.cut,
          copy: edit.copy,
          paste: () => edit.paste(true),
          duplicate: edit.duplicate,
          rename: edit.rename,
          delete: edit.remove,
          clearSelection: edit.clearSelection,
        },
  );
  return null;
}

/** Open project: top bar, document tabs, Toolbox and schematic (Workflow tab) or a cell
 * editor, right dock and bottom panel. */
export function Workspace({ view }: { view: ProjectView }) {
  const { active } = useEditor();
  return (
    <WorkspaceUiProvider>
      <EditShortcuts />
      <div className="flex h-screen flex-col overflow-hidden">
        <TopBar view={view} />
        <TabBar view={view} />
        <div className="flex min-h-0 flex-1">
          {/* The schematic stays mounted to keep its viewport while another tab is shown. */}
          <div className={cn("flex min-w-0 flex-1", active !== null && "hidden")}>
            <Toolbox />
            <main className="min-w-0 flex-1">
              <Schematic project={view.project} missing={view.missing} />
            </main>
          </div>
          {active !== null && (
            <main className="min-w-0 flex-1 overflow-hidden">
              <CellEditor key={active} cellId={active} view={view} />
            </main>
          )}
          <Dock />
        </div>
        <BottomPanel />
      </div>
    </WorkspaceUiProvider>
  );
}
