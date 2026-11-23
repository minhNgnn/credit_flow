"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { FindingDistEntry } from "../../lib/monitor";

const STANCES = ["SUPPORT", "CAUTION", "OPPOSE", "NEED_DATA"] as const;
const STANCE_COLORS: Record<string, string> = {
  SUPPORT: "#00853E",
  CAUTION: "#FFC10E",
  OPPOSE: "#F04E45",
  NEED_DATA: "#6E7C8E",
};

export default function StanceStackedBar({ findings_distribution }: { findings_distribution: FindingDistEntry[] }) {
  const agentIds = Array.from(new Set(findings_distribution.map((d) => d.agent_id))).sort();
  const data = agentIds.map((agent_id) => {
    const row: Record<string, string | number> = { agent_id };
    for (const s of STANCES) row[s] = 0;
    for (const d of findings_distribution) if (d.agent_id === agent_id) row[d.stance] = d.n;
    return row;
  });
  if (agentIds.length === 0) return <div className="text-sm text-muted-foreground">Không có nhận định.</div>;
  return (
    <div className="h-60">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 24, top: 8, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="agent_id" tick={{ fontSize: 10 }} angle={-12} textAnchor="end" height={50} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {STANCES.map((s) => (
            <Bar key={s} dataKey={s} stackId="stance" fill={STANCE_COLORS[s]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
