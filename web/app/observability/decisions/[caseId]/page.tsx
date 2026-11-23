"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import DecisionCard from "../../../components/observability/DecisionCard";
import FindingDrawer from "../../../components/observability/FindingDrawer";
import { fetchCase } from "../../../lib/api";
import type { CaseDetail } from "../../../lib/types";
import { useI18n } from "../../../lib/i18n";

export default function DecisionsDetail() {
  const { tv } = useI18n();
  const { caseId } = useParams<{ caseId: string }>();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchCase(caseId)
      .then(setDetail)
      .catch((e: Error) => console.error("DecisionsDetail fetchCase:", e));
  }, [caseId]);

  if (!detail) return <div className="text-sm text-muted-foreground">{tv("Đang tải…")}</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-base font-medium">{tv("Quyết định — hồ sơ {id}", { id: caseId })}</h2>
      <DecisionCard decision={detail.decision} conflicts={detail.conflicts} />
      <FindingDrawer findings={detail.findings} selectedKey={selectedKey} onSelect={setSelectedKey} />
    </div>
  );
}