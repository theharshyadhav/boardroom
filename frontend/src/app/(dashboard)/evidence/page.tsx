"use client";
import { useEffect, useState } from "react";
import { Search, Newspaper, XCircle, Sparkles, Boxes, Megaphone, MessageSquare, Target, Cloud } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";
import { EvidenceGraphDiagram } from "@/components/EvidenceGraphDiagram";
import type { DataSource, MaterialEvent, EvidenceGraph } from "@/lib/types";

const SOURCE_ICON: Record<string, React.ElementType> = {
  sales: Boxes, inventory: Boxes, marketing: Megaphone, reviews: MessageSquare, competitor: Target, weather: Cloud, news: Newspaper,
};

export default function EvidencePage() {
  const { profile } = useAuth();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [events, setEvents] = useState<MaterialEvent[]>([]);
  const [graph, setGraph] = useState<EvidenceGraph | null>(null);

  useEffect(() => {
    api.evidenceSources().then(setSources);
    api.events(profile?.region).then(setEvents);
    api.evidenceGraph().then(setGraph);
  }, [profile]);

  return (
    <div>
      <PageHeader title="Evidence Explorer" sub="Every insight, traced to its source" />

      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-3.5"><Search size={16} className="text-[var(--purple)]" /> Data Sources</div>
          <div className="flex flex-col gap-2.5">
            {sources.map((s) => {
              const Icon = SOURCE_ICON[s.id] || Boxes;
              return (
                <div key={s.id} className="flex items-center gap-3 px-3.5 py-3 rounded-xl bg-white/[0.025] border border-white/[0.09]">
                  <div className="w-8.5 h-8.5 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--grad-brand-soft)" }}>
                    <Icon size={16} className="text-[var(--cyan)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12.5px] font-semibold">{s.name}</div>
                    <div className="text-[10.5px] text-[var(--text-tertiary)] font-mono-tab mt-0.5">
                      {s.count.toLocaleString()} records · updated {s.freshnessLabel} · {s.lineage}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass p-5">
          <div className="text-[14.5px] font-bold flex items-center gap-2 mb-3.5"><Newspaper size={16} className="text-[var(--purple)]" /> Traced Insights</div>
          <div className="flex flex-col gap-3">
            {events.map((e) => (
              <div key={e.id} className="flex items-start gap-3 px-3.5 py-3 rounded-xl bg-white/[0.025] border border-white/[0.09]">
                <div className="w-8.5 h-8.5 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--grad-brand-soft)" }}>
                  {e.abstain ? <XCircle size={16} className="text-[var(--cyan)]" /> : <Sparkles size={16} className="text-[var(--cyan)]" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12.5px] font-semibold">{e.title}</div>
                  <div className="text-[11px] text-[var(--text-tertiary)] my-1.5 flex flex-wrap gap-1">
                    {e.sources.map((s) => <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.06]">{s}</span>)}
                  </div>
                  <div className="flex items-center gap-2.5">
                    <Badge tone={e.confidence.band}>{e.confidence.band} · {e.confidence.score}/100</Badge>
                    {e.confidence.breakdown && (
                      <span className="text-[10.5px] text-[var(--text-tertiary)]">
                        freshness {e.confidence.breakdown.freshness}/100 · history {e.confidence.breakdown.history}/100 · agreement {e.confidence.breakdown.agreement}/100
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="glass p-5">
        <div className="text-[14.5px] font-bold mb-1">Traceability Graph</div>
        <div className="text-[11.5px] text-[var(--text-tertiary)] mb-2">
          Built with NetworkX on the backend, laid out by topological generation — source → KPI → event. Drag nodes to explore.
        </div>
        {graph && <EvidenceGraphDiagram graph={graph} />}
      </div>
    </div>
  );
}
