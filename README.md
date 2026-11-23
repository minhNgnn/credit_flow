> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# SHBExpert Flow — dashmint_ai (English)

**Multi-agent AI for SME credit appraisal.** An AI workspace that prepares an evidence-backed lending recommendation for a bank's Credit Officer — it never approves a loan itself.

## Who it's for

**Credit Officers (CO)** and **Relationship Managers (RM)** at a bank who appraise loan applications from small and medium businesses.

## The problem

- **Too many documents to cross-check by hand.** One application has financial statements, tax filings, valuation certificates, ownership records and credit-bureau (CIC) data. Inconsistencies, such as revenue that differs between the financial statements and the tax filing, are easy to miss.
- **Many specialist views, one decision.** Financial, collateral, legal and policy checks each need their own expertise, and disagreements between them are rarely made explicit.
- **Generic AI isn't trustworthy here.** Plain chatbots invent numbers, can't show where a claim came from, and leave no audit trail. That is unacceptable in a regulated credit process.

## The solution

- **An Orchestrator with expert agents.** The Orchestrator plans the work; Financial, Collateral & Legal, Customer 360 and Policy agents analyse the case in parallel.
- **A Conflict Detector and challenge loop.** When agents disagree, the conflict is surfaced and debated rather than averaged away.
- **Evidence for every claim.** Each finding links to the exact page and line of the source PDF, highlighted in the viewer.
- **Hard gates before scoring.** Serious red flags block approval whatever the score: bad debt (CIC group 3 or worse), DSCR below 1.3, or an expired valuation.
- **A chat assistant per case.** The CO asks follow-up questions and gets streamed answers grounded only in that case's findings.
- **A complete audit trail.** Every LLM call, tool call and decision goes into an append-only log that the application cannot edit.

## How it's built

- **Agents:** LangGraph Orchestrator and Workers, with state checkpointed in Postgres.
- **The LLM explains, it never calculates.** Every decision number (DSCR, LTV, coverage, revenue mismatch) comes from deterministic Python tools exposed over **MCP**; the LLM only interprets them ([docs/ai-safety-grounding.md](docs/ai-safety-grounding.md)).
- **RAG:** Qdrant vector store holding policy, legal checklists and industry knowledge.
- **Provider-agnostic LLM layer:** tiers and providers are set in [worker/config/models.yaml](worker/config/models.yaml). The demo runs on OpenRouter, and `LLM_MOCK=true` runs the whole flow offline.
- **Backend:** FastAPI, Postgres, Redis job queue, MinIO document store, SSE live progress.
- **Frontend:** Next.js / React dashboard with 8 screens, a PDF evidence viewer and EN/VI support.
- **Observability:** self-hosted Langfuse tracing for every agent and LLM call.
- **Deployment:** the full stack runs in Docker Compose on a single VM, provisioned with Terraform.

## Results

Ablation on 24 synthetic cases × 3 runs, same model, only the architecture changed ([docs/eval-multi-vs-single-agent.md](docs/eval-multi-vs-single-agent.md)):

| | Single agent | Multi-agent |
|---|---|---|
| Correct decision | 12.5% | **87.5%** |
| Numeric accuracy | 0.12 | **0.80** |
| Risk recall | 0.65 | **1.00** |

The cost is about 1.9× the latency (around 21 s per case), which is worth it for a credit decision.

---

**SHBExpert Flow** is an SME credit-appraisal workspace (synthetic data, built for demos and a competition). An Orchestrator plans the work and delegates it to expert agents; the agents challenge each other in a structured way, and the result is merged into an **evidence-backed** recommendation package for the Credit Officer.

> ⚠️ **Governance notice:** every checklist, policy, threshold, hard gate, scorecard weight and approval flow in this system is a **simulation for the competition**. It is not SHB's official process or risk appetite. The system only produces **recommendations** for the Credit Officer; it does not approve, sign or disburse. All data is **synthetic**.

## 1. What the system contains

The whole stack runs **on a single Linux server** (Ubuntu 22.04, 4 vCPU / 16 GB RAM / 100 GB SSD, no GPU) using Docker Compose. Only two paths cross the VM boundary: the browser calling the proxy, and the worker calling the LLM provider.

### Application services

| Service | Port | Tech | Role |
|---|---|---|---|
| `web` | 3000 | Next.js / React | 8-screen dashboard: Case Queue, Overview, Documents, Expert Council, Conflicts, Recommendation, Conditions, Audit. Supports **EN/VI** (use the VI \| EN toggle in the sidebar footer). |
| `api` | 8000 | FastAPI | Owns CaseState. REST + SSE run status. The only place that checks RBAC, validates schemas and emits (append-only) audit events. |
| `worker` | — | Python + LangGraph | The AI brain: Orchestrator + expert agents + deterministic functions. Receives jobs via Redis; exposes no port. |
| `tools-mock` | 8100 | FastAPI | Mock APIs for CIC, KYC/AML, valuation, LOS — with a seed-deterministic mode (offline fallback). |

### Infrastructure

| Service | Role |
|---|---|
| `postgres:16` | CaseState, versioned findings, tasks, conflicts, conditions, append-only event log, LangGraph checkpoints. |
| `qdrant` | Vector store for the policy pack, legal checklist and industry knowledge (accessed via `mcp-rag`). |
| `redis:7` | `api` → `worker` job queue; pub/sub pushes agent progress to SSE. |
| `minio` | S3-compatible object store: documents by version + hash (files are not stored in Postgres). |
| `mcp-*` | MCP layer: `mcp-deterministic`, `mcp-rag`, `mcp-external`, `mcp-state` — the worker calls tools through these. |

A diagram and more detail are in [`docs/architecture/overview.md`](docs/architecture/overview.md).

## 2. Main features

- **Case Queue & Dashboard** — COs/RMs manage and track cases under appraisal.
- **Orchestrator + Expert Agents** — planning and parallel task assignment across agents: `collateral`, `financial`, `customer360`, `policy`, plus challenger agents.
- **Evidence Drawer** — every claim cites the exact page/region of a document (with a MinIO presigned URL).
- **Expert Council & Conflicts** — shows the expert panel and where agents disagree.
- **Credit Memo & Scoring** — appraisal summary + weighted scorecard (simulated).
- **Chat Orchestrator** — per-case Q&A that cites evidence back to findings.
- **Audit trail** — append-only event log, traces every LLM/tool call.
- **Demo fallback (PRD 14.4)** — `LLM_MOCK=true` runs the full flow on seed-deterministic results, with no LLM key or internet.

## 3. Quick start

**Requirements:** Docker + Docker Compose v2. Optionally `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` — otherwise set `LLM_MOCK=true`.

1. **Configure the environment**
   ```bash
   cp .env.example .env
   # Edit .env: Postgres/MinIO passwords, LLM key, or keep LLM_MOCK=true
   ```
2. **Start the stack**
   ```bash
   docker compose up -d --build
   docker compose ps          # wait until every service is healthy
   ```
   Default endpoints (bound to localhost): Dashboard http://localhost:3000 · API http://localhost:8000 (health: `/health`) · MinIO console http://localhost:9001
3. **Migrate & seed demo data** (safe to re-run)
   ```bash
   bash scripts/bootstrap_deploy.sh
   ```
   It runs `alembic upgrade head`, seeds the policy pack into Qdrant (`mcp-rag`), seeds reference data (collateral/legal checklist, customer360), and seeds the golden + synthetic cases.
4. **Use the system** — open http://localhost:3000, pick a case in the **Case Queue**, watch agent progress live over SSE in **Overview**, open **Documents** for the evidence drawer, **Expert Council** for the challenges, and **Recommendation** for the recommendation and its conditions. Switch the UI language with the **VI | EN** toggle at the bottom of the sidebar.

## 4. Repository layout

```
api/                 FastAPI — CaseState, REST, SSE, RBAC, audit events
web/                 Next.js — 8-screen dashboard + EN/VI i18n
worker/              LangGraph runtime — orchestrator, agents, chat
mcp-*/               MCP layer (deterministic / rag / external / state)
tools-mock/          Mock CIC/KYC/AML/valuation/LOS APIs
shared/              Models, schemas, constants shared by api & worker
scripts/             Migrate + seed (bootstrap_deploy.sh, seed_case_c0*.py, ...)
postgres/            Init role bootstrap (least-privilege)
infra/               Terraform (optional VM deployment)
deploy/              Caddyfile + deploy.sh (runs on the VM)
docs/architecture/   overview.md · ai-architecture_v2.md · data-flow.md
```

## 5. Deploying to a VM

You can deploy to a single Linux VM with `deploy/deploy.sh` + `docker-compose.prod.yml` (Caddy is the only proxy). See the header comment of `deploy/deploy.sh` and section 2 of `docs/architecture/overview.md`.

## 6. License / Scope

A demo / competition project. It is **not** connected to a real Core Banking/LOS/CIC/AML system, does not approve or disburse, and contains no real customer data. All data is synthetic.

---

<a id="vi"></a>

# 🇻🇳 Tiếng Việt

# SHBExpert Flow — dashmint_ai

Hệ thống **SHBExpert Flow** là không gian làm việc thẩm định tín dụng SME (Synthetic, phục vụ demo/cuộc thi). Một Orchestrator lập kế hoạch và giao việc cho các expert agent, các agent phản biện có cấu trúc, rồi hợp nhất thành một gói khuyến nghị **có bằng chứng** cho Credit Officer.

> ⚠️ **Lưu ý quản trị:** Mọi checklist, chính sách, ngưỡng, hard gate, trọng số scorecard và luồng phê duyệt trong hệ thống này là **mô phỏng phục vụ cuộc thi**, không phải quy trình hoặc khẩu vị rủi ro chính thức của SHB. Hệ thống chỉ tạo **khuyến nghị** cho Credit Officer; nó không phê duyệt, không ký và không giải ngân. Toàn bộ dữ liệu là **synthetic**.

---

## 1. Hệ thống gồm những gì

Toàn bộ stack chạy **trọn vẹn trên một máy chủ Linux duy nhất** (Ubuntu 22.04, 4 vCPU / 16 GB RAM / 100 GB SSD, không cần GPU) bằng Docker Compose. Chỉ có hai đường cut qua biên VM: trình duyệt gọi vào proxy, và worker gọi ra LLM provider.

### Service ứng dụng

| Service | Cổng | Công nghệ | Vai trò |
|---|---|---|---|
| `web` | 3000 | Next.js / React | Dashboard 8 màn: Case Queue, Overview, Documents, Expert Council, Conflicts, Recommendation, Conditions, Audit. Hỗ trợ EN/VI i18n. |
| `api` | 8000 | FastAPI | Chủ sở hữu CaseState. REST + SSE trạng thái chạy. Nơi duy nhất kiểm tra RBAC, validate schema, sinh event audit (append-only). |
| `worker` | — | Python + LangGraph | Bộ não AI: Orchestrator + expert agents + deterministic functions. Nhận job qua Redis, không expose cổng. |
| `tools-mock` | 8100 | FastAPI | API mock cho CIC, KYC/AML, valuation, LOS — có chế độ deterministic theo seed (fallback khi mất mạng). |

### Hạ tầng

| Service | Vai trò |
|---|---|
| `postgres:16` | CaseState, findings (versioned), tasks, conflicts, conditions, event log append-only, LangGraph checkpoint. |
| `qdrant` | Vector store cho policy pack, legal checklist, industry knowledge (truy cập qua `mcp-rag`). |
| `redis:7` | Job queue `api` → `worker`; pub/sub đẩy tiến độ agent lên SSE. |
| `minio` | Object store S3-compatible: document theo version + hash (file không lưu trong Postgres). |
| `mcp-*` | Lớp MCP: `mcp-deterministic`, `mcp-rag`, `mcp-external`, `mcp-state` — worker gọi tool qua đây. |

Sơ đồ và dạng chi tiết hơn trong [`docs/architecture/overview.md`](docs/architecture/overview.md).

---

## 2. Chức năng chính

- **Case Queue & Dashboard** — CO/RM quản lý và theo dõi hồ sơ đang thẩm định.
- **Orchestrator + Expert Agents** — lập kế hoạch, phân việc song song giữa các agent:
  - `collateral` (tài sản đảm bảo), `financial` (tài chính), `customer360` (khách hàng 360°), `policy` (chính sách) và các agent phản biện.
- **Evidence Drawer** — mỗi claim trích nguồn tới đúng trang/vùng tài liệu (gửi kèm presigned URL MinIO).
- **Expert Council & Conflicts** — hiển thị hội đồng chuyên gia và điểm bất đồng giữa các agent.
- **Credit Memo & Scoring** — tóm tắt thẩm định + scorecard có trọng số (mô phỏng).
- **Chat Orchestrator** — chat Q&A theo case, dẫn nguồn bằng chứng ngược về findings.
- **Audit trail** — event log append-only, trace từng LLM/tool call.
- **Fallback demo (PRD 14.4)** — `LLM_MOCK=true` chạy toàn luồng bằng kết quả deterministic theo seed, không cần key LLM hay internet.

---

## 3. Hướng dẫn sử dụng nhanh

### Yêu cầu

- Docker + Docker Compose v2
- (Tuỳ chọn) `ANTHROPIC_API_KEY` hoặc `OPENAI_API_KEY` — nếu không có, đặt `LLM_MOCK=true`.

### Bước 1 — Cấu hình môi trường

```bash
cp .env.example .env
# Sửa .env: mật khẩu Postgres/MinIO, key LLM, hoặc giữ LLM_MOCK=true
```

### Bước 2 — Khởi động stack

```bash
docker compose up -d --build
docker compose ps          # chờ tới khi mọi service báo healthy
```

Sau khi healthy, các cổng truy cập (mặc định bind localhost):
- Dashboard: http://localhost:3000
- API: http://localhost:8000  (health: `/health`)
- MinIO console: http://localhost:9001

### Bước 3 — Migrate & seed dữ liệu demo

```bash
bash scripts/bootstrap_deploy.sh
```

Script này (an toàn khi chạy lại nhiều lần) sẽ:
1. `alembic upgrade head` — tạo schema trong Postgres.
2. Seed policy pack vào Qdrant (`mcp-rag`).
3. Seed reference data (collateral/legal checklist, customer360).
4. Seed các golden case + synthetic case.

### Bước 4 — Dùng hệ thống

Mở http://localhost:3000, chọn một case trong **Case Queue**, vào màn **Overview** để xem tiến độ agent theo thời gian thực qua SSE, mở **Documents** để xem evidence drawer, **Expert Council** để xem phản biện, **Recommendation** để xem khuyến nghị + điều kiện kèm theo.

---

## 4. Cấu trúc thư mục

```
api/                 FastAPI — CaseState, REST, SSE, RBAC, event audit
web/                 Next.js — dashboard 8 màn + i18n EN/VI
worker/              LangGraph runtime — orchestrator, agents, chat
mcp-*/               Lớp MCP (deterministic / rag / external / state)
tools-mock/          API mock CIC/KYC/AML/valuation/LOS
shared/              Models, schemas, constants dùng chung giữa api & worker
scripts/             Migrate + seed (bootstrap_deploy.sh, seed_case_c0*.py, ...)
postgres/            Init role bootstrap (least-privilege)
infra/               Terraform (deploy VM tùy chọn)
deploy/              Caddyfile + deploy.sh (chạy trên VM)
docs/architecture/   overview.md · ai-architecture_v2.md · data-flow.md
```

---

## 5. Производство / Deploy lên VM

Có thể deploy lên một VM Linux bằng `deploy/deploy.sh` + `docker-compose.prod.yml` (Caddy làm proxy duy nhất). Xem hướng dẫn chi tiết trong comment đầu file `deploy/deploy.sh` và `docs/architecture/overview.md` mục 2.

---

## 6. Giấy phép / Phạm vi

Dự án demo/_cuộc thi. **Không** kết nối Core Banking/LOS/CIC/AML thật, không phê duyệt, không giải ngân, không dữ liệu khách hàng thật. Toàn bộ dữ liệu synthetic.