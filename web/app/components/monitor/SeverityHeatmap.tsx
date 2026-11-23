"use client";

import type { SeverityDistEntry } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

const SEVERITIES = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
const SEV_OPACITY: Record<string, number> = {
  INFO: 0.20,
  LOW: 0.35,
  MEDIUM: 0.55,
  HIGH: 0.80,
  CRITICAL: 1.0,
};

export default function SeverityHeatmap({ severity_distribution }: { severity_distribution: SeverityDistEntry[] }) {
  const { tv } = useI18n();
  const agentIds = Array.from(new Set(severity_distribution.map((d) => d.agent_id))).sort();
  if (agentIds.length === 0) return <div className="text-sm text-muted-foreground">{tv("Không có dữ liệu mức độ.")}</div>;
  const lookup = new Map<string, number>();
  for (const d of severity_distribution) lookup.set(`${d.agent_id}|${d.severity}`, d.n);
  const maxN = Math.max(1, ...severity_distribution.map((d) => d.n));
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-muted-foreground">Agent</th>
            {SEVERITIES.map((s) => (
              <th key={s} className="px-2 py-1 text-center text-muted-foreground">{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {agentIds.map((agent) => (
            <tr key={agent}>
              <td className="px-2 py-1 font-mono text-muted-foreground">{agent}</td>
              {SEVERITIES.map((sev) => {
                const n = lookup.get(`${agent}|${sev}`) ?? 0;
                const op = n === 0 ? 0.05 : (n / maxN) * SEV_OPACITY[sev];
                return (
                  <td key={sev} className="px-1 py-1">
                    <div
                      className="flex h-9 items-center justify-center rounded tabular-nums"
                      style={{ background: `rgba(240, 78, 69, ${op})`, color: op > 0.6 ? "white" : "var(--foreground)" }}
                      title={`${agent} · ${sev}: ${n}`}
                    >
                      {n || ""}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
