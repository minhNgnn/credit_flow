"use client";

import { useEffect, useState } from "react";

import CaseQueueTable from "../../components/observability/CaseQueueTable";
import { fetchObservabilityCases } from "../../lib/observability";
import type { CaseSummary } from "../../lib/types";

export default function CollaborationFinder() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  useEffect(() => {
    fetchObservabilityCases()
      .then(setCases)
      .catch((e: Error) => console.error("CollaborationFinder fetchObservabilityCases:", e));
  }, []);
  return (
    <div>
      <h2 className="mb-3 text-base font-medium">Chọn hồ sơ để xem phân luồng</h2>
      <CaseQueueTable
        cases={cases}
        emptyHint="Chưa có hồ sơ nào."
        linkPrefix="/observability/collaboration/"
      />
    </div>
  );
}