"use client";

import type { CaseDetail, Conflict, Decision as DecisionType } from "../../lib/types";
import { useI18n } from "../../lib/i18n";

interface Props {
  decision: DecisionType | null;
  conflicts: Conflict[];
}

function vnd(n: number | null | undefined): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(n);
}

function Strings({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className="text-sm text-muted-foreground">{title}</div>
      <ul className="list-disc pl-5 text-sm">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export default function DecisionCard({ decision, conflicts }: Props) {
  const { tv } = useI18n();
  if (!decision) {
    return (
      <div className="rounded border border-border p-4 text-sm text-muted-foreground">
        {tv("Chưa có Quyết định tổng hợp — hồ sơ vẫn đang phân tích hoặc chưa synthesize.")}
      </div>
    );
  }
  const hardFail = decision.hard_gates.some((g) => g.status === "FAIL");
  return (
    <div className="space-y-3 rounded border border-border p-4">
      <div>
        <div className="text-sm text-muted-foreground">{tv("Khuyến nghị")}</div>
        <div className="text-base font-semibold">
          {decision.recommendation}
          {hardFail && (
            <span className="ml-2 rounded bg-destructive px-2 py-0.5 text-xs text-destructive-foreground">
              {tv("cổ cứng fail")}
            </span>
          )}
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-muted-foreground">{tv("Hạn mức yêu cầu")}</dt>
        <dd className="tabular-nums">{vnd(decision.requested_amount_vnd)}</dd>
        <dt className="text-muted-foreground">{tv("Hạn mức đề xuất")}</dt>
        <dd className="tabular-nums">{vnd(decision.recommended_amount_vnd)}</dd>
        <dt className="text-muted-foreground">{tv("Thời hạn đề xuất")}</dt>
        <dd className="tabular-nums">{decision.recommended_tenor_months ?? "—"} {tv("tháng")}</dd>
      </dl>
      <div>
        <div className="text-sm text-muted-foreground">{tv("Cổng cứng")}</div>
        <ul className="text-sm">
          {decision.hard_gates.map((g) => (
            <li key={g.gate_id} className="flex items-center gap-2">
              <span
                className={
                  "rounded px-1.5 py-0.5 text-xs " +
                  (g.status === "PASS"
                    ? "bg-secondary text-secondary-foreground"
                    : "bg-destructive text-destructive-foreground")
                }
              >
                {g.status}
              </span>
              <span className="font-mono">{g.gate_id}</span>
              {g.reason && <span className="text-muted-foreground">— {g.reason}</span>}
            </li>
          ))}
        </ul>
      </div>
      {decision.scores.length > 0 && (
        <div>
          <div className="text-sm text-muted-foreground">{tv("Điểm số")}</div>
          <ul className="text-sm">
            {decision.scores.map((s) => (
              <li key={s.dimension} className="flex justify-between">
                <span>{s.dimension}</span>
                <span className="tabular-nums">
                  {s.score} / {s.max}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Strings title={tv("Điểm mạnh")} items={decision.strengths} />
      <Strings title={tv("Rủi ro")} items={decision.risks} />
      <Strings title={tv("Điều kiện tiên quyết")} items={decision.conditions_precedent} />
      <Strings title={tv("Bất đồng còn lại")} items={decision.dissent} />
      <div className="mt-2 text-xs text-muted-foreground">
        {tv("Phiên bản chính sách")}: {decision.policy_version ?? "—"} · {tv("Ma trận quyết định")}:{" "}
        {decision.decision_matrix_version ?? "—"}
      </div>
      {conflicts.length > 0 && (
        <div className="text-xs">
          <span className="text-muted-foreground">{tv("Mâu thuẫn:")} </span>
          {conflicts.map((c) => (
            <span key={c.conflict_id} className="mr-2 inline-block">
              {c.issue_key} ({tv("vòng")} {c.round}, {c.status})
            </span>
          ))}
        </div>
      )}
    </div>
  );
}