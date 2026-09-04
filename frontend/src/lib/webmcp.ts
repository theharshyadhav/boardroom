/**
 * WebMCP integration for BoardMind.
 *
 * WebMCP is experimental, so this module is deliberately optional: browsers
 * without document.modelContext continue to use the application normally.
 */
import { api } from "./api";

type ToolExecute = (input: Record<string, unknown>) => Promise<unknown>;

interface ToolSpec {
  name: string;
  title: string;
  description: string;
  inputSchema: Record<string, unknown>;
  execute: ToolExecute;
  readOnlyHint?: boolean;
  consequentialHint?: boolean;
}

const emptySchema = { type: "object", properties: {} };

const TOOLS: ToolSpec[] = [
  // Exposes the current KPI snapshot, optionally scoped to a region.
  {
    name: "get_kpis",
    title: "Get KPIs",
    description: "Returns BoardMind's current executive KPI snapshot, optionally filtered by region.",
    inputSchema: { type: "object", properties: { region: { type: "string", description: "Optional region filter." } } },
    execute: async ({ region }) => api.kpis(typeof region === "string" ? region : null),
    readOnlyHint: true,
  },
  // Exposes material business events detected by the deterministic analytics layer.
  {
    name: "get_events",
    title: "Get Material Events",
    description: "Returns material business events detected by BoardMind, optionally filtered by region.",
    inputSchema: { type: "object", properties: { region: { type: "string", description: "Optional region filter." } } },
    execute: async ({ region }) => api.events(typeof region === "string" ? region : null),
    readOnlyHint: true,
  },
  // Exposes the price, volume, and other driver decomposition for detected changes.
  {
    name: "get_driver_tree",
    title: "Get Driver Tree",
    description: "Returns the deterministic driver tree explaining the main business changes.",
    inputSchema: emptySchema,
    execute: async () => api.driverTree(),
    readOnlyHint: true,
  },
  // Exposes the source-to-insight evidence graph used for traceability.
  {
    name: "get_evidence",
    title: "Get Evidence",
    description: "Returns the evidence graph linking data sources, KPIs, and material events.",
    inputSchema: emptySchema,
    execute: async () => api.evidenceGraph(),
    readOnlyHint: true,
  },
  // Exposes transparent, deterministic recommendations from the existing engine.
  {
    name: "get_recommendations",
    title: "Get Recommendations",
    description: "Returns BoardMind's current explainable recommendations for executive action.",
    inputSchema: emptySchema,
    execute: async () => api.recommendations(),
    readOnlyHint: true,
  },
  // Exposes the narrative endpoint, which phrases already-computed numbers for a persona.
  {
    name: "generate_summary",
    title: "Generate Executive Summary",
    description: "Generates an executive summary for the requested BoardMind persona.",
    inputSchema: {
      type: "object",
      properties: { persona: { type: "string", description: "Audience persona, such as ceo or finance." } },
      required: ["persona"],
    },
    execute: async ({ persona }) => api.summary(typeof persona === "string" ? persona : "ceo"),
  },
  // Runs the existing business simulation with explicit decision levers.
  {
    name: "run_business_simulation",
    title: "Run Business Simulation",
    description: "Simulates business outcomes using BoardMind's existing decision simulation engine.",
    inputSchema: {
      type: "object",
      properties: {
        region: { type: "string", description: "Optional region to simulate." },
        priceChangePct: { type: "number", description: "Price change percentage." },
        marketingSpendPct: { type: "number", description: "Marketing spend change percentage." },
        inventoryInvestPct: { type: "number", description: "Inventory investment change percentage." },
        supplierSwitch: { type: "boolean", description: "Whether to switch supplier." },
      },
      required: ["priceChangePct", "marketingSpendPct", "inventoryInvestPct", "supplierSwitch"],
    },
    execute: async ({ region, priceChangePct, marketingSpendPct, inventoryInvestPct, supplierSwitch }) =>
      api.simulate(typeof region === "string" ? region : null, {
        priceChangePct: Number(priceChangePct),
        marketingSpendPct: Number(marketingSpendPct),
        inventoryInvestPct: Number(inventoryInvestPct),
        supplierSwitch: supplierSwitch === true,
      }),
  },
  // Exposes the registered enterprise agents and their current health.
  {
    name: "get_agents",
    title: "Get Agents",
    description: "Returns BoardMind's registered enterprise agents, capabilities, and health status.",
    inputSchema: emptySchema,
    execute: async () => api.agents(),
    readOnlyHint: true,
  },
  // Starts the real Boardroom workflow and returns its workflow identifier.
  {
    name: "launch_boardroom_workflow",
    title: "Launch Boardroom Workflow",
    description: "Launches a Boardroom initiative workflow for the supplied goal and role.",
    inputSchema: {
      type: "object",
      properties: {
        goal: { type: "string", description: "Initiative or business goal." },
        role: { type: "string", description: "Launching role, defaulting to ceo." },
      },
      required: ["goal"],
    },
    execute: async ({ goal, role }) => api.launchProject(String(goal), typeof role === "string" ? role : "ceo"),
    consequentialHint: true,
  },
  // Exposes the live Boardroom dashboard derived from proposals, tasks, and activity.
  {
    name: "get_boardroom_dashboard",
    title: "Get Boardroom Dashboard",
    description: "Returns the current Boardroom health, budget, sprint, campaign, and approval dashboard.",
    inputSchema: emptySchema,
    execute: async () => api.boardroomDashboard(),
    readOnlyHint: true,
  },
  // Exposes Boardroom tasks, optionally filtered by status.
  {
    name: "get_tasks",
    title: "Get Boardroom Tasks",
    description: "Returns Boardroom tasks, optionally filtered by task status.",
    inputSchema: { type: "object", properties: { status: { type: "string", description: "Optional task status filter." } } },
    execute: async ({ status }) => api.tasks(typeof status === "string" ? status : undefined),
    readOnlyHint: true,
  },
  // Exposes runtime observability metrics for the agent platform.
  {
    name: "get_observability",
    title: "Get Observability",
    description: "Returns BoardMind agent execution, workflow, failure, and LLM telemetry metrics.",
    inputSchema: emptySchema,
    execute: async () => api.obsSummary(),
    readOnlyHint: true,
  },
  // Checks whether the deployed FastAPI backend is healthy.
  {
    name: "health_check",
    title: "Health Check",
    description: "Checks the health of the deployed BoardMind backend API.",
    inputSchema: emptySchema,
    execute: async () => api.health(),
    readOnlyHint: true,
  },
];

let registered = false;
let registrationPromise: Promise<{ supported: boolean; registered: number }> | null = null;

/** Registers all BoardMind tools when the browser implements WebMCP. */
export async function registerWebMcpTools(): Promise<{ supported: boolean; registered: number }> {
  if (registrationPromise) return registrationPromise;

  registrationPromise = registerToolsOnce();
  return registrationPromise;
}

async function registerToolsOnce(): Promise<{ supported: boolean; registered: number }> {
  if (typeof document === "undefined" || !("modelContext" in document)) {
    return { supported: false, registered: 0 };
  }

  const modelContext = (document as Document & {
    modelContext?: { registerTool: (tool: Record<string, unknown>) => void | Promise<void> };
  }).modelContext;
  if (!modelContext || typeof modelContext.registerTool !== "function") {
    return { supported: false, registered: 0 };
  }
  if (registered) return { supported: true, registered: TOOLS.length };

  let count = 0;
  for (const tool of TOOLS) {
    try {
      await modelContext.registerTool({
        name: tool.name,
        title: tool.title,
        description: tool.description,
        inputSchema: tool.inputSchema,
        execute: async (input: Record<string, unknown>) => {
          try {
            return await tool.execute(input);
          } catch (error) {
            return {
              ok: false,
              error: error instanceof Error ? error.message : "WebMCP tool execution failed",
            };
          }
        },
        annotations: {
          readOnlyHint: tool.readOnlyHint === true,
          consequentialHint: tool.consequentialHint === true,
        },
      });
      count++;
    } catch (error) {
      console.warn(`WebMCP: failed to register tool "${tool.name}"`, error);
    }
  }
  registered = true;
  console.log(`Registered ${count} WebMCP tools`);
  return { supported: true, registered: count };
}

// Kept for the existing Boardroom status panel; registration is now app-wide.
export const registerBoardroomWebMcpTools = registerWebMcpTools;
export const BOARDROOM_WEBMCP_TOOL_NAMES = TOOLS.map((tool) => tool.name);
