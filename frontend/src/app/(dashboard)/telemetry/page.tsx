"use client";
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/Sidebar";
import type { Telemetry } from "@/lib/types";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="glass px-4 py-3.5">
      <div className="text-[10.5px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1.5">{label}</div>
      <div className="text-[19px] font-bold font-mono-tab">{value}</div>
    </div>
  );
}

export default function TelemetryPage() {
  const [t, setT] = useState<Telemetry | null>(null);

  useEffect(() => {
    const load = () => api.telemetry().then(setT).catch(() => {});
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <PageHeader title="Runtime Telemetry" sub="Model usage, latency, and cost — live" />
      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
        <Stat label="Provider" value={t?.provider ?? "—"} />
        <Stat label="Model in use" value={<span className="text-[14px]">{t?.model ?? "—"}</span>} />
        <Stat label="API key configured" value={t?.configured ? "Yes" : "No"} />
        <Stat label="Model calls" value={t?.calls ?? 0} />
        <Stat label="Avg latency" value={`${t?.avgLatencyMs ?? 0}ms`} />
        <Stat label="Cache hits" value={t?.cacheHits ?? 0} />
        <Stat label="Input / output tokens" value={`${t?.inputTokens ?? 0} / ${t?.outputTokens ?? 0}`} />
        <Stat label="Est. cost (session)" value={`$${(t?.estimatedCostUsd ?? 0).toFixed(4)}`} />
      </div>
      <div className="glass p-5">
        <div className="text-[14.5px] font-bold flex items-center gap-2 mb-1"><Sparkles size={16} className="text-[var(--purple)]" /> Call log</div>
        <div className="text-[11.5px] text-[var(--text-tertiary)] mb-3.5">Most recent first · polls every 4s</div>
        <div className="flex flex-col gap-1.5">
          {(!t || t.log.length === 0) && (
            <div className="text-[12px] text-[var(--text-tertiary)]">
              No model calls yet this session — visit Dashboard or Boardroom to trigger narrative generation.
            </div>
          )}
          {t?.log.map((l, i) => (
            <div key={i} className="font-mono-tab text-[11px] px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.09] flex justify-between gap-2.5">
              <span>{l.ts}</span>
              <span>{l.cached ? "cache hit" : l.ok === false ? `fallback (${l.reason || "call failed"})` : "live call"}</span>
              <span>{l.latency ?? 0}ms</span>
              <span>{l.inTok ?? 0}→{l.outTok ?? 0} tok</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
