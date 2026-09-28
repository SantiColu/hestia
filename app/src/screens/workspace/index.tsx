import type { ProjectView } from "@/api/client";
import { BottomPanel } from "./bottom-panel";
import { WorkspaceUiProvider } from "./context";
import { Dock } from "./dock";
import { Schematic } from "./schematic";
import { Toolbox } from "./toolbox";
import { TopBar } from "./top-bar";

/** Open project: top bar, Toolbox, schematic, right dock and bottom panel. */
export function Workspace({ view }: { view: ProjectView }) {
  return (
    <WorkspaceUiProvider>
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
