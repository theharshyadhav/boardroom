"use client";
import ReactFlow, { Background, Controls, Node, Edge, MarkerType } from "reactflow";
import type { EvidenceGraph } from "@/lib/types";

const KIND_COLOR: Record<string, string> = { source: "rgba(34,211,238,0.5)", kpi: "rgba(139,92,246,0.5)", event: "rgba(248,113,113,0.5)" };
const KIND_BG: Record<string, string> = { source: "rgba(34,211,238,0.08)", kpi: "var(--grad-brand-soft)", event: "rgba(248,113,113,0.08)" } as Record<string, string>;

function EvNode({ data }: { data: { label: string; kind: string; severity?: string } }) {
  return (
    <div
      className="px-3 py-2 rounded-[11px] border text-[11px] font-semibold"
      style={{ background: KIND_BG[data.kind] || "rgba(255,255,255,0.04)", borderColor: KIND_COLOR[data.kind] || "rgba(255,255,255,0.14)", maxWidth: 180 }}
    >
      {data.label}
    </div>
  );
}
const nodeTypes = { ev: EvNode };

export function EvidenceGraphDiagram({ graph }: { graph: EvidenceGraph }) {
  const nodes: Node[] = graph.nodes.map((n) => ({ id: n.id, type: "ev", position: n.position, data: n.data }));
  const edges: Edge[] = graph.edges.map((e) => ({
    id: e.id, source: e.source, target: e.target, label: e.label,
    style: { stroke: "rgba(139,92,246,0.4)" },
    labelStyle: { fill: "rgba(255,255,255,0.4)", fontSize: 9 },
    labelBgStyle: { fill: "#09090B" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139,92,246,0.5)" },
  }));

  return (
    <div style={{ height: 460 }}>
      <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.1 }}
        nodesDraggable={true} nodesConnectable={false} elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(255,255,255,0.06)" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
