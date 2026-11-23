"use client";

import { useEffect, useRef, useState } from "react";

import type { StepEvent } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

interface Props {
  caseIds: string[];
}

interface FeedItem {
  ts: number;
  case_id: string;
  type: string;
  step?: string;
  label?: string;
}

export default function EventStream({ caseIds }: Props) {
  const { tv, lang } = useI18n();
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const sourcesRef = useRef<EventSource[]>([]);

  useEffect(() => {
    const items: FeedItem[] = [];
    const sources: EventSource[] = [];
    for (const cid of caseIds.slice(0, 5)) {
      const source = new EventSource(`/api/cases/${cid}/stream`);
      source.addEventListener("message", (ev: MessageEvent) => {
        try {
          const data: StepEvent = JSON.parse(ev.data);
          if (["step_started","step_completed","step_failed","job_started","job_completed","job_failed"].includes(data.type)) {
            items.unshift({ ts: Date.now(), case_id: data.case_id ?? cid, type: data.type, step: data.step, label: data.label });
            if (items.length > 50) items.pop();
            setFeed([...items]);
          }
        } catch { /* keepalive */ }
      });
      sources.push(source);
    }
    sourcesRef.current = sources;
    return () => { sources.forEach((s) => s.close()); sourcesRef.current = []; };
  }, [caseIds.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">{tv("Hoạt động trực tiếp (top 50)")}</h4>
      <ul className="space-y-1 font-mono text-xs">
        {feed.length === 0 ? <li className="text-muted-foreground">{tv("Chưa có sự kiện nào.")}</li> : null}
        {feed.map((item, i) => {
          const tone = item.type.includes("failed") ? "text-red-600" : item.type.includes("started") ? "text-blue-600" : "text-emerald-600";
          const verb = item.type.includes("started") ? tv("bắt đầu") : item.type.includes("failed") ? tv("lỗi") : tv("xong");
          return (
            <li key={`${item.ts}-${i}`} className="flex items-center gap-3">
              <span className="text-muted-foreground tabular-nums">{new Date(item.ts).toLocaleTimeString(lang === "en" ? "en-GB" : "vi-VN")}</span>
              <span className="font-mono">{item.case_id}</span>
              <span className={tone}>{verb}</span>
              <span className="text-muted-foreground">{item.label ?? item.step ?? item.type}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
