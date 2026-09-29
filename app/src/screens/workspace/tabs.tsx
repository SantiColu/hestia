import { Workflow, X } from "lucide-react";
import type { ProjectView } from "@/api/client";
import { StageStatusIcon } from "@/components/feedback/stage-status";
import { cn } from "@/lib/utils";
import { useEditor } from "@/project/editor";
import { findCell, findSystem } from "@/project/lookup";

/** `DocTab` / `DocTab/Active` in `hestia.lib.pen`. */
const tabClass = (selected: boolean) =>
  cn(
    "group/tab flex h-9 max-w-75 shrink-0 cursor-pointer items-center gap-2 border-r border-border pr-2.5 pl-3 text-ui text-muted-foreground hover:text-foreground",
    selected && "border-b-2 border-b-primary bg-background pt-0.5 font-medium text-foreground",
  );

/** Document tabs under the top bar: Workflow (fixed) and one per open cell. */
export function TabBar({ view }: { view: ProjectView }) {
  const { tabs, active, activate, close, drafts } = useEditor();
  const { project } = view;

  return (
    <nav
      aria-label="Pestañas"
      className="flex h-9.25 shrink-0 items-end overflow-x-auto border-b border-border bg-surface"
    >
      <button
        type="button"
        role="tab"
        aria-selected={active === null}
        className={tabClass(active === null)}
        onClick={() => activate(null)}
      >
        <Workflow className="size-3.5 text-subtle-foreground" aria-hidden /> Workflow
      </button>
      {tabs.map((id) => {
        const cell = findCell(project, id);
        if (!cell) return null;
        const system = findSystem(project, cell.system_id)?.name ?? "";
        const selected = active === id;
        return (
          <div
            key={id}
            role="tab"
            aria-selected={selected}
            title={`${cell.name} · ${system}`}
            className={tabClass(selected)}
            onClick={() => activate(id)}
            onAuxClick={(event) => event.button === 1 && void close(id)}
          >
            <StageStatusIcon status={cell.status} />
            <span className="truncate">{cell.name}</span>
            <span className="truncate text-xs font-normal text-subtle-foreground">{system}</span>
            {drafts[id] && (
              <span
                className="size-1.5 shrink-0 rounded-full bg-primary"
                title="Borrador sin aplicar"
                aria-label="Borrador sin aplicar"
              />
            )}
            <button
              type="button"
              aria-label="Cerrar pestaña"
              title="Cerrar (Ctrl+W)"
              className={cn(
                "flex size-4.5 shrink-0 items-center justify-center rounded-lg text-subtle-foreground hover:bg-surface-2 hover:text-foreground",
                selected && "text-muted-foreground",
              )}
              onClick={(event) => {
                event.stopPropagation();
                void close(id);
              }}
            >
              <X className="size-3" />
            </button>
          </div>
        );
      })}
    </nav>
  );
}
