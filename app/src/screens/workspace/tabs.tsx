import { Workflow, X } from "lucide-react";
import type { ProjectView } from "@/api/client";
import { StageStatusIcon } from "@/components/feedback/stage-status";
import { cn } from "@/lib/utils";
import { useEditor } from "@/project/editor";

const tabClass =
  "group/tab flex h-8 max-w-[260px] shrink-0 items-center gap-1.5 border-r border-border px-3 text-[13px] text-muted-foreground hover:text-foreground";

/** Document tabs under the top bar: Workflow (fixed) and one per open cell. */
export function TabBar({ view }: { view: ProjectView }) {
  const { tabs, active, activate, close, drafts } = useEditor();
  const { cells, systems } = view.project;

  return (
    <nav
      aria-label="Pestañas"
      className="flex h-8 shrink-0 items-stretch overflow-x-auto border-b border-border bg-surface"
    >
      <button
        type="button"
        className={cn(tabClass, active === null && "bg-background text-foreground")}
        onClick={() => activate(null)}
      >
        <Workflow className="size-3.5" aria-hidden /> Workflow
      </button>
      {tabs.map((id) => {
        const cell = cells.find((c) => c.id === id);
        if (!cell) return null;
        const system = systems.find((s) => s.id === cell.system_id);
        const title = `${cell.name} · ${system?.name ?? ""}`;
        const selected = active === id;
        return (
          <div
            key={id}
            role="tab"
            aria-selected={selected}
            title={title}
            className={cn(
              tabClass,
              "cursor-pointer pr-1.5",
              selected && "bg-background text-foreground",
            )}
            onClick={() => activate(id)}
            onAuxClick={(event) => event.button === 1 && void close(id)}
          >
            <StageStatusIcon status={cell.status} />
            <span className="truncate">{title}</span>
            {drafts[id] && (
              <span
                className="size-1.5 shrink-0 rounded-full bg-muted-foreground"
                title="Borrador sin aplicar"
                aria-label="Borrador sin aplicar"
              />
            )}
            <button
              type="button"
              aria-label="Cerrar pestaña"
              title="Cerrar (Ctrl+W)"
              className="flex size-5 items-center justify-center rounded-md text-subtle-foreground hover:bg-surface-2 hover:text-foreground"
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
