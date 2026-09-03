"use client";
import { useEffect, useState } from "react";
import { ActivitySquare, Cloud, GitBranch, ShieldAlert, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import type { ObservabilitySummary, WorkflowSummary, WorkflowTimeline, AuditEntry } from "@/lib/api";
import { PageHeader } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="glass px-4 py-3.5">
      <div className="text-[10.5px] text-[var(--text-tertiary)] uppercase tracking-wide mb-1.5">{label}</div>
      <div className="text-[19px] font-bold font-mono-tab">{value}</div>
    </div>
  );
}

function TimelineDrilldown({ workflowId }: { workflowId: string }) {
  const [tl, setTl] = useState<WorkflowTimeline | null>(null);
  useEffect(() => { api.workflowTimeline(workflowId).then(setTl).catch(() => {}); }, [workflowId]);
  if (!tl) return <div className="text-[11.5px] text-[var(--text-tertiary)] px-3 py-2">Loading\u2026</div>;
  return (
    <div className="flex flex-col gap-1.5 px-3.5 py-3 bg-white/[0.015] border-t border-white/[0.07]">
      {tl.steps.length === 0 && <div className="text-[11.5px] text-[var(--text-tertiary)]">No steps recorded yet.</div>}
      {tl.steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2.5 text-[11.5px]">
          <Badge tone={s.status === "success" ? "low" : "critical"}>{s.status}</Badge>
          <span className="font-semibold">{s.agent.replace(/_/g, " ")}</span>
          <span className="text-[var(--text-tertiary)]">{s.topic_in} {s.topic_out ? `\u2192 ${s.topic_out}` : ""}</span>
          <span className="ml-auto font-mono-tab text-[var(--text-tertiary)]">{s.duration_ms.toFixed(0)}ms</span>
        </div>
      ))}
    </div>
  );
}

export default function ObservabilityPage() {
  const [summary, setSummary] = useState<ObservabilitySummary | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [tab, setTab] = useState<"timeline" | "logs">("timeline");

  useEffect(() => {
    const load = () => {
      api.obsSummary().then(setSummary).catch(() => {});
      api.workflows(15).then(setWorkflows).catch(() => {});
      api.auditLog(30).then(setAudit).catch(() => {});
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <PageHeader title="Enterprise Observability" sub="Cloud status, agent execution, Pub/Sub workflows, and the security audit trail" />

      <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
        <Stat label="Agents healthy" value={`${summary?.agents_healthy ?? 0} / ${summary?.agents_total ?? 0}`} />
        <Stat label="Agents running" value={summary?.agents_running ?? 0} />
        <Stat label="Total executions" value={summary?.total_executions ?? 0} />
        <Stat label="Failed workflows" value={summary?.failed_workflows ?? 0} />
        <Stat label="Workflows tracked" value={summary?.workflows_tracked ?? 0} />
        <Stat label="Gemini calls" value={summary?.llm_telemetry.calls ?? 0} />
        <Stat label="Tokens in/out" value={`${summary?.llm_telemetry.in_tokens ?? 0} / ${summary?.llm_telemetry.out_tokens ?? 0}`} />
        <Stat label="Est. cost" value={`$${(summary?.llm_telemetry.estimated_cost_usd ?? 0).toFixed(4)}`} />
      </div>

      <div className="glass p-4 mb-4 flex items-center gap-3">
        <Cloud size={16} className="text-[var(--purple)]" />
        <div className="text-[12.5px]">
          <span className="font-semibold">Cloud status: </span>
          Firestore + Pub/Sub {summary && summary.workflows_tracked >= 0 ? "reachable" : "unknown"} \u00b7 agents reporting live to this dashboard.
        </div>
      </div>

      <div className="flex gap-2 mb-3">
        <button onClick={() => setTab("timeline")} className={`text-[12px] font-semibold px-3 py-1.5 rounded-lg ${tab === "timeline" ? "bg-white/[0.08]" : "text-[var(--text-tertiary)]"}`}>
          <GitBranch size={12} className="inline mr-1" /> Execution Timeline
        </button>
        <button onClick={() => setTab("logs")} className={`text-[12px] font-semibold px-3 py-1.5 rounded-lg ${tab === "logs" ? "bg-white/[0.08]" : "text-[var(--text-tertiary)]"}`}>
          <ShieldAlert size={12} className="inline mr-1" /> Security Audit Log
        </button>
      </div>

      {tab === "timeline" ? (
        <div className="glass p-0 overflow-hidden">
          {workflows.length === 0 && <div className="p-5 text-[12.5px] text-[var(--text-tertiary)]">No workflows yet \u2014 trigger one from Executive Watch.</div>}
          {workflows.map((w) => (
            <div key={w.workflow_id} className="border-b border-white/[0.06] last:border-0">
              <button
                onClick={() => setExpanded(expanded === w.workflow_id ? null : w.workflow_id)}
                className="w-full flex items-center gap-3 px-3.5 py-3 text-left hover:bg-white/[0.02]"
              >
                <ChevronRight size={14} className={`transition-transform ${expanded === w.workflow_id ? "rotate-90" : ""}`} />
                <ActivitySquare size={13} className="text-[var(--purple)]" />
                <span className="text-[12.5px] font-semibold">{w.root_topic}</span>
                <span className="text-[11px] text-[var(--text-tertiary)] font-mono-tab">{w.workflow_id.slice(0, 8)}</span>
                <span className="ml-auto text-[11px] text-[var(--text-tertiary)]">{new Date(w.started_at).toLocaleString()}</span>
              </button>
              {expanded === w.workflow_id && <TimelineDrilldown workflowId={w.workflow_id} />}
            </div>
          ))}
        </div>
      ) : (
        <div className="glass p-0 overflow-hidden">
          {audit.length === 0 && <div className="p-5 text-[12.5px] text-[var(--text-tertiary)]">No audit entries yet.</div>}
          {audit.map((a, i) => (
            <div key={i} className="flex items-center gap-3 px-3.5 py-2.5 border-b border-white/[0.06] last:border-0 text-[11.5px]">
              <Badge tone={a.decision === "allowed" ? "low" : a.decision === "flagged" ? "high" : "critical"}>{a.decision}</Badge>
              <span className="font-semibold">{a.action}</span>
              <span className="text-[var(--text-tertiary)] truncate flex-1">{JSON.stringify(a.detail)}</span>
              <span className="text-[var(--text-tertiary)] font-mono-tab shrink-0">{new Date(a.ts).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
