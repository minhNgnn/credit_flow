"use client";

import type { CaseDetail, Finding } from "../../lib/types";
import { useI18n } from "../../lib/i18n";

interface Props {
  findings: Finding[];
  selectedKey: string | null;
  onSelect: (key: string | null) => void;
}

export default function FindingDrawer({ findings, selectedKey, onSelect }: Props) {
  const { tv } = useI18n();
  const selected = findings.find((f) => f.finding_key === selectedKey) ?? null;
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h3 className="mb-2 text-sm font-medium">{tv("Nhận định")} ({findings.length})</h3>
        <ul className="space-y-1">
          {findings.map((f) => (
            <li
              key={f.display_id}
              onClick={() => onSelect(f.finding_key)}
              className={
                "cursor-pointer rounded border border-border px-2 py-1 text-sm hover:bg-muted " +
                (selected?.finding_key === f.finding_key ? "bg-muted" : "")
              }
            >
              <div className="font-mono">{f.display_id}</div>
              <div className="text-xs text-muted-foreground">
                {f.agent_id} · {f.stance} · {f.severity}
              </div>
            </li>
          ))}
        </ul>
      </div>
      <div>
        {selected ? (
          <div className="space-y-2 rounded border border-border p-3 text-sm">
            <div className="font-mono">{selected.display_id}</div>
            <p>{selected.claim}</p>
            <dl className="grid grid-cols-2 gap-1">
              <dt className="text-muted-foreground">{tv("Thái độ")}</dt>
              <dd>{selected.stance}</dd>
              <dt className="text-muted-foreground">{tv("Mức độ")}</dt>
              <dd>{selected.severity}</dd>
              <dt className="text-muted-foreground">{tv("Độ tin cậy")}</dt>
              <dd>{(selected.confidence * 100).toFixed(0)}%</dd>
              <dt className="text-muted-foreground">{tv("Phiên bản")}</dt>
              <dd>v{selected.version}</dd>
            </dl>
            {selected.change_reason && (
              <p className="italic text-muted-foreground">{tv("Lý do thay đổi")}: {selected.change_reason}</p>
            )}
            {selected.evidence_ids.length > 0 && (
              <div className="text-xs">
                <span className="text-muted-foreground">{tv("Bằng chứng:")} </span>
                {selected.evidence_ids.join(", ")}
              </div>
            )}
            {selected.citations.length > 0 && (
              <div className="text-xs">
                <span className="text-muted-foreground">{tv("Trích dẫn:")} </span>
                <ul className="list-disc pl-5">
                  {selected.citations.map((c, i) => (
                    <li key={i}>
                      {c.source_id}
                      {c.version ? ` v${c.version}` : ""}
                      {c.section ? ` (${c.section})` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded border border-border p-3 text-sm text-muted-foreground">
            {tv("Chọn một nhận định để xem chi tiết.")}
          </div>
        )}
      </div>
    </div>
  );
}