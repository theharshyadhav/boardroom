"use client";
import { motion } from "framer-motion";
import type { MaterialEvent } from "@/lib/types";
import { Badge } from "./ui/badge";

const DOT_COLOR: Record<string, string> = { critical: "var(--red)", high: "var(--amber)", medium: "var(--purple)", low: "#64748B" };

export function EventFeed({ events }: { events: MaterialEvent[] }) {
  const visible = events.filter((e) => !e.abstain);
  if (visible.length === 0) {
    return <div className="text-[12px] text-[var(--text-tertiary)]">No material events in scope.</div>;
  }
  return (
    <div className="relative pl-5.5">
      <div
        className="absolute left-1.5 top-1 bottom-1 w-[1.5px]"
        style={{ background: "linear-gradient(180deg, rgba(139,92,246,0.5), rgba(255,255,255,0.03))" }}
      />
      {visible.map((e, i) => (
        <motion.div
          key={e.id}
          initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, delay: i * 0.06 }}
          className="relative pb-5 last:pb-0"
        >
          <span
            className="absolute -left-5.5 top-0.5 w-2.5 h-2.5 rounded-full border-2"
            style={{ background: DOT_COLOR[e.severity], borderColor: "var(--bg)", boxShadow: `0 0 0 1.5px ${DOT_COLOR[e.severity]}` }}
          />
          <div className="text-[13px] font-bold">{e.title}</div>
          <div className="text-[11px] text-[var(--text-tertiary)] mt-0.5 flex items-center gap-1.5">
            {e.region || "All regions"} · <Badge tone={e.severity}>{e.severity}</Badge> · {e.confidence.band} confidence
          </div>
          <div className="text-[12px] text-[var(--text-secondary)] mt-1.5 leading-relaxed">{e.body}</div>
        </motion.div>
      ))}
    </div>
  );
}
