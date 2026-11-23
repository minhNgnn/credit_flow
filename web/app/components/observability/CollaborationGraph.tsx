"use client";

import { useEffect, useRef, useState } from "react";
import { useI18n } from "../../lib/i18n";

interface StepNode {
  step: string;
  label: string;
  x: number;
  y: number;
}

interface StepEdge {
  from: string;
  to: string;
  loop?: boolean;
}

const NODES: StepNode[] = [
  { step: "plan", label: "Lập kế hoạch", x: 400, y: 40 },
  { step: "financial", label: "Financial Agent", x: 180, y: 140 },
  { step: "policy", label: "Policy Agent", x: 320, y: 140 },
  { step: "collateral", label: "Collateral Agent", x: 460, y: 140 },
  { step: "customer360", label: "Customer 360", x: 600, y: 140 },
  { step: "detect", label: "Đối chiếu mâu thuẫn", x: 400, y: 250 },
  { step: "challenge", label: "Hỏi lại (round 1→2)", x: 240, y: 340 },
  { step: "synthesize", label: "Tổng hợp quyết định", x: 400, y: 410 },
  { step: "transition", label: "Chốt trạng thái", x: 400, y: 470 },
];

const EDGES: StepEdge[] = [
  { from: "plan", to: "financial" },
  { from: "plan", to: "policy" },
  { from: "plan", to: "collateral" },
  { from: "plan", to: "customer360" },
  { from: "financial", to: "detect" },
  { from: "policy", to: "detect" },
  { from: "collateral", to: "detect" },
  { from: "customer360", to: "detect" },
  { from: "detect", to: "challenge" },
  { from: "challenge", to: "detect", loop: true },
  { from: "detect", to: "synthesize" },
  { from: "synthesize", to: "transition" },
];

type StepStatus = "idle" | "running" | "ok" | "fail";

interface Props {
  caseId: string;
  conflicts: { issue_key: string; round: number; status: string }[];
}

export default function CollaborationGraph({ caseId, conflicts }: Props) {
  const { tv } = useI18n();
  const [states, setStates] = useState<Record<string, StepStatus>>({});
  const [seasonedRound, setSeasonedRound] = useState<number>(0);
  const [liveRound, setLiveRound] = useState<number>(0);
  const sourceRef = useRef<EventSource | null>(null);
  const sawChallengeCount = useRef<number>(0);

  // Seed from already-recorded conflicts on initial case detail load.
  useEffect(() => {
    const maxR = conflicts.reduce((m, c) => Math.max(m, c.round), 0);
    setSeasonedRound(maxR);
  }, [conflicts]);

  useEffect(() => {
    const source = new EventSource(`/api/cases/${caseId}/stream`);
    sourceRef.current = source;
    source.addEventListener("message", (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "step_started") {
          setStates((prev) => ({ ...prev, [data.step]: "running" }));
        } else if (data.type === "step_completed") {
          setStates((prev) => ({ ...prev, [data.step]: "ok" }));
        } else if (data.type === "step_failed") {
          setStates((prev) => ({ ...prev, [data.step]: "fail" }));
        }
        // Track live rounds: every challenge step_started increments round.
        if (data.step === "challenge" && data.type === "step_started") {
          sawChallengeCount.current += 1;
          setLiveRound(sawChallengeCount.current);
        }
      } catch {
        /* keepalive */
      }
    });
    return () => source.close();
  }, [caseId]);

  const activeRound = Math.max(seasonedRound, liveRound);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-sm">
        <span className="text-muted-foreground">{tv("Vòng challenge:")}</span>
        <span className="rounded bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
          {activeRound} / 2
        </span>
      </div>
      <svg viewBox="0 0 800 510" className="w-full rounded border border-border">
        {/* Edges */}
        {EDGES.map((e, i) => {
          const a = NODES.find((n) => n.step === e.from)!;
          const b = NODES.find((n) => n.step === e.to)!;
          const d = e.loop
            ? `M ${a.x} ${a.y} C ${a.x - 80} ${a.y - 60}, ${b.x - 80} ${b.y + 80}, ${b.x} ${b.y}`
            : `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
          const aStatus = states[e.from] ?? "idle";
          const bStatus = states[e.to] ?? "idle";
          const active =
            aStatus === "running" || aStatus === "ok" || bStatus === "running";
          const stroke = active ? "#3b82f6" : "#cbd5e1";
          return (
            <path
              key={i}
              d={d}
              stroke={stroke}
              strokeWidth={aStatus === "running" ? 2.5 : 1.2}
              fill="none"
              strokeDasharray={e.loop ? "5 5" : undefined}
              className={bStatus === "running" ? "animate-pulse" : ""}
            />
          );
        })}
        {/* Nodes */}
        {NODES.map((n) => {
          const s: StepStatus = states[n.step] ?? "idle";
          const fill =
            s === "running" ? "#3b82f6" : s === "ok" ? "#10b981" : s === "fail" ? "#ef4444" : "#f8fafc";
          const stroke =
            s === "running" ? "#1d4ed8" : s === "fail" ? "#b91c1c" : s === "ok" ? "#047857" : "#cbd5e1";
          return (
            <g key={n.step}>
              <rect
                x={n.x - 70}
                y={n.y - 16}
                width={140}
                height={32}
                rx={6}
                fill={fill}
                stroke={stroke}
                strokeWidth={1.5}
                className={s === "running" ? "animate-pulse" : ""}
              />
              <text
                x={n.x}
                y={n.y + 4}
                textAnchor="middle"
                fontSize={11}
                fill={s === "idle" ? "#334155" : "#ffffff"}
              >
                {tv(n.label)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="text-sm text-muted-foreground">
        {Object.keys(states).length === 0
          ? tv("Đang chờ sự kiện từ worker (chạy /cases/{id}/analyze để xem)…")
          : tv("Đang theo dõi trực tiếp đồ thị phân luồng.")}
      </div>
    </div>
  );
}