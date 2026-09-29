import { useState, type DragEvent } from "react";
import { ChevronDown, Columns2, GripVertical, Layers } from "lucide-react";
import type { Blueprint } from "@/api/client";
import { SectionLabel } from "@/components/navigation/section-label";
import { cn } from "@/lib/utils";
import { useProject } from "@/project/store";
import { useWorkspaceUi } from "./context";
import { STAGE_ICONS } from "./stage-icons";

const itemClass =
  "group/item flex h-7 cursor-grab items-center gap-2 rounded-lg px-2 text-[13px] text-foreground hover:bg-surface-2 active:cursor-grabbing";

/** Phase tree. Drag a phase (whole system) or a single stage onto the canvas or a cell. */
export function Toolbox() {
  const { catalog } = useProject();
  const { startDrag, endDrag } = useWorkspaceUi();
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(new Set());

  const dragProps = (item: Blueprint) => ({
    draggable: true,
    onDragStart: (event: DragEvent) => {
      event.dataTransfer.setData("text/plain", item.template ?? item.stage ?? "");
      event.dataTransfer.effectAllowed = "copy";
      startDrag(item);
    },
    onDragEnd: endDrag,
  });

  const toggle = (phase: string) =>
    setCollapsed((current) => {
      const next = new Set(current);
      if (!next.delete(phase)) next.add(phase);
      return next;
    });

  return (
    <aside className="flex w-[232px] shrink-0 flex-col border-r border-border bg-surface">
      <header className="flex h-9 shrink-0 items-center border-b border-border px-3">
        <h2 className="text-[13px] font-semibold">Toolbox</h2>
      </header>
      <div className="flex min-h-0 flex-col gap-1.5 overflow-y-auto p-2">
        {catalog?.phases.map((phase) => {
          // "Fase 0 · Viabilidad" → label "Fase 0", description "Viabilidad".
          const [label, description] = phase.name.split(" · ");
          const open = !collapsed.has(phase.phase);
          return (
            <div key={phase.phase} className="flex flex-col">
              <div
                {...dragProps({ template: phase.template, stage: null })}
                className="group/item flex h-[30px] cursor-grab items-center gap-1.5 rounded-lg pr-2 pl-1 hover:bg-surface-2 active:cursor-grabbing"
              >
                <button
                  type="button"
                  aria-label={open ? "Contraer" : "Expandir"}
                  aria-expanded={open}
                  onClick={() => toggle(phase.phase)}
                  className="flex size-3 items-center justify-center text-subtle-foreground"
                >
                  <ChevronDown
                    className={cn("size-3 transition-transform", !open && "-rotate-90")}
                  />
                </button>
                <Layers className="size-3.5 text-muted-foreground" aria-hidden />
                <span className="text-[13px] font-semibold">{label}</span>
                <span className="flex-1 truncate text-xs text-subtle-foreground">
                  {description}
                </span>
                <GripVertical
                  className="hidden size-3.5 text-subtle-foreground group-hover/item:block"
                  aria-hidden
                />
              </div>
              {open && (
                <div className="pb-1 pl-[9px]">
                  <div className="flex flex-col border-l border-border py-0.5 pl-1.5">
                    {catalog.stages
                      .filter((stage) => stage.phase === phase.phase)
                      .map((stage) => {
                        const Icon = STAGE_ICONS[stage.stage];
                        return (
                          <div
                            key={stage.stage}
                            {...dragProps({ template: null, stage: stage.stage })}
                            className={itemClass}
                          >
                            <Icon
                              className="size-3.5 text-muted-foreground group-hover/item:text-foreground"
                              aria-hidden
                            />
                            <span className="flex-1 truncate">{stage.name}</span>
                            <GripVertical
                              className="hidden size-3.5 text-muted-foreground group-hover/item:block"
                              aria-hidden
                            />
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
        <div className="px-1 pt-2.5 pb-0.5">
          <SectionLabel>Post-proceso</SectionLabel>
        </div>
        <div className={cn(itemClass, "cursor-not-allowed opacity-40")} title="Pronto">
          <Columns2 className="size-3.5 text-muted-foreground" aria-hidden />
          Comparación
        </div>
      </div>
      <p className="px-4 py-2 text-[11px] leading-snug text-subtle-foreground">
        Arrastrá una fase para crearla completa, o una etapa sola. Soltala sobre una celda para
        ramificar.
      </p>
    </aside>
  );
}
