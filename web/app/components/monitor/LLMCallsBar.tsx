"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { LLMCallsEntry } from "../../lib/monitor";
import { useI18n } from "../../lib/i18n";

export default function LLMCallsBar({ llm_calls_per_case, total_llm_calls }: { llm_calls_per_case: LLMCallsEntry[]; total_llm_calls: number }) {
  const { tv } = useI18n();
  if (llm_calls_per_case.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        {tv("Chưa có dữ liệu LLM call. Tổng: {n} lần (FPT AI không trả usage trong trace — hiển thị số lần gọi thay vì token).", { n: total_llm_calls })}
      </div>
    );
  }
  const data = llm_calls_per_case.slice(0, 15).map((d) => ({ case_id: d.case_id, n: d.n }));
  return (
    <div>
      <div className="text-xs text-muted-foreground">
        {tv("Tổng {n} lần gọi LLM cho {m} hồ sơ (FPT AI chưa report usage → đếm lần thay vì token).", { n: total_llm_calls, m: llm_calls_per_case.length })}
      </div>
      <div className="h-48">
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ left: 100, right: 24, top: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="case_id" tick={{ fontSize: 10 }} width={120} />
            <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => [tv("{n} lần", { n: v }), tv("gọi LLM")]} />
            <Bar dataKey="n" fill="#0066B3" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
