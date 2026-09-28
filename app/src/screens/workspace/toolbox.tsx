import type { DragEvent } from "react";
import { GripVertical, Layers, Square, SquareStack } from "lucide-react";
import type { Blueprint } from "@/api/client";
import { SectionLabel } from "@/components/navigation/section-label";
import { cn } from "@/lib/utils";
import { useProject } from "@/project/store";
import { useWorkspaceUi } from "./context";

/** Phase tree. Drag a phase (whole system) or a single stage onto the canvas or a cell. */
export function Toolbox() {
  const { catalog } = useProject();
  const { startDrag, endDrag } = useWorkspaceUi();

  const dragProps = (item: Blueprint) => ({
    draggable: true,
    onDragStart: (event: DragEvent) => {
      event.dataTransfer.setData("text/plain", item.template ?? item.stage ?? "");
      event.dataTransfer.effectAllowed = "copy";
      startDrag(item);
    },
    onDragEnd: endDrag,
  });

  const itemClass =
    "flex h-7 cursor-grab items-center gap-2 rounded-md px-2 text-[13px] text-muted-foreground hover:bg-surface-2 hover:text-foreground active:cursor-grabbing";

  return (
    <aside className="flex w-56 shrink-0 flex-col gap-3 overflow-y-auto border-r border-border bg-surface p-3">
      <SectionLabel>Toolbox</SectionLabel>
      {catalog?.phases.map((phase) => (
        <div key={phase.phase} className="flex flex-col gap-0.5">
          <div
            {...dragProps({ template: phase.template, stage: null })}
            className={cn(itemClass, "font-medium text-foreground")}
          >
            <SquareStack className="size-3.5 text-subtle-foreground" aria-hidden />
            <span className="flex-1 truncate">{phase.name}</span>
            <GripVertical className="size-3.5 text-subtle-foreground" aria-hidden />
          </div>
          <div className="ml-3.5 flex flex-col gap-0.5 border-l border-border pl-2">
            {catalog.stages
              .filter((stage) => stage.phase === phase.phase)
              .map((stage) => (
                <div
                  key={stage.stage}
                  {...dragProps({ template: null, stage: stage.stage })}
                  className={itemClass}
                >
                  <Square className="size-3 text-subtle-foreground" aria-hidden />
                  <span className="truncate">{stage.name}</span>
                </div>
              ))}
          </div>
        </div>
      ))}
      <SectionLabel className="mt-2">Post-proceso</SectionLabel>
      <div className={cn(itemClass, "cursor-not-allowed opacity-40")} title="Pronto">
        <Layers className="size-3.5" aria-hidden />
        Comparación
      </div>
    </aside>
  );
}
