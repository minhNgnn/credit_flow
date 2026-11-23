"use client";

import { useEffect, useRef, useState } from "react";

import { fetchMonitorLogs, type WorkerLogs } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

export default function WorkerLogsBox() {
  const { tv, lang } = useI18n();
  const [data, setData] = useState<WorkerLogs | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchLogs = () => {
      fetchMonitorLogs(200)
        .then((d) => { if (!cancelled) { setData(d); setErr(null); } })
        .catch((e: Error) => { if (!cancelled) setErr(String(e)); });
    };
    fetchLogs();
    timerRef.current = setInterval(fetchLogs, 10000);
    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div>
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">{tv("Nhật ký worker (200 dòng, poll 10s)")}</h4>
      {err && <div className="text-sm text-red-700">{tv("Lỗi:")} <code>{err}</code></div>}
      {data?.error && !err && (
        <div className="text-sm text-amber-700">
          {tv("Docker không khả dụng")}: <code>{data.error}</code> — {tv("chạy monitor trong host có Docker để xem log.")}
        </div>
      )}
      {data?.lines && data.lines.length > 0 ? (
        <pre className="max-h-72 overflow-auto rounded border border-border bg-muted p-2 text-xs leading-tight font-mono whitespace-pre-wrap">
          {data.lines.join("\n")}
        </pre>
      ) : null}
      {!data?.error && data?.lines && data.lines.length === 0 ? (
        <div className="text-sm text-muted-foreground">{tv("Chưa có log worker.")}</div>
      ) : null}
      {data?.fetched_at ? (
        <div className="mt-1 text-[10px] text-muted-foreground">{tv("Lúc")} {new Date(data.fetched_at).toLocaleString(lang === "en" ? "en-GB" : "vi-VN")} · container {data.container}</div>
      ) : null}
    </div>
  );
}
