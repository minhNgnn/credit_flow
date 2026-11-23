# Multi-Agent Observability Dashboard — Design

- **Ngày**: 2026-07-19
- **Branch**: `feat/multi-agent-observability` (tạo từ `origin/frontend`)
- **Worktree**: `/home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability`
- **Scope hackathon**: 2–4 ngày
- **Key deliverable**: dashboard Next.js hiển thị agent traces + task status + decisions + collaboration flows cho pipeline phân tích tín dụng đa agent (LangGraph + 4 expert agent + 4 MCP server)

---

## 1. Mục tiêu & phạm vi

### 1.1 Mục tiêu

Cung cấp một dashboard quan sát (observability) cho pipeline phân tích tín dụng đa agent đang chạy trong `worker`, đáp ứng 4 nhu cầu:

1. **Trace**: thấy được mỗi lần gọi LLM (prompt, response, token, cost, latency), mỗi tool call MCP (input, output, latency), mỗi node graph (start/end, parent/child) — theo `case_id`.
2. **Status**: thấy được case nào đang chạy, agent nào đang chạy trong case đó, ở round mấy.
3. **Decisions**: thấy được findings đã viết (kèm version, change_reason, evidence, citations), DecisionPackage cuối cùng (hard gates, scores, strengths, risks, dissent, conditions).
4. **Collaboration**: thấy được fan-out 4 agent song song + challenge loop + conflict detection, có animation live khi case đang chạy.

### 1.2 Phạm vi (in scope)

- Langfuse container on-prem (data residency ngân hàng — không đưa PII tín dụng ra SaaS)
- Langfuse Python SDK native trong `worker/app/llm/adapter.py` + 1 helper `call_tool()` mới — auto context propagation
- 1 FastAPI router `/observability/*` đọc Postgres hiện có
- 1 Next.js route group `/observability` với 4 tab theo SHB Design System
- SSE live cập nhật dùng Redis pub/sub đã có
- Next.js route handler proxy sang Langfuse REST API (server-side, giấu API key)

### 1.3 Out of scope (YAGNI)

- ❌ OpenTelemetry/Prometheus pipeline riêng — chọn Langfuse SDK native cho đơn giản
- ❌ Export audit PDF
- ❌ Replay benchmark
- ❌ Trace Chat Orchestrator (`worker/app/chat/`) — v1 chỉ trace analysis graph, chat sau
- ❌ LangGraph-specific Langfuse integration (no node-level auto-tracing) — chỉ intercept ở adapter + tool helper, đủ cho demo
- ❌ Cost alert, SLO, SRE dashboard

---

## 2. Báo cáo nghiên cứu hệ thống hiện tại

### 2.1 Topology graph (LangGraph — `worker/app/graph/build.py`)

```
plan ──┬─► financial ──┐
       ├─► policy ─────┤
       ├─► collateral ─┼─► detect ─► (open conflicts?) ─► challenge ─► detect ─► ...
       └─► customer360 ┘                              └─► synthesize ─► transition ─► END
```

- 4 expert agent chạy song song trong 1 LangGraph superstep (FanOut), converge tại `detect`
- `detect` là **pure function** (group findings theo `issue_key`, flag khác `stance`) — không phải LLM
- `challenge` loop giới hạn 2 round (`MAX_ROUNDS`), edge condition đọc `ConflictRecord.round` từ Postgres — **không trông vào LLM**
- `synthesize` = hard gates → scorecard → writes `DecisionPackage`
- `transition` = duy nhất 1 tool call `mcp-state::update_case_status` trong toàn pipeline

### 2.2 4 expert agent — cùng 1 pattern lặp

```
DB reads (run_sync) → MCP tool calls (MultiServerMCPClient.get_tools()[name].ainvoke)
                    → LLM call (complete(tier=, system=, user=))
                    → Finding write (run_sync(write_finding_sync, FindingIn(...)))
```

| Agent | Tool allowlist | `AGENT_ID` |
|-------|---------------|------------|
| financial | mcp-deterministic | `financial_analysis` |
| policy | mcp-rag | `policy_compliance` |
| collateral | mcp-deterministic + shared.db | `collateral_legal` |
| customer360 | mcp-external + shared.db | `customer_360` |

### 2.3 Observability đã có sẵn — tận dụng cho dashboard

**Events table** (`shared/models.py::Event`, append-only — migration 0002 đã revoke UPDATE/DELETE ở DB role):

- `event_type` ∈ `{FINDING_WRITTEN, CONFLICT_DETECTED, CONFLICT_RESOLVED, CONFLICT_UNRESOLVED, DECISION_SYNTHESIZED, STATE_TRANSITION, TARGETED_QUESTION_SENT, CHAT_MESSAGE}`
- Có `seq` (monotonic per `case_id`), `actor` `{type, id}`, `payload` JSONB, `versions` JSONB
- → Đây đã là **decision timeline đầy đủ** cho Decisions tab

**Redis pub/sub** (`progress:{case_id}`):

- `job_started`, `job_completed`, `job_failed` (từ `worker/app/main.py::_publish`)
- `step_started`, `step_completed`, `step_failed` (từ `worker/app/graph/build.py::_with_progress` — wrap mỗi node) → đã là **live event feed**

**Findings** (`shared/models.py::Finding`): `version`, `change_reason`, `evidence_ids`, `citations`, `metrics`, `confidence`, `severity`, `stance`, `issue_key`, `agent_id` → sẵn cấu trúc cho drill-down.

**ConflictRecord** (`shared/models.py::ConflictRecord`): `round`, `status` (OPEN/RESOLVED/UNRESOLVED), `source_findings`, `targeted_questions` → sẵn cấu trúc cho Collaboration tab.

**DecisionPackage** (`shared/models.py::DecisionPackage`): `recommendation`, `hard_gates`, `scores`, `strengths`, `risks`, `dissent`, `conditions_precedent`, `policy_version`, `decision_matrix_version` → sẵn cho Decisions tab.

### 2.4 Khoảng trống quan sát — nơi Langfuse lấp

| Khoảng trống | Nguồn thoả |
|--------------|------------|
| Không có `trace_id` trong Postgres | Langfuse trace id = `case_id` (metadata join) |
| Không trace LLM (prompt/response/token/cost/latency) | `langfuse.observe(as_type="generation")` decorate `adapter.complete()`/`stream_complete()` |
| Không trace tool (input/output/latency mỗi MCP call) | helper `call_tool()` bọc `tools[name].ainvoke(...)` với span |
| Không trace latency chính xác theo node | `_with_progress` thêm span start/end |
| Không lưu cost theo run (NFR-08) | Langfuse tổng token+cost theo `trace.id == case_id` |

### 2.5 Integration points xác định

| Cấp trace | Vị trí code | Langfuse primitive |
|----------|-------------|--------------------|
| **Run** (toàn graph cho 1 case) | `worker/app/main.py::_consume_jobs` — quanh `compiled_graph.ainvoke(...)` | `langfuse.trace(name="case_analysis", metadata={"case_id": case_id})` |
| **Node** (mỗi graph node) | `worker/app/graph/build.py::_with_progress(...)` — thêm open/close span | `trace.span(...)` — SDK tự gắn parent qua `contextvars` |
| **LLM generation** | `worker/app/llm/adapter.py::complete()` và `stream_complete()` — duy nhất 1 cục | `@observe(as_type="generation")` auto-wrap |
| **Tool call** | Mới: `worker/app/agents/common.py::call_tool(tools, name, /, **args)` — gom các `tools["x"].ainvoke(...)` | `span(name=f"tool.{name}", metadata={"tool": name})` |

**Khả năng propagation**: Langfuse Python SDK tự xử lý `trace_id`/`parent_id` qua `contextvars` → từ `main.py` mở trace, mọi `complete()` trong agent thừa kế tự động. Zero plumbing thủ công.

### 2.6 Banking requirements thoả

| Nhu cầu ngân hàng | Cách thoả |
|-------------------|----------|
| Data residency (PII tín dụng không ra cloud SaaS) | Langfuse on-prem container, data nằm trong VM |
| Lịch sử / audit append-only, không sửa | Events table đã revoke UPDATE/DELETE role; Langfuse trace immutable |
| Truy vết (replay) theo case | `langfuse.trace.id == case_id` + Events.seq monotonic |
| Cost accountability per case | Langfuse tổng token+cost theo `trace.id == case_id` |
| Collaboration decision rationale visible | `ConflictRecord.round` + `Finding.change_reason` + `DecisionPackage.dissent` |
| Dashboard "đậm vibe ngân hàng", lịch sử | `web/SHB Design System` (tokens + CRM dashboard template đã có) |

---

## 3. Kiến trúc tổng thể

### 3.1 Sơ đồ

```
                        ┌──────────────────────────────────────────────────────┐
                        │             Next.js Dashboard /observability         │
                        │  4 tab: Traces | Status | Decisions | Collaboration │
                        │  (SHB Design System)                                  │
                        └───┬───────────────┬────────────────────┬─────────────┘
                            │ REST           │ SSE (live)         │ REST proxy
                            ▼               ▼                    ▼
                  FastAPI /observability  Redis pub/sub    Next.js route handler
                  ├── GET /cases          progress:{cid}    → Langfuse REST API
                  ├── GET /cases{id}/timeline                /api/public/traces
                  ├── GET /cases/{id}/findings                ?metadata.case_id=X
                  ├── GET /cases/{id}/decision                (server-side, API key
                  ├── GET /cases/{id}/conflicts                 không expose browser)
                  └── GET /cases/{id}/events
                            │
                            ▼
                        Postgres
                  cases / events / findings /
                  decisions / conflicts
                        ▲
                        │ (write path hiện có, không đổi)
                        │
   ┌─────────────┐     │     ┌──────────────────────┐     ┌──────────────┐
   │ worker     │─────┘     │ langfuse SDK wrapping │     │ langfuse     │
   │ LangGraph  │           │ adapter.py + MCP      │────►│ (on-prem)    │
   │ (agents)   │           │                       │     │ port :3001   │
   └─────────────┘           └──────────────────────┘     └──────────────┘
```

### 3.2 5 đơn vị độc lập — mỗi đơn vị 1 mục đích, giao tiếp qua interface cố định

| # | Đơn vị | Mục đích | Phụ thuộc |
|---|--------|----------|-----------|
| **U1** | `worker/app/observability/tracing.py` (MỚI) | Langfuse SDK wiring; expose `trace_case_run()`, `call_tool()`, decorate `complete()`/`stream_complete()` | `langfuse` SDK Python |
| **U2** | `worker/app/graph/build.py` + `worker/app/agents/common.py` (sửa) | Dùng U1: `trace_case_run()` quanh `ainvoke`, `call_tool()` thay `.ainvoke` trực tiếp, `_with_progress` thêm span | U1 |
| **U3** | `api/app/routers/observability.py` (MỚI) | FastAPI endpoint đọc Postgres | Postgres + `shared.models` |
| **U4** | `web/app/observability/` (MỚI) | 4 tab dashboard bằng SHB Design System | api (REST), Redis (SSE), Langfuse (REST proxy) |
| **U5** | `langfuse` docker-compose service (MỚI) + `.env` flag | Trace store on-prem, optional (`OBSERVABILITY_ENABLED`) | docker compose |

Mỗi đơn vị test được độc lập (xem §7).

---

## 4. Interfaces (hợp đồng cố định)

### 4.1 U1 → U2 (Python)

```python
# worker/app/observability/tracing.py
from contextlib import asynccontextmanager
from typing import Any

@asynccontextmanager
async def trace_case_run(case_id: str, *, metadata: dict | None = None):
    """Mở một Langfuse trace với id = case_id (nguyên chủ ý để JOIN với
    Postgres). Yields một context object có `.current_span()`. Tự đóng khi
    thoát. No-op khi OBSERVABILITY_ENABLED=false (yield context rỗng, không
    network). Phải được await với `async with trace_case_run(...) as ctx:`."""

async def call_tool(tools: dict, name: str, /, **args: Any) -> Any:
    """Wrap `tools[name].ainvoke(args)` với một span tên `tool.{name}`, tự
    capture input/output, metadata.case_id thừa kế từ trace đang chạy.
    No-op span khi OBSERVABILITY_ENABLED=false (chỉ gọi ainvoke)."""

# adapter.py được decorate:
#   @langfuse.observe(as_type="generation")
#   async def complete(*, tier, system, user): ...
# metadata tự thêm {tier, model, provider} từ cfg
```

### 4.2 U3 → U4 (HTTP REST, JSON)

```
GET  /observability/cases
  → [{case_id, customer_id, state, version, created_at, updated_at, owner, requested_facility}]

GET  /observability/cases/{id}/timeline
  → [{seq, event_type, actor, timestamp, payload, versions}]

GET  /observability/cases/{id}/findings
  → [{display_id, finding_key, issue_key, agent_id, stance, severity, confidence,
      version, change_reason, metrics, evidence_ids, citations, created_at}]

GET  /observability/cases/{id}/decision
  → {recommendation, requested_amount_vnd, recommended_amount_vnd,
      recommended_tenor_months, hard_gates, scores, strengths, risks, dissent,
     conditions_precedent, policy_version, decision_matrix_version, created_at}
   | null  (case chưa synthesize)

GET  /observability/cases/{id}/conflicts
  → [{conflict_id, issue_key, round, status, source_findings, targeted_questions,
      created_at, updated_at}]

GET  /observability/cases/{id}/trace
  → {langfuse_trace_id, langfuse_url}   # redirect helper tới Traces tab
```

Tất cả read-only, không mutate state. Endpoint mount vào `api/app/main.py` qua `app.include_router(observatory.router)`.

### 4.3 SSE contract (không đổi)

Redis channel `progress:{case_id}` → `api` proxy → web EventSource. Pattern đã có ở `web/app/sse/cases/[caseId]/`. Dashboard subscribe channel này cho Status tab + Collaboration tab animation.

### 4.4 Web → Langfuse (server-side proxy)

Next.js route handler (App Router, `web/app/observability/api/traces/[caseId]/route.ts`):

```
GET /observability/api/traces/[caseId]
  → server-side call: Langfuse GET /api/public/traces?metadata.case_id={caseId}
  → returns: {trace_id, name, timestamp, total_cost, total_tokens, spans, generations}
  → Langfuse API key read server-side from env LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY
```

Không bao giờ expose Langfuse URL/key cho browser. CORS không cần vì server-side.

---

## 5. Data flow cụ thể

```
worker/app/main.py::_consume_jobs():
  async with trace_case_run(case_id=C06) as ctx:
    await compiled_graph.ainvoke({...}, config={...})

worker/app/graph/build.py::_with_progress(step_id, node_fn):
  # mở span quanh node_fn, tự gắn parent qua contextvars
  await publish_progress(...)  # step_started — giữ nguyên
  with ctx.span(name=step_id, metadata={"agent_id":...}) if ctx else nullctx:
    result = await node_fn(state)
  await publish_progress(...)  # step_completed — giữ nguyên

worker/app/llm/adapter.py::complete():  # decorated @observe(as_type="generation")
  # SDK tự capture prompt/response/token/cost/latency

worker/app/agents/common.py::call_tool(tools, "calculate_financial_ratios", financials=...):
  # SDK tự open span tool.calculate_financial_ratios, capture input/output

→ Langfuse batched upload (async, fire-and-forget, không block worker)
→ trace.id = C06, spans lồng nhau tự động qua contextvars
```

---

## 6. Routing dashboard Next.js

```
/observability                         → redirect /observability/status
/observability/status                  → bảng case queue + live SSE tick
/observability/traces                  → list recent traces (Langfuse REST)
/observability/traces/[caseId]         → Gantt timeline (Langfuse spans + Postgres events overlay)
/observability/decisions               → case finder
/observability/decisions/[caseId]      → finding list drawer + DecisionPackage card + version diff
/observability/collaboration           → case finder
/observability/collaboration/[caseId]  → animated graph (SSE live) + ConflictRecord edge coloring
```

## 7. Style (banking)

- Dùng `web/SHB Design System` tokens (color, typography, spacing) đã có sẵn — không tự chế token mới
- Status tab dùng SHB CRM Dashboard template làm base layout
- Traces Gantt: `recharts` (đã có dependency) — không thêm lib
- Collaboration graph: custom SVG (animated dashes khi node nhận `step_started` từ SSE)
- Convention label tiếng Việt: "Hồ sơ" thay "Case", "Quyết định" thay "Decision", "Nhận định" thay "Finding", "Mâu thuẫn" thay "Conflict". Không emoji trong UI chính.

---

## 8. Error handling

| Lỗi | Hành vi |
|-----|---------|
| `OBSERVABILITY_ENABLED=false` | U1 no-op (span/generation stub rỗng), U5 container tắt. Dashboard Traces tab hiển thị banner "Tính năng quan sát chưa bật" + fallback Postgres timeline |
| Langfuse network fail | SDK chạy offline, batch retry, **không crash worker** (fire-and-forget default) |
| api endpoint Postgres fail | HTTP 503 + log traceback vào stderr of `api` |
| Web → Langfuse proxy fail | Traces tab degrade: hiển thị timeline từ `/observability/cases/{id}/timeline` (Postgres events) — vẫn đầy đủ finding/conflict/decision events |
| SSE disconnect | auto-reconnect EventSource (browser native) |

---

## 9. Testing

| Đơn vị | Test |
|--------|------|
| **U1** | pytest mock `langfuse.Langfuse` client, run `trace_case_run` + `complete()`, assert spans có metadata đúng (`case_id`, `tier`, `model`); assert no-op khi `OBSERVABILITY_ENABLED=false` |
| **U2** | Tất cả test hiện có trong `tests/` phải vẫn pass (không phá `_with_progress`); thêm 1 test assert `call_tool()` đã wrap một MCP call với span |
| **U3** | pytest `TestClient` chạy 6 endpoint, schema-match contract trong §4.2; test empty case (chưa synthesize decision) trả `null` không crash |
| **U4** | jest/playwright component test cho 4 tab render với mock data fixture |
| **U5** | docker compose up smoke test: `curl langfuse:3001/api/public/health` trả 200 |

---

## 10. Cảnh tỉnh YAGNI

- ❌ OpenTelemetry/Prometheus pipeline — chọn Langfuse SDK native
- ❌ Export audit PDF
- ❌ Replay benchmark (golden scenarios)
- ❌ LangGraph-specific Langfuse integration (không tự trace every node từ graph internal — chỉ intercept ở adapter + helper)
- ❌ Cost alert / SLO / SRE dashboard
- ❌ Trace Chat Orchestrator ở v1 (sau)
- ❌ PII redaction trong Langfuse (data on-prem nên không yêu cầu; nếu cần thêm sau)

---

## 11. Biến môi trường mới

Append vào `.env.example`:

```
# Observability (Langfuse on-prem) — set false để tắt toàn bộ trace
OBSERVABILITY_ENABLED=true
LANGFUSE_HOST=http://langfuse:3001
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Worker đọc `OBSERVABILITY_ENABLED`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`. Web chỉ đọc `LANGFUSE_HOST` + 2 keys (cho proxy server-side).

---

## 12. Plan triển khai nhanh (4 ngày)

| Ngày | Đơn vị | Công việc | Done when |
|------|--------|-----------|-----------|
| 1 | U5 + U1 | docker-compose langfuse + `.env`; `worker/app/observability/tracing.py`decorate `complete()`/`stream_complete()` + `call_tool()` + `trace_case_run()`; test U1 | `pytest tests/observability/test-tracing.py` pass; `langfuse` healthcheck |
| 2 | U2 | sửa `build.py::_with_progress` thêm span; sửa `agents/common.py` expose `call_tool()`; sửa từng agent từ `.ainvoke` sang `call_tool`; chạy test tích hợp hiện có | `pytest` không bị fail mới; Langfuse UI thấy trace đầy đủ node+tool+generation khi gọi `/cases/{id}/analyze` |
| 3 | U3 + U4a | `api/app/routers/observability.py` + test; Status tab + Decisions tab bằng SHB Design System | `/observability/cases` trả JSON; 2 tab render được trong web |
| 4 | U4b | Traces tab + Collaboration tab (graph animation SVG + SSE) | Smoke demo chạy được 1 case end-to-end và thấy trace+collab live |

---

## 13. Risk

| Risk | Mitigation |
|------|-----------|
| Langfuse SDK conflict với `langchain-mcp-adapters` contextvars | Đã verify Langfuse SDK chỉ dùng `contextvars` riêng — test sớm ngày 1 |
| `langfuse` docker image nặng | Dùng image chính thức, không tự build; check CPU/RAM heap, nếu cao giảm `OBSERVABILITY_ENABLED=false` trong demo |
| SHB Design System không có component cho Gantt/graph | Traces dùng recharts; Collaboration vẽ SVG custom (2 ngày 4 có thời gian) |
| `adapter.py` decorate có thể phá `LLM_MOCK=true` mode | Test U1 assert mock mode vẫn trả đúng response (decorate không thay return value) |
| Thiên về hackathon → debt kỹ thuật | Ghi README spec về "v1 chỉ observability demo, không production-grade"; cách tắt qua env; cách migrate lên OTel sau |

---

## 14. Tham chiếu

- `docs/architecture/overview.md` — kiến trúc tổng quan, Langfuse đã được ghi như "tuỳ chọn"
- `docs/architecture/ai-architecture.md` §4, §5.2–§5.7, §9.2, §10 — graph topology, agent design, conflict detector, decision synthesis
- `docs/architecture/ai-architecture_v2.md` §11.8 — Chat Orchestrator (out of scope v1)
- `worker/app/graph/build.py` — graph implementation hiện tại
- `worker/app/llm/adapter.py` — single LLM integration point
- `shared/models.py` — Event, Finding, ConflictRecord, DecisionPackage schema
- `web/SHB Design System/` — design tokens + CRM template