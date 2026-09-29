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
import {
  API_URL,
  api,
  isApiError,
  unwrap,
  type Catalog,
  type Change,
  type MutationResult,
  type ProjectEvent,
  type ProjectView,
  type RecentProject,
} from "@/api/client";

export type Message = {
  id: number;
  time: Date;
  text: string;
  tone: "info" | "warning" | "error";
  author?: string;
};

type ProjectContextValue = {
  /** False until the first session fetch answered. */
  loaded: boolean;
  /** API unreachable (the SSE stream is down). */
  offline: boolean;
  catalog: Catalog | null;
  /** The open project, or null when none is open. */
  view: ProjectView | null;
  recents: RecentProject[];
  history: Change[];
  messages: Message[];
  setView: (view: ProjectView | null) => void;
  refresh: () => Promise<void>;
  refreshRecents: () => Promise<void>;
  notify: (text: string, tone?: Message["tone"]) => void;
  /** Report an error from any action in the Messages panel. */
  fail: (error: unknown) => void;
  /** Run a schematic write; the result replaces the view. Errors go to Messages. */
  mutate: (run: () => Promise<MutationResult>) => Promise<MutationResult | null>;
};

const ProjectContext = createContext<ProjectContextValue | null>(null);

const EVENT_TYPES: ProjectEvent["type"][] = [
  "project_created",
  "project_opened",
  "project_saved",
  "project_closed",
  "project_changed",
];

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [loaded, setLoaded] = useState(false);
  const [offline, setOffline] = useState(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [view, setView] = useState<ProjectView | null>(null);
  const [recents, setRecents] = useState<RecentProject[]>([]);
  const [history, setHistory] = useState<Change[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const nextId = useRef(1);

  const push = useCallback((message: Omit<Message, "id" | "time">) => {
    const id = nextId.current++;
    setMessages((list) => [...list.slice(-199), { ...message, id, time: new Date() }]);
  }, []);

  const notify = useCallback(
    (text: string, tone: Message["tone"] = "info") => push({ text, tone }),
    [push],
  );

  const fail = useCallback(
    (error: unknown) => {
      const text = error instanceof Error ? error.message : String(error);
      push({ text, tone: "error" });
    },
    [push],
  );

  const refresh = useCallback(async () => {
    try {
      const session = await unwrap(api.GET("/session"));
      setView(session.project);
      setOffline(false);
      if (session.project) setHistory(await unwrap(api.GET("/project/history")));
      else setHistory([]);
    } catch (error) {
      if (isApiError(error, "unreachable")) setOffline(true);
      else fail(error);
    } finally {
      setLoaded(true);
    }
  }, [fail]);

  const refreshRecents = useCallback(async () => {
    try {
      setRecents(await unwrap(api.GET("/recents")));
    } catch (error) {
      fail(error);
    }
  }, [fail]);

  const mutate = useCallback(
    async (run: () => Promise<MutationResult>) => {
      try {
        const result = await run();
        setView(result.view);
        return result;
      } catch (error) {
        fail(error);
        return null;
      }
    },
    [fail],
  );

  const loadCatalog = useCallback(async () => {
    try {
      setCatalog(await unwrap(api.GET("/catalog")));
    } catch (error) {
      if (isApiError(error, "unreachable")) setOffline(true);
    }
  }, []);

  // Real-time events (ADR 0012): whoever made the change, refetch and log it. The first
  // `connected` event (also after a reconnect) loads catalog, session and recents.
  useEffect(() => {
    const source = new EventSource(`${API_URL}/events`);
    source.addEventListener("connected", () => {
      // Also on reconnect: the API may have restarted.
      setOffline(false);
      void loadCatalog();
      void refresh();
      void refreshRecents();
    });
    source.onerror = () => {
      setOffline(true);
      setLoaded(true);
    };
    const onEvent = (raw: MessageEvent<string>) => {
      const event = JSON.parse(raw.data) as ProjectEvent;
      push({ text: event.message, tone: "info", author: event.change?.author.name });
      // What upgrading an older file dropped (e.g. links no longer valid, ADR 0016).
      for (const warning of event.warnings) push({ text: warning, tone: "warning" });
      void refresh();
      if (event.type !== "project_changed") void refreshRecents();
    };
    for (const type of EVENT_TYPES) source.addEventListener(type, onEvent);
    return () => source.close();
  }, [push, loadCatalog, refresh, refreshRecents]);

  const value = useMemo<ProjectContextValue>(
    () => ({
      loaded,
      offline,
      catalog,
      view,
      recents,
      history,
      messages,
      setView,
      refresh,
      refreshRecents,
      notify,
      fail,
      mutate,
    }),
    [
      loaded,
      offline,
      catalog,
      view,
      recents,
      history,
      messages,
      refresh,
      refreshRecents,
      notify,
      fail,
      mutate,
    ],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- the provider and its hook live together
export function useProject(): ProjectContextValue {
  const value = useContext(ProjectContext);
  if (!value) throw new Error("useProject must be used inside ProjectProvider");
  return value;
}
