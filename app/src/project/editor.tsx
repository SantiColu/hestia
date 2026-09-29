import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { JsonObject } from "@/lib/json";
import { useDialogs } from "./dialogs";
import { useProject } from "./store";

/**
 * Document tabs and unapplied drafts (docs/ux-workspace.md, «Editor de celda»).
 *
 * UI state only: the open tabs are remembered per project in this browser (not in the
 * `.hestia`), and a draft lives here until it is applied or discarded (ADR 0017).
 */
type EditorValue = {
  /** Open cell tabs, in order. Workflow is always first and is not listed. */
  tabs: string[];
  /** Active cell tab; null is Workflow. */
  active: string | null;
  open: (cellId: string) => void;
  activate: (cellId: string | null) => void;
  /** Close a cell tab; asks before discarding its draft. */
  close: (cellId: string) => Promise<void>;
  closeActive: () => void;
  drafts: Readonly<Record<string, JsonObject>>;
  setDraft: (cellId: string, draft: JsonObject | null) => void;
  /** Ask before losing every unapplied draft (closing or replacing the project). */
  confirmDiscardDrafts: () => Promise<boolean>;
};

const EditorContext = createContext<EditorValue | null>(null);

type Stored = { tabs: string[]; active: string | null };

function storageKey(projectId: string): string {
  return `hestia.tabs.${projectId}`;
}

function load(projectId: string): Stored {
  try {
    const raw = window.localStorage.getItem(storageKey(projectId));
    const parsed = raw ? (JSON.parse(raw) as Partial<Stored>) : {};
    return { tabs: parsed.tabs ?? [], active: parsed.active ?? null };
  } catch {
    return { tabs: [], active: null };
  }
}

function store(projectId: string, value: Stored) {
  try {
    window.localStorage.setItem(storageKey(projectId), JSON.stringify(value));
  } catch {
    // Remembering tabs is a convenience; ignore storage errors.
  }
}

export function EditorProvider({ children }: { children: ReactNode }) {
  const { view, notify } = useProject();
  const dialogs = useDialogs();
  const projectId = view?.project.id ?? null;
  const [state, setState] = useState<Stored & { projectId: string | null }>({
    projectId: null,
    tabs: [],
    active: null,
  });
  const [drafts, setDrafts] = useState<Record<string, JsonObject>>({});

  // Another project: restore its tabs and drop the drafts of the previous one.
  if (state.projectId !== projectId) {
    setState({ projectId, ...(projectId ? load(projectId) : { tabs: [], active: null }) });
    setDrafts({});
  }

  useEffect(() => {
    if (state.projectId) store(state.projectId, { tabs: state.tabs, active: state.active });
  }, [state]);

  // A cell that no longer exists (deleted, undone, removed by an agent) closes its tab.
  const cells = view?.project.cells;
  const notified = useRef(new Set<string>());
  useEffect(() => {
    if (!cells) return;
    const alive = new Set(cells.map((cell) => cell.id));
    const gone = state.tabs.filter((id) => !alive.has(id));
    if (gone.length === 0) return;
    for (const id of gone) {
      if (notified.current.has(id)) continue;
      notified.current.add(id);
      notify("Se cerró una pestaña: su celda ya no existe.");
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reacting to the API's view
    setState((current) => ({
      ...current,
      tabs: current.tabs.filter((id) => alive.has(id)),
      active: current.active && alive.has(current.active) ? current.active : null,
    }));
    setDrafts((current) =>
      Object.fromEntries(Object.entries(current).filter(([id]) => alive.has(id))),
    );
  }, [cells, state.tabs, notify]);

  const open = useCallback((cellId: string) => {
    setState((current) => ({
      ...current,
      tabs: current.tabs.includes(cellId) ? current.tabs : [...current.tabs, cellId],
      active: cellId,
    }));
  }, []);

  const activate = useCallback((cellId: string | null) => {
    setState((current) => ({ ...current, active: cellId }));
  }, []);

  const setDraft = useCallback((cellId: string, draft: JsonObject | null) => {
    setDrafts((current) => {
      const next = { ...current };
      if (draft) next[cellId] = draft;
      else delete next[cellId];
      return next;
    });
  }, []);

  const draftsRef = useRef(drafts);
  useEffect(() => {
    draftsRef.current = drafts;
  });

  const close = useCallback(
    async (cellId: string) => {
      if (draftsRef.current[cellId]) {
        const discard = await dialogs.askConfirm({
          title: "Borrador sin aplicar",
          description: "Esta pestaña tiene cambios sin aplicar. Si la cerrás, se pierden.",
          confirmLabel: "Descartar y cerrar",
        });
        if (!discard) return;
        setDraft(cellId, null);
      }
      setState((current) => {
        const index = current.tabs.indexOf(cellId);
        const tabs = current.tabs.filter((id) => id !== cellId);
        const active =
          current.active === cellId
            ? (tabs[Math.min(index, tabs.length - 1)] ?? null)
            : current.active;
        return { ...current, tabs, active };
      });
    },
    [dialogs, setDraft],
  );

  const activeRef = useRef(state.active);
  useEffect(() => {
    activeRef.current = state.active;
  });
  const closeActive = useCallback(() => {
    if (activeRef.current) void close(activeRef.current);
  }, [close]);

  const confirmDiscardDrafts = useCallback(async () => {
    const count = Object.keys(draftsRef.current).length;
    if (count === 0) return true;
    const discard = await dialogs.askConfirm({
      title: "Borradores sin aplicar",
      description:
        count === 1
          ? "Una celda tiene cambios sin aplicar. Si continuás, se pierden."
          : `${count} celdas tienen cambios sin aplicar. Si continuás, se pierden.`,
      confirmLabel: "Descartar borradores",
    });
    if (discard) setDrafts({});
    return discard;
  }, [dialogs]);

  const value = useMemo<EditorValue>(
    () => ({
      tabs: state.tabs,
      active: state.active,
      open,
      activate,
      close,
      closeActive,
      drafts,
      setDraft,
      confirmDiscardDrafts,
    }),
    [state, open, activate, close, closeActive, drafts, setDraft, confirmDiscardDrafts],
  );
  return <EditorContext.Provider value={value}>{children}</EditorContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useEditor(): EditorValue {
  const value = useContext(EditorContext);
  if (!value) throw new Error("useEditor must be used inside EditorProvider");
  return value;
}
