import { memo } from "react";
import { Handle, Position as HandlePosition, type Node, type NodeProps } from "@xyflow/react";
import { Pencil } from "lucide-react";
import type { Cell, Link, System } from "@/api/client";
import { StageStatusBadge } from "@/components/feedback/stage-status";
import { cn } from "@/lib/utils";
import { CellMenu, SystemMenu } from "./menus";
import { useWorkspaceUi } from "./context";
import type { SchematicActions } from "./actions";

export type SystemNodeData = {
  system: System;
  cells: Cell[];
  links: Link[];
  actions: SchematicActions;
};

export type SystemNodeType = Node<SystemNodeData, "system">;

export const SYSTEM_WIDTH = 240;

/** A system block: header (drag handle, name, menu) and one row per cell. */
export const SystemNode = memo(function SystemNode({ data }: NodeProps<SystemNodeType>) {
  const { system, cells, links, actions } = data;
  const { selection, select, validTargets } = useWorkspaceUi();
  const systemSelected = selection?.kind === "system" && selection.id === system.id;

  return (
    <div
      style={{ width: SYSTEM_WIDTH }}
      className={cn(
        "rounded-lg border border-border-strong bg-surface text-[13px]",
        systemSelected && "border-primary ring-1 ring-primary",
      )}
    >
      <SystemMenu system={system} actions={actions}>
        <div
          className="system-drag flex h-9 cursor-grab items-center gap-2 border-b border-border px-3"
          onClick={() => select({ kind: "system", id: system.id })}
          onDoubleClick={() => void actions.renameSystem(system.id)}
        >
          <span className="flex-1 truncate font-medium">{system.name}</span>
          <button
            type="button"
            className="nodrag text-subtle-foreground hover:text-foreground"
            aria-label="Renombrar sistema"
            onClick={(event) => {
              event.stopPropagation();
              void actions.renameSystem(system.id);
            }}
          >
            <Pencil className="size-3.5" />
          </button>
        </div>
      </SystemMenu>
      {cells.map((cell) => {
        const selected = selection?.kind === "cell" && selection.id === cell.id;
        const target = validTargets?.has(cell.id) ?? false;
        return (
          <CellMenu key={cell.id} cell={cell} links={links} actions={actions}>
            <div
              data-cell-id={cell.id}
              className={cn(
                "relative flex h-8 items-center gap-2 border-b border-border px-3 last:border-b-0",
                selected && "bg-primary-soft",
                validTargets && !target && "opacity-40",
                target && "outline-1 -outline-offset-1 outline-primary",
              )}
              onClick={() => select({ kind: "cell", id: cell.id })}
            >
              <Handle
                type="target"
                id={`in-${cell.id}`}
                position={HandlePosition.Left}
                className="size-2! border-border-strong! bg-surface-2!"
              />
              <span className="flex-1 truncate">{cell.name}</span>
              <StageStatusBadge status={cell.status} className="h-4 px-1.5 text-[10px]" />
              <Handle
                type="source"
                id={`out-${cell.id}`}
                position={HandlePosition.Right}
                className="size-2! border-border-strong! bg-surface-2!"
              />
            </div>
          </CellMenu>
        );
      })}
    </div>
  );
});
