import type {
  RoleProfile, DataSource, KpiResponse, MaterialEvent, DriverTree,
  Recommendation, FeedbackStats, BoardroomMessage, SimulateResult, Telemetry, EvidenceGraph,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://boardroom-api-25xh.onrender.com")
  .trim()
  .replace(/\/+$/, "");
const BASE = API_URL;

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string }>("/api/health"),

  listRoles: () => req<Array<{ key: string } & RoleProfile>>("/api/auth/roles"),
  login: (role: string) =>
    req<{ token: string; role: string; profile: RoleProfile }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ role }),
    }),

  freshness: () => req<DataSource[]>("/api/data/freshness"),

  kpis: (region?: string | null) =>
    req<KpiResponse>(`/api/kpis${region ? `?region=${encodeURIComponent(region)}` : ""}`),

  events: (region?: string | null) =>
    req<MaterialEvent[]>(`/api/events${region ? `?region=${encodeURIComponent(region)}` : ""}`),

  driverTree: () => req<DriverTree>("/api/driver-tree"),

  evidenceSources: () => req<DataSource[]>("/api/evidence/sources"),
  evidenceInsights: () => req<MaterialEvent[]>("/api/evidence/insights"),
  evidenceGraph: () => req<EvidenceGraph>("/api/evidence/graph"),

  recommendations: () => req<Recommendation[]>("/api/recommendations"),

  getFeedback: (recId: string) => req<FeedbackStats>(`/api/feedback/${recId}`),
  postFeedback: (recId: string, action: "accepted" | "rejected" | "modified") =>
    req<FeedbackStats>("/api/feedback", { method: "POST", body: JSON.stringify({ recId, action }) }),
  resetFeedback: () => req<{ ok: boolean }>("/api/feedback", { method: "DELETE" }),

  simulate: (region: string | null, levers: {
    priceChangePct: number; marketingSpendPct: number; inventoryInvestPct: number; supplierSwitch: boolean;
  }) =>
    req<SimulateResult>(`/api/simulate${region ? `?region=${encodeURIComponent(region)}` : ""}`, {
      method: "POST",
      body: JSON.stringify(levers),
    }),

  summary: (persona: string) => req<{ persona: string; text: string }>(`/api/summary?persona=${persona}`),
  boardroom: () => req<BoardroomMessage[]>("/api/boardroom"),
  ask: (question: string) => req<{ answer: string }>("/api/ask", { method: "POST", body: JSON.stringify({ question }) }),

  telemetry: () => req<Telemetry>("/api/telemetry"),

  // --- Enterprise agent platform ------------------------------------------
  agents: () => req<AgentSummary[]>("/api/agents"),
  agentDetail: (name: string) => req<AgentDetail>(`/api/agents/${name}`),
  runAgent: (name: string, role: string) =>
    req<{ status: string; workflow_id: string; topic: string }>(`/api/agents/${name}/run`, {
      method: "POST",
      body: JSON.stringify({ role }),
    }),

  watchStatus: () => req<WatchStatus>("/api/watch/status"),
  toggleWatch: (enabled: boolean) =>
    req<{ enabled: boolean }>(`/api/watch/toggle?enabled=${enabled}`, { method: "POST" }),
  triggerReportUploaded: (filename: string) =>
    req<{ status: string; workflow_id: string }>(`/api/watch/report-uploaded?filename=${encodeURIComponent(filename)}`, {
      method: "POST",
    }),
  triggerScheduledTick: (job: string) =>
    req<{ status: string; workflow_id: string; job: string }>(`/api/watch/scheduled-tick?job=${encodeURIComponent(job)}`, {
      method: "POST",
    }),

  obsSummary: () => req<ObservabilitySummary>("/api/observability/summary"),
  workflows: (limit = 20) => req<WorkflowSummary[]>(`/api/observability/workflows?limit=${limit}`),
  workflowTimeline: (id: string) => req<WorkflowTimeline>(`/api/observability/workflows/${id}`),
  alerts: (unackOnly = false) => req<Alert[]>(`/api/observability/alerts?unacknowledged_only=${unackOnly}`),
  ackAlert: (alertId: string) =>
    req<{ status: string }>("/api/observability/alerts/ack", { method: "POST", body: JSON.stringify({ alertId }) }),
  auditLog: (limit = 100) => req<AuditEntry[]>(`/api/observability/audit-log?limit=${limit}`),

  // --- Boardroom collaboration -------------------------------------------
  launchProject: (goal: string, role = "ceo") =>
    req<{ status: string; workflow_id: string }>("/api/boardroom/launch", { method: "POST", body: JSON.stringify({ goal, role }) }),
  proposals: (status: "pending" | "all" = "pending") => req<Proposal[]>(`/api/boardroom/proposals?status=${status}`),
  decideProposal: (proposalId: string, decision: string, role: string, edited_payload?: Record<string, unknown>) =>
    req<{ status: string; proposal: Proposal }>(`/api/boardroom/proposals/${proposalId}/decision`, {
      method: "POST", body: JSON.stringify({ decision, role, edited_payload }),
    }),
  boardroomActivity: (limit = 60) => req<ActivityEntry[]>(`/api/boardroom/activity?limit=${limit}`),
  boardroomWorkflows: (limit = 10) => req<{ workflow_id: string; started_at: string }[]>(`/api/boardroom/workflows?limit=${limit}`),
  boardroomConversation: (workflowId: string) => req<Conversation>(`/api/boardroom/conversation/${workflowId}`),
  boardroomDashboard: () => req<BoardroomDashboard>("/api/boardroom/dashboard"),
  tasks: (status?: string) => req<TaskItem[]>(`/api/boardroom/tasks${status ? `?status=${status}` : ""}`),
};

export interface ConversationMessage {
  speaker: string; text: string; kind: "proposal" | "decision" | "activity"; ts: string;
}
export interface Conversation {
  workflow_id: string; messages: ConversationMessage[];
}

export interface Proposal {
  id: string; agent: string; kind: string; title: string; body: string;
  payload: Record<string, unknown>; actions: string[]; status: string;
  decision: string | null; decided_by: string | null; workflow_id: string; created_at: string;
}
export interface ActivityEntry {
  agent: string; verb: string; detail: string; workflow_id?: string;
  department_color?: string; ts: string;
}
export interface TaskItem {
  id: string; title: string; owner: string; department: string;
  deadline: string | null; kind: string; status: string; created_at: string;
}
export interface BoardroomDashboard {
  company_health_score: number; budget_status: string; sprint_progress_pct: number;
  campaign_status: string; active_agents: number; total_agents: number;
  pending_approvals: number; recent_decisions: Proposal[]; upcoming_milestones: TaskItem[];
}

export interface AgentSummary {
  name: string; version: string; description: string; capabilities: string[];
  permissions: string[]; subscribes_to: string[]; status: string; health: string;
  last_execution_ts?: string; execution_count?: number; avg_runtime_ms?: number; memory_size: number;
}
export interface AgentDetail extends AgentSummary {
  recent_memory: Array<{ id: string; kind: string; summary: string; data: unknown; created_at: string }>;
}
export interface WatchStatus {
  enabled: boolean; interval_seconds: number; last_tick_at?: string; last_tick_job?: string; pubsub_live: boolean;
}
export interface ObservabilitySummary {
  agents_total: number; agents_running: number; agents_healthy: number; total_executions: number;
  workflows_tracked: number; failed_workflows: number;
  llm_telemetry: { calls: number; cache_hits: number; in_tokens: number; out_tokens: number; estimated_cost_usd: number };
}
export interface WorkflowSummary {
  workflow_id: string; root_topic: string; started_at: string; status: string;
}
export interface WorkflowStep {
  agent: string; topic_in: string; topic_out: string | null; duration_ms: number;
  status: string; reasoning_summary: string; error?: string | null; ts: string;
}
export interface WorkflowTimeline extends WorkflowSummary {
  steps: WorkflowStep[];
}
export interface Alert {
  id: string; severity: string; title: string; body: string; agent: string;
  workflow_id?: string; created_at: string; acknowledged: boolean;
}
export interface AuditEntry {
  action: string; decision: string; detail: Record<string, unknown>; ts: string;
}
