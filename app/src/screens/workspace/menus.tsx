import { useState, type ReactElement } from "react";
import {
  ClipboardPaste,
  Copy,
  CopyPlus,
  GitBranchPlus,
  Pencil,
  Plus,
  RefreshCw,
  Scissors,
  Trash2,
  Unlink,
} from "lucide-react";
import { api, unwrap, type Blueprint, type Cell, type Link, type System } from "@/api/client";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuShortcut,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useUpdateCell } from "@/project/actions";
import { isComputation } from "@/project/lookup";
import { useProject } from "@/project/store";
import type { SchematicActions } from "./actions";
import { useWorkspaceUi } from "./context";
import { includesTarget, type Target } from "./target";
import { STAGE_ICONS } from "./stage-icons";

type MenuProps<T> = { actions: SchematicActions; children: ReactElement } & T;

/**
 * Right-clicking an item outside the selection selects it (the shortcuts shown act on the
 * selection); inside a multiple selection, the selection stays. Also checks whether the
 * clipboard holds something to paste. Returns what cut, copy and delete act on.
 */
function useMenuTargets(target: Target) {
  const { selection, select, checkClipboard } = useWorkspaceUi();
  const inSelection = includesTarget(selection, target);
  const onOpen = (open: boolean) => {
    if (!open) return;
    if (!inSelection) select(target);
    void checkClipboard();
  };
  return { targets: inSelection ? selection : [target], onOpen };
}

/** Cut and copy (`targets`), paste (into `systemId`) and duplicate (`target`), as in the Edit
 * menu. */
function ClipboardItems({
  target,
  targets,
  systemId,
  actions,
}: {
  target: Target;
  targets: readonly Target[];
  systemId: string;
  actions: SchematicActions;
}) {
  const { canPaste } = useWorkspaceUi();
  return (
    <>
      <ContextMenuItem onClick={() => void actions.cut(targets)}>
        <Scissors /> Cortar <ContextMenuShortcut>Ctrl+X</ContextMenuShortcut>
      </ContextMenuItem>
      <ContextMenuItem onClick={() => void actions.copy(targets)}>
        <Copy /> Copiar <ContextMenuShortcut>Ctrl+C</ContextMenuShortcut>
      </ContextMenuItem>
      <ContextMenuItem
        disabled={!canPaste}
        onClick={() => void actions.paste({ targetSystemId: systemId })}
      >
        <ClipboardPaste /> Pegar <ContextMenuShortcut>Ctrl+V</ContextMenuShortcut>
      </ContextMenuItem>
      <ContextMenuItem disabled={targets.length > 1} onClick={() => void actions.duplicate(target)}>
        <CopyPlus /> Duplicar <ContextMenuShortcut>Ctrl+D</ContextMenuShortcut>
      </ContextMenuItem>
    </>
  );
}

/** Right-click menu of a system: rename, add stage, update (disabled), clipboard, delete. */
export function SystemMenu({ system, actions, children }: MenuProps<{ system: System }>) {
  const { catalog } = useProject();
  const target: Target = { kind: "system", id: system.id };
  const { targets, onOpen } = useMenuTargets(target);
  return (
    <ContextMenu onOpenChange={onOpen}>
      <ContextMenuTrigger render={children} />
      <ContextMenuContent>
        <ContextMenuItem onClick={() => void actions.renameSystem(system.id)}>
          <Pencil /> Renombrar <ContextMenuShortcut>F2</ContextMenuShortcut>
        </ContextMenuItem>
        <ContextMenuSub>
          <ContextMenuSubTrigger>
            <Plus /> Agregar etapa
          </ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {catalog?.stages.map((stage) => {
              const Icon = STAGE_ICONS[stage.stage];
              return (
                <ContextMenuItem
                  key={stage.stage}
                  onClick={() => void actions.addCell(system.id, stage.stage)}
                >
                  <Icon /> {stage.name}
                </ContextMenuItem>
              );
            })}
          </ContextMenuSubContent>
        </ContextMenuSub>
        <ContextMenuItem disabled>
          <RefreshCw /> Actualizar
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ClipboardItems target={target} targets={targets} systemId={system.id} actions={actions} />
        <ContextMenuSeparator />
        <ContextMenuItem variant="destructive" onClick={() => void actions.remove(targets)}>
          <Trash2 /> Eliminar <ContextMenuShortcut>Supr</ContextMenuShortcut>
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

/** Right-click menu of a cell: rename, update (computation stages), branch, unlink, clipboard,
 * delete. */
export function CellMenu({
  cell,
  links,
  actions,
  children,
}: MenuProps<{ cell: Cell; links: Link[] }>) {
  const { catalog, fail } = useProject();
  const updateCell = useUpdateCell();
  // Branch options come from the API when the menu opens (the workflow decides).
  const [options, setOptions] = useState<Blueprint[] | null>(null);
  const target: Target = { kind: "cell", id: cell.id };
  const { targets, onOpen } = useMenuTargets(target);
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
    <ContextMenu
      onOpenChange={(open) => {
        onOpen(open);
        if (open) void loadOptions();
      }}
    >
      <ContextMenuTrigger render={children} />
      <ContextMenuContent>
        <ContextMenuItem onClick={() => void actions.renameCell(cell.id)}>
          <Pencil /> Renombrar <ContextMenuShortcut>F2</ContextMenuShortcut>
        </ContextMenuItem>
        <ContextMenuItem
          disabled={!isComputation(catalog, cell.stage)}
          onClick={() => void updateCell(cell.id)}
        >
          <RefreshCw /> Actualizar
        </ContextMenuItem>
        <ContextMenuSub>
          <ContextMenuSubTrigger>
            <GitBranchPlus /> Ramificar
          </ContextMenuSubTrigger>
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
            <Unlink /> Desvincular
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
        <ClipboardItems
          target={target}
          targets={targets}
          systemId={cell.system_id}
          actions={actions}
        />
        <ContextMenuSeparator />
        <ContextMenuItem variant="destructive" onClick={() => void actions.remove(targets)}>
          <Trash2 /> Eliminar <ContextMenuShortcut>Supr</ContextMenuShortcut>
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
