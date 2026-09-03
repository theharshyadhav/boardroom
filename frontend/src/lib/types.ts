export type MaterialityBand = "critical" | "high" | "medium" | "low";
export type ConfidenceBand = "high" | "medium" | "low";

export interface RoleProfile {
  key?: string;
  name: string;
  title: string;
  region: string | null;
  hideFinance: boolean;
}

export interface Confidence {
  score: number;
  band: ConfidenceBand;
  breakdown?: Record<string, number>;
}

export interface DataSource {
  id: string;
  name: string;
  cadenceMins: number;
  count: number;
  freshnessMins: number;
  freshnessLabel: string;
  lineage: string;
}

export interface MaterialWindow {
  offset: number;
  pct: number;
  z: number;
  start_date: string;
  end_date: string;
}

export interface KpiSeries {
  values: number[];
  latest: number;
  liveDeltaPct: number;
  materialWindow: MaterialWindow;
  materialityBand: MaterialityBand;
}

export interface KpiResponse {
  dates: string[];
  series: Record<"revenue" | "profit" | "orders" | "invHealth" | "csat", KpiSeries>;
}

export interface MaterialEvent {
  id: string;
  title: string;
  severity: MaterialityBand;
  kpi: string;
  region: string | null;
  body: string;
  sources: string[];
  confidence: Confidence;
  abstain?: boolean;
  eventWindow?: { start: string; end: string };
}

export interface DriverNode {
  id: string;
  label: string;
  pct: number;
  value?: number;
  parent?: string;
}

export interface DriverTree {
  nodes: DriverNode[];
  southDeltaPct: number;
  totalDeltaPct: number;
  eventWindow: { start: string; end: string };
  southZ: number;
  priceEffect: number;
  volumeEffect: number;
}

export interface Recommendation {
  id: string;
  driver: string;
  lever: string;
  action: string;
  impact: string;
  owner: string;
  confidence: Confidence;
  monitoring: string;
  feedbackStats?: FeedbackStats;
}

export interface FeedbackStats {
  accepted: number;
  rejected: number;
  modified: number;
  blended: number;
}

export interface BoardroomMessage {
  role: string;
  message: string;
}

export interface SimulateResult {
  base: { revenue: number; profit: number; orders: number; invHealth: number; csat: number };
  result: { revenue: number; profit: number; orders: number; invHealth: number; risk: number; csat: number };
}

export interface TelemetryLogEntry {
  ts: string;
  cached: boolean;
  ok?: boolean;
  latency?: number;
  inTok?: number;
  outTok?: number;
  reason?: string;
}

export interface Telemetry {
  provider: string;
  model: string;
  configured: boolean;
  calls: number;
  cacheHits: number;
  avgLatencyMs: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
  log: TelemetryLogEntry[];
}

export interface EvidenceGraphNode {
  id: string;
  position: { x: number; y: number };
  data: { label: string; kind: string; severity?: string };
}
export interface EvidenceGraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}
export interface EvidenceGraph {
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
}
