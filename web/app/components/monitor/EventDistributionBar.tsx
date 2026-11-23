"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { EventDistEntry } from "../../lib/monitor";

export default function EventDistributionBar({ event_distribution }: { event_distribution: EventDistEntry[] }) {
  if (event_distribution.length === 0) return <div className="text-sm text-muted-foreground">Chưa có sự kiện.</div>;
  const data = event_distribution.map((d) => ({ name: d.event_type, n: d.n }));
  return (
    <div className="h-56">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 24, top: 8, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={70} interval={0} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => [`${v}`, "events"]} />
          <Bar dataKey="n" fill="#00853E" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
