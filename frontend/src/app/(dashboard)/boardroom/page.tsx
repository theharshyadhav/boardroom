"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, CheckCircle2, Rocket, Check, Pencil, X, Activity, Gauge, Wallet, Megaphone, Users2, MessageSquare, List } from "lucide-react";
import { api } from "@/lib/api";
import type { Proposal, ActivityEntry, BoardroomDashboard, ConversationMessage, AgentSummary } from "@/lib/api";
import { registerBoardroomWebMcpTools } from "@/lib/webmcp";
import { PageHeader } from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import type { BoardroomMessage } from "@/lib/types";

const AGENT_COLOR: Record<string, string> = {
  CEO: "linear-gradient(135deg,#8B5CF6,#6D28D9)", CFO: "linear-gradient(135deg,#3B82F6,#1D4ED8)",
  CMO: "linear-gradient(135deg,#22D3EE,#0891B2)", COO: "linear-gradient(135deg,#34D399,#059669)",
  "Risk Officer": "linear-gradient(135deg,#F87171,#B91C1C)", "Operations Head": "linear-gradient(135deg,#FBBF24,#B45309)",
};
const DEPT_TONE: Record<string, string> = {
  marketing_agent: "#22D3EE", design_agent: "#F472B6", engineering_agent: "#34D399",
  hr_agent: "#FBBF24", finance_agent: "#8B5CF6", CEO: "#A78BFA", system: "#94A3B8",
};

function initials(role: string) {
  return role.split(/[_ ]/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

function ProposalCard({ p, onDecide }: { p: Proposal; onDecide: (decision: string) => void }) {
  const color = DEPT_TONE[p.agent] ?? "#8B5CF6";
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 30 }} className="glass p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-extrabold text-white shrink-0" style={{ background: color }}>
          {initials(p.agent)}
        </div>
        <div className="text-[12.5px] font-bold">{p.agent.replace(/_/g, " ")}</div>
        <Badge tone="medium">{p.kind.replace(/_/g, " ")}</Badge>
      </div>
      <div className="text-[13px] font-semibold mb-1">{p.title}</div>
      <div className="text-[12px] text-[var(--text-secondary)] leading-relaxed mb-3 whitespace-pre-wrap">{p.body}</div>
      <div className="flex flex-wrap gap-2">
        {p.actions.map((action) => (
          <Button key={action} size="sm" variant={action === "reject" ? "ghost" : "primary"} onClick={() => onDecide(action)}>
            {action === "approve" && <Check size={12} />}
            {action === "reject" && <X size={12} />}
            {action === "edit" && <Pencil size={12} />}
            {action.replace(/_/g, " ")}
          </Button>
        ))}
      </div>
    </motion.div>
  );
}

function StatCard({ icon: Icon, label, value }: { icon: any; label: string; value: React.ReactNode }) {
  return (
    <div className="glass px-4 py-3.5 flex items-center gap-3">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--grad-brand-soft)" }}>
        <Icon size={15} className="text-[var(--purple)]" />
      </div>
      <div>
        <div className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wide">{label}</div>
        <div className="text-[15px] font-bold">{value}</div>
      </div>
    </div>
  );
}

const HUMAN_ROLES = new Set(["ceo", "cmo", "cfo", "coo", "human", "risk_officer", "operations_head"]);

function isHuman(speaker: string) {
  return HUMAN_ROLES.has(speaker.toLowerCase()) || !speaker.includes("_agent");
}

function ChatBubble({ msg }: { msg: ConversationMessage }) {
  const mine = isHuman(msg.speaker);
  const color = DEPT_TONE[msg.speaker] ?? (mine ? "#8B5CF6" : "#94A3B8");
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`flex ${mine ? "justify-end" : "justify-start"} mb-2.5`}
    >
      <div className={`flex gap-2 max-w-[85%] ${mine ? "flex-row-reverse" : ""}`}>
        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-extrabold text-white shrink-0 mt-0.5"
             style={{ background: color }}>
          {initials(msg.speaker)}
        </div>
        <div>
          <div className={`text-[10px] text-[var(--text-tertiary)] mb-0.5 ${mine ? "text-right" : ""}`}>
            {msg.speaker.replace(/_/g, " ")} {msg.kind === "decision" && <Badge tone="low">decision</Badge>}
          </div>
          <div
            className="text-[12px] leading-relaxed px-3 py-2 rounded-2xl whitespace-pre-wrap"
            style={{
              background: mine ? "var(--grad-brand-soft)" : "rgba(255,255,255,0.04)",
              border: `1px solid ${mine ? "rgba(139,92,246,0.3)" : "rgba(255,255,255,0.08)"}`,
              borderTopRightRadius: mine ? 4 : undefined,
              borderTopLeftRadius: mine ? undefined : 4,
            }}
          >
            {msg.text}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function TypingIndicator({ agent }: { agent: string }) {
  return (
    <div className="flex items-center gap-2 mb-2.5">
      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-extrabold text-white shrink-0"
           style={{ background: DEPT_TONE[agent] ?? "#94A3B8" }}>
        {initials(agent)}
      </div>
      <div className="px-3 py-2 rounded-2xl rounded-tl-[4px] flex gap-1" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
        {[0, 1, 2].map((i) => (
          <motion.span key={i} className="w-1.5 h-1.5 rounded-full bg-[var(--text-tertiary)]"
            animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }} />
        ))}
      </div>
    </div>
  );
}

function ConversationPanel() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [runningAgents, setRunningAgents] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const workflows = await api.boardroomWorkflows(1).catch(() => []);
      const agents = await api.agents().catch(() => [] as AgentSummary[]);
      if (cancelled) return;
      setRunningAgents(agents.filter((a) => a.status === "running").map((a) => a.name));
      if (workflows.length === 0) { setMessages([]); return; }
      const conv = await api.boardroomConversation(workflows[0].workflow_id).catch(() => null);
      if (conv && !cancelled) setMessages(conv.messages);
    };
    load();
    const id = setInterval(load, 3000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return (
    <div className="glass p-4 max-h-[560px] overflow-y-auto">
      {messages.length === 0 && (
        <div className="text-[12.5px] text-[var(--text-tertiary)] text-center py-8">
          No conversation yet \u2014 launch a project to watch departments talk it through.
        </div>
      )}
      <AnimatePresence>
        {messages.map((m, i) => <ChatBubble key={i} msg={m} />)}
      </AnimatePresence>
      {runningAgents.map((a) => <TypingIndicator key={a} agent={a} />)}
    </div>
  );
}

function CollaborationTab() {
  const { roleKey } = useAuth();
  const [goal, setGoal] = useState("Launch an AI Resume Builder in one month");
  const [launching, setLaunching] = useState(false);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [dashboard, setDashboard] = useState<BoardroomDashboard | null>(null);
  const [webmcp, setWebmcp] = useState<{ supported: boolean; registered: number } | null>(null);
  const [rightView, setRightView] = useState<"conversation" | "timeline">("conversation");

  const refresh = () => {
    api.proposals("pending").then(setProposals).catch(() => {});
    api.boardroomActivity(40).then(setActivity).catch(() => {});
    api.boardroomDashboard().then(setDashboard).catch(() => {});
  };

  useEffect(() => {
    refresh();
    registerBoardroomWebMcpTools().then(setWebmcp);
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, []);

  async function launch() {
    setLaunching(true);
    try {
      await api.launchProject(goal, roleKey || "ceo");
      setTimeout(refresh, 600);
    } finally {
      setLaunching(false);
    }
  }

  async function decide(proposal: Proposal, decision: string) {
    await api.decideProposal(proposal.id, decision, roleKey || "ceo").catch(() => {});
    refresh();
  }

  return (
    <div>
      <div className="glass p-4 mb-4 flex items-center gap-3">
        <input
          value={goal} onChange={(e) => setGoal(e.target.value)}
          placeholder="Launch an AI Resume Builder in one month"
          className="flex-1 bg-transparent border border-white/[0.12] rounded-lg px-3.5 py-2.5 text-[13px] outline-none focus:border-[var(--purple)]"
        />
        <Button variant="primary" onClick={launch} disabled={launching || !goal.trim()}>
          <Rocket size={13} /> {launching ? "Launching\u2026" : "Launch"}
        </Button>
      </div>

      {dashboard && (
        <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: "repeat(6,1fr)" }}>
          <StatCard icon={Gauge} label="Health score" value={dashboard.company_health_score} />
          <StatCard icon={Wallet} label="Budget" value={dashboard.budget_status.replace(/_/g, " ")} />
          <StatCard icon={Activity} label="Sprint" value={`${dashboard.sprint_progress_pct}%`} />
          <StatCard icon={Megaphone} label="Campaign" value={dashboard.campaign_status.replace(/_/g, " ")} />
          <StatCard icon={Users2} label="Active agents" value={`${dashboard.active_agents}/${dashboard.total_agents}`} />
          <StatCard icon={CheckCircle2} label="Pending approvals" value={dashboard.pending_approvals} />
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 max-lg:grid-cols-1">
        <div>
          <div className="text-[12px] font-bold uppercase tracking-wide text-[var(--text-tertiary)] mb-2.5">Pending human approvals</div>
          <div className="flex flex-col gap-3">
            <AnimatePresence>
              {proposals.length === 0 && (
                <div className="glass p-5 text-[12.5px] text-[var(--text-tertiary)] text-center">
                  No pending proposals \u2014 launch a project above to see departments collaborate.
                </div>
              )}
              {proposals.map((p) => (
                <ProposalCard key={p.id} p={p} onDecide={(d) => decide(p, d)} />
              ))}
            </AnimatePresence>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2.5">
            <div className="text-[12px] font-bold uppercase tracking-wide text-[var(--text-tertiary)]">
              {rightView === "conversation" ? "Agent conversation" : "Live activity"}
            </div>
            <div className="flex gap-1">
              <button onClick={() => setRightView("conversation")}
                className={`p-1.5 rounded-md ${rightView === "conversation" ? "bg-white/[0.08]" : "text-[var(--text-tertiary)]"}`}
                title="Conversation view"><MessageSquare size={13} /></button>
              <button onClick={() => setRightView("timeline")}
                className={`p-1.5 rounded-md ${rightView === "timeline" ? "bg-white/[0.08]" : "text-[var(--text-tertiary)]"}`}
                title="Timeline view"><List size={13} /></button>
            </div>
          </div>

          {rightView === "conversation" ? (
            <ConversationPanel />
          ) : (
            <div className="glass p-0 overflow-hidden max-h-[560px] overflow-y-auto">
              {activity.length === 0 && <div className="p-5 text-[12.5px] text-[var(--text-tertiary)]">No activity yet.</div>}
              {activity.map((a, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  className="flex items-start gap-2.5 px-3.5 py-2.5 border-b border-white/[0.06] last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: DEPT_TONE[a.agent] ?? "#8B5CF6" }} />
                  <div className="min-w-0">
                    <span className="text-[12px] font-semibold">{a.agent.replace(/_/g, " ")}</span>
                    <span className="text-[12px] text-[var(--text-tertiary)]"> {a.verb} </span>
                    <div className="text-[11.5px] text-[var(--text-secondary)] truncate">{a.detail}</div>
                  </div>
                  <span className="ml-auto text-[10px] text-[var(--text-tertiary)] shrink-0">{new Date(a.ts).toLocaleTimeString()}</span>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {webmcp && (
        <div className="text-[10.5px] text-[var(--text-tertiary)] mt-4">
          WebMCP tools {webmcp.supported ? `registered (${webmcp.registered}) \u2014 this browser's built-in agent can drive this page directly` : "not supported in this browser yet (experimental W3C spec, Chrome origin trial) \u2014 the same actions are available via the UI above"}.
        </div>
      )}
    </div>
  );
}

function PerspectivesTab() {
  const [agentsMsgs, setAgentsMsgs] = useState<BoardroomMessage[]>([]);
  const [loading, setLoading] = useState(true);

  function convene() {
    setLoading(true);
    api.boardroom().then(setAgentsMsgs).finally(() => setLoading(false));
  }
  useEffect(() => { convene(); }, []);

  const execs = agentsMsgs.filter((a) => a.role !== "Decision Agent");
  const decision = agentsMsgs.find((a) => a.role === "Decision Agent");

  return (
    <div>
      <div className="flex justify-end mb-3">
        <Button variant="primary" size="sm" onClick={convene} disabled={loading}><Send size={13} /> Convene the boardroom</Button>
      </div>
      <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        {loading
          ? [0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="glass p-4.5">
                <div className="skeleton w-9 h-9 rounded-[11px] mb-2.5" />
                <div className="skeleton h-3 w-[70%] mb-2" />
                <div className="skeleton h-3 w-full mb-1.5" />
                <div className="skeleton h-3 w-[60%]" />
              </div>
            ))
          : execs.map((a, i) => (
              <motion.div key={a.role} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }} className="glass p-4.5">
                <div className="flex items-center gap-2.5 mb-2.5">
                  <div className="w-9 h-9 rounded-[11px] flex items-center justify-center text-[13px] font-extrabold text-white shrink-0" style={{ background: AGENT_COLOR[a.role] || AGENT_COLOR.CEO }}>
                    {initials(a.role)}
                  </div>
                  <div>
                    <div className="text-[13.5px] font-bold">{a.role}</div>
                    <div className="text-[10.5px] text-[var(--text-tertiary)]">Executive perspective</div>
                  </div>
                </div>
                <div className="text-[12.5px] leading-relaxed text-[var(--text-secondary)]">{a.message}</div>
              </motion.div>
            ))}
        {!loading && decision && (
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
            className="glass p-5 col-span-3 max-lg:col-span-1" style={{ background: "var(--grad-brand-soft)", borderColor: "rgba(139,92,246,0.35)" }}
          >
            <div className="flex items-center gap-2.5 mb-2.5">
              <div className="w-9 h-9 rounded-[11px] flex items-center justify-center text-white" style={{ background: "var(--grad-brand)" }}>
                <CheckCircle2 size={18} />
              </div>
              <div>
                <div className="text-[13.5px] font-bold">Decision Agent \u2014 Consensus</div>
                <div className="text-[10.5px] text-[var(--text-tertiary)]">Synthesized from all six perspectives above</div>
              </div>
            </div>
            <div className="text-[13px] text-white leading-relaxed">{decision.message}</div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default function BoardroomPage() {
  const [tab, setTab] = useState<"collab" | "perspectives">("collab");
  return (
    <div>
      <PageHeader title="Boardroom" sub="Human + AI departments collaborating in real time \u2014 you're always the decision maker" />
      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab("collab")} className={`text-[12px] font-semibold px-3 py-1.5 rounded-lg ${tab === "collab" ? "bg-white/[0.08]" : "text-[var(--text-tertiary)]"}`}>Collaboration</button>
        <button onClick={() => setTab("perspectives")} className={`text-[12px] font-semibold px-3 py-1.5 rounded-lg ${tab === "perspectives" ? "bg-white/[0.08]" : "text-[var(--text-tertiary)]"}`}>Executive Perspectives</button>
      </div>
      {tab === "collab" ? <CollaborationTab /> : <PerspectivesTab />}
    </div>
  );
}
