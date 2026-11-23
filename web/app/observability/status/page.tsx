"use client";

import { useEffect, useState } from "react";

import CaseQueueTable from "../../components/observability/CaseQueueTable";
import { fetchObservabilityCases } from "../../lib/observability";
import type { CaseSummary } from "../../lib/types";
import { useI18n } from "../../lib/i18n";

interface LiveStep {
  case_id: string;
  type: "step_started" | "step_completed" | "step_failed";
  label: string;
  ts: number;
}

export default function StatusTab() {
  const { tv } = useI18n();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [live, setLive] = useState<Record<string, LiveStep>>({});

  useEffect(() => {
    fetchObservabilityCases()
      .then(setCases)
      .catch((e) => console.error("fetchObservabilityCases:", e));
  }, []);

  useEffect(() => {
    // One SSE per visible case for v1 — light for hackathon. The existing
    // /api/cases/{id}/stream endpoint (next.config.mjs rewrites /api/* to
    // api) carries step_started/step_completed/step_failed events.
    const active = cases.slice(0, 5);
    const sources: EventSource[] = [];
    for (const c of active) {
      const source = new EventSource(`/api/cases/${c.case_id}/stream`);
      source.addEventListener("message", (ev: MessageEvent) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data);
          if (["step_started", "step_completed", "step_failed"].includes(data.type)) {
            setLive((prev) => ({
              ...prev,
              [c.case_id]: { case_id: c.case_id, type: data.type, label: data.label ?? data.step, ts: Date.now() },
            }));
          }
        } catch {
          /* ignore non-JSON keepalive */
        }
      });
      sources.push(source);
    }
    return () => sources.forEach((s) => s.close());
  }, [cases]);

  return (
    <div>
      <h2 className="mb-3 text-base font-medium">{tv("Hàng đợi hồ sơ")}</h2>
      <CaseQueueTable cases={cases} emptyHint="Chưa có hồ sơ nào trong hệ thống." />
      <h2 className="mb-3 mt-6 text-base font-medium">{tv("Hoạt động đang chạy")}</h2>
      {Object.keys(live).length === 0 ? (
        <div className="text-sm text-muted-foreground">{tv("Chưa có tác nhân nào đang chạy.")}</div>
      ) : (
        <ul className="space-y-2 text-sm">
          {Object.values(live).map((l) => (
            <li key={l.case_id} className="flex items-center gap-3">
              <span className="font-mono">{l.case_id}</span>
              <span
                className={
                  "rounded px-2 py-0.5 text-xs " +
                  (l.type === "step_started"
                    ? "bg-primary text-primary-foreground"
                    : l.type === "step_failed"
                      ? "bg-destructive text-destructive-foreground"
                      : "bg-secondary text-secondary-foreground")
                }
              >
                {l.type === "step_started" ? tv("đang chạy") : l.type === "step_failed" ? tv("lỗi") : tv("xong")}
              </span>
              <span className="text-muted-foreground">{l.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}