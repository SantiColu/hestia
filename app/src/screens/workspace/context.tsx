import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, unwrap, type Blueprint } from "@/api/client";
import { useProject } from "@/project/store";

export type Selection = { kind: "system" | "cell"; id: string } | null;

type WorkspaceUi = {
  selection: Selection;
  select: (selection: Selection) => void;
  /** What is being dragged from the Toolbox. */
  dragItem: Blueprint | null;
  /** Cells highlighted as valid targets (Toolbox drag or a link being drawn), per the API. */
  validTargets: ReadonlySet<string> | null;
  startDrag: (item: Blueprint) => void;
  startConnect: (sourceCellId: string) => void;
  endDrag: () => void;
};

const Context = createContext<WorkspaceUi | null>(null);

export function WorkspaceUiProvider({ children }: { children: ReactNode }) {
  const { fail } = useProject();
  const [selection, select] = useState<Selection>(null);
  const [dragItem, setDragItem] = useState<Blueprint | null>(null);
  const [validTargets, setValidTargets] = useState<ReadonlySet<string> | null>(null);
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

  const value = useMemo(
    () => ({ selection, select, dragItem, validTargets, startDrag, startConnect, endDrag }),
    [selection, dragItem, validTargets, startDrag, startConnect, endDrag],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useWorkspaceUi(): WorkspaceUi {
  const value = useContext(Context);
  if (!value) throw new Error("useWorkspaceUi must be used inside WorkspaceUiProvider");
  return value;
}
