import { useState, type ReactElement } from "react";
import { api, unwrap, type Blueprint, type Cell, type Link, type System } from "@/api/client";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useProject } from "@/project/store";
import type { SchematicActions } from "./actions";

type MenuProps<T> = { actions: SchematicActions; children: ReactElement } & T;

/** Right-click menu of a system: rename, add stage, update (disabled), duplicate, delete. */
export function SystemMenu({ system, actions, children }: MenuProps<{ system: System }>) {
  const { catalog } = useProject();
  return (
    <ContextMenu>
      <ContextMenuTrigger render={children} />
      <ContextMenuContent>
        <ContextMenuItem onClick={() => void actions.renameSystem(system.id)}>
          Renombrar
        </ContextMenuItem>
        <ContextMenuSub>
          <ContextMenuSubTrigger>Agregar etapa</ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {catalog?.stages.map((stage) => (
              <ContextMenuItem
                key={stage.stage}
                onClick={() => void actions.addCell(system.id, stage.stage)}
              >
                {stage.name}
              </ContextMenuItem>
            ))}
          </ContextMenuSubContent>
        </ContextMenuSub>
        <ContextMenuItem disabled>Actualizar</ContextMenuItem>
        <ContextMenuItem onClick={() => void actions.duplicateSystem(system.id)}>
          Duplicar
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem variant="destructive" onClick={() => void actions.deleteSystem(system.id)}>
          Eliminar
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

/** Right-click menu of a cell: rename, update (disabled), branch, unlink, delete. */
export function CellMenu({
  cell,
  links,
  actions,
  children,
}: MenuProps<{ cell: Cell; links: Link[] }>) {
  const { fail } = useProject();
  // Branch options come from the API when the menu opens (the workflow decides).
  const [options, setOptions] = useState<Blueprint[] | null>(null);
  const touching = links.filter(
    (link) => link.source_cell_id === cell.id || link.target_cell_id === cell.id,
  );

  const loadOptions = async () => {
    setOptions(null);
    try {
      setOptions(
        await unwrap(
          api.GET("/project/cells/{cell_id}/branch-options", {
            params: { path: { cell_id: cell.id } },
          }),
        ),
      );
    } catch (error) {
      fail(error);
      setOptions([]);
    }
  };

  return (
    <ContextMenu onOpenChange={(open) => open && void loadOptions()}>
      <ContextMenuTrigger render={children} />
      <ContextMenuContent>
        <ContextMenuItem onClick={() => void actions.renameCell(cell.id)}>
          Renombrar
        </ContextMenuItem>
        <ContextMenuItem disabled>Actualizar</ContextMenuItem>
        <ContextMenuSub>
          <ContextMenuSubTrigger>Ramificar</ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {options === null && <ContextMenuLabel>Cargando…</ContextMenuLabel>}
            {options?.length === 0 && <ContextMenuLabel>Nada para ramificar</ContextMenuLabel>}
            {options?.map((option) => (
              <ContextMenuItem
                key={option.template ?? option.stage}
                onClick={() => void actions.branch(cell.id, option)}
              >
                {actions.blueprintName(option)}
              </ContextMenuItem>
            ))}
          </ContextMenuSubContent>
        </ContextMenuSub>
        <ContextMenuSub>
          <ContextMenuSubTrigger disabled={touching.length === 0}>
            Desvincular
          </ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {touching.map((link) => (
              <ContextMenuItem key={link.id} onClick={() => void actions.unlink(link)}>
                {actions.cellName(link.source_cell_id)} → {actions.cellName(link.target_cell_id)}
              </ContextMenuItem>
            ))}
          </ContextMenuSubContent>
        </ContextMenuSub>
        <ContextMenuSeparator />
        <ContextMenuItem variant="destructive" onClick={() => void actions.deleteCell(cell.id)}>
          Eliminar
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
