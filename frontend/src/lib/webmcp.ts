/**
 * WebMCP tool registration for BoardMind Boardroom.
 *
 * Uses the real, current W3C WebMCP draft API (Web Machine Learning
 * Community Group, CG-DRAFT as of Aug 2026): `document.modelContext`,
 * with `registerTool({name, title, description, inputSchema, execute,
 * annotations})`. This is an experimental, in-progress spec behind an
 * origin trial in Chrome — `document.modelContext` will not exist in most
 * browsers today, so every call here is feature-detected and this module
 * no-ops cleanly when it's absent. See:
 * https://webmachinelearning.github.io/webmcp/
 *
 * These tools are not a bolted-on gimmick: they are the SAME endpoints the
 * Boardroom UI itself calls (lib/api.ts / this file share the API base
 * URL), so a browser agent using WebMCP and a human clicking buttons are
 * both driving the identical backend state — proposals, tasks, and the
 * activity feed are shared, live, and visible to both.
 *
 * Per the WebMCP threat model (spec §6.3.1), tool results that echo back
 * agent-authored text (proposal bodies, report contents) are marked
 * `untrustedContentHint: true` so a calling agent's model treats that
 * content as data, not instructions.
 */
import { API_URL } from "./api";

type ToolExecute = (input: any) => Promise<any>;

interface ToolSpec {
  name: string;
  title: string;
  description: string;
  inputSchema: object;
  execute: ToolExecute;
  readOnlyHint?: boolean;
  untrustedContentHint?: boolean;
}

async function call(path: string, method: "GET" | "POST", body?: unknown) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

const TOOLS: ToolSpec[] = [
  {
    name: "create_project",
    title: "Create Project",
    description:
      "Creates a new company initiative/product and notifies Marketing, Engineering, and HR " +
      "agents, who each independently propose next steps for a human to approve.",
    inputSchema: {
      type: "object",
      properties: { goal: { type: "string", description: "The product/initiative goal, e.g. 'Launch an AI resume builder in one month'" } },
      required: ["goal"],
    },
    execute: async ({ goal }) => call("/api/boardroom/launch", "POST", { goal, role: "ceo" }),
  },
  {
    name: "assign_task",
    title: "Assign Task",
    description: "Assigns a task to an owner within a department.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string" },
        owner: { type: "string" },
        department: { type: "string" },
        deadline: { type: "string", description: "ISO date, optional" },
      },
      required: ["title", "owner"],
    },
    execute: async (input) => call("/api/boardroom/tasks", "POST", { ...input, kind: "task" }),
  },
  {
    name: "generate_campaign",
    title: "Generate Campaign",
    description:
      "Asks the Marketing Agent to propose launch strategies for a given goal. Returns a pending " +
      "proposal id that a human must approve before Design is engaged.",
    inputSchema: { type: "object", properties: { goal: { type: "string" } }, required: ["goal"] },
    execute: async ({ goal }) => call("/api/boardroom/launch", "POST", { goal, role: "cmo" }),
    untrustedContentHint: true,
  },
  {
    name: "create_design",
    title: "Create Design",
    description: "Reads the latest pending design proposal (landing page concepts) for review.",
    inputSchema: { type: "object", properties: {} },
    execute: async () => {
      const proposals = await call("/api/boardroom/proposals?status=pending", "GET");
      return proposals.filter((p: any) => p.kind === "design_concepts");
    },
    readOnlyHint: true,
    untrustedContentHint: true,
  },
  {
    name: "estimate_budget",
    title: "Estimate Budget",
    description: "Reads the latest pending budget review proposal from Finance.",
    inputSchema: { type: "object", properties: {} },
    execute: async () => {
      const proposals = await call("/api/boardroom/proposals?status=pending", "GET");
      return proposals.filter((p: any) => p.kind === "budget_review");
    },
    readOnlyHint: true,
    untrustedContentHint: true,
  },
  {
    name: "approve_budget",
    title: "Approve Budget",
    description: "Approves (or reduces) a pending Finance budget-review proposal by its id.",
    inputSchema: {
      type: "object",
      properties: {
        proposalId: { type: "string" },
        decision: { type: "string", enum: ["approve_anyway", "reduce_budget"] },
        role: { type: "string", description: "Approver's role, e.g. cfo" },
      },
      required: ["proposalId", "decision", "role"],
    },
    execute: async ({ proposalId, decision, role }) =>
      call(`/api/boardroom/proposals/${proposalId}/decision`, "POST", { decision, role }),
  },
  {
    name: "launch_campaign",
    title: "Launch Campaign",
    description: "Approves a pending Marketing campaign-strategy proposal, which engages Design next.",
    inputSchema: {
      type: "object",
      properties: { proposalId: { type: "string" }, role: { type: "string" } },
      required: ["proposalId", "role"],
    },
    execute: async ({ proposalId, role }) =>
      call(`/api/boardroom/proposals/${proposalId}/decision`, "POST", { decision: "approve", role }),
  },
  {
    name: "publish_website",
    title: "Publish Website",
    description: "Approves a pending Design landing-page-concept proposal, marking it selected for publish.",
    inputSchema: {
      type: "object",
      properties: { proposalId: { type: "string" }, role: { type: "string" } },
      required: ["proposalId", "role"],
    },
    execute: async ({ proposalId, role }) =>
      call(`/api/boardroom/proposals/${proposalId}/decision`, "POST", { decision: "approve", role }),
  },
  {
    name: "update_deadline",
    title: "Update Deadline",
    description: "Updates the deadline on an existing task.",
    inputSchema: {
      type: "object",
      properties: { taskId: { type: "string" }, deadline: { type: "string" } },
      required: ["taskId", "deadline"],
    },
    execute: async ({ taskId, deadline }) => call(`/api/boardroom/tasks/${taskId}/deadline`, "POST", { deadline }),
  },
  {
    name: "generate_report",
    title: "Generate Report",
    description: "Returns the current company workspace dashboard (health score, budget, sprint, campaign status).",
    inputSchema: { type: "object", properties: {} },
    execute: async () => call("/api/boardroom/dashboard", "GET"),
    readOnlyHint: true,
  },
  {
    name: "hire_contractor",
    title: "Hire Contractor",
    description: "Approves a pending HR contractor-hire proposal by its id.",
    inputSchema: {
      type: "object",
      properties: { proposalId: { type: "string" }, role: { type: "string" } },
      required: ["proposalId", "role"],
    },
    execute: async ({ proposalId, role }) =>
      call(`/api/boardroom/proposals/${proposalId}/decision`, "POST", { decision: "approve", role }),
  },
  {
    name: "create_sprint",
    title: "Create Sprint",
    description: "Creates a sprint-tracking task for the Engineering department.",
    inputSchema: {
      type: "object",
      properties: { title: { type: "string" }, owner: { type: "string" }, deadline: { type: "string" } },
      required: ["title", "owner"],
    },
    execute: async (input) => call("/api/boardroom/tasks", "POST", { ...input, department: "engineering", kind: "sprint" }),
  },
  {
    name: "complete_task",
    title: "Complete Task",
    description: "Marks a task complete.",
    inputSchema: { type: "object", properties: { taskId: { type: "string" } }, required: ["taskId"] },
    execute: async ({ taskId }) => call(`/api/boardroom/tasks/${taskId}/complete`, "POST"),
  },
];

let registered = false;

/** Feature-detects `document.modelContext` and registers every Boardroom
 * tool if present. Safe to call multiple times (idempotent) and safe to
 * call in browsers without WebMCP support (no-ops). */
export async function registerBoardroomWebMcpTools(): Promise<{ supported: boolean; registered: number }> {
  if (typeof document === "undefined" || !("modelContext" in document)) {
    return { supported: false, registered: 0 };
  }
  if (registered) return { supported: true, registered: TOOLS.length };

  const modelContext = (document as any).modelContext;
  let count = 0;
  for (const tool of TOOLS) {
    try {
      await modelContext.registerTool({
        name: tool.name,
        title: tool.title,
        description: tool.description,
        inputSchema: tool.inputSchema,
        execute: tool.execute,
        annotations: {
          readOnlyHint: !!tool.readOnlyHint,
          untrustedContentHint: !!tool.untrustedContentHint,
        },
      });
      count++;
    } catch (err) {
      // A tool with the same name may already be registered (e.g. React
      // strict-mode double-invoke in dev) — safe to ignore.
      console.warn(`WebMCP: failed to register tool "${tool.name}"`, err);
    }
  }
  registered = true;
  return { supported: true, registered: count };
}

export const BOARDROOM_WEBMCP_TOOL_NAMES = TOOLS.map((t) => t.name);
