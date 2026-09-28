import { Bot, Command, FileOutput, GitCompare, RefreshCw, Save, ScrollText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ProjectView } from "@/api/client";
import { fileLabel, useEditActions, useFileActions } from "@/project/actions";
import { useProject } from "@/project/store";

const menuTrigger =
  "h-7 rounded-md px-2 text-[13px] text-muted-foreground hover:bg-surface-2 hover:text-foreground aria-expanded:bg-surface-2 disabled:pointer-events-none disabled:opacity-40";

export function TopBar({ view }: { view: ProjectView }) {
  const { recents } = useProject();
  const file = useFileActions();
  const edit = useEditActions();
  const { document, project } = view;
  const outdated = project.cells.filter((cell) => cell.status === "outdated").length;

  return (
    <header className="flex h-10 shrink-0 items-center gap-1 border-b border-border bg-surface px-2">
      <img src="/favicon.svg" alt="Hestia" className="mr-1 size-5" />
      <DropdownMenu>
        <DropdownMenuTrigger className={menuTrigger}>Archivo</DropdownMenuTrigger>
        <DropdownMenuContent className="w-64">
          <DropdownMenuItem onClick={() => void file.newProject()}>
            Nuevo <DropdownMenuShortcut>Ctrl+N</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => void file.openProject()}>
            Abrir… <DropdownMenuShortcut>Ctrl+O</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger disabled={recents.length === 0}>
              Recientes
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="w-72">
              {recents.map((recent) => (
                <DropdownMenuItem
                  key={recent.path}
                  disabled={!recent.exists}
                  title={recent.path}
                  onClick={() => void file.openProject(recent.path)}
                >
                  <span className="truncate">{recent.name}</span>
                  {!recent.exists && (
                    <DropdownMenuShortcut className="text-error">no existe</DropdownMenuShortcut>
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => void file.save()}>
            Guardar <DropdownMenuShortcut>Ctrl+S</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => void file.saveAs()}>
            Guardar como… <DropdownMenuShortcut>Ctrl+Shift+S</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => void file.closeProject()}>
            Cerrar <DropdownMenuShortcut>Ctrl+W</DropdownMenuShortcut>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <DropdownMenu>
        <DropdownMenuTrigger className={menuTrigger}>Editar</DropdownMenuTrigger>
        <DropdownMenuContent className="w-72">
          <DropdownMenuItem disabled={!document.can_undo} onClick={edit.undo}>
            Deshacer <DropdownMenuShortcut>Ctrl+Z</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuItem disabled={!document.can_redo} onClick={edit.redo}>
            Rehacer <DropdownMenuShortcut>Ctrl+Shift+Z</DropdownMenuShortcut>
          </DropdownMenuItem>
          {document.undo_summary && (
            <DropdownMenuLabel className="truncate font-normal">
              Último: {document.undo_summary}
            </DropdownMenuLabel>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {["Ver", "Proyecto", "Ayuda"].map((label) => (
        <button key={label} type="button" disabled className={menuTrigger}>
          {label}
        </button>
      ))}

      <div className="mx-auto flex items-center gap-2 text-[13px]">
        <span className="font-medium" title={document.path ?? "Sin guardar"}>
          {fileLabel(view)}
        </span>
        {document.dirty && (
          <>
            <span
              className="text-warn"
              title="Cambios sin guardar"
              aria-label="Cambios sin guardar"
            >
              ●
            </span>
            <Button
              size="icon-xs"
              variant="ghost"
              title="Guardar (Ctrl+S)"
              onClick={() => void file.save()}
            >
              <Save />
            </Button>
          </>
        )}
      </div>

      {/* Future tools: visible, disabled until the features exist. */}
      <Button size="sm" variant="ghost" disabled title="Paleta de comandos (pronto)">
        <Command data-icon="inline-start" /> Ctrl+K
      </Button>
      <Button size="icon-sm" variant="ghost" disabled title="Comparar (pronto)">
        <GitCompare />
      </Button>
      <Button size="icon-sm" variant="ghost" disabled title="Informe (pronto)">
        <ScrollText />
      </Button>
      <Button size="icon-sm" variant="ghost" disabled title="Exportar a NX (pronto)">
        <FileOutput />
      </Button>
      <Button size="icon-sm" variant="ghost" disabled title="Stefan (pronto)">
        <Bot />
      </Button>
      <span className="ml-2 font-mono text-[11px] text-subtle-foreground tabular-nums">
        {outdated} desactualizadas
      </span>
      <Button size="sm" variant="secondary" disabled title="Requiere cálculo (pronto)">
        <RefreshCw data-icon="inline-start" /> Actualizar todo
      </Button>
    </header>
  );
}
