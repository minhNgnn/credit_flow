"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useI18n } from "../../lib/i18n";

interface GanttItem {
  name: string;
  start: number; // ms epoch
  end: number; // ms epoch
  kind: "node" | "tool" | "gen";
}

export default function TraceGantt({ items }: { items: GanttItem[] }) {
  const { tv } = useI18n();
  if (!items.length) {
    return <div className="text-sm text-muted-foreground">{tv("Không có vết chạy nào cho hồ sơ này.")}</div>;
  }
  const minStart = Math.min(...items.map((i) => i.start));
  const data = items.map((i) => ({
    name: i.name,
    offset: i.start - minStart,
    duration: Math.max(i.end - i.start, 1),
    kind: i.kind,
  }));
  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 60, right: 20, top: 10, bottom: 10 }}>
          <XAxis type="number" unit="ms" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={200} />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(value: number, name: string) =>
              name === "duration" ? `${value} ms` : String(value)
            }
          />
          <Bar dataKey="offset" stackId="t" fill="transparent" />
          <Bar dataKey="duration" stackId="t" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}