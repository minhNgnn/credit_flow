"use client";

import { useEffect, useState } from "react";

import CaseStateDonut from "../components/monitor/CaseStateDonut";
import ConflictDonut from "../components/monitor/ConflictDonut";
import DecisionDonut from "../components/monitor/DecisionDonut";
import EventDistributionBar from "../components/monitor/EventDistributionBar";
import EventStream from "../components/monitor/EventStream";
import KPIStrip from "../components/monitor/KPIStrip";
import LLMCallsBar from "../components/monitor/LLMCallsBar";
import LatencyTree from "../components/monitor/LatencyTree";
import Panel from "../components/monitor/Panel";
import SeverityHeatmap from "../components/monitor/SeverityHeatmap";
import StanceStackedBar from "../components/monitor/StanceStackedBar";
import WorkerLogsBox from "../components/monitor/WorkerLogsBox";
import { fetchMonitorOverview, type MonitorKPI, type MonitorOverview } from "../lib/monitor";
import { fetchObservabilityCases } from "../lib/observability";
import type { CaseSummary } from "../lib/types";
import { useI18n } from "../lib/i18n";

const emptyKpi: MonitorKPI = {
  total_cases: 0,
  cases_by_state: {},
  total_findings: 0,
  total_conflicts: 0,
  conflicts_open: 0,
  conflicts_unresolved: 0,
  total_decisions: 0,
  total_events: 0,
  total_traces: 0,
  total_llm_calls: 0,
};

export default function MonitorPage() {
  const { tv } = useI18n();
  const [overview, setOverview] = useState<MonitorOverview | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [caseIds, setCaseIds] = useState<string[]>([]);

  useEffect(() => {
    fetchMonitorOverview()
      .then(setOverview)
      .catch((e: Error) => setErr(String(e)));
  }, []);

  useEffect(() => {
    fetchObservabilityCases()
      .then((cs: CaseSummary[]) => setCaseIds(cs.slice(0, 5).map((c) => c.case_id)))
      .catch((e: Error) => console.error("fetchObservabilityCases:", e));
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 space-y-2 border-b border-border bg-background/95 px-6 py-3 backdrop-blur">
        <div className="flex items-baseline justify-between">
          <h1 className="text-lg font-semibold">SHB Expert Flow · AI Monitor</h1>
          <span className="flex items-center gap-2 text-xs">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            live
          </span>
        </div>
        {overview ? <KPIStrip kpi={overview.kpi} /> : null}
      </header>
      <main className="space-y-4 px-6 py-4">
        {err ? (
          <div className="rounded-lg border border-border bg-red-50 px-4 py-3 text-sm text-red-900">
            {tv("Không thể tải dữ liệu")}: <code>{err}</code>
          </div>
        ) : null}
        {!overview && !err ? <div className="text-sm text-muted-foreground">{tv("Đang tải…")}</div> : null}
        {overview ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title={tv("SRE · Tình trạng & Độ trễ")}>
              <div className="space-y-3">
                <CaseStateDonut cases_by_state={overview.kpi.cases_by_state} />
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Độ trễ theo node / tool")}</h4>
                <LatencyTree latency={overview.latency} />
              </div>
            </Panel>
            <Panel title={tv("Hội đồng agent · Chất lượng")}>
              <div className="space-y-3">
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Thái độ theo agent (SUPPORT / CAUTION / OPPOSE / NEED_DATA)")}</h4>
                <StanceStackedBar findings_distribution={overview.findings_distribution} />
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Mức độ (severity × agent)")}</h4>
                <SeverityHeatmap severity_distribution={overview.severity_distribution} />
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Mâu thuẫn")}</h4>
                <ConflictDonut
                  conflict_distribution={overview.conflict_distribution}
                  conflict_round_distribution={overview.conflict_round_distribution}
                />
              </div>
            </Panel>
            <Panel title={tv("LLM & Tools · Số lần gọi")}>
              <div className="space-y-3">
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Số lần gọi LLM theo hồ sơ")}</h4>
                <LLMCallsBar llm_calls_per_case={overview.llm_calls_per_case} total_llm_calls={overview.kpi.total_llm_calls} />
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Quyết định tổng hợp")}</h4>
                <DecisionDonut decision_distribution={overview.decision_distribution} />
                <h4 className="text-xs font-medium text-muted-foreground">{tv("Sự kiện hệ thống (FINDING_WRITTEN, CONFLICT_*, ...)")}</h4>
                <EventDistributionBar event_distribution={overview.event_distribution} />
              </div>
            </Panel>
            <Panel title={tv("Hoạt động & Nhật ký worker")}>
              <div className="space-y-3">
                <EventStream caseIds={caseIds} />
                <WorkerLogsBox />
              </div>
            </Panel>
          </div>
        ) : null}
      </main>
      <footer className="border-t border-border px-6 py-2 text-xs text-muted-foreground">
        SHB Expert AI Monitor v0.1
      </footer>
    </div>
  );
}