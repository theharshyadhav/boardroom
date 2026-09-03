"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Cpu, Clock, Zap, Database, ShieldCheck, X, Play } from "lucide-react";
import { api } from "@/lib/api";
import type { AgentSummary, AgentDetail } from "@/lib/api";
import { PageHeader } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

const HEALTH_TONE: Record<string, "low" | "high" | "critical"> = {
  healthy: "low", degraded: "high", down: "critical",
};

function AgentCard({ agent, onOpen }: { agent: AgentSummary; onOpen: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      onClick={onOpen}
      className="glass glass-hover p-4.5 flex flex-col gap-3 cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-[9px] flex items-center justify-center shrink-0" style={{ background: "var(--grad-brand-soft)" }}>
            <Bot size={16} className="text-[var(--purple)]" />
          </div>
          <div>
            <div className="text-[13.5px] font-bold tracking-tight">{agent.name.replace(/_/g, " ")}</div>
            <div className="text-[10.5px] text-[var(--text-tertiary)]">v{agent.version}</div>
          </div>
        </div>
        <Badge tone={HEALTH_TONE[agent.health] ?? "neutral"}>{agent.health}</Badge>
      </div>
      <div className="text-[11.5px] text-[var(--text-secondary)] leading-snug">{agent.description}</div>
      <div className="flex flex-wrap gap-1.5">
        {agent.capabilities?.slice(0, 4).map((c) => (
          <span key={c} className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.09] text-[var(--text-tertiary)]">{c}</span>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/[0.07] text-center">
        <div>
          <div className="text-[13px] font-bold font-mono-tab">{agent.execution_count ?? 0}</div>
          <div className="text-[9.5px] text-[var(--text-tertiary)] uppercase">Runs</div>
        </div>
        <div>
          <div className="text-[13px] font-bold font-mono-tab">{Math.round(agent.avg_runtime_ms ?? 0)}ms</div>
          <div className="text-[9.5px] text-[var(--text-tertiary)] uppercase">Avg time</div>
        </div>
        <div>
          <div className="text-[13px] font-bold font-mono-tab">{agent.memory_size}</div>
          <div className="text-[9.5px] text-[var(--text-tertiary)] uppercase">Memories</div>
        </div>
      </div>
    </motion.div>
  );
}

function AgentDrawer({ name, onClose }: { name: string; onClose: () => void }) {
  const { roleKey } = useAuth();
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState<string | null>(null);

  useEffect(() => {
    api.agentDetail(name).then(setDetail).catch(() => {});
  }, [name]);

  async function runNow() {
    if (!roleKey) return;
    setRunning(true);
    setRunMsg(null);
    try {
      const res = await api.runAgent(name, roleKey);
      setRunMsg(`Dispatched \u2014 workflow ${res.workflow_id.slice(0, 8)}\u2026 on topic "${res.topic}"`);
    } catch (e) {
      setRunMsg(e instanceof Error ? e.message : "Failed to trigger agent");
    } finally {
      setRunning(false);
    }
  }

  return (
    <motion.div
      initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", damping: 28, stiffness: 260 }}
      className="fixed top-0 right-0 h-screen w-full max-w-[440px] bg-[#0c0c0e] border-l border-white/[0.09] z-50 overflow-y-auto p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="text-[16px] font-bold tracking-tight">{name.replace(/_/g, " ")}</div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.06]"><X size={18} /></button>
      </div>

      {!detail ? (
        <div className="text-[12px] text-[var(--text-tertiary)]">Loading\u2026</div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="text-[12.5px] text-[var(--text-secondary)]">{detail.description}</div>

          <div className="glass p-3.5">
            <div className="text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)] mb-2 flex items-center gap-1.5"><ShieldCheck size={12} /> Permissions</div>
            <div className="flex flex-wrap gap-1.5">
              {detail.permissions.map((p) => <Badge key={p} tone="neutral">{p}</Badge>)}
            </div>
          </div>

          <div className="glass p-3.5">
            <div className="text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)] mb-2 flex items-center gap-1.5"><Zap size={12} /> Subscribes to (Pub/Sub topics)</div>
            <div className="flex flex-wrap gap-1.5">
              {detail.subscribes_to.map((t) => <Badge key={t} tone="medium">{t}</Badge>)}
            </div>
          </div>

          <Button variant="primary" onClick={runNow} disabled={running}>
            <Play size={13} /> {running ? "Dispatching\u2026" : "Run now"}
          </Button>
          {runMsg && <div className="text-[11px] text-[var(--text-tertiary)]">{runMsg}</div>}

          <div>
            <div className="text-[10.5px] uppercase tracking-wide text-[var(--text-tertiary)] mb-2 flex items-center gap-1.5"><Database size={12} /> Memory Viewer \u2014 recent entries</div>
            <div className="flex flex-col gap-1.5">
              {detail.recent_memory.length === 0 && (
                <div className="text-[11.5px] text-[var(--text-tertiary)]">No memory yet \u2014 this agent hasn&apos;t executed.</div>
              )}
              {detail.recent_memory.map((m) => (
                <div key={m.id} className="text-[11px] px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.09]">
                  <div className="flex justify-between mb-1">
                    <Badge tone="neutral">{m.kind}</Badge>
                    <span className="text-[var(--text-tertiary)]">{new Date(m.created_at).toLocaleString()}</span>
                  </div>
                  <div className="text-[var(--text-secondary)] leading-snug">{m.summary}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [openAgent, setOpenAgent] = useState<string | null>(null);

  useEffect(() => {
    const load = () => api.agents().then(setAgents).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <PageHeader title="Agent Registry" sub="Every autonomous ADK agent running in the mesh \u2014 live status, health, and memory" />
      <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
        {agents.map((a) => (
          <AgentCard key={a.name} agent={a} onOpen={() => setOpenAgent(a.name)} />
        ))}
      </div>
      {agents.length === 0 && (
        <div className="glass p-6 text-center text-[12.5px] text-[var(--text-tertiary)] mt-4">
          <Cpu size={20} className="mx-auto mb-2 opacity-50" />
          No agents reporting yet. The backend initializes all six ADK agents at startup \u2014 check the API is running.
        </div>
      )}
      <AnimatePresence>
        {openAgent && <AgentDrawer name={openAgent} onClose={() => setOpenAgent(null)} />}
      </AnimatePresence>
    </div>
  );
}
