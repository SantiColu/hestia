import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, unwrap, type Blueprint, type Position } from "@/api/client";
import { readFragment } from "@/project/fragment";
import { useProject } from "@/project/store";
import { includesTarget, type Target } from "./target";

type WorkspaceUi = {
  /** Selected systems and cells; empty when nothing is selected. */
  selection: readonly Target[];
  /** Select only `target` (null clears the selection). */
  select: (target: Target | null) => void;
  /** Add `target` to the selection or take it out (Ctrl/Shift + click). */
  toggleSelected: (target: Target) => void;
  /** Replace the selection (box selection on the canvas). */
  selectMany: (targets: Target[]) => void;
  /** What is being dragged from the Toolbox. */
  dragItem: Blueprint | null;
  /** Cells highlighted as valid targets (Toolbox drag or a link being drawn), per the API. */
  validTargets: ReadonlySet<string> | null;
  startDrag: (item: Blueprint) => void;
  startConnect: (sourceCellId: string) => void;
  endDrag: () => void;
  /** The clipboard holds a Hestia fragment (checked when an Edit menu opens and after copy). */
  canPaste: boolean;
  checkClipboard: () => Promise<void>;
  setCanPaste: (canPaste: boolean) => void;
  /** Last pointer position over the canvas, in schematic units; null when outside. */
  pointerRef: { current: Position | null };
};

const Context = createContext<WorkspaceUi | null>(null);

export function WorkspaceUiProvider({ children }: { children: ReactNode }) {
  const { fail } = useProject();
  const [selection, setSelection] = useState<readonly Target[]>([]);
  const select = useCallback((target: Target | null) => setSelection(target ? [target] : []), []);
  const toggleSelected = useCallback(
    (target: Target) =>
      setSelection((current) =>
        includesTarget(current, target)
          ? current.filter((t) => t.kind !== target.kind || t.id !== target.id)
          : [...current, target],
      ),
    [],
  );
  const selectMany = useCallback((targets: Target[]) => setSelection(targets), []);
  const [dragItem, setDragItem] = useState<Blueprint | null>(null);
  const [validTargets, setValidTargets] = useState<ReadonlySet<string> | null>(null);
  const [canPaste, setCanPaste] = useState(false);
  const pointerRef = useRef<Position | null>(null);
  // Ignore answers that arrive after the drag ended or another started.
  const token = useRef(0);

  const load = useCallback(
    async (request: () => Promise<{ cell_ids: string[] }>) => {
      const current = ++token.current;
      setValidTargets(new Set());
      try {
        const { cell_ids } = await request();
        if (token.current === current) setValidTargets(new Set(cell_ids));
      } catch (error) {
        fail(error);
      }
    },
    [fail],
  );

  const startDrag = useCallback(
    (item: Blueprint) => {
      setDragItem(item);
      const query = item.template
        ? { template: item.template }
        : { stage: item.stage ?? undefined };
      void load(() => unwrap(api.GET("/project/branch-targets", { params: { query } })));
    },
    [load],
  );

  const startConnect = useCallback(
    (sourceCellId: string) => {
      void load(() =>
        unwrap(
          api.GET("/project/cells/{cell_id}/link-targets", {
            params: { path: { cell_id: sourceCellId } },
          }),
        ),
      );
    },
    [load],
  );

  const endDrag = useCallback(() => {
    token.current++;
    setDragItem(null);
    setValidTargets(null);
  }, []);

  const checkClipboard = useCallback(async () => {
    setCanPaste((await readFragment()) !== null);
  }, []);

  const value = useMemo(
    () => ({
      selection,
      select,
      toggleSelected,
      selectMany,
      dragItem,
      validTargets,
      startDrag,
      startConnect,
      endDrag,
      canPaste,
      checkClipboard,
      setCanPaste,
      pointerRef,
    }),
    [
      selection,
      select,
      toggleSelected,
      selectMany,
      dragItem,
      validTargets,
      startDrag,
      startConnect,
      endDrag,
      canPaste,
      checkClipboard,
    ],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- the provider and its hook live together
export function useWorkspaceUi(): WorkspaceUi {
  const value = useContext(Context);
  if (!value) throw new Error("useWorkspaceUi must be used inside WorkspaceUiProvider");
  return value;
}
