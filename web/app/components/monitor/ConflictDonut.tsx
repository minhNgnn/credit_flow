"use client";

import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ConflictDistEntry, ConflictRoundEntry } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

const STATUS_COLORS: Record<string, string> = {
  RESOLVED: "#00853E",
  OPEN: "#FFC10E",
  UNRESOLVED: "#F04E45",
};

export default function ConflictDonut({
  conflict_distribution,
  conflict_round_distribution,
}: {
  conflict_distribution: ConflictDistEntry[];
  conflict_round_distribution: ConflictRoundEntry[];
}) {
  const { tv } = useI18n();
  const donutData = conflict_distribution.map((c) => ({ name: c.status, value: c.n }));
  const total = donutData.reduce((s, d) => s + d.value, 0);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <div className="h-40">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={donutData} dataKey="value" nameKey="name" innerRadius={36} outerRadius={62} paddingAngle={2}>
                {donutData.map((d) => (
                  <Cell key={d.name} fill={STATUS_COLORS[d.name] ?? "#cbd5e1"} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number, n: string) => [`${v}`, n]} contentStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        {total === 0 ? (
          <div className="text-center text-xs text-muted-foreground">{tv("Chưa có mâu thuẫn.")}</div>
        ) : (
          <ul className="text-xs">
            {donutData.map((d) => (
              <li key={d.name} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full inline-block" style={{ background: STATUS_COLORS[d.name] ?? "#cbd5e1" }} />
                {d.name}: {d.value}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="text-xs font-medium text-muted-foreground mb-1">{tv("Số vòng theo issue_key")}</h4>
        {conflict_round_distribution.length === 0 ? (
          <div className="text-xs text-muted-foreground">—</div>
        ) : (
          <div className="h-40">
            <ResponsiveContainer>
              <BarChart data={conflict_round_distribution} layout="vertical" margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="issue_key" tick={{ fontSize: 10 }} width={120} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Bar dataKey="max_round" fill="#0066B3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
