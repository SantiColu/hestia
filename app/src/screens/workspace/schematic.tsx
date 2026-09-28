import { useCallback, useMemo, useState, type DragEvent } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  useReactFlow,
  type Connection,
  type Edge,
  type NodeChange,
  type OnConnectStart,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { EmptyState } from "@/components/data/empty-state";
import type { Project } from "@/api/client";
import { useProject } from "@/project/store";
import { useSchematicActions } from "./actions";
import { useWorkspaceUi } from "./context";
import { SystemNode, type SystemNodeType } from "./system-node";

const nodeTypes = { system: SystemNode };

function cellIdFromHandle(handle: string | null | undefined): string | null {
  return handle ? handle.replace(/^(in|out)-/, "") : null;
}

/** The project schematic: systems as nodes, links as orthogonal edges between cell rows. */
function SchematicCanvas({ project }: { project: Project }) {
  const actions = useSchematicActions();
  const { notify } = useProject();
  const { selection, select, dragItem, validTargets, startConnect, endDrag } = useWorkspaceUi();
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
          actions,
        },
      })),
    [project, actions],
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
      project.links.map((link) => {
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
          type: "smoothstep",
          selectable: false,
          style: { stroke: color, strokeWidth: highlighted ? 1.5 : 1 },
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 14, height: 14 },
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
    <div className="relative size-full" onDragOver={onDragOver} onDrop={onDrop}>
      <ReactFlow<SystemNodeType>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        colorMode="dark"
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
        <Background gap={24} color="var(--border)" />
        <Controls showInteractive={false} />
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

export function Schematic({ project }: { project: Project }) {
  return (
    <ReactFlowProvider>
      <SchematicCanvas project={project} />
    </ReactFlowProvider>
  );
}
