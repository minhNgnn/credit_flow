"use client";

import type { MonitorKPI } from "../../lib/monitor";

interface KPIBadgeProps {
  label: string;
  value: number | string;
  tone?: "default" | "positive" | "warning" | "critical" | "info";
}

const toneClasses: Record<NonNullable<KPIBadgeProps["tone"]>, string> = {
  default: "bg-muted text-foreground",
  positive: "bg-emerald-100 text-emerald-900",
  warning: "bg-amber-100 text-amber-900",
  critical: "bg-red-100 text-red-900",
  info: "bg-blue-100 text-blue-900",
};

function KPIBadge({ label, value, tone = "default" }: KPIBadgeProps) {
  return (
    <div className={`flex flex-col gap-0.5 rounded-md px-3 py-2 ${toneClasses[tone]}`}>
      <span className="text-[10px] uppercase tracking-wide opacity-70">{label}</span>
      <span className="text-xl font-semibold tabular-nums">{value}</span>
    </div>
  );
}

export default function KPIStrip({ kpi }: { kpi: MonitorKPI }) {
  const ready = kpi.cases_by_state["READY_FOR_REVIEW"] ?? 0;
  const draft = kpi.cases_by_state["DRAFT"] ?? 0;
  const analyzing = kpi.cases_by_state["ANALYZING"] ?? 0;
  return (
    <div className="flex flex-wrap gap-2">
      <KPIBadge label="Hồ sơ" value={kpi.total_cases} tone="info" />
      <KPIBadge label="Sẵn duyệt" value={ready} tone="positive" />
      <KPIBadge label="Bản nháp" value={draft} tone="warning" />
      {analyzing > 0 && <KPIBadge label="Đang chạy" value={analyzing} tone="info" />}
      <KPIBadge label="Nhận định" value={kpi.total_findings} />
      <KPIBadge label="Mâu thuẫn" value={kpi.total_conflicts} tone={kpi.total_conflicts > 0 ? "critical" : "default"} />
      <KPIBadge label="Quyết định" value={kpi.total_decisions} />
      <KPIBadge label="Sự kiện" value={kpi.total_events} />
      <KPIBadge label="Vết chạy" value={kpi.total_traces} tone="info" />
      <KPIBadge label="Lần gọi LLM" value={kpi.total_llm_calls} tone="info" />
    </div>
  );
}