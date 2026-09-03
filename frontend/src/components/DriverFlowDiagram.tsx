"use client";
import { useMemo } from "react";
import ReactFlow, { Background, Controls, Node, Edge, MarkerType, Position } from "reactflow";
import type { DriverTree } from "@/lib/types";

function DriverNodeBox({ data }: { data: { label: string; pct: number; big?: boolean; negative?: boolean } }) {
  return (
    <div
      className="glass px-3.5 py-2.5 rounded-[13px]"
      style={{ width: 160, background: data.big ? "var(--grad-brand-soft)" : undefined, borderColor: data.big ? "rgba(139,92,246,0.4)" : undefined }}
    >
      <div className="text-[11.5px] font-bold text-white truncate">{data.label}</div>
      <div className="text-[12px] font-mono-tab font-bold mt-0.5" style={{ color: data.negative ? "var(--red)" : "var(--cyan)" }}>
        {data.pct}% share
      </div>
    </div>
  );
}

const nodeTypes = { driver: DriverNodeBox };

export function DriverFlowDiagram({ tree }: { tree: DriverTree }) {
  const { nodes, edges } = useMemo(() => {
    const price = tree.nodes.find((n) => n.id === "price")!;
    const volume = tree.nodes.find((n) => n.id === "volume")!;
    const children = tree.nodes.filter((n) => n.parent === "volume");

    const nodes: Node[] = [
      {
        id: "revenue", type: "driver", position: { x: 20, y: 140 },
        data: { label: "Revenue (Total)", pct: Math.round(tree.totalDeltaPct), big: true, negative: tree.totalDeltaPct < 0 },
        sourcePosition: Position.Right, targetPosition: Position.Left,
      },
      {
        id: "price", type: "driver", position: { x: 320, y: 30 },
        data: { label: price.label, pct: price.pct, negative: (price.value ?? 0) < 0 },
        sourcePosition: Position.Right, targetPosition: Position.Left,
      },
      {
        id: "volume", type: "driver", position: { x: 320, y: 250 },
        data: { label: volume.label, pct: volume.pct, negative: (volume.value ?? 0) < 0 },
        sourcePosition: Position.Right, targetPosition: Position.Left,
      },
      ...children.map((c, i) => ({
        id: c.id, type: "driver", position: { x: 640, y: 20 + i * 95 },
        data: { label: c.label, pct: c.pct, negative: true },
        targetPosition: Position.Left,
      })),
    ];

    const edgeStyle = { stroke: "rgba(139,92,246,0.55)", strokeWidth: 2 };
    const edges: Edge[] = [
      { id: "e-rev-price", source: "revenue", target: "price", style: edgeStyle, markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139,92,246,0.6)" } },
      { id: "e-rev-vol", source: "revenue", target: "volume", style: { ...edgeStyle, strokeWidth: 3 }, markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139,92,246,0.6)" } },
      ...children.map((c) => ({
        id: `e-vol-${c.id}`, source: "volume", target: c.id,
        style: { ...edgeStyle, strokeWidth: 1 + c.pct / 20 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "rgba(139,92,246,0.6)" },
      })),
    ];

    return { nodes, edges };
  }, [tree]);

  return (
    <div style={{ height: 360 }}>
      <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.15 }}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(255,255,255,0.06)" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
