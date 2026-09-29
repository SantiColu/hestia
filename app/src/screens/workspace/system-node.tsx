import { memo, type MouseEvent } from "react";
import { Handle, Position as HandlePosition, type Node, type NodeProps } from "@xyflow/react";
import { Ellipsis, GitBranchPlus, Pencil, TriangleAlert } from "lucide-react";
import type { Cell, Link, StageType, System } from "@/api/client";
import { StageStatusIcon } from "@/components/feedback/stage-status";
import { cn } from "@/lib/utils";
import { useEditor } from "@/project/editor";
import { CellMenu, SystemMenu } from "./menus";
import { useWorkspaceUi } from "./context";
import type { SchematicActions } from "./actions";

export type SystemNodeData = {
  system: System;
  cells: Cell[];
  links: Link[];
  /** Required stage types missing from each cell's context (from the API). */
  missing: Record<string, StageType[]>;
  actions: SchematicActions;
};

export type SystemNodeType = Node<SystemNodeData, "system">;

export const SYSTEM_WIDTH = 224;

const headerButton =
  "nodrag flex size-6 items-center justify-center rounded-lg text-subtle-foreground hover:bg-border hover:text-foreground";

const handleClass =
  "size-2! border-border-strong! bg-surface-2! opacity-0 transition-opacity group-hover/cell:opacity-100";

/** Open the system's context menu from the header's ellipsis button, below the button. */
function openMenuFrom(event: MouseEvent<HTMLButtonElement>) {
  event.stopPropagation();
  const rect = event.currentTarget.getBoundingClientRect();
  event.currentTarget.dispatchEvent(
    new globalThis.MouseEvent("contextmenu", {
      bubbles: true,
      cancelable: true,
      clientX: rect.left,
      clientY: rect.bottom + 4,
    }),
  );
}

/** A system block: header (drag handle, name, rename, menu) and one row per cell. */
export const SystemNode = memo(function SystemNode({ data }: NodeProps<SystemNodeType>) {
  const { system, cells, links, missing, actions } = data;
  const { selection, select, validTargets } = useWorkspaceUi();
  const editor = useEditor();
  const systemSelected = selection?.kind === "system" && selection.id === system.id;

  return (
    <div
      style={{ width: SYSTEM_WIDTH }}
      className={cn(
        "overflow-hidden rounded-lg border border-border-strong bg-surface",
        systemSelected && "border-primary",
      )}
    >
      <SystemMenu system={system} actions={actions}>
        <div
          className="system-drag flex h-8 cursor-grab items-center gap-1 border-b border-border-strong bg-surface-2 pr-1 pl-2.5"
          onClick={() => select({ kind: "system", id: system.id })}
          onDoubleClick={() => void actions.renameSystem(system.id)}
        >
          <span className="flex-1 truncate text-[13px] font-semibold">{system.name}</span>
          <button
            type="button"
            className={headerButton}
            aria-label="Renombrar sistema"
            title="Renombrar"
            onClick={(event) => {
              event.stopPropagation();
              void actions.renameSystem(system.id);
            }}
          >
            <Pencil className="size-3.5" />
          </button>
          <button
            type="button"
            className={headerButton}
            aria-label="Menú del sistema"
            title="Más acciones"
            onClick={openMenuFrom}
          >
            <Ellipsis className="size-3.5" />
          </button>
        </div>
      </SystemMenu>
      {cells.map((cell) => {
        const selected = selection?.kind === "cell" && selection.id === cell.id;
        const target = validTargets?.has(cell.id) ?? false;
        const cellMissing = missing[cell.id];
        return (
          <CellMenu key={cell.id} cell={cell} links={links} actions={actions}>
            <div
              data-cell-id={cell.id}
              className={cn(
                "group/cell relative flex h-[30px] items-center gap-2 border-b border-border px-2.5 last:border-b-0",
                selected && "bg-primary-soft outline-1 -outline-offset-1 outline-primary",
                validTargets && !target && "opacity-40",
                target && "outline-1 -outline-offset-1 outline-primary",
              )}
              onClick={() => select({ kind: "cell", id: cell.id })}
              onDoubleClick={() => editor.open(cell.id)}
            >
              <Handle
                type="target"
                id={`in-${cell.id}`}
                position={HandlePosition.Left}
                className={handleClass}
              />
              <span className="flex-1 truncate text-[13px] font-medium">{cell.name}</span>
              {cellMissing && !target && (
                <TriangleAlert
                  className="size-3.5 shrink-0 text-warn"
                  aria-label="Contexto incompleto"
                >
                  <title>
                    {`Falta en su contexto: ${cellMissing.map(actions.stageName).join(", ")}`}
                  </title>
                </TriangleAlert>
              )}
              {target ? (
                <GitBranchPlus
                  className="size-3.5 shrink-0 text-primary"
                  aria-label="Destino válido"
                />
              ) : (
                <StageStatusIcon status={cell.status} />
              )}
              <Handle
                type="source"
                id={`out-${cell.id}`}
                position={HandlePosition.Right}
                className={handleClass}
              />
            </div>
          </CellMenu>
        );
      })}
    </div>
  );
});
