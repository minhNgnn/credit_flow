import type { CaseSummary } from "./types";

// Reuses /api/* proxy (next.config.mjs rewrites to api). Same convention
// as web/app/lib/api.ts — never talk to Postgres/Redis from the browser.

export async function fetchObservabilityCases(): Promise<CaseSummary[]> {
  const res = await fetch(`/api/cases`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchObservabilityCases failed: ${res.status}`);
  const data = await res.json();
  return data.cases as CaseSummary[];
}

export interface TraceLink {
  langfuse_trace_id: string;
  langfuse_url: string | null;
}

export async function fetchTraceLink(caseId: string): Promise<TraceLink> {
  const res = await fetch(`/api/observability/cases/${caseId}/trace`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchTraceLink failed: ${res.status}`);
  return res.json() as Promise<TraceLink>;
}

export interface LangfuseSpan {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  parent_id?: string | null;
  metadata?: Record<string, unknown>;
  level?: "DEBUG" | "DEFAULT" | "WARNING" | "ERROR";
}

export interface LangfuseGeneration extends LangfuseSpan {
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

export interface LangfuseTraceSummary {
  id: string;
  name: string;
  timestamp: string;
  total_cost?: number;
  total_tokens?: number;
}

export interface LangfuseTraceBlob {
  enabled: boolean;
  trace: LangfuseTraceSummary | null;
  spans: LangfuseSpan[];
  generations: LangfuseGeneration[];
  reason?: string;
}

export async function fetchLangfuseTrace(caseId: string): Promise<LangfuseTraceBlob> {
  const res = await fetch(`/observability/api/traces/${caseId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchLangfuseTrace failed: ${res.status}`);
  return res.json() as Promise<LangfuseTraceBlob>;
}