import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge as FlowEdge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import {
  AlertTriangle,
  Flag,
  Map,
  Merge,
  RefreshCw,
  Search,
  ShieldCheck,
  TextSelect,
} from "lucide-react";
import { useMemo } from "react";
import type { DiagnosisItem, Edge, StepRecord } from "../api/types";

const icons = {
  plan: Map,
  retrieve: Search,
  extract: TextSelect,
  check: ShieldCheck,
  reformulate: RefreshCw,
  synthesize: Merge,
};
type WaypointData = {
  step: StepRecord;
  diagnosis?: DiagnosisItem;
  selected: boolean;
  affected?: boolean;
  faded?: boolean;
  groundTruth?: "injected" | "proven";
  compact?: boolean;
};
type WaypointNode = Node<WaypointData, "waypoint">;

function Waypoint({ data }: NodeProps<WaypointNode>) {
  const { step, diagnosis, selected, affected, faded, groundTruth, compact } =
    data;
  const Icon = step.error
    ? AlertTriangle
    : (icons[step.name as keyof typeof icons] ?? Map);
  const rank = diagnosis?.rank;
  const score = diagnosis?.score ?? 0;
  const heat =
    rank === 1
      ? "border-2 border-orange bg-orange-tint"
      : score > 0.6
        ? "border-2 border-caution bg-caution-tint"
        : score >= 0.25
          ? "border border-caution bg-caution-tint"
          : "border border-rule bg-panel";
  return (
    <div
      className={`relative flex h-16 w-[220px] items-center gap-3 rounded-node px-3 ${heat} ${step.reused ? "border-dashed opacity-60" : ""} ${step.error ? "border-warning" : ""} ${selected ? "outline outline-2 outline-offset-2 outline-advisory" : ""} ${affected ? "outline outline-2 outline-offset-2 outline-caution" : ""} ${faded ? "opacity-40" : ""} ${compact ? "scale-90" : ""}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2 !w-2 !border-ink !bg-panel"
      />
      {rank === 1 && (
        <span className="absolute -top-6 left-1 text-xs font-medium text-orange">
          Most likely cause
        </span>
      )}
      <span className="relative grid h-7 w-7 shrink-0 place-items-center rounded-full border border-current">
        <Icon className="h-[18px] w-[18px]" />
        {rank === 1 && (
          <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rotate-45 bg-orange" />
        )}
        {rank && rank > 1 && rank <= 3 && (
          <span className="absolute -right-2 -top-2 grid h-4 w-4 place-items-center rounded-full bg-caution text-[10px] text-white">
            {rank}
          </span>
        )}
      </span>
      <span className="min-w-0">
        <span className="block truncate font-mono text-xs">
          {step.step_key}
        </span>
        <span className="block truncate text-sm text-graphite">
          {step.output_text}
        </span>
      </span>
      {step.reused && (
        <span className="absolute bottom-1 right-2 text-[10px] text-graphite">
          reused
        </span>
      )}
      {groundTruth && (
        <span
          title={groundTruth === "injected" ? "Injected here" : "Proven cause"}
          className="absolute -right-2 -top-2 grid h-5 w-5 place-items-center rounded-full bg-ink text-white"
        >
          <Flag className="h-3 w-3" />
        </span>
      )}
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2 !w-2 !border-ink !bg-panel"
      />
    </div>
  );
}
const nodeTypes = { waypoint: Waypoint };
export type ExecutionRouteProps = {
  steps: StepRecord[];
  edges: Edge[];
  ranking?: DiagnosisItem[];
  selectedKey?: string | null;
  onSelect?: (key: string | null) => void;
  highlight?: string[];
  compact?: boolean;
  revealUpTo?: number;
  groundTruth?: { injected?: string; proven?: string };
};

export default function ExecutionRoute({
  steps,
  edges,
  ranking = [],
  selectedKey,
  onSelect,
  highlight,
  compact = false,
  revealUpTo,
  groundTruth,
}: ExecutionRouteProps) {
  const visible =
    revealUpTo === undefined
      ? steps
      : steps.filter((step) => step.idx <= revealUpTo);
  const { nodes, flowEdges } = useMemo(() => {
    const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
    graph.setGraph({ rankdir: "LR", ranksep: compact ? 45 : 90, nodesep: 28 });
    visible.forEach((step) =>
      graph.setNode(step.step_key, { width: 220, height: 64 }),
    );
    const visibleKeys = new Set(visible.map((step) => step.step_key));
    edges
      .filter(
        (edge) => visibleKeys.has(edge.source) && visibleKeys.has(edge.target),
      )
      .forEach((edge) => graph.setEdge(edge.source, edge.target));
    dagre.layout(graph);
    const top = ranking.find((item) => item.rank === 1)?.step_key;
    const nextNodes: WaypointNode[] = visible.map((step) => {
      const position = graph.node(step.step_key);
      const diagnosis = ranking.find((item) => item.step_key === step.step_key);
      const affected = highlight?.includes(step.step_key);
      const marker =
        groundTruth?.injected === step.step_key
          ? "injected"
          : groundTruth?.proven === step.step_key
            ? "proven"
            : undefined;
      return {
        id: step.step_key,
        type: "waypoint",
        position: { x: position.x - 110, y: position.y - 32 },
        data: {
          step,
          diagnosis,
          selected: selectedKey === step.step_key,
          affected,
          faded: Boolean(highlight && !affected),
          groundTruth: marker,
          compact,
        },
      };
    });
    const nextEdges: FlowEdge[] = edges
      .filter(
        (edge) => visibleKeys.has(edge.source) && visibleKeys.has(edge.target),
      )
      .map((edge) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        style: {
          stroke: edge.target === top ? "#FF4F00" : "rgba(20,32,43,.55)",
          strokeWidth: 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: edge.target === top ? "#FF4F00" : "#5B6873",
        },
      }));
    return { nodes: nextNodes, flowEdges: nextEdges };
  }, [visible, edges, ranking, selectedKey, highlight, compact, groundTruth]);
  return (
    <div
      className="h-full min-h-[340px] w-full bg-paper"
      aria-label="Execution route"
    >
      <ReactFlow
        nodes={nodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: compact ? 0.05 : 0.15 }}
        minZoom={0.35}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, node) => onSelect?.(node.id)}
        onPaneClick={() => onSelect?.(null)}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          id="minor"
          variant={BackgroundVariant.Lines}
          gap={24}
          size={1}
          color="#DFE5E8"
        />
        <Background
          id="major"
          variant={BackgroundVariant.Lines}
          gap={120}
          size={1}
          color="#C9D2D8"
        />
        {!compact && (
          <Controls showInteractive={false} position="bottom-left" />
        )}
      </ReactFlow>
    </div>
  );
}
