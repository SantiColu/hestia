import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { Lock, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TextField } from "@/components/forms/text-field";

export type UnsavedChoice = "save" | "discard" | "cancel";

type RenameRequest = { title: string; current: string };
type YesNoRequest = { title: string; description: string; confirmLabel: string };

type DialogsValue = {
  askUnsaved: (fileLabel: string) => Promise<UnsavedChoice>;
  /** Resolves true when the user decides to take over the lock. */
  askLocked: (message: string) => Promise<boolean>;
  /** The new name. Null when cancelled. */
  askRename: (request: RenameRequest) => Promise<string | null>;
  /** A yes/no question (e.g. discard unapplied drafts). Resolves true on confirm. */
  askConfirm: (request: YesNoRequest) => Promise<boolean>;
};

type Pending =
  | { kind: "unsaved"; fileLabel: string; resolve: (choice: UnsavedChoice) => void }
  | { kind: "locked"; message: string; resolve: (force: boolean) => void }
  | { kind: "rename"; request: RenameRequest; resolve: (name: string | null) => void }
  | { kind: "yesno"; request: YesNoRequest; resolve: (confirmed: boolean) => void };

const DialogsContext = createContext<DialogsValue | null>(null);

/** Promise-based dialogs shared by file actions and schematic actions. */
export function DialogsProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<Pending | null>(null);

  const askUnsaved = useCallback(
    (fileLabel: string) =>
      new Promise<UnsavedChoice>((resolve) => setPending({ kind: "unsaved", fileLabel, resolve })),
    [],
  );
  const askLocked = useCallback(
    (message: string) =>
      new Promise<boolean>((resolve) => setPending({ kind: "locked", message, resolve })),
    [],
  );
  const askRename = useCallback(
    (request: RenameRequest) =>
      new Promise<string | null>((resolve) => setPending({ kind: "rename", request, resolve })),
    [],
  );

  const askConfirm = useCallback(
    (request: YesNoRequest) =>
      new Promise<boolean>((resolve) => setPending({ kind: "yesno", request, resolve })),
    [],
  );

  const value = useMemo(
    () => ({ askUnsaved, askLocked, askRename, askConfirm }),
    [askUnsaved, askLocked, askRename, askConfirm],
  );

  const close = () => setPending(null);

  return (
    <DialogsContext.Provider value={value}>
      {children}
      {pending?.kind === "unsaved" && (
        <UnsavedDialog
          fileLabel={pending.fileLabel}
          onAnswer={(choice) => {
            close();
            pending.resolve(choice);
          }}
        />
      )}
      {pending?.kind === "locked" && (
        <LockedDialog
          message={pending.message}
          onAnswer={(force) => {
            close();
            pending.resolve(force);
          }}
        />
      )}
      {pending?.kind === "rename" && (
        <RenameDialog
          request={pending.request}
          onAnswer={(name) => {
            close();
            pending.resolve(name);
          }}
        />
      )}
      {pending?.kind === "yesno" && (
        <YesNoDialog
          request={pending.request}
          onAnswer={(confirmed) => {
            close();
            pending.resolve(confirmed);
          }}
        />
      )}
    </DialogsContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- the provider and its hook live together
export function useDialogs(): DialogsValue {
  const value = useContext(DialogsContext);
  if (!value) throw new Error("useDialogs must be used inside DialogsProvider");
  return value;
}

function UnsavedDialog({
  fileLabel,
  onAnswer,
}: {
  fileLabel: string;
  onAnswer: (choice: UnsavedChoice) => void;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onAnswer("cancel")}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cambios sin guardar</DialogTitle>
          <DialogDescription>
            {fileLabel} tiene cambios sin guardar. ¿Guardarlos antes de continuar?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onAnswer("cancel")}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={() => onAnswer("discard")}>
            Descartar cambios
          </Button>
          <Button onClick={() => onAnswer("save")}>
            <Save data-icon="inline-start" />
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LockedDialog({
  message,
  onAnswer,
}: {
  message: string;
  onAnswer: (force: boolean) => void;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onAnswer(false)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="size-4" /> Proyecto bloqueado
          </DialogTitle>
          <DialogDescription>
            {message} Abrirlo igual puede hacer que se pierdan cambios de la otra instancia.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onAnswer(false)}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={() => onAnswer(true)}>
            Abrir de todos modos
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RenameDialog({
  request,
  onAnswer,
}: {
  request: RenameRequest;
  onAnswer: (name: string | null) => void;
}) {
  const [name, setName] = useState(request.current);
  const submit = () => {
    if (name.trim()) onAnswer(name.trim());
  };
  return (
    <Dialog open onOpenChange={(open) => !open && onAnswer(null)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{request.title}</DialogTitle>
        </DialogHeader>
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <TextField
            label="Nombre"
            value={name}
            autoFocus
            onChange={(event) => setName(event.target.value)}
          />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onAnswer(null)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!name.trim()}>
              Renombrar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function YesNoDialog({
  request,
  onAnswer,
}: {
  request: YesNoRequest;
  onAnswer: (confirmed: boolean) => void;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onAnswer(false)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{request.title}</DialogTitle>
          <DialogDescription>{request.description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onAnswer(false)}>
            Cancelar
          </Button>
          <Button variant="destructive" onClick={() => onAnswer(true)}>
            {request.confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
