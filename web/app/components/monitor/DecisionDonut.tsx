"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { DecisionDistEntry } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

const COLOR: Record<string, string> = {
  APPROVE: "#00853E",
  APPROVE_WITH_CONDITIONS: "#00853E",
  REFER: "#FFC10E",
  NEED_INFO: "#FFC10E",
  REJECT: "#F04E45",
};

export default function DecisionDonut({ decision_distribution }: { decision_distribution: DecisionDistEntry[] }) {
  const { tv } = useI18n();
  if (decision_distribution.length === 0) return <div className="text-sm text-muted-foreground">{tv("Chưa có quyết định.")}</div>;
  const data = decision_distribution.map((d) => ({ name: d.recommendation, value: d.n }));
  return (
    <div>
      <div className="h-40">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={62} paddingAngle={2}>
              {data.map((d) => (
                <Cell key={d.name} fill={COLOR[d.name] ?? "#cbd5e1"} />
              ))}
            </Pie>
            <Tooltip formatter={(v: number, n: string) => [`${v}`, n]} contentStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 text-xs space-y-0.5">
        {data.map((d) => (
          <li key={d.name} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full inline-block" style={{ background: COLOR[d.name] ?? "#cbd5e1" }} />
            {d.name}: {d.value}
          </li>
        ))}
      </ul>
    </div>
  );
}
