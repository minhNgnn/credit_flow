> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# SHBExpert Flow documentation — where to start (English)

> **The authoritative architecture document is [`architecture/ai-architecture_v2.md`](architecture/ai-architecture_v2.md).** `ai-architecture.md` (v1) is kept as a historical reference; `overview.md` and `data-flow.md` describe topology and data flow and are still useful, but where they conflict with v2, v2 wins.

All data in the system is **synthetic**, declared on every case (`synthetic_flag`). The system only produces **recommendations** for the Credit Officer — it does not approve, sign or disburse. All checklists/thresholds/weights are **simulations for the competition**, not SHB's official risk process.

## Read by purpose

| You want to know | Read | Lines |
|---|---|---|
| What the system contains, which service calls which | [`architecture/overview.md`](architecture/overview.md) | 267 |
| AI architecture: Orchestrator, Expert Workcell, evidence, tool boundary | [`architecture/ai-architecture_v2.md`](architecture/ai-architecture_v2.md) | 1884 |
| How data flows, the state machine, decision diagrams | [`architecture/data-flow.md`](architecture/data-flow.md) | 571 |
| **Is multi-agent really better than single-agent — with numbers** | [`eval-multi-vs-single-agent.md`](eval-multi-vs-single-agent.md) | 463 |
| **AI safety: grounding, anti-hallucination, prompt injection, audit** | [`ai-safety-grounding.md`](ai-safety-grounding.md) | 134 |
| How the synthetic data is generated | [`synthetic-data-pipeline-plan.md`](synthetic-data-pipeline-plan.md) | 256 |
| Data gaps versus PRD §9 | [`data-prd9-matching-report.md`](data-prd9-matching-report.md) | 183 |

## What is RUNNING vs. what is still design

`ai-architecture_v2.md` labels every item **CURRENT / TARGET v2 / MOCK / OPEN** (see its §0). A quick summary so you do not have to read all 1884 lines:

### Running for real (CURRENT)

| Capability | Evidence in code |
|---|---|
| Orchestrator + 4 parallel expert agents, with a conflict detector and challenge loop | `worker/app/graph/build.py` (LangGraph, Postgres checkpoint) |
| Real MCP tool boundary: 4 separate servers, per-agent tool permissions | `mcp-deterministic` / `mcp-rag` / `mcp-external` / `mcp-state` |
| Deterministic computation — the LLM never computes numbers itself | `mcp-deterministic/app/server.py`, each result carries a `formula_version` |
| Hard gates G1–G9 run BEFORE the scorecard | `worker/app/graph/decision.py::_check_hard_gates` |
| Evidence is mandatory for HIGH/CRITICAL findings | `shared/state.py::write_finding` → `EvidenceRequiredError` |
| Append-only audit log, UPDATE/DELETE revoked at the DB layer | `api/alembic/versions/0002_revoke_events_mutation.py` |
| **Single-agent vs multi-agent eval harness** — 24 cases × 3 runs × 2 variants = 144 real runs | [`../eval/`](../eval/), results in [`../eval/compare/summary.md`](../eval/compare/summary.md) |
| **Prompt-injection defence** for untrusted content | `worker/app/llm/sanitize.py` |
| Chat Orchestrator (case follow-up questions, streaming) | `worker/app/chat/orchestrator.py` |
| Dashboard: queue, overview, expert council, conflicts, recommendation, audit | `web/app/` (Next.js) |

### Still design (TARGET v2) or missing

The full list is in `ai-architecture_v2.md` §17 and `ai-safety-grounding.md` §6. The most notable items, **disclosed rather than hidden**:

- **No RBAC/auth yet** — stated in `api/app/routers/internal.py`.
- **Gate G2 (KYC) fails open** when the Customer 360 finding is missing (`decision.py`).
- **No leverage gate** — the `HIGH_LEVERAGE` archetype can still yield `APPROVE`; the eval publishes this number instead of ignoring it.
- **The 5th agent (Industry) is a placeholder** — the `INDUSTRY_GOVERNANCE` score is fixed.
- **No Document Processing / OCR** — `extracted_fields` are written by seed scripts.
- **No automated tests or CI yet.**

## Headline numbers (measured, not estimated)

From [`eval-multi-vs-single-agent.md`](eval-multi-vs-single-agent.md) — same model (Llama-3.3-70B via FPT AI Factory), same test set, only the architecture differs:

| Metric | single-agent | multi-agent |
|---|---|---|
| Correct decision | 0.125 | **0.875** |
| Numeric accuracy | 0.117 | **0.801** |
| Risk recall | 0.651 | **1.000** |
| Stability (pass³) | 0.708 | **1.000** |
| False alarms (lower is better) | 0.125 | **0** |
| Run time | **~10.9s** | ~20.9s |

This eval also **found a real safety bug** in the system itself (customers with CIC group 3–4 debt were still `APPROVE`d). It was fixed with hard gates G7–G9 and re-verified with numbers: `decision_correct` 0.500 → 0.875. Details in [`ai-safety-grounding.md`](ai-safety-grounding.md) §4.1.

---

<a id="vi"></a>

# 🇻🇳 Tiếng Việt

# Tài liệu SHBExpert Flow — đọc từ đâu

> **Bản authoritative về kiến trúc là [`architecture/ai-architecture_v2.md`](architecture/ai-architecture_v2.md).**
> `ai-architecture.md` (v1) giữ lại làm tham chiếu lịch sử; `overview.md` và
> `data-flow.md` mô tả topology/luồng dữ liệu và vẫn hữu ích, nhưng chỗ nào mâu
> thuẫn với v2 thì lấy v2 làm chuẩn.

Toàn bộ dữ liệu trong hệ thống là **synthetic**, khai báo rõ ở từng case
(`synthetic_flag`). Hệ thống chỉ tạo **khuyến nghị** cho Credit Officer — không
phê duyệt, không ký, không giải ngân. Mọi checklist/ngưỡng/trọng số là **mô
phỏng cho cuộc thi**, không phải quy trình rủi ro chính thức của SHB.

---

## Đọc theo mục đích

| Bạn muốn biết | Đọc file này | Dòng |
|---|---|---|
| Hệ thống gồm gì, service nào gọi service nào | [`architecture/overview.md`](architecture/overview.md) | 267 |
| Kiến trúc AI: Orchestrator, Expert Workcell, evidence, tool boundary | [`architecture/ai-architecture_v2.md`](architecture/ai-architecture_v2.md) | 1884 |
| Dữ liệu chạy qua hệ thống thế nào, state machine, sơ đồ quyết định | [`architecture/data-flow.md`](architecture/data-flow.md) | 571 |
| **Multi-agent có thật sự hơn single-agent không — số đo** | [`eval-multi-vs-single-agent.md`](eval-multi-vs-single-agent.md) | 463 |
| **An toàn AI: grounding, chống hallucination, prompt injection, audit** | [`ai-safety-grounding.md`](ai-safety-grounding.md) | 134 |
| Dữ liệu synthetic được sinh ra sao | [`synthetic-data-pipeline-plan.md`](synthetic-data-pipeline-plan.md) | 256 |
| Khoảng cách dữ liệu so với yêu cầu PRD §9 | [`data-prd9-matching-report.md`](data-prd9-matching-report.md) | 183 |

---

## Cái gì ĐÃ CHẠY, cái gì còn là thiết kế

`ai-architecture_v2.md` dùng hệ nhãn **CURRENT / TARGET v2 / MOCK / OPEN** (xem
§0 của file đó). Tóm tắt nhanh để không phải đọc hết 1884 dòng:

### Đã chạy thật (CURRENT)

| Năng lực | Bằng chứng trong code |
|---|---|
| Orchestrator + 4 expert agent chạy song song, có conflict detector và challenge loop | `worker/app/graph/build.py` (LangGraph, checkpoint Postgres) |
| Tool boundary qua MCP thật, 4 server tách biệt, phân quyền tool theo agent | `mcp-deterministic` / `mcp-rag` / `mcp-external` / `mcp-state` |
| Tính toán xác định — LLM không bao giờ tự tính số | `mcp-deterministic/app/server.py`, mỗi kết quả có `formula_version` |
| Hard gate G1–G9 chạy TRƯỚC scorecard | `worker/app/graph/decision.py::_check_hard_gates` |
| Bắt buộc bằng chứng cho finding HIGH/CRITICAL | `shared/state.py::write_finding` → `EvidenceRequiredError` |
| Audit log append-only, thu hồi quyền UPDATE/DELETE ở tầng DB | `api/alembic/versions/0002_revoke_events_mutation.py` |
| **Eval harness single-agent vs multi-agent** — 24 case × 3 lượt × 2 variant = 144 lượt chạy thật | [`../eval/`](../eval/), kết quả ở [`../eval/compare/summary.md`](../eval/compare/summary.md) |
| **Phòng thủ prompt injection** cho nội dung không đáng tin | `worker/app/llm/sanitize.py` |
| Chat Orchestrator (hỏi tiếp theo hồ sơ, streaming) | `worker/app/chat/orchestrator.py` |
| Dashboard: queue, overview, expert council, conflicts, recommendation, audit | `web/app/` (Next.js) |

### Còn là thiết kế (TARGET v2) hoặc còn thiếu

Danh sách đầy đủ ở `ai-architecture_v2.md` §17 và `ai-safety-grounding.md` §6.
Những mục đáng chú ý nhất, **công bố rõ chứ không giấu**:

- **Chưa có RBAC/auth** — `api/app/routers/internal.py` ghi rõ.
- **Gate G2 (KYC) fail-open** khi thiếu finding Customer 360 (`decision.py`).
- **Chưa có gate đòn bẩy** — archetype `HIGH_LEVERAGE` vẫn có thể ra `APPROVE`;
  eval công bố con số này thay vì bỏ qua.
- **Agent thứ 5 (Industry) là placeholder** — điểm `INDUSTRY_GOVERNANCE` cố định.
- **Document Processing / OCR chưa có** — `extracted_fields` do seed script ghi.
- **Chưa có test tự động và CI.**

---

## Số liệu nổi bật (đo thật, không ước lượng)

Từ [`eval-multi-vs-single-agent.md`](eval-multi-vs-single-agent.md) — cùng model
(Llama-3.3-70B qua FPT AI Factory), cùng bộ đề, chỉ khác kiến trúc:

| Chỉ số | single-agent | multi-agent |
|---|---|---|
| Quyết định đúng | 0.125 | **0.875** |
| Độ chính xác số học | 0.117 | **0.801** |
| Độ phủ rủi ro (recall) | 0.651 | **1.000** |
| Độ ổn định (pass³) | 0.708 | **1.000** |
| Cảnh báo giả (thấp = tốt) | 0.125 | **0** |
| Thời gian chạy | **~10.9s** | ~20.9s |

Bộ eval này cũng **phát hiện một lỗi an toàn thật** trong chính hệ thống (khách
nợ CIC nhóm 3–4 vẫn được `APPROVE`), lỗi đó đã được vá bằng hard gate G7–G9 và
kiểm chứng lại bằng số: `decision_correct` 0.500 → 0.875. Chi tiết ở
[`ai-safety-grounding.md`](ai-safety-grounding.md) §4.1.
