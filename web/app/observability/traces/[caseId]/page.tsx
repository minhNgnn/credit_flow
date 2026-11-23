"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import TraceGantt from "../../../components/observability/TraceGantt";
import { fetchLangfuseTrace, type LangfuseTraceBlob } from "../../../lib/observability";

export default function TraceDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [blob, setBlob] = useState<LangfuseTraceBlob | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchLangfuseTrace(caseId)
      .then(setBlob)
      .catch((e: Error) => setErr(String(e)));
  }, [caseId]);

  if (err) {
    return <div className="text-sm text-destructive-foreground">Lỗi tải trace: {err}</div>;
  }
  if (!blob) return <div className="text-sm text-muted-foreground">Đang tải…</div>;
  if (!blob.enabled) {
    return <div className="text-sm text-muted-foreground">Tính năng quan sát chưa bật. Đặt OBSERVABILITY_ENABLED=true và LANGFUSE_HOST để dùng được.</div>;
  }
  if (!blob.trace) {
    return (
      <div className="text-sm text-muted-foreground">
        Chưa có vết chạy Langfuse cho hồ sơ {caseId}. (Có thể worker chưa chạy analyze cho hồ sơ này, hoặc Langfuse chưa nhận được.)
        {blob.reason ? ` ${blob.reason}` : ""}
      </div>
    );
  }

  // Union spans + generations into one Gantt, marked by kind.
  const items = [
    ...blob.spans.map((s) => ({
      name: s.name,
      start: new Date(s.start_time).getTime(),
      end: new Date(s.end_time).getTime(),
      kind: (s.name.startsWith("tool.") ? "tool" : "node") as "tool" | "node",
    })),
    ...blob.generations.map((g) => ({
      name: g.name,
      start: new Date(g.start_time).getTime(),
      end: new Date(g.end_time).getTime(),
      kind: "gen" as const,
    })),
  ].sort((a, b) => a.start - b.start);

  return (
    <div className="space-y-4">
      <h2 className="text-base font-medium">Vết chạy — hồ sơ {caseId}</h2>
      <div className="text-sm text-muted-foreground">
        Trace ID: <code>{blob.trace.id}</code> · Tổng token:{" "}
        {blob.trace.total_tokens ?? "—"} · Cost (USD): {blob.trace.total_cost ?? "—"}
      </div>
      <TraceGantt items={items} />
    </div>
  );
}