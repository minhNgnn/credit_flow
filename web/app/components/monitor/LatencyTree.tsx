"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { LatencyEntry } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

export default function LatencyTree({ latency }: { latency: LatencyEntry[] }) {
  const { tv } = useI18n();
  if (latency.length === 0) {
    return <div className="text-sm text-muted-foreground">{tv("Không có dữ liệu latency (Langfuse chưa bật hoặc chưa có trace).")}</div>;
  }
  const data = latency.slice(0, 20).map((l) => ({
    name: l.name,
    avg_ms: l.avg_ms,
    max_ms: l.max_ms,
    count: l.count,
  }));
  return (
    <div className="h-72">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 100, right: 24, top: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis type="number" unit="ms" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={140} />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(v: number, name: string, item: { payload?: { max_ms?: number; count?: number } }) =>
              name === "avg_ms" ? [`${v} ms (max=${item.payload?.max_ms}, n=${item.payload?.count})`, "avg"] : [`${v} ms`, name]
            }
          />
          <Bar dataKey="avg_ms" fill="#0066B3" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
