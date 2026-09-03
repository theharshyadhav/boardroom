"use client";
import { motion } from "framer-motion";
import { ResponsiveContainer, AreaChart, Area } from "recharts";
import { ConfidenceRing } from "./ConfidenceRing";
import { Badge } from "./ui/badge";
import type { MaterialityBand, ConfidenceBand } from "@/lib/types";

export function KpiCard({
  label, value, deltaPct, values, band, confScore, confBand, onClick,
}: {
  label: string; value: string; deltaPct: number; values: number[];
  band: MaterialityBand; confScore: number; confBand: ConfidenceBand; onClick?: () => void;
}) {
  const up = deltaPct >= 0;
  const chartData = values.map((v, i) => ({ i, v }));
  const color = up ? "#34D399" : "#F87171";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      onClick={onClick}
      className="glass glass-hover p-4.5 flex flex-col gap-2.5 cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-semibold text-[var(--text-secondary)]">{label}</div>
          <div className="text-[27px] font-bold tracking-tight font-mono-tab">{value}</div>
        </div>
        <ConfidenceRing score={confScore} band={confBand} />
      </div>
      <div className="h-8.5 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={`spark-${label.replace(/\s/g, "")}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.8} fill={`url(#spark-${label.replace(/\s/g, "")})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-between mt-0.5">
        <div className="text-xs font-bold font-mono-tab flex items-center gap-1" style={{ color }}>
          {up ? "▲" : "▼"} {Math.abs(deltaPct).toFixed(1)}%
        </div>
        <Badge tone={band}>{band}</Badge>
      </div>
    </motion.div>
  );
}
