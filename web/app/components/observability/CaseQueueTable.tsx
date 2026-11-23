"use client";

import Link from "next/link";

import type { CaseSummary } from "../../lib/types";
import { useI18n } from "../../lib/i18n";

interface Props {
  cases: CaseSummary[];
  emptyHint?: string;
  /** Where each row should deep-link to. Defaults to collaboration tab. */
  linkPrefix?: string;
}

export default function CaseQueueTable({
  cases,
  emptyHint = "Chưa có hồ sơ.",
  linkPrefix = "/observability/collaboration/",
}: Props) {
  const { tv } = useI18n();
  if (cases.length === 0) {
    return <div className="text-sm text-muted-foreground">{tv(emptyHint)}</div>;
  }
  return (
    <div className="overflow-x-auto rounded border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">{tv("Mã hồ sơ")}</th>
            <th className="px-3 py-2 text-left">{tv("Khách hàng")}</th>
            <th className="px-3 py-2 text-left">{tv("Trạng thái")}</th>
            <th className="px-3 py-2 text-left">{tv("Cập nhật")}</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.case_id} className="cursor-pointer border-t border-border hover:bg-muted">
              <td className="px-3 py-2 font-mono">
                <Link href={`${linkPrefix}${c.case_id}`}>{c.case_id}</Link>
              </td>
              <td className="px-3 py-2">{c.customer_id}</td>
              <td className="px-3 py-2">{c.state}</td>
              <td className="px-3 py-2 tabular-nums">{new Date(c.updated_at).toLocaleString("vi-VN")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}