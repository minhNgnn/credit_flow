// Typed fetchers for the AI Monitor dashboard. Browser → /api/* rewrite
// → api /monitor/overview and /monitor/logs (server-side, never chạm DB
// nor Langfuse keys directly from the browser).
// Spec contract docs/superpowers/specs/2026-07-19-ai-monitor-dashboard-design.md §6.

export interface MonitorKPI {
  total_cases: number;
  cases_by_state: Record<string, number>;
  total_findings: number;
  total_conflicts: number;
  conflicts_open: number;
  conflicts_unresolved: number;
  total_decisions: number;
  total_events: number;
  total_traces: number;
  total_llm_calls: number;
}

export interface FindingDistEntry { agent_id: string; stance: string; n: number; }
export interface SeverityDistEntry { agent_id: string; severity: string; n: number; }
export interface EventDistEntry { event_type: string; n: number; }
export interface ConflictDistEntry { status: string; n: number; }
export interface ConflictRoundEntry { issue_key: string; max_round: number; n: number; }
export interface DecisionDistEntry { recommendation: string; n: number; }
export interface LatencyEntry { name: string; avg_ms: number; max_ms: number; count: number; }
export interface LLMCallsEntry { case_id: string; n: number; }

export interface MonitorOverview {
  kpi: MonitorKPI;
  findings_distribution: FindingDistEntry[];
  severity_distribution: SeverityDistEntry[];
  event_distribution: EventDistEntry[];
  conflict_distribution: ConflictDistEntry[];
  conflict_round_distribution: ConflictRoundEntry[];
  decision_distribution: DecisionDistEntry[];
  latency: LatencyEntry[];
  llm_calls_per_case: LLMCallsEntry[];
}

export interface WorkerLogs {
  container: string;
  fetched_at: string;
  lines: string[];
  error: string | null;
}

export async function fetchMonitorOverview(): Promise<MonitorOverview> {
  const res = await fetch(`/api/monitor/overview`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchMonitorOverview failed: ${res.status}`);
  return res.json() as Promise<MonitorOverview>;
}

export async function fetchMonitorLogs(lines = 200): Promise<WorkerLogs> {
  const res = await fetch(`/api/monitor/logs?lines=${lines}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchMonitorLogs failed: ${res.status}`);
  return res.json() as Promise<WorkerLogs>;
}

// SSE event shape used by the live activity feed.
export interface StepEvent {
  case_id?: string;
  type: "step_started" | "step_completed" | "step_failed" | "job_started" | "job_completed" | "job_failed" | string;
  step?: string;
  label?: string;
}