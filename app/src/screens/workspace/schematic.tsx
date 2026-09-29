import { useCallback, useMemo, useState, type CSSProperties, type DragEvent } from "react";
import {
  MarkerType,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  useReactFlow,
  useViewport,
  type Connection,
  type Edge,
  type NodeChange,
  type OnConnectStart,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Maximize, Minus, Plus } from "lucide-react";
import { EmptyState } from "@/components/data/empty-state";
import type { Project, StageType } from "@/api/client";
import { useProject } from "@/project/store";
import { useSchematicActions } from "./actions";
import { useWorkspaceUi } from "./context";
import { SystemNode, type SystemNodeType } from "./system-node";

const nodeTypes = { system: SystemNode };

const zoomButton =
  "flex h-6 items-center justify-center rounded-lg px-1.5 text-muted-foreground hover:bg-surface-2 hover:text-foreground";

/** Zoom out / percentage / zoom in / fit, bottom left of the canvas. */
function ZoomControl() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { zoom } = useViewport();
  return (
    <Panel
      position="bottom-left"
      className="m-4! flex h-7 items-center gap-0.5 rounded-lg border border-border bg-surface px-1"
    >
      <button
        type="button"
        className={zoomButton}
        aria-label="Alejar"
        onClick={() => void zoomOut()}
      >
        <Minus className="size-3.5" />
      </button>
      <span className="px-1.5 font-mono text-[11px] text-muted-foreground tabular-nums">
        {Math.round(zoom * 100)} %
      </span>
      <button
        type="button"
        className={zoomButton}
        aria-label="Acercar"
        onClick={() => void zoomIn()}
      >
        <Plus className="size-3.5" />
      </button>
      <button
        type="button"
        className={zoomButton}
        aria-label="Ajustar vista"
        title="Ajustar vista"
        onClick={() => void fitView({ maxZoom: 1 })}
      >
        <Maximize className="size-3.5" />
      </button>
    </Panel>
  );
}

function cellIdFromHandle(handle: string | null | undefined): string | null {
  return handle ? handle.replace(/^(in|out)-/, "") : null;
}

/** The project schematic: systems as nodes, links as orthogonal edges between cell rows. */
function SchematicCanvas({
  project,
  missing,
}: {
  project: Project;
  missing: Record<string, StageType[]>;
}) {
  const actions = useSchematicActions();
  const { notify } = useProject();
  const { selection, select, dragItem, validTargets, startConnect, endDrag, pointerRef } =
    useWorkspaceUi();
  const { screenToFlowPosition } = useReactFlow();

  const built = useMemo<SystemNodeType[]>(
    () =>
      project.systems.map((system) => ({
        id: system.id,
        type: "system",
        position: system.position,
        dragHandle: ".system-drag",
        data: {
          system,
          cells: system.cell_ids.flatMap((id) => project.cells.find((c) => c.id === id) ?? []),
          links: project.links,
          missing,
          actions,
        },
      })),
    [project, missing, actions],
  );

  // Local copy so dragging is smooth; the API position wins on every project change.
  const [nodes, setNodes] = useState<SystemNodeType[]>(built);
  const [shown, setShown] = useState(built);
  if (shown !== built) {
    setShown(built);
    setNodes(built);
  }

  const systemOf = useMemo(
    () => new Map(project.cells.map((cell) => [cell.id, cell.system_id])),
    [project.cells],
  );

  const edges = useMemo<Edge[]>(
    () =>
      // Links inside a system are implied by the block (as in the design and in Workbench):
      // only links between systems are drawn.
      project.links
        .filter((link) => systemOf.get(link.source_cell_id) !== systemOf.get(link.target_cell_id))
        .map((link) => {
          const highlighted =
            selection?.kind === "cell"
              ? selection.id === link.source_cell_id || selection.id === link.target_cell_id
              : selection?.kind === "system" &&
                (systemOf.get(link.source_cell_id) === selection.id ||
                  systemOf.get(link.target_cell_id) === selection.id);
          const color = highlighted ? "var(--primary)" : "var(--subtle-foreground)";
          return {
            id: link.id,
            source: systemOf.get(link.source_cell_id) ?? "",
            sourceHandle: `out-${link.source_cell_id}`,
            target: systemOf.get(link.target_cell_id) ?? "",
            targetHandle: `in-${link.target_cell_id}`,
            // Orthogonal connector with a 7 × 8 px arrow (Link/Straight, Link/Elbow in the design).
            type: "smoothstep",
            pathOptions: { borderRadius: 0 },
            selectable: false,
            style: { stroke: color, strokeWidth: 1 },
            markerEnd: { type: MarkerType.ArrowClosed, color, width: 28, height: 20 },
          };
        }),
    [project.links, selection, systemOf],
  );

  const onNodesChange = useCallback(
    (changes: NodeChange<SystemNodeType>[]) =>
      setNodes((current) => applyNodeChanges(changes, current)),
    [],
  );

  const onConnectStart: OnConnectStart = useCallback(
    (_, { handleId, handleType }) => {
      const cellId = cellIdFromHandle(handleId);
      if (cellId && handleType === "source") startConnect(cellId);
    },
    [startConnect],
  );

  const isValidConnection = useCallback(
    (connection: Connection | Edge) => {
      const target = cellIdFromHandle(connection.targetHandle);
      return !validTargets || (target !== null && validTargets.has(target));
    },
    [validTargets],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      const source = cellIdFromHandle(connection.sourceHandle);
      const target = cellIdFromHandle(connection.targetHandle);
      if (source && target) void actions.link(source, target);
    },
    [actions],
  );

  const onDragOver = (event: DragEvent) => {
    if (!dragItem) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  };

  const onDrop = (event: DragEvent) => {
    if (!dragItem) return;
    event.preventDefault();
    const item = dragItem;
    const cellElement = (event.target as HTMLElement).closest<HTMLElement>("[data-cell-id]");
    const cellId = cellElement?.dataset.cellId;
    endDrag();
    if (cellId) {
      if (validTargets?.has(cellId)) void actions.branch(cellId, item);
      else notify(`No se puede ramificar ${actions.blueprintName(item)} desde esa celda.`, "error");
      return;
    }
    void actions.createSystem(item, screenToFlowPosition({ x: event.clientX, y: event.clientY }));
  };

  return (
    <div
      className="relative size-full bg-background"
      onDragOver={onDragOver}
      onDrop={onDrop}
      // Where Ctrl+V pastes (docs/ux-workspace.md).
      onMouseMove={(event) => {
        pointerRef.current = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      }}
      onMouseLeave={() => {
        pointerRef.current = null;
      }}
    >
      <ReactFlow<SystemNodeType>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        colorMode="dark"
        style={{ "--xy-background-color": "var(--bg)" } as CSSProperties}
        minZoom={0.3}
        fitView
        fitViewOptions={{ maxZoom: 1 }}
        proOptions={{ hideAttribution: true }}
        onNodesChange={onNodesChange}
        onNodeDragStop={(_, node) => void actions.moveSystem(node.id, node.position)}
        onConnectStart={onConnectStart}
        onConnectEnd={endDrag}
        isValidConnection={isValidConnection}
        onConnect={onConnect}
        onPaneClick={() => select(null)}
        deleteKeyCode={null}
      >
        <ZoomControl />
      </ReactFlow>
      {project.systems.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <EmptyState
            title="Esquemático vacío"
            description="Arrastrá una fase o una etapa desde el Toolbox para crear un sistema."
          />
        </div>
      )}
    </div>
  );
}

export function Schematic({
  project,
  missing,
}: {
  project: Project;
  missing: Record<string, StageType[]>;
}) {
  return (
    <ReactFlowProvider>
      <SchematicCanvas project={project} missing={missing} />
    </ReactFlowProvider>
  );
}
