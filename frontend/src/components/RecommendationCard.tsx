"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Edit3, X, ArrowRight } from "lucide-react";
import type { Recommendation } from "@/lib/types";
import { api } from "@/lib/api";
import { ConfidenceRing } from "./ConfidenceRing";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

export function RecommendationCard({ rec, index }: { rec: Recommendation; index: number }) {
  const [stats, setStats] = useState(rec.feedbackStats);
  const [lastAction, setLastAction] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(action: "accepted" | "rejected" | "modified") {
    setBusy(true);
    try {
      const s = await api.postFeedback(rec.id, action);
      setStats(s);
      setLastAction({ accepted: "Accepted", rejected: "Rejected", modified: "Marked for modification" }[action]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }} className="glass p-4.5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[13.5px] font-bold flex items-center gap-1.5"><Check size={15} /> Recommendation</div>
        <div className="flex items-center gap-2">
          <Badge tone={rec.confidence.band}>{rec.confidence.band} confidence</Badge>
          <ConfidenceRing score={rec.confidence.score} band={rec.confidence.band} />
        </div>
      </div>
      <div className="flex items-center flex-wrap gap-1.5 mb-3.5">
        <span className="text-[10.5px] px-2.5 py-1 rounded-lg bg-white/[0.05] border border-white/[0.09] text-[var(--text-secondary)]">{rec.driver}</span>
        <ArrowRight size={11} className="text-[var(--text-tertiary)]" />
        <span className="text-[10.5px] px-2.5 py-1 rounded-lg bg-white/[0.05] border border-white/[0.09] text-[var(--text-secondary)]">{rec.lever}</span>
        <ArrowRight size={11} className="text-[var(--text-tertiary)]" />
        <span className="text-[10.5px] px-2.5 py-1 rounded-lg" style={{ background: "var(--grad-brand-soft)", border: "1px solid rgba(139,92,246,0.3)" }}>{rec.action}</span>
      </div>
      <div className="text-[12.5px] text-[var(--text-secondary)] leading-relaxed mb-2.5">
        <b className="text-white">Expected impact —</b> {rec.impact}
      </div>
      <div className="text-[12px] text-[var(--text-tertiary)] mb-3.5">
        Owner: <b className="text-[var(--text-secondary)]">{rec.owner}</b> · Monitoring: {rec.monitoring}
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-white/[0.09] flex-wrap gap-2">
        <div className="text-[11px] text-[var(--text-tertiary)]">
          {lastAction && <span>{lastAction} · </span>}
          Similar recommendations accepted <b className="font-mono-tab text-[var(--cyan)]">{stats?.blended ?? 70}%</b> of the time historically
        </div>
        <div className="flex gap-1.5">
          <Button size="sm" disabled={busy} onClick={() => submit("accepted")}><Check size={12} /> Accept</Button>
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => submit("modified")}><Edit3 size={12} /> Modify</Button>
          <Button variant="dangerOutline" size="sm" disabled={busy} onClick={() => submit("rejected")}><X size={12} /> Reject</Button>
        </div>
      </div>
    </motion.div>
  );
}
