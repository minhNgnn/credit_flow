"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS: Record<string, string> = {
  READY_FOR_REVIEW: "#00853E",
  ANALYZING: "#0066B3",
  DRAFT: "#FFC10E",
  NEED_INFO: "#FFC10E",
};

export default function CaseStateDonut({ cases_by_state }: { cases_by_state: Record<string, number> }) {
  const data = Object.entries(cases_by_state).map(([state, value]) => ({ name: state, value }));
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <div className="text-sm text-muted-foreground">Chưa có hồ sơ.</div>;
  return (
    <div>
      <div className="h-48">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={48} outerRadius={72} paddingAngle={2}>
              {data.map((d) => (
                <Cell key={d.name} fill={COLORS[d.name] ?? "#cbd5e1"} />
              ))}
            </Pie>
            <Tooltip formatter={(v: number, n: string) => [`${v}`, n]} contentStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 text-xs space-y-0.5">
        {data.map((d) => (
          <li key={d.name} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full inline-block" style={{ background: COLORS[d.name] ?? "#cbd5e1" }} />
            {d.name}: {d.value}
          </li>
        ))}
      </ul>
    </div>
  );
}
