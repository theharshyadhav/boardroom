"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, GitBranch, Newspaper, AlertOctagon, Send, Check } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/Sidebar";
import { FreshnessTicker, PersonaSelect } from "@/components/Topbar";
import { KpiCard } from "@/components/KpiCard";
import { TimelineChart } from "@/components/TimelineChart";
import { EventFeed } from "@/components/EventFeed";
import { ExecutiveSummaryCard } from "@/components/ExecutiveSummary";
import { DriverFlowDiagram } from "@/components/DriverFlowDiagram";
import { ConfidenceRing } from "@/components/ConfidenceRing";
import { Button } from "@/components/ui/button";
import { fmtINR, fmtNum } from "@/lib/utils";
import type { KpiResponse, MaterialEvent, DriverTree } from "@/lib/types";

const METRICS: Array<{ key: keyof KpiResponse["series"]; label: string; fmt: (v: number) => string; finance?: boolean }> = [
  { key: "revenue", label: "Revenue", fmt: fmtINR },
  { key: "profit", label: "Profit", fmt: fmtINR, finance: true },
  { key: "orders", label: "Orders", fmt: fmtNum },
  { key: "csat", label: "Customer Satisfaction", fmt: (v) => `${Math.round(v)}/100` },
  { key: "invHealth", label: "Inventory Health", fmt: (v) => `${Math.round(v)}%` },
];

export default function DashboardPage() {
  const { profile } = useAuth();
  const [kpis, setKpis] = useState<KpiResponse | null>(null);
  const [events, setEvents] = useState<MaterialEvent[]>([]);
  const [tree, setTree] = useState<DriverTree | null>(null);
  const [activeMetric, setActiveMetric] = useState<keyof KpiResponse["series"]>("revenue");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profile) return;
    setLoading(true);
    Promise.all([api.kpis(profile.region), api.events(profile.region), api.driverTree()])
      .then(([k, e, t]) => { setKpis(k); setEvents(e); setTree(t); })
      .finally(() => setLoading(false));
  }, [profile]);

  const cards = METRICS.filter((m) => !(m.finance && profile?.hideFinance));
  const npEvent = events.find((e) => e.id === "evt_new_product");

  return (
    <div>
      <PageHeader title="Dashboard" sub="Real-time executive overview" right={<><FreshnessTicker /><PersonaSelect /></>} />

      {profile?.region && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-red-400/[0.06] border border-red-400/[0.22] text-[12px] text-red-300 mb-4">
          <AlertOctagon size={15} /> Viewing is scoped to <b className="mx-1">{profile.region}</b> per your regional access — other regions are hidden.
        </div>
      )}
      {profile?.hideFinance && !profile?.region && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-red-400/[0.06] border border-red-400/[0.22] text-[12px] text-red-300 mb-4">
          <AlertOctagon size={15} /> Profit &amp; margin figures are restricted for your role.
        </div>
      )}

      {loading || !kpis ? (
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cards.length},1fr)` }}>
          {cards.map((c) => <div key={c.key} className="skeleton h-[150px] rounded-2xl" />)}
        </div>
      ) : (
        <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: `repeat(auto-fit,minmax(190px,1fr))` }}>
          {cards.map((c) => {
            const s = kpis.series[c.key];
            const evtId = c.key === "revenue" || c.key === "profit" ? "evt_revenue_drop" : c.key === "invHealth" ? "evt_weather" : null;
            const conf = evtId ? events.find((e) => e.id === evtId)?.confidence : { score: 82, band: "high" as const };
            return (
              <KpiCard
                key={c.key}
                label={c.label}
                value={c.fmt(s.latest)}
                deltaPct={s.liveDeltaPct}
                values={s.values.slice(-30)}
                band={s.materialityBand}
                confScore={conf?.score ?? 82}
                confBand={conf?.band ?? "high"}
              />
            );
          })}
        </div>
      )}

      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "2fr 1fr" }}>
        <div className="glass p-5">
          <div className="flex items-center justify-between mb-3.5 flex-wrap gap-2">
            <div>
              <div className="text-[14.5px] font-bold flex items-center gap-2"><Sparkles size={16} className="text-[var(--purple)]" /> KPI Timeline</div>
              <div className="text-[11.5px] text-[var(--text-tertiary)] mt-0.5">Hover to inspect · dashed segment is a 10-day linear forecast</div>
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {cards.map((c) => (
                <button
                  key={c.key}
                  onClick={() => setActiveMetric(c.key)}
                  className="font-mono-tab text-[11px] px-2.5 py-1.5 rounded-full border"
                  style={activeMetric === c.key
                    ? { background: "var(--grad-brand-soft)", borderColor: "rgba(139,92,246,0.4)" }
                    : { background: "rgba(255,255,255,0.03)", borderColor: "var(--glass-border)" }}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
          {kpis && <TimelineChart dates={kpis.dates} values={kpis.series[activeMetric].values} />}
        </div>
        <ExecutiveSummaryCard />
      </div>

      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "1fr 1.3fr" }}>
        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-1"><Newspaper size={16} className="text-[var(--purple)]" /> Material Event Feed</div>
          <div className="text-[11.5px] text-[var(--text-tertiary)] mb-3.5">Ranked by materiality (z-score vs. historical distribution)</div>
          <EventFeed events={events} />
        </div>
        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-1"><GitBranch size={16} className="text-[var(--purple)]" /> Root Cause Analysis — Revenue</div>
          <div className="text-[11.5px] text-[var(--text-tertiary)] mb-1">Deterministic driver decomposition, not model-generated</div>
          {tree && <DriverFlowDiagram tree={tree} />}
        </div>
      </div>

      {npEvent && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass p-5">
          <div className="flex items-center gap-2.5 mb-3.5">
            <div className="text-[14.5px] font-bold">Sparse-History Watch</div>
            <ConfidenceRing score={npEvent.confidence.score} band={npEvent.confidence.band} />
          </div>
          <div className="p-4.5 rounded-2xl bg-amber-400/[0.05] border border-dashed border-amber-400/[0.35]">
            <div className="font-bold text-[13px] mb-1.5">{npEvent.title}</div>
            <div className="text-[12.5px] text-[var(--text-secondary)] leading-relaxed">{npEvent.body}</div>
            <div className="flex gap-2 mt-3">
              <Button variant="ghost" size="sm"><Send size={12} /> Request more data</Button>
              <Button variant="ghost" size="sm"><Check size={12} /> Flag for analyst review</Button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
