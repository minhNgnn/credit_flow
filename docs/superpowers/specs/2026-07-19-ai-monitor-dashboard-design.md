# AI Monitor Dashboard — Design

- **Ngày**: 2026-07-19
- **Branch**: `feat/multi-agent-observability` (worktree)
- **Stack**: `shbexpert-flow-obs` (compose project đã tách độc lập với repo chính)
- **Scope**: ~6-12 giờ, ngày 4 của hackathon
- **Deliverable**: route `/monitor` — trang dashboard giám sát AI monitor cho giám khảo/IT đánh giá sản phẩm multi-agent, với 3 lớp dữ liệu obsc分明: trace + logs + metrics (query-time aggregation, không thêm bảng/worker).

---

## 1. Mục tiêu & phạm vi

### 1.1 Mục tiêu

Cung cấp một trang dashboard overview ("AI Monitor") phục vụ giám khảo/IT đánh giá sản phẩm. Dashboard phải hiển thị cả ba lớp dữ liệu quan sát:

1. **Trace** — LLM prompt/response, tool call input/output, graph node progress (đã có trong Langfuse từ spec 2026-07-19 trước; monitor chỉ tiêu thụ qua Langfuse proxy).
2. **Logs** — Event stream real-time + error log worker (lấy 200 dòng gần nhất stdout worker via Docker API).
3. **Metrics** — Query-time aggregation từ Postgres (`events/findings/conflicts/decisions/cases`) + Langfuse REST (`/api/public/observations`): case state distribution, latency per node/tool, stance per agent, severity heatmap, conflict status, decision recommendation distribution, # LLM calls per case.

### 1.2 In scope

- Route Next.js mới `/monitor` + `/monitor/cases/[caseId]` — KHÔNG dùng layout `observability`, brand "SHB Expert Flow · AI Monitor".
- 1 FastAPI endpoint mới `GET /api/monitor/overview` (aggregation multiple SQL GROUP BY trong 1 request).
- 1 FastAPI endpoint mới `GET /api/monitor/logs` (200 dòng stdout worker gần nhất qua `docker exec` hoặc `docker logs` clip sidecar).
- 7 React component charts (recharts + SVG SHB tokens).
- KPI strip header: 7 cases · 6 READY · 1 DRAFT · 169 findings · 8 conflicts · N traces · LLM calls.
- SSE live: subscribe top 5 streams của case gần nhất — đẩy vào activity feed + update case state donut.

### 1.3 Out of scope (YAGNI)

- ❌ Timeseries materialized (bảng `metrics_snapshot`, background worker periodic) — chọn query-time aggregation.
- ❌ Alerting, incident history.
- ❌ Export PDF/PNG.
- ❌ Multi-tenant / user picker.
- ❌ p90/p99 (chỉ hiển thị avg+max cho demo; đo lường đầy đủ thêm sau).
- ❌ Token cost USD (FPT AI chưa expose usage trong SDK → trả null/0; monitor hiển thị "# LLM calls" thay vì "token").
- ❌ Latency-by-hour heatmap.
- ❌ Login (Langfuse UI riêng đã có — monitor chỉ read-only).

---

## 2. Ba lớp dữ liệu — cách thu thập

### 2.1 Trace (đã có, monitor tiêu thụ)

| Source | Đường dẫn | Dữ liệu |
|--------|-----------|---------|
| Langfuse REST | `GET /api/public/traces?metadata.case_id={id}&limit=1` | trace_id, name, timestamp |
| Langfuse REST | `GET /api/public/observations?traceId={id}&limit=100` | spans (name, startTime, endTime, level) + generations (input.kwargs.user, output, latency) |

Monitor SERVER-SIDE đọc việc này (route handler trong web) hoặc endpoint `/api/monitor/overview` aggregate luôn trong 1 call. Browser仍未 thấy keys.

### 2.2 Logs — 2 sub-layers

| Sub-layer | Source | Mục đích |
|-----------|--------|----------|
| **Event stream (cấp ứng dụng)** | Bảng Postgres `events` (append-only, đã revoke UPDATE/DELETE) — `event_type ∈ {FINDING_WRITTEN, CONFLICT_*, DECISION_SYNTHESIZED, STATE_TRANSITION, TARGETED_QUESTION_SENT}` + `seq`, `actor`, `timestamp`, `payload` JSONB | Activity feed + KPI counts + event distribution chart |
| **Worker stdout (cấp runtime)** | `docker logs shbexpert-flow-obs-worker-1 --tail 200` qua FastAPI `GET /api/monitor/logs` | Error log panel — xem nội dung worker (job_failed, span export retry, traceback) |

Cả 2 hiển thị trong monitor: event stream là timeline nhẹ (top 50 gần nhất, refresh khi SSE đẩy); stdout worker là panel nghiền, khoán 10s `setInterval` poll.

### 2.3 Metrics — query-time aggregation

| Metric | SQL source | Aggregation |
|--------|-----------|-------------|
| Case state distribution | `SELECT state, count(*) FROM cases GROUP BY 1` | Donut chart |
| KPI totals | `SELECT count(*) FROM findings / conflicts / decisions` (3 truy vấn) | KPI strip header |
| Findings stance × agent | `SELECT agent_id, stance, count(*) FROM findings GROUP BY 1, 2` | Stacked bar by agent (4 bar, mỗi bar = stance breakdown) |
| Findings severity × agent | `SELECT agent_id, severity, count(*) FROM findings GROUP BY 1, 2` | Heatmap (agent × severity) |
| Conflict status | `SELECT status, count(*) FROM conflicts GROUP BY 1` | Donut |
| Decision recommendation | `SELECT recommendation, count(*) FROM decisions GROUP BY 1` | Donut |
| Event type distribution | `SELECT event_type, count(*) FROM events GROUP BY 1` | Bar chart |
| Node/tool latency (avg/max/count) | `GET /api/public/observations?limit=100` (Langfuse, recent 5 traces) → filter type=SPAN, group by name, tính avg/ms и max từ startTime/endTime | Latency tree table OR bar chart |
| LLM calls per case | Đếm generations per trace_id | Bar chart 7 cases |
| Live activity (top 5 case streams) | `EventSource('/api/cases/{id}/stream')` for each of top-5 cases recent | Activity feed + state donut live update |

### 2.4 Cảnh tỉnh data layout

**Không** thêm bảng. **Không** thêm worker cron. **Không** thêm schema migration. Tất cả aggregates query realtime từ schema hiện có. Lý do: chỉ 7-10 case trong demo hackathon — Postgres + Redis + Langfuse đủ throughput, không cần timeseries store.

---

## 3. Route layout

```
http://localhost:3100/monitor              ← main overview page (single-page)
http://localhost:3100/monitor/cases/[id]   ← drill-down detail (optional v1.1)
```

Khi vào `/monitor`, Next.js `app/monitor/page.tsx` (`"use client"`) gọi 2 fetch song song:
1. `GET /api/monitor/overview` (data tổng hợp, 1 object)
2. `GET /api/monitor/logs` (worker stdout nhật ký gần nhất)

Sau đó mở `EventSource` tới 5 streams của top-5 case gần nhất để hiển thị hoạt động trực tiếp (SSE decoding trong component `EventStream` và dispatch bằng CustomEvent để các thành phần khác như case donut update).

## 4. UI layout (grid 3x2)

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  SHB logo · "AI Monitor" · KPI strip: cases=7 · READY=6 · DRAFT=1 · findings=169 ·     │
│  conflicts=8 · decisions=10 · traces=5 · LLM_calls=37   [●live]                          │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  PANEL 1 (row 1, col 1): SRE — Case & Latency                                          │
│  ┌─ Case state donut (ready/draft/analyzing) ── Latency tree (avg/max/count per node) │
│  └─ Failed jobs bar (job_failed vs job_completed)                                      │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  PANEL 2 (row 1, col 2): Agent Council Quality                                         │
│  ┌─ Stance stacked bar by agent (4 agents, 4 stances)                                  │
│  ├─ Severity heatmap (agent × severity)                                                │
│  └─ Conflict status donut + Conflict round count by issue_key                          │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  PANEL 3 (row 2, col 1): LLM calls & Cost (surrogate)                                  │
│  ┌─ LLM calls per case (bar)  — top large from 5 recent traces                         │
│  ├─ Nodes by # times called (bar) — financial/policy/collateral/customer360/synth ...   │
│  └─ Tool calls count (bar) — calculate_* / search_policy / etc. ranking                │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  PANEL 4 (row 2, col 2): Logs — Event stream + Worker stdout                          │
│  ┌─ Live activity feed (top 50 gần nhất, refresh khi SSE push) — case_id · step · label│
│  └─ Worker stdout box (200 dòng gần nhất, poll 10s) — scrollbar                        │
└───────────────────────────────────────────────────────────────────────────────────────┘
Footer: refresh pulse · trace: 5 · logs: 221 events · metrics realtime · SHB Expert AI Monitor v0.1
```

Mỗi panel là một thẻ có tiêu đề, biểu tượng, và có thể thu gọn. Sử dụng 2 cột qua `lg:grid-cols-2`; xếp chồng trên di động.

---

## 5. Files (và trách nhiệm)

### Backend (Python — FastAPI)

| File | Trách nhiệm |
|------|-------------|
| `api/app/routers/monitor.py` (MỚI) | 2 endpoint `GET /monitor/overview` + `GET /monitor/logs`. Tổng hợp SQL trên `shared.models` + gọi Langfuse REST cho observations/latency |
| `api/app/main.py` (sửa) | `app.include_router(monitor.router)` |

### Frontend (Next.js)

| File | Trách nhiệm |
|------|-------------|
| `web/app/monitor/page.tsx` (MỚI) | Trang chính — gọi fetch overview + logs + SSE subscription top-5 streams + render grid |
| `web/app/lib/monitor.ts` (MỚI) | Typed fetcher `fetchMonitorOverview(): Promise<MonitorOverview>` + `fetchMonitorLogs(): Promise<WorkerLogs>` |
| `web/app/components/monitor/KPIStrip.tsx` (MỚI) | KPI badges header |
| `web/app/components/monitor/CaseStateDonut.tsx` (MỚI) | Donut `cases_ready/draft/analyzing` |
| `web/app/components/monitor/LatencyTree.tsx` (MỚI) | Bar chart avg/max latency theo node/tool |
| `web/app/components/monitor/StanceStackedBar.tsx` (MỚI) | Stacked bar stance × agent |
| `web/app/components/monitor/SeverityHeatmap.tsx` (MỚI) | Heatmap agent (rows) × severity (cols) — màu SHB cam/navy gradient |
| `web/app/components/monitor/ConflictDonut.tsx` (MỚI) | Donut conflict status + bar round count |
| `web/app/components/monitor/DecisionDonut.tsx` (MỚI) | Donut recommendation (APPROVE/REJECT/REFER/NEED_INFO/...) |
| `web/app/components/monitor/EventDistributionBar.tsx` (MỚI) | Bar chart event_type distribution |
| `web/app/components/monitor/LLMCallsBar.tsx` (MỚI) | Bar chart LLM calls per case (top N) |
| `web/app/components/monitor/EventStream.tsx` (MỚI) | Live activity feed (top 50, SSE triggered) |
| `web/app/components/monitor/WorkerLogsBox.tsx` (MỚI) | Worker stdout hộp thoại (poll 10s) |

**Test:** `tests/observability/test_monitor_router.py` (MỚI) — TestClient với mocked session, verify endpoint `/monitor/overview` trả đủ field + counts khi seeded; `/monitor/logs` trả string log (mock `docker` call).

---

## 6. Interfaces (hợp đồng cố định)

### 6.1 Endpoint contract: `GET /api/monitor/overview`

```typescript
interface MonitorOverview {
  kpi: {
    total_cases: number;
    cases_by_state: Record<string, number>;     // {READY_FOR_REVIEW: 6, DRAFT: 1, ...}
    total_findings: number;
    total_conflicts: number;
    conflicts_open: number;
    conflicts_unresolved: number;
    total_decisions: number;
    total_events: number;
    total_traces: number;                        // từ Langfuse (DB tổng hợp)
    total_llm_calls: number;                     // total generations cho 5 trace gần nhất
  };
  findings_distribution: Array<{ agent_id: string; stance: string; n: number }>;
  severity_distribution: Array<{ agent_id: string; severity: string; n: number }>;
  event_distribution: Array<{ event_type: string; n: number }>;
  conflict_distribution: Array<{ status: string; n: number }>;
  conflict_round_distribution: Array<{ issue_key: string; max_round: number; n: number }>;
  decision_distribution: Array<{ recommendation: string; n: number }>;
  latency: Array<{ name: string; avg_ms: number; max_ms: number; count: number }>;
  llm_calls_per_case: Array<{ case_id: string; n: number }>;
}
```

Endpoint response luôn có đủ 9 field; nếu một field fail (vd Langfuse down), trả mảng rỗng cho field đó chứ không crash — partial degrade.

### 6.2 Endpoint contract: `GET /api/monitor/logs?lines=200`

```typescript
interface WorkerLogs {
  container: string;       // "shbexpert-flow-obs-worker-1"
  fetched_at: string;      // ISO timestamp
  lines: string[];         // 200 dòng gần nhất
  error: string | null;    // nếu `docker logs` fail
}
```

Triển khai: chạy `subprocess.run(["docker", "logs", "shbexpert-flow-obs-worker-1", "--tail", "200"], capture_output=True, text=True, timeout=5)` — bắt `FileNotFoundError` (docker chưa cài) + `timeout`. Trả về error thay vì 500.

### 6.3 Fail-trạng thái (failing) degrade

- Postgres down → `/monitor/overview` trả 503; frontend hiển thị banner "Postgres không khả dụng" + bỏ grid.
- Langfuse down/empty → `latency` rỗng, `total_llm_calls=0`; phần hiển thị khoa học sự cố "trống dữ liệu".
- `docker logs` fail → `error: "docker logs không khả dụng"` → thực hiện WorkerLogsBox chỉ hiện banner lỗi, các thành phần khác vẫn full.

---

## 7. Giao diện người dùng (UI) theo SHB Design System (ngân hàng)

- Tokens: `bg-background`, `text-foreground`, `text-muted-foreground`, `border-border` (đã định nghĩa trong `web/app/globals.css`).
- Màu biểu đồ cố định:
  - SUPPORT: `#00853E` (xanh SHB)
  - CAUTION: `#FFC10E` (vàng)
  - OPPOSE: `#F04E45` (đỏ cảnh báo)
  - NEED_DATA: `#6E7C8E` (xám)
  - PASS / APPROVE: `#00853E`
  - FAIL / REJECT: `#F04E45`
  - REVIEW / REFER / NEED_INFO: `#FFC10E`
  - READY_FOR_REVIEW: `#00853E`
  - DRAFT / ANALYZING: `#0066B3`
  - Conflict RESOLVED: `#00853E`; UNRESOLVED: `#F04E45`; OPEN: `#FFC10E`
- Typography: tiêu đề panel `text-sm font-semibold text-muted-foreground uppercase tracking-wide`, số KPI `text-2xl font-semibold tabular-nums`.
- Padding pattern: thẻ `border border-border rounded-lg p-4 space-y-3`.
- Header sticky: `sticky top-0 z-10 bg-background/95 backdrop-blur`.
- Nhãn tiếng Việt: "Hồ sơ", "Nhận định", "Mâu thuẫn", "Quyết định", "Vết chạy", "Sự kiện", "Nhật ký worker". Không có biểu tượng cảm xúc ngoài ●live pulse.

---

## 8. Live activity feed

- On `monitor/page.tsx` mounting: gọi `fetchObservabilityCases()` (đã có từ `lib/observability.ts`) để lấy top 5 case gần nhất. Subscribe `EventSource(/api/cases/{id}/stream)` cho từng case.
- Mỗi khi `step_started` / `step_completed` / `step_failed` đến, đẩy vào state `liveEvents` giới hạn vòng tròn 50 dòng (bỏ dòng cũ nhất):
  ```
  [12:34:56] C06 · bước financial bắt đầu
  [12:34:57] C06 · bước financial xong
  [12:34:58] C06 · phát hiện mâu thuẫn · bắt đầu lại (challenge)
  ```
- Hoạt động trực tiếp kéo theo Case State Donut update nếu sự kiện là `STATE_TRANSITION` (rare cho top-5 nhưng cover được).
- WorkerLogsBox `setInterval(fetchMonitorLogs, 10000)` — poll 10s. Tạm dừng khi tab bị ẩn (`document.hidden`).

---

## 9. Lỗi/hạ cấp

- **Langfuse reach fail**: thử gọi Langfuse `/api/public/traces?limit=5` đầu server-side; nếu thất bại, để `latency: []` và `total_llm_calls: 0`.
- **Docker không cài đặt/cannot reach**: endpoint `/monitor/logs` trả `error: "...message..."`, frontend hiển thị banner "Nhật ký worker không khả dụng — chạy trong host có Docker".
- **SSE fail**: `EventSource.onError` → console.warn + dừng feed; vẫn hiển thị dữ liệu tĩnh từ tổng hợp khi tải trang.
- **Tổng hợp SQL thồi (Postgres timeout)**: endpoint `/monitor/overview` trả 503 (`{"detail": "aggregation query timeout"}`); frontend hiển thị banner "Dữ liệu Postgres không khả dụng" + lưới trống.
- **Dữ liệu thay đổi trong phiên**: việc cập nhật `kpi`, `findings`, v.v. chỉ thực hiện khi tải lại trang. Hoạt động trực tiếp bổ sung/sửa đổi. Giám khảo có thể F5 trực tiếp.

---

## 10. Thử nghiệm

| Đơn vị | Thử nghiệm |
|-------|------|
| `api/app/routers/monitor.py` | `tests/observability/test_monitor_router.py` — TestClient với session mock: 1) chèn dữ liệu mẫu → gọi `/monitor/overview` → JSON khớp contract + đếm đúng; 2) gọi `/monitor/logs` → mock `subprocess.run` → trả chuỗi dòng; 3) khi Docker bị thiếu → `error` field set, HTTP 200 |
| React components | visual smoke (render với fixture tĩnh, kiểm tra DOM có chart element) — tùy chọn cho hackathon |

---

## 11. Tham chiếu

- Spec cha: `docs/superpowers/specs/2026-07-19-multi-agent-observability-design.md` (commit `1909448`)
- Plan cha: `docs/superpowers/plans/2026-07-19-multi-agent-observability.md`
- Schema: `shared/models.py` (Event, Finding, ConflictRecord, DecisionPackage, Case)
- Langfuse REST đã xác thực trực tiếp (xem commit `778ce0e` endpoint observations + limit=100)
- SHB design tokens: `web/app/globals.css`