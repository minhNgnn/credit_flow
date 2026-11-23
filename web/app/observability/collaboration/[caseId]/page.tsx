"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import CollaborationGraph from "../../../components/observability/CollaborationGraph";
import { fetchCase } from "../../../lib/api";
import type { CaseDetail } from "../../../lib/types";
import { useI18n } from "../../../lib/i18n";

export default function CollaborationDetail() {
  const { tv } = useI18n();
  const { caseId } = useParams<{ caseId: string }>();
  const [detail, setDetail] = useState<CaseDetail | null>(null);

  useEffect(() => {
    fetchCase(caseId)
      .then(setDetail)
      .catch((e: Error) => console.error("CollaborationDetail fetchCase:", e));
  }, [caseId]);

  if (!detail) return <div className="text-sm text-muted-foreground">{tv("Đang tải…")}</div>;
  return (
    <div className="space-y-4">
      <h2 className="text-base font-medium">{tv("Phân luồng — hồ sơ {id}", { id: caseId })}</h2>
      <CollaborationGraph caseId={caseId} conflicts={detail.conflicts} />
    </div>
  );
}