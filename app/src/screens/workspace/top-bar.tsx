import {
  Bot,
  ClipboardPaste,
  Columns2,
  Copy,
  CopyPlus,
  FileOutput,
  FilePlus,
  FileText,
  FolderOpen,
  History,
  Pencil,
  Redo2,
  RefreshCw,
  Save,
  SaveAll,
  Scissors,
  Search,
  SquareDashedMousePointer,
  Trash2,
  Undo2,
  X,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ProjectView } from "@/api/client";
import { fileLabel, useFileActions } from "@/project/actions";
import { useProject } from "@/project/store";
import { useSchematicActions } from "./actions";
import { useWorkspaceUi } from "./context";
import { useEditCommands } from "./edit";

const menuTrigger =
  "flex h-7 items-center rounded-lg px-2 text-[13px] text-muted-foreground hover:bg-surface-2 hover:text-foreground aria-expanded:bg-surface-2 aria-expanded:text-foreground disabled:pointer-events-none disabled:opacity-40";

/** «Deshacer renombrar sistema»: the verb plus the operation's label from the API. */
function withLabel(verb: string, label: string | null): string {
  return label ? `${verb} ${label}` : verb;
}

const divider = <span className="h-4 w-px shrink-0 bg-border" aria-hidden />;

/** Future tools: visible, disabled until the features exist. */
const TOOLS: [LucideIcon, string][] = [
  [Search, "Paleta de comandos (Ctrl+K)"],
  [Columns2, "Comparar"],
  [FileText, "Informe"],
  [FileOutput, "Exportar a NX"],
  [Bot, "Stefan"],
];

export function TopBar({ view }: { view: ProjectView }) {
  const { recents } = useProject();
  const file = useFileActions();
  const edit = useEditCommands(useSchematicActions());
  const { checkClipboard } = useWorkspaceUi();
  const { document, project } = view;
  const outdated = project.cells.filter((cell) => cell.status === "outdated").length;

  return (
    <header className="flex h-11 shrink-0 items-center gap-2.5 border-b border-border bg-surface pr-2.5 pl-3.5">
      <img src="/brand/hestia-mark.svg" alt="Hestia" className="h-6 w-[21px]" />
      <nav className="flex items-center px-1.5">
        <DropdownMenu>
          <DropdownMenuTrigger className={menuTrigger}>Archivo</DropdownMenuTrigger>
          <DropdownMenuContent className="w-[260px]" sideOffset={4}>
            <DropdownMenuItem onClick={() => void file.newProject()}>
              <FilePlus /> Nuevo proyecto <DropdownMenuShortcut>Ctrl+N</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => void file.openProject()}>
              <FolderOpen /> Abrir… <DropdownMenuShortcut>Ctrl+O</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger disabled={recents.length === 0}>
                <History /> Recientes
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
              <Save /> Guardar <DropdownMenuShortcut>Ctrl+S</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => void file.saveAs()}>
              <SaveAll /> Guardar como… <DropdownMenuShortcut>Ctrl+Shift+S</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled>
              <FileOutput /> Exportar a NX… <DropdownMenuShortcut>pronto</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem disabled>
              <FileText /> Generar informe… <DropdownMenuShortcut>pronto</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => void file.closeProject()}>
              <X /> Cerrar proyecto <DropdownMenuShortcut>Ctrl+Shift+W</DropdownMenuShortcut>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu onOpenChange={(open) => open && void checkClipboard()}>
          <DropdownMenuTrigger className={menuTrigger}>Editar</DropdownMenuTrigger>
          <DropdownMenuContent className="w-[280px]" sideOffset={4}>
            <DropdownMenuItem
              disabled={!document.can_undo}
              title={document.undo_summary ?? undefined}
              onClick={edit.undo}
            >
              <Undo2 />
              <span className="truncate">{withLabel("Deshacer", document.undo_label)}</span>
              <DropdownMenuShortcut>Ctrl+Z</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={!document.can_redo}
              title={document.redo_summary ?? undefined}
              onClick={edit.redo}
            >
              <Redo2 />
              <span className="truncate">{withLabel("Rehacer", document.redo_label)}</span>
              <DropdownMenuShortcut>Ctrl+Shift+Z</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled={!edit.target} onClick={edit.cut}>
              <Scissors /> Cortar <DropdownMenuShortcut>Ctrl+X</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!edit.target} onClick={edit.copy}>
              <Copy /> Copiar <DropdownMenuShortcut>Ctrl+C</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!edit.canPaste} onClick={() => edit.paste(false)}>
              <ClipboardPaste /> Pegar <DropdownMenuShortcut>Ctrl+V</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!edit.target} onClick={edit.duplicate}>
              <CopyPlus /> Duplicar <DropdownMenuShortcut>Ctrl+D</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled={!edit.target} onClick={edit.rename}>
              <Pencil /> Renombrar <DropdownMenuShortcut>F2</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!edit.target} onClick={edit.clearSelection}>
              <SquareDashedMousePointer /> Deseleccionar{" "}
              <DropdownMenuShortcut>Esc</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" disabled={!edit.target} onClick={edit.remove}>
              <Trash2 /> Eliminar <DropdownMenuShortcut>Supr</DropdownMenuShortcut>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        {["Ver", "Proyecto", "Ayuda"].map((label) => (
          <button key={label} type="button" disabled className={menuTrigger}>
            {label}
          </button>
        ))}
      </nav>
      {divider}

      <div className="flex h-7 items-center gap-1.5 pl-2">
        <span
          className="text-[13px] font-semibold text-foreground"
          title={document.path ?? "Sin guardar"}
        >
          {fileLabel(view)}
        </span>
        {document.dirty && (
          <>
            <span
              className="size-1.5 rounded-full bg-muted-foreground"
              title="Cambios sin guardar"
              aria-label="Cambios sin guardar"
            />
            <Button
              size="icon-sm"
              variant="ghost"
              title="Guardar (Ctrl+S)"
              aria-label="Guardar"
              onClick={() => void file.save()}
            >
              <Save />
            </Button>
          </>
        )}
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-0.5">
        {TOOLS.map(([Icon, label]) => (
          <Button
            key={label}
            size="icon-sm"
            variant="ghost"
            disabled
            title={`${label} (pronto)`}
            aria-label={label}
            className="text-subtle-foreground disabled:opacity-40"
          >
            <Icon />
          </Button>
        ))}
      </div>
      {divider}
      {outdated > 0 && (
        <span className="inline-flex items-center gap-1.5 rounded-lg bg-warn-soft px-2 py-[3px] text-xs font-medium text-warn tabular-nums">
          <span className="size-1.5 rounded-full bg-warn" aria-hidden />
          {outdated} desactualizada{outdated === 1 ? "" : "s"}
        </span>
      )}
      <Button size="sm" disabled title="Requiere cálculo (pronto)">
        <RefreshCw data-icon="inline-start" /> Actualizar todo
      </Button>
    </header>
  );
}
