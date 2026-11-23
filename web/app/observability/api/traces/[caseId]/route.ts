/**
 * Server-side proxy to Langfuse REST API for one case's trace.
 * Browser never sees LANGFUSE_* keys — only this route handler reads them.
 *
 * Langfuse v3 REST shape (verified live against langfuse:3.221.1):
 *   GET /api/public/traces?metadata.case_id={caseId}&limit=1
 *   Headers: Authorization: Basic base64(pk:sk)
 * Per-trace observations (spans AND generations, type-filtered client-side):
 *   GET /api/public/observations?traceId={traceId}&limit=200
 *
 * Spans and generations are observations with type="SPAN" / "GENERATION";
 * the /api/public/observations endpoint returns both, no need for two calls.
 *
 * Returns: { enabled, trace, spans, generations } — always 200, with
 * reason set on degrade paths so the Traces tab can show a banner.
 *
 * NOTE on real Langfuse REST: this is written defensively; field names
 * follow Langfuse v3 docs (trace.id, trace.name, trace.timestamp,
 * observation.startTime/endTime, observation.parentObservationId,
 * observation.metadata, observation.usage). If the live API differs at
 * run time, the proxy will still return SOMETHING parseable and the
 * Traces tab degrades gracefully to the Postgres-backed case detail.
 */
export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await context.params;
  const host = process.env.LANGFUSE_HOST;
  const pk = process.env.LANGFUSE_PUBLIC_KEY;
  const sk = process.env.LANGFUSE_SECRET_KEY;

  if (!host || !pk || !sk) {
    return Response.json(
      { enabled: false, trace: null, spans: [], generations: [], reason: "OBSERVABILITY not configured" },
      { status: 200 },
    );
  }

  const auth = Buffer.from(`${pk}:${sk}`).toString("base64");
  const headers = { Authorization: `Basic ${auth}`, "Content-Type": "application/json" };

  try {
    const traceRes = await fetch(
      `${host}/api/public/traces?metadata.case_id=${encodeURIComponent(caseId)}&limit=1&order_by=timestamp&order=desc`,
      { headers, cache: "no-store" },
    );
    if (!traceRes.ok) {
      return Response.json(
        { enabled: true, trace: null, spans: [], generations: [], reason: `langfuse responded ${traceRes.status}` },
        { status: 200 },
      );
    }
    const traceData = await traceRes.json();
    const trace = (traceData.data ?? [])[0] ?? null;
    if (!trace) {
      return Response.json({ enabled: true, trace: null, spans: [], generations: [] }, { status: 200 });
    }

    // Single call: GET /api/public/observations?traceId={id} returns both
    // SPAN and GENERATION observations. Filter type client-side.
    const obsRes = await fetch(
      `${host}/api/public/observations?traceId=${encodeURIComponent(trace.id)}&limit=100`,
      { headers, cache: "no-store" },
    );
    const obsData = obsRes.ok ? ((await obsRes.json()).data ?? []) : [];
    const spansData = obsData.filter((o: { type?: string }) => o.type === "SPAN");
    const gensData = obsData.filter((o: { type?: string }) => o.type === "GENERATION");

    return Response.json(
      {
        enabled: true,
        trace: {
          id: trace.id,
          name: trace.name,
          timestamp: trace.timestamp,
          total_cost: trace.totalCost,
          total_tokens: trace.totalTokens,
        },
        spans: spansData.map((s: { id: string; name: string; startTime: string; endTime: string; parentObservationId?: string | null; metadata?: Record<string, unknown>; level?: string; usage?: { promptTokens?: number; completionTokens?: number; totalTokens?: number } }) => ({
          id: s.id,
          name: s.name,
          start_time: s.startTime,
          end_time: s.endTime,
          parent_id: s.parentObservationId ?? null,
          metadata: s.metadata ?? {},
          level: s.level,
        })),
        generations: gensData.map((g: { id: string; name: string; startTime: string; endTime: string; parentObservationId?: string | null; metadata?: Record<string, unknown>; level?: string; usage?: { promptTokens?: number; completionTokens?: number; totalTokens?: number } }) => ({
          id: g.id,
          name: g.name,
          start_time: g.startTime,
          end_time: g.endTime,
          parent_id: g.parentObservationId ?? null,
          metadata: g.metadata ?? {},
          level: g.level,
          usage: g.usage
            ? {
                prompt_tokens: g.usage.promptTokens,
                completion_tokens: g.usage.completionTokens,
                total_tokens: g.usage.totalTokens,
              }
            : undefined,
        })),
      },
      { status: 200 },
    );
  } catch (e) {
    return Response.json(
      { enabled: true, trace: null, spans: [], generations: [], reason: String(e) },
      { status: 200 },
    );
  }
}