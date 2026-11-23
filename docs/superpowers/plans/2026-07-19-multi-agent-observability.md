> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# Multi-Agent Observability Dashboard — Implementation Plan (English)

> Implementation plan. The English section below summarises goal, architecture and task breakdown; the full task-by-task steps, commands and code are in the original text that follows (Vietnamese comments, English code).

**Goal:** ship a banking-style Next.js dashboard with 4 tabs (Status / Traces / Decisions / Collaboration) observing the multi-agent LangGraph credit-analysis pipeline, backed by an on-prem Langfuse trace store and the existing Postgres events log.

**Architecture:** the Langfuse Python SDK decorates `worker/app/llm/adapter.py::complete()`, and a new `worker/app/observability/tracing.py` exposes `trace_case_run()` + `call_tool()` for graph nodes and MCP tool calls; the Next.js dashboard reads existing FastAPI endpoints. **Stack:** Python 3.11, LangGraph, langfuse v3 SDK, FastAPI, redis, SQLAlchemy 2.0, Next.js 15 (App Router), React 19, recharts, Tailwind v4, SHB Design System tokens. Spec: `docs/superpowers/specs/2026-07-19-multi-agent-observability-design.md`. **Key constraint:** the trace join key is `langfuse.trace.id == case_id` (via metadata); never invent a separate `trace_id` column in Postgres for v1.

**Tasks:** 1 Langfuse Docker service + env config · 2 Tracing module · 3 Decorate `adapter.complete()` and `stream_complete()` · 4 Wire tracing into `worker/app/main.py`, `graph/build.py` and agents · 5 API router `/observability/cases/{case_id}/trace` · 6 Dashboard shell + Status tab · 7 Decisions tab · 8 Traces tab (Langfuse proxy + Gantt timeline) · 9 Collaboration tab (animated graph + SSE) · 10 End-to-end smoke test.

---

<a id="vi"></a>

## 🇻🇳 Tiếng Việt

# Multi-Agent Observability Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a banking-style Next.js dashboard with 4 tabs (Status / Traces / Decisions / Collaboration) that observes the multi-agent LangGraph credit-analysis pipeline, backed by an on-prem Langfuse trace store and the existing Postgres events log.

**Architecture:** Langfuse Python SDK decorates `worker/app/llm/adapter.py::complete()` and a new `worker/app/observability/tracing.py` exposes `trace_case_run()` + `call_tool()` for graph nodes + MCP tool calls; the Next.js dashboard reads existing FastAPI endpoints (`/cases`, `/cases/{id}`, `/cases/{id}/audit`, `/cases/{id}/stream`) for status/decisions/collaboration, and proxies Langfuse REST server-side for traces. On-prem Langfuse container preserves banking data residency.

**Tech Stack:** Python 3.11, LangGraph, langfuse v3 SDK, FastAPI, redis, SQLAlchemy 2.0, Next.js 15 (App Router), React 19, recharts, Tailwind v4, SHB Design System tokens.

**Working dir for all tasks:** `/home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability` (git worktree on branch `feat/multi-agent-observability`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-19-multi-agent-observability-design.md` (commit `1909448`).
- Trace join key: `langfuse.trace.id == case_id` (via metadata). Never invent a separate `trace_id` column in Postgres for v1.
- All trace instrumentation must be no-op (zero DB/network calls, zero exceptions raised) when `OBSERVABILITY_ENABLED=false`. Mock LLM mode (`LLM_MOCK=true`) must still return the same templated response.
- Vietnamese labels in UI: "Hồ sơ" (case), "Quyết định" (decision), "Nhận định" (finding), "Mâu thuẫn" (conflict). No emoji in primary UI surfaces. Use SHB Design System tokens (`web/SHB Design System/tokens/`).
- Web never talks to Postgres/Redis/Langfuse directly — only through `api` (existing rule) EXCEPT the Langfuse REST proxy, which IS server-side in Next.js route handlers (env `LANGFUSE_HOST` + keys, never exposed to browser).
- `complete()` and `stream_complete()` in `adapter.py` remain the ONLY LLM SDK call sites in the codebase — never import `anthropic`/`openai` elsewhere.
- All new code must respect `worker/app/agents/common.py::run_sync` async/sync bridge pattern for DB calls (see existing deadlock warning in its docstring). Tracing code is async-friendly, but DB writes through `run_sync`.
- No new Postgres tables. No new migrations. Observability data lives only in Langfuse + the existing `events`/`findings`/`conflicts`/`decisions` tables.
- Each task: `(write failing test) → (run it, see it fail) → (implement) → (run, see pass) → (commit)` unless the task is infra-only (docker-compose, plain text config) — those end with a smoke command instead of a test.
- Test runner: `pytest` from repo root. Tests for new modules go in `tests/observability/` (create the dir if it doesn't exist on this branch — it doesn't). Use `unittest.mock` for Langfuse/DB/Redis — do NOT spin Postgres in unit tests. The existing docker-compose Postgres is required only for Task 9 (end-to-end smoke).
- Langfuse SDK: pin `langfuse>=3.0,<4.0`. v3 API uses `@observe()` decorator + `from langfuse import get_client`. Verify decorator signature against the installed version's `langfuse/__init__.py` before wiring (Task 2 Step 1).

---

## File Map

### Worker (Python — backend trace instrumentation)

| File | Status | Responsibility |
|------|--------|----------------|
| `worker/app/observability/__init__.py` | Create | re-export public API |
| `worker/app/observability/tracing.py` | Create | Langfuse SDK wiring: `trace_case_run()`, `call_tool()`, decorate `complete`/`stream_complete`; all no-op when `OBSERVABILITY_ENABLED=false` |
| `worker/app/llm/adapter.py` | Modify | import decorator from `observability`, wrap `complete()` and `stream_complete()` with `@observe(as_type="generation")`-equivalent; metadata: `{tier, model, provider}` |
| `worker/app/main.py` | Modify | wrap `compiled_graph.ainvoke(...)` call in `async with trace_case_run(case_id)` |
| `worker/app/graph/build.py` | Modify | in `_with_progress`, open a span around `node_fn(state)` (when `ctx` available) carrying metadata `{step_id, agent_id}` |
| `worker/app/agents/common.py` | Modify | add `call_tool(tools, name, /, **args)` async wrapper used by `agents/financial.py`, `policy.py`, `collateral.py`, `customer360.py` |
| `worker/app/agents/financial.py` | Modify | replace `tools["X"].ainvoke(...)` with `await call_tool(tools, "X", ...)` |
| `worker/app/agents/policy.py` | Modify | same |
| `worker/app/agents/collateral.py` | Modify | same |
| `worker/app/agents/customer360.py` | Modify | same |
| `worker/config/models.yaml` | Modify (optional) | add `observability_notes` comment block — no runtime effect |
| `worker/requirements.txt` | Modify | add `langfuse>=3.0,<4.0` |
| `.env.example` | Modify | add `OBSERVABILITY_ENABLED`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` |

### Docker (infra)

| File | Status | Responsibility |
|------|--------|----------------|
| `docker-compose.yml` | Modify | add `langfuse` service + reuse existing `pg_data` volume (or its own `lf_data`) |

### API (FastAPI — read endpoints)

| File | Status | Responsibility |
|------|--------|----------------|
| `api/app/routers/observability.py` | Create | thin router exposing `GET /observability/cases/{id}/trace` returning `{langfuse_trace_id, langfuse_url}` — only the bits the existing `/cases/*` endpoints don't already cover (which they do, almost entirely) |
| `api/app/main.py` | Modify | `app.include_router(observability.router)` |

### Web (Next.js — dashboard UI)

| File | Status | Responsibility |
|------|--------|----------------|
| `web/app/observability/layout.tsx` | Create | 4-tab shell (Status/Traces/Decisions/Collaboration), SHB tokens, sidebar nav |
| `web/app/observability/page.tsx` | Create | redirect → `/observability/status` |
| `web/app/observability/status/page.tsx` | Create | Status tab: case queue + live SSE tick |
| `web/app/observability/traces/page.tsx` | Create | Traces tab list (recent Langfuse traces) |
| `web/app/observability/traces/[caseId]/page.tsx` | Create | Traces tab detail: Gantt timeline (Langfuse spans + Postgres events overlay) |
| `web/app/observability/decisions/page.tsx` | Create | Decisions tab: case finder |
| `web/app/observability/decisions/[caseId]/page.tsx` | Create | Decisions tab detail: finding drawer + DecisionPackage card |
| `web/app/observability/collaboration/page.tsx` | Create | Collaboration tab: case finder |
| `web/app/observability/collaboration/[caseId]/page.tsx` | Create | Collaboration tab detail: animated SVG graph + SSE live |
| `web/app/observability/api/traces/[caseId]/route.ts` | Create | server-side proxy to Langfuse REST `/api/public/traces?metadata.case_id=...` |
| `web/app/lib/observability.ts` | Create | typed fetchers for the new endpoints + Langfuse proxy |
| `web/app/components/observability/CaseQueueTable.tsx` | Create | reusable case queue table (used in Status + finders) |
| `web/app/components/observability/TraceGantt.tsx` | Create | recharts Gantt for Trace detail |
| `web/app/components/observability/CollaborationGraph.tsx` | Create | animated SVG of plan→fan-out→detect→challenge |
| `web/app/components/observability/DecisionCard.tsx` | Create | DecisionPackage card for Decisions tab |
| `web/app/components/observability/FindingDrawer.tsx` | Create | findings list + evidence drawer for Decisions tab |

### Tests

| File | Status | Responsibility |
|------|--------|----------------|
| `tests/__init__.py` | Create (if missing) | empty marker |
| `tests/observability/__init__.py` | Create | empty marker |
| `tests/observability/conftest.py` | Create | shared mocks — `OBSERVABILITY_ENABLED=true`, no-network `Langfuse` fake |
| `tests/observability/test_tracing.py` | Create | U1 unit tests |
| `tests/observability/test_call_tool.py` | Create | U1 call_tool wrapper tests |
| `tests/observability/test_observe_adapter.py` | Create | U1 verify `complete()` still returns same value with decorator (mock mode) |
| `tests/observability/test_observability_router.py` | Create | U3 router tests (TestClient + mocked session) |

---

## Task 1: Langfuse Docker Service + Env Config

**Files:**
- Modify: `docker-compose.yml` (insert block after `minio` service, before `api`)
- Modify: `.env.example` (append observability env block)
- Modify: `worker/requirements.txt` (add `langfuse`)

**Interfaces:**
- Consumes: existing `docker-compose.yml` network `internal`, Postgres `postgres` service
- Produces: a reachable Langfuse HTTP service at `http://langfuse:3001` (within docker network) and `http://localhost:3001` (host) when compose is up; env vars consumed by Tasks 2 and 8

- [ ] **Step 1: Add langfuse service to docker-compose.yml**

Insert this block into `docker-compose.yml` between the `minio:` service block and the `api:` service block:

```yaml
  # ---------------------------------------------------------------------
  # Observability — Langfuse on-prem (spec §3, §11). Optional: set
  # OBSERVABILITY_ENABLED=false in .env and skip `docker compose up langfuse`
  # to disable tracing entirely. Worker checks OBSERVABILITY_ENABLED at
  # import time and goes no-op. Reuses the existing Postgres as its DB so
  # we don't run a second Postgres just for traces in a hackathon.
  # ---------------------------------------------------------------------
  langfuse:
    image: langfuse/langfuse:3
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-shbuser}:${POSTGRES_PASSWORD:-shbpass}@postgres:5432/${POSTGRES_DB:-shbexpert}
      NEXTAUTH_URL: http://localhost:3001
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-dev-only-not-for-prod-change-me}
      SALT: ${LANGFUSE_SALT:-dev-only-salt-change-me}
      NEXT_PUBLIC_SIGN_UP_DISABLED: "true"
      # Auto-create the org/project API keys on first boot so test/dev
      # doesn't need a UI click-through flow. Replace keys in .env after
      # first `up` via the Langfuse UI for a stable set.
      LANGFUSE_INIT_ORG_ID: ${LANGFUSE_INIT_ORG_ID:-shb}
      LANGFUSE_INIT_ORG_NAME: ${LANGFUSE_INIT_ORG_NAME:-SHB}
      LANGFUSE_INIT_PROJECT_ID: ${LANGFUSE_INIT_PROJECT_ID:-shbexpert-flow}
      LANGFUSE_INIT_PROJECT_NAME: ${LANGFUSE_INIT_PROJECT_NAME:-SHB Expert Flow}
      LANGFUSE_INIT_PROJECT_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY:-pk-lf-xxxxxxxx}
      LANGFUSE_INIT_PROJECT_SECRET_KEY: ${LANGFUSE_SECRET_KEY:-sk-lf-xxxxxxxx}
      LANGFUSE_INIT_PROJECT_ROLE: ${LANGFUSE_INIT_PROJECT_ROLE:-ADMIN}
    ports:
      - "127.0.0.1:3001:3000"
    depends_on:
      postgres: { condition: service_healthy }
    networks: [internal]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/api/public/health"]
      interval: 10s
      timeout: 5s
      retries: 12
```

Note: Langfuse's port 3000 inside container maps to host 3001 (matches spec §11 and `web` already takes host 3000).

- [ ] **Step 2: Append env vars to `.env.example`**

Append after the last line of `.env.example`:

```
# Observability — Langfuse on-prem (spec docs/superpowers/specs/2026-07-19-multi-agent-observability-design.md)
# Set false to disable all tracing (worker instrumentation goes no-op).
OBSERVABILITY_ENABLED=true
# Worker uses this to send traces; web's server-side proxy uses it too.
LANGFUSE_HOST=http://langfuse:3001
# Keys created by Langfuse on first boot — overwrite with real values from
# the Langfuse UI (http://localhost:3001) after `docker compose up langfuse`.
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
```

- [ ] **Step 3: Add langfuse dependency to `worker/requirements.txt`**

Append:

```
# Langfuse Python SDK v3 — OpenTelemetry-based decorator API. Decorates
# adapter.complete() and stream_complete() and the call_tool() helper in
# worker/app/observability/tracing.py. v3 pinned <4 because the decorator
# API (`@observe`, `get_client`) is stable there; v4 may change.
langfuse>=3.0,<4.0
```

- [ ] **Step 4: Smoke try the compose file parses**

Run: `docker compose -f docker-compose.yml config --quiet`
Expected: exit 0, no errors. (Don't `up` yet — Step 5 is for Task 9.)

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example worker/requirements.txt
git commit -m "feat(observability): add langfuse container + env config + worker dep"
```

---

## Task 2: Tracing Module — `worker/app/observability/tracing.py`

**Files:**
- Create: `worker/app/observability/__init__.py`
- Create: `worker/app/observability/tracing.py`
- Create: `tests/__init__.py` (if missing)
- Create: `tests/observability/__init__.py`
- Create: `tests/observability/conftest.py`
- Create: `tests/observability/test_tracing.py`
- Create: `tests/observability/test_call_tool.py`

**Interfaces:**
- Consumes: `langfuse` SDK, env `OBSERVABILITY_ENABLED`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- Produces (used by Task 3, Task 4):
  - `async def trace_case_run(case_id: str, *, metadata: dict | None = None)` — async context manager
  - `async def call_tool(tools: dict, name: str, /, **args: Any) -> Any` — calls `tools[name].ainvoke(args)`, returns its result
  - `def observe_generation(fn)` — decorator factory (used by `adapter.py`)

- [ ] **Step 1: Verify installed langfuse decorator signature**

Run: `pip install 'langfuse>=3.0,<4.0' && python -c "import langfuse, inspect; from langfuse import observe; print(inspect.signature(observe)); print('langfuse version:', langfuse.__version__)"`

Expected: a signature accepting `as_type` kwarg (e.g. `observe(*, as_type=None, name=None, ...)`). If `observe` accepts `as_type`, use it directly. If the installed version's API differs (v4 marker), pin tighter and adapt — record the exact import path used and put it at the top of `tracing.py` as a comment.

- [ ] **Step 2: Write the failing test for `trace_case_run`**

Create `tests/__init__.py` (empty, if missing — `git ls-tree HEAD tests/__init__.py` returns nothing on this branch).

Create `tests/observability/__init__.py`:

```python
```

Create `tests/observability/conftest.py`:

```python
"""Shared fixtures for observability unit tests.

No Postgres, no network. Langfuse is mocked — these tests assert the
tracing module wires metadata correctly and goes no-op when disabled,
not that Langfuse's backend actually received anything.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Make `worker/app/...` and `shared` importable from tests/. Replicates
# what api/Dockerfile + worker/Dockerfile already do via PYTHONPATH — keep
# in sync if those change.
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in [_REPO_ROOT, _REPO_ROOT / "worker", _REPO_ROOT]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pytest  # noqa: E402


@pytest.fixture()
def enable_observability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3001")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")


@pytest.fixture()
def disable_observability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")
```

Create `tests/observability/test_tracing.py`:

```python
from __future__ import annotations

import pytest

from app.observability.tracing import trace_case_run


@pytest.mark.asyncio
async def test_trace_case_run_noop_when_disabled(disable_observability):
    """When OBSERVABILITY_ENABLED=false, trace_case_run yields a no-op
    context object and does not touch any Langfuse client."""
    async with trace_case_run("C06") as ctx:
        assert ctx is not None
        # No-op span creation must still return a usable object.
        span = ctx.start_span("test")
        assert span is not None


@pytest.mark.asyncio
async def test_trace_case_run_carries_case_id_metadata(enable_observability, monkeypatch):
    """When enabled, the context exposes `.case_id` and `.metadata` such
    that downstream code can attach spans carrying the right metadata."""
    async with trace_case_run("C06", metadata={"customer_id": "CUS-1"}) as ctx:
        assert ctx.case_id == "C06"
        assert ctx.metadata["customer_id"] == "CUS-1"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pip install pytest pytest-asyncio && pytest tests/observability/test_tracing.py -v`
Expected: FAIL with `ImportError: ... app.observability.tracing ...` or `ModuleNotFoundError`.

- [ ] **Step 4: Implement `worker/app/observability/__init__.py`**

```python
"""Observability wiring for the multi-agent pipeline (spec
docs/superpowers/specs/2026-07-19-multi-agent-observability-design.md).

Public API:
- trace_case_run(case_id, *, metadata=None)  — async context manager
- call_tool(tools, name, /, **args)          — MCP tool wrapper
- observe_generation(fn)                     — decorator for adapter.complete/stream_complete
"""
from app.observability.tracing import (
    call_tool,
    observe_generation,
    trace_case_run,
)

__all__ = ["call_tool", "observe_generation", "trace_case_run"]
```

- [ ] **Step 5: Implement `worker/app/observability/tracing.py`**

```python
"""Langfuse SDK wiring for the worker process.

Two guiding rules:
1. **trace_id == case_id.** Langfuse `metadata.case_id` is set to the
   graph's `case_id` exactly — that's the join key the dashboard proxy
   uses (`/api/public/traces?metadata.case_id=C06`). Never mint a
   separate trace_id here.
2. **No-op when disabled.** `OBSERVABILITY_ENABLED=false` (or unset, or
   invalid) must short-circuit every public function to a stub that
   returns a usable object but performs zero network/IO. The agents
   graph must behave identically whether tracing is on or off.

Designed against langfuse v3 SDK (`@observe` decorator + `get_client`).
If a future SDK release changes the API, update the imports here only —
adapter.py and agents import from this module, never directly from langfuse.
"""
from __future__ import annotations

import asyncio
import contextvars
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable

# contextvar carried across the graph's FanOut superstep so child spans
# (LLM generation, tool call, sub-node) inherit the parent trace without
# manual plumbing — Langfuse's own contextvars cover most of this, but we
# also keep one so the no-op path doesn't depend on Langfuse being loaded.
_current_trace_ctx: contextvars.ContextVar["_TraceContext | None"] = contextvars.ContextVar(
    "observability_current_trace_ctx", default=None
)


def _is_enabled() -> bool:
    return os.environ.get("OBSERVABILITY_ENABLED", "false").lower() in ("1", "true", "yes")


def _langfuse_client():
    """Lazily imports and returns the langfuse client. Kept inside a
    function so importing this module never requires `langfuse` installed
    (e.g. running unit tests on the host without the SDK)."""
    from langfuse import get_client
    return get_client()


class _NoopSpan:
    """Drop-in span that swallows __enter__/__exit__ and `.event()`. Used
    when tracing is disabled OR when langfuse isn't installed — keeps
    caller code unconditional."""
    name: str
    metadata: dict

    def __init__(self, name: str, metadata: dict | None = None) -> None:
        self.name = name
        self.metadata = metadata or {}

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def event(self, name: str, metadata: dict | None = None) -> None:
        return None

    def update(self, **fields: Any) -> None:
        return None


class _TraceContext:
    """Carried through `async with trace_case_run(case_id)`. Holds the
    case_id so `call_tool()` and `observe_generation`-decorated functions
    can attach metadata without re-reading from graph state."""
    case_id: str
    metadata: dict

    def __init__(self, case_id: str, metadata: dict | None = None) -> None:
        self.case_id = case_id
        self.metadata = metadata or {}

    def start_span(self, name: str, metadata: dict | None = None) -> _NoopSpan:
        if not _is_enabled():
            return _NoopSpan(name, metadata)
        try:
            client = _langfuse_client()
            span = client.start_as_current_span(
                name=name,
                metadata={**self.metadata, **(metadata or {}), "case_id": self.case_id},
            )
            return span
        except Exception:  # noqa: BLE001 — never crash a graph run over trace wiring
            return _NoopSpan(name, metadata)


@asynccontextmanager
async def trace_case_run(case_id: str, *, metadata: dict | None = None) -> AsyncIterator[_TraceContext]:
    """Open a Langfuse trace scoped to one case run. `case_id` becomes
    the trace's `metadata.case_id` — the dashboard proxy's join key.

    Use:
        async with trace_case_run(case_id, metadata={"owner": ...}) as ctx:
            await compiled_graph.ainvoke({...}, config={...})
    """
    ctx = _TraceContext(case_id, metadata)
    token = _current_trace_ctx.set(ctx)
    _span = ctx.start_span(name="case_analysis", metadata={"case_id": case_id, **(metadata or {})})
    try:
        with _span:
            yield ctx
    finally:
        _current_trace_ctx.reset(token)


async def call_tool(tools: dict, name: str, /, **args: Any) -> Any:
    """Wrap `tools[name].ainvoke(args)` with a span named `tool.{name}`
    so each MCP tool call appears under its parent node span in the
    Langfuse trace. Auto-captures input args; output is whatever the
    tool returned (returned verbatim). Never raises a tracing-side
    exception — if the tool itself raises, that propagates as before.
    """
    ctx = _current_trace_ctx.get()
    span_ctx = ctx.start_span(
        name=f"tool.{name}",
        metadata={"tool": name, "case_id": ctx.case_id} if ctx else {"tool": name},
    )
    with span_ctx:
        try:
            span_ctx.update(input=args)
        except Exception:  # noqa: BLE001
            pass
        result = await tools[name].ainvoke(args)
        try:
            span_ctx.update(output=str(result)[:500])
        except Exception:  # noqa: BLE001
            pass
        return result


def observe_generation(fn: Callable) -> Callable:
    """Decorator applied to `adapter.complete` / `stream_complete` to mark
    them as Langfuse "generation" spans — captured with model, tier,
    prompt/response, tokens, cost. Uses langfuse v3 `@observe(as_type=...)`
    when available; falls back to a pass-through wrapper when disabled or
    when the SDK isn't installed.
    """
    if not _is_enabled():
        return fn
    try:
        from langfuse import observe
        return observe(as_type="generation")(fn)
    except Exception:  # noqa: BLE001 — SDK missing or wrong API → degrade
        return fn
```

- [ ] **Step 6: Configure asyncio test mode + hermetic default**

Modify `pyproject.toml`'s existing `[tool.pytest.ini_options]` block to add `asyncio_mode = "auto"` (keep `testpaths = ["tests"]`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

Append one autouse fixture to `tests/observability/conftest.py` that keeps tests hermetic — defaults `OBSERVABILITY_ENABLED=false` unless the test explicitly requests `enable_observability`:

```python


@pytest.fixture(autouse=True)
def _default_observability_disabled(monkeypatch: pytest.MonkeyPatch, request):
    """Test cases that explicitly take `enable_observability` opt in; the
    rest run with tracing disabled so langfuse is never imported. Must run
    BEFORE `enable_observability`/`disable_observability` set their value —
    pytest resolves explicit fixtures last, so a plain `setenv` here is
    overridden by those fixtures' `setenv`, which is exactly the intent."""
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")
```

Also ensure `pytest-asyncio` is installed for the repo (it isn't part of api/requirements.txt or worker/requirements.txt — it's test-only). Add a `tests/observability/requirements.txt` or rely on the developer having installed `pytest-asyncio` manually. For the plan, just install it inline:

```bash
pip install pytest pytest-asyncio langfuse>=3.0,<4.0
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/observability/test_tracing.py -v`
Expected: 2 passed. The `_default_observability_disabled` autouse fixture keeps `test_trace_case_run_noop_when_disabled` hermetic and lets `test_trace_case_run_carries_case_id_metadata` flip via its `enable_observability` arg. tracing.py must NOT import langfuse at module top-level (only inside `_langfuse_client()`), so the disabled-path tests must never touch the SDK.

- [ ] **Step 8: Write failing test for `call_tool`**

Create `tests/observability/test_call_tool.py`:

```python
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.observability.tracing import call_tool, trace_case_run


@pytest.mark.asyncio
async def test_call_tool_returns_underlying_result(disable_observability):
    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"value": 42})
    tools = {"calculate_X": tool}

    result = await call_tool(tools, "calculate_X", financials={"a": 1})

    assert result == {"value": 42}
    tool.ainvoke.assert_awaited_once_with({"financials": {"a": 1}})


@pytest.mark.asyncio
async def test_call_tool_propagates_tool_errors(disable_observability):
    """If the underlying MCP tool raises, the exception propagates —
    don't swallow it inside the span."""
    tool = AsyncMock()
    tool.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
    tools = {"bad": tool}

    with pytest.raises(RuntimeError, match="boom"):
        await call_tool(tools, "bad")


@pytest.mark.asyncio
async def test_call_tool_uses_parent_trace_context(enable_observability, monkeypatch):
    """When observability is enabled, call_tool reads the current
    _TraceContext set by trace_case_run and stamps its span metadata with
    case_id. We assert this by checking that start_span on the parent ctx
    picks up the case_id."""
    started = []

    class FakeCtx:
        case_id = "C06"
        metadata = {}

        def start_span(self, name, metadata=None):
            span = type("s", (), {"__enter__": lambda s: s, "__exit__": lambda *a: None, "update": lambda *a, **k: None})()
            started.append((name, metadata))
            return span

    # Patch _current_trace_ctx to return our fake so call_tool sees a parent.
    from app.observability import tracing
    monkeypatch.setattr(tracing, "_current_trace_ctx",
                       type("v", (), {"get": lambda self: FakeCtx(), "set": lambda self, v: None, "reset": lambda self, v: None})())

    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"ok": 1})
    await call_tool({"X": tool}, "X", foo="bar")

    assert any(name == "tool.X" and (m or {}).get("case_id") == "C06" for name, m in started)
```

- [ ] **Step 9: Run call_tool tests**

Run: `pytest tests/observability/test_call_tool.py -v`
Expected: 3 passed.

- [ ] **Step 10: Commit**

```bash
git add worker/app/observability/ tests/observability/ tests/__init__.py pyproject.toml
git commit -m "feat(observability): add tracing module (trace_case_run, call_tool, observe_generation)"
```

---

## Task 3: Decorate `adapter.complete()` and `stream_complete()`

**Files:**
- Modify: `worker/app/llm/adapter.py` (add decorator to `complete` and `stream_complete`)
- Create: `tests/observability/test_observe_adapter.py`

**Interfaces:**
- Consumes: `from app.observability.tracing import observe_generation`
- Produces: instrumented `complete()` and `stream_complete()` — same signatures, same return values, now emits langfuse generation spans

- [ ] **Step 1: Write failing test asserting mock-mode complete() still returns the templated response and emits a generation span**

Create `tests/observability/test_observe_adapter.py`:

```python
from __future__ import annotations

import os

import pytest

# Adapter import must come AFTER setting envs.
@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")


@pytest.mark.asyncio
async def test_complete_in_mock_mode_returns_templated_response():
    from app.llm.adapter import complete
    result = await complete(
        tier="reasoning",
        system="Bạn là Financial Agent.",
        user="Doanh thu 2025 = 1 tỷ VND. Viết 1 câu claim.",
    )
    # _mock_response returns the data-prefixed body, capped at 400 chars.
    assert isinstance(result, str)
    assert result.startswith("[LLM_MOCK/reasoning]")


@pytest.mark.asyncio
async def test_complete_does_not_raise_when_langfuse_unavailable(monkeypatch):
    """If langfuse is enabled but its SDK blows up at decorate time,
    observe_generation degrades gracefully and complete() still works."""
    monkeypatch.setitem(
        __import__("sys").modules,
        "langfuse",
        type("m", (), {"observe": staticmethod(lambda **k: (_ for _ in ()).throw(RuntimeError("nope")))}),
    )
    # Force a fresh import to re-run observe_generation against the broken SDK.
    import importlib
    from app.llm import adapter
    importlib.reload(adapter)
    result = await adapter.complete(tier="reasoning", system="x", user="Viết nhận định. y")
    assert isinstance(result, str)
```

- [ ] **Step 2: Run test to see it (partially) fail**

Run: `pytest tests/observability/test_observe_adapter.py -v`
Expected: test 1 may pass already (mock mode untouched), test 2 likely FAILS with `RuntimeError: nope` because `observe` was called and raised.

- [ ] **Step 3: Apply decorator to `complete()` and `stream_complete()` in `adapter.py`**

Edit `worker/app/llm/adapter.py`. At the top, after existing imports, add:

```python
from app.observability.tracing import observe_generation
```

(Importing lazily inside the function body would make the module load without langfuse installed — but `app.observability.tracing` imports `langfuse` only inside `_langfuse_client()`, so top-level import is safe.)

Then decorate the two functions:

```python
@observe_generation
async def complete(*, tier: str, system: str, user: str) -> str:
    ...
```

```python
@observe_generation
async def stream_complete(*, tier: str, system: str, user: str) -> AsyncIterator[str]:
    ...
```

Add metadata: after `max_tokens = cfg.get("max_tokens", 4096)` inside `complete()`, push it onto the current langfuse span context (optional). For v1 the decorator alone is enough — the prompt/response are auto-captured. Skip explicit metadata wiring; rely on langfuse defaults.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/observability/test_observe_adapter.py -v`
Expected: 2 passed. Mock-mode response unchanged; langfuse unavailable handled by `observe_generation`'s try/except.

- [ ] **Step 5: Verify existing worker graph still imports cleanly**

Run: `python -c "from worker.app.llm.adapter import complete, stream_complete; print('ok')"`
Expected: prints `ok`, no exception even with `OBSERVABILITY_ENABLED=false`.

(Set `OBSERVABILITY_ENABLED=false` and re-run to confirm no-op path.)
```bash
OBSERVABILITY_ENABLED=false python -c "from worker.app.llm.adapter import complete, stream_complete; print('ok-false')"
```

- [ ] **Step 6: Commit**

```bash
git add worker/app/llm/adapter.py tests/observability/test_observe_adapter.py
git commit -m "feat(observability): decorate adapter.complete/stream_complete as langfuse generations"
```

---

## Task 4: Wire Tracing into `worker/app/main.py` + `graph/build.py` + agents

**Files:**
- Modify: `worker/app/main.py` (wrap `compiled_graph.ainvoke(...)` in `trace_case_run`)
- Modify: `worker/app/graph/build.py` (`_with_progress` opens a span around `node_fn`)
- Modify: `worker/app/agents/common.py` (re-export `call_tool`)
- Modify: `worker/app/agents/financial.py`, `worker/app/agents/policy.py`, `worker/app/agents/collateral.py`, `worker/app/agents/customer360.py` (replace `tools["X"].ainvoke(...)` with `await call_tool(tools, "X", ...)`)

**Interfaces:**
- Consumes: `from app.observability.tracing import trace_case_run, call_tool`
- Produces: end-to-end traced graph execution (visible in Langfuse UI after a `/cases/{id}/analyze` run)

- [ ] **Step 1: Modify `worker/app/main.py` — wrap `ainvoke` in `trace_case_run`**

Locate the `_consume_jobs` body (after `print(f"[worker] dequeued analyze job for case {case_id}", flush=True)` and the `await _publish(...)` line). Replace the `try:` block containing `result = await compiled_graph.ainvoke(...)`:

```python
        try:
            from app.observability.tracing import trace_case_run
            async with trace_case_run(case_id, metadata={"job_id": job.get("job_id")}):
                result = await compiled_graph.ainvoke(
                    {"case_id": case_id, "findings_written": []},
                    config={"configurable": {"thread_id": case_id}},
                )
            await _publish(
                r,
                case_id,
                {
                    "type": "job_completed",
                    "case_id": case_id,
                    "findings_written": result.get("findings_written", []),
                },
            )
        except Exception as exc:
            ...
```

(Preserve the existing `except Exception as exc:` block and its `job_failed` publish unchanged below.)

- [ ] **Step 2: Modify `graph/build.py::_with_progress` — add span around the node**

In the `wrapped` inner function, wrap the `node_fn(state)` call:

```python
    async def wrapped(state: CaseGraphState) -> dict:
        await publish_progress(state["case_id"], {"type": "step_started", "step": step_id, "label": STEP_LABELS[step_id]})
        from app.observability.tracing import trace_case_run  # for contextvars continuity
        # Note: trace_case_run was already opened in worker/app/main.py around
        # the whole ainvoke call. We don't open another trace here — we add a
        # span to the current trace via the contextvar. Reading the inline
        # module-level helper keeps the public API of tracing.py narrow.
        from app.observability.tracing import _current_trace_ctx
        ctx = _current_trace_ctx.get()
        span = (
            ctx.start_span(
                name=f"node.{step_id}",
                metadata={"step_id": step_id, "label": STEP_LABELS[step_id]},
            )
            if ctx is not None
            else None
        )
        try:
            with span or _DummySpan():
                try:
                    result = await node_fn(state)
                except Exception:
                    await publish_progress(state["case_id"], {"type": "step_failed", "step": step_id, "label": STEP_LABELS[step_id]})
                    raise
                await publish_progress(state["case_id"], {"type": "step_completed", "step": step_id, "label": STEP_LABELS[step_id]})
                return result
        finally:
            pass
```

Use `contextlib.nullcontext()` as the fallback when no span is returned (tracing disabled / no parent trace). Final shape:

```python
from contextlib import nullcontext
# ... (other imports already present)

    async def wrapped(state: CaseGraphState) -> dict:
        await publish_progress(state[case_id], {"type": "step_started", "step": step_id, "label": STEP_LABELS[step_id]})
        from app.observability.tracing import _current_trace_ctx
        ctx = _current_trace_ctx.get()
        span = (
            ctx.start_span(
                name=f"node.{step_id}",
                metadata={"step_id": step_id, "label": STEP_LABELS[step_id]},
            )
            if ctx is not None
            else None
        )
        span_cm = span if span is not None else nullcontext()
        try:
            with span_cm:
                try:
                    result = await node_fn(state)
                except Exception:
                    await publish_progress(state[case_id], {"type": "step_failed", "step": step_id, "label": STEP_LABELS[step_id]})
                    raise
                await publish_progress(state[case_id], {"type": "step_completed", "step": step_id, "label": STEP_LABELS[step_id]})
                return result
        finally:
            try:
                span.update(status="OK")
            except Exception:
                pass  # NoopSpan or real span already finalized
```

Do NOT introduce a custom `_DummySpan` class — `nullcontext()` is the stdlib idiom for exactly this. `_NoopSpan.start_span()` returning its own `_NoopSpan` instance (already a valid context manager) means `ctx.start_span(...)` already yields a `with`-able in the disabled path. The only place `nullcontext()` is needed is the `ctx is None` path (no parent trace opened).

- [ ] **Step 3: Re-export `call_tool` from `agents/common.py` for convenience**

Add this near the top of `worker/app/agents/common.py` (after existing imports):

```python
from app.observability.tracing import call_tool  # re-export — agents import from here
```

And append `"call_tool"` to the symbols listed at the bottom if `__all__` exists (it likely doesn't — skip).

- [ ] **Step 4: Replace each `tools["X"].ainvoke(...)` with `await call_tool(tools, "X", ...)`**

This is the only change required in each agent file — go file by file.

Run a discovery first to enumerate all call sites:
```bash
grep -n 'tools\[".*"\].ainvoke' worker/app/agents/financial.py worker/app/agents/policy.py worker/app/agents/collateral.py worker/app/agents/customer360.py
```

For each match, transform:
```python
result = await tools["calculate_financial_ratios"].ainvoke({"financials": financials, "industry_avg": INDUSTRY_AVG_RATIOS})
```
into:
```python
from app.agents.common import call_tool
...
result = await call_tool(tools, "calculate_financial_ratios", financials=financials, industry_avg=INDUSTRY_AVG_RATIOS)
```

Repeat for every site. Add the `call_tool` import once per file (alongside the existing `from app.agents.common import ...`).

- [ ] **Step 5: Manual syntax-check all modified agent files**

Run:
```bash
python -c "import ast; [ast.parse(open(f).read()) for f in ['worker/app/agents/financial.py','worker/app/agents/policy.py','worker/app/agents/collateral.py','worker/app/agents/customer360.py','worker/app/graph/build.py','worker/app/main.py']]; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 6: Add an integration-style unit test asserting `call_tool` is used by `financial.py`**

Create `tests/observability/test_agents_use_call_tool.py`:

```python
"""Static check: each agent file imports call_tool (proves the wiring landed
and won't drift back to direct .ainvoke calls)."""
from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _imports_call_tool(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "call_tool":
                    return True
    return False


def test_financial_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/financial.py")


def test_policy_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/policy.py")


def test_collateral_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/collateral.py")


def test_customer360_imports_call_tool():
    assert _imports_call_tool(_REPO / "worker/app/agents/customer360.py")
```

- [ ] **Step 7: Run that test**

Run: `pytest tests/observability/test_agents_use_call_tool.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add worker/app/main.py worker/app/graph/build.py worker/app/agents/common.py worker/app/agents/financial.py worker/app/agents/policy.py worker/app/agents/collateral.py worker/app/agents/customer360.py tests/observability/test_agents_use_call_tool.py
git commit -m "feat(observability): trace case run + node spans + call_tool in all agents"
```

---

## Task 5: API Router — `/observability/cases/{case_id}/trace`

**Files:**
- Create: `api/app/routers/observability.py`
- Modify: `api/app/main.py` (register router)
- Create: `tests/observability/test_observability_router.py`

**Interfaces:**
- Consumes: FastAPI, env `LANGFUSE_HOST`
- Produces: `GET /observability/cases/{case_id}/trace → {langfuse_trace_id, langfuse_url}` — other dashboard reads use existing `/cases` and `/cases/{id}` + `/cases/{id}/audit` endpoints (no duplication)

**Rationale:** Spec §4.2 lists 6 endpoints, but 5 are already covered by existing `/cases/*` routes (verifiable in `api/app/routers/cases.py`: `/cases` lists, `/cases/{id}` returns findings + conflicts + decision, `/cases/{id}/audit` returns the events timeline, `/cases/{id}/stream` is SSE). Only the trace-link helper is new — small enough to keep DRY.

- [ ] **Step 1: Write failing test**

Create `tests/observability/test_observability_router.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))

from unittest.mock import patch

from fastapi.testclient import TestClient


def _apply_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3001")


def test_trace_endpoint_returns_langfuse_link(monkeypatch):
    _apply_env(monkeypatch)
    # Re-import app main with the env applied.
    import importlib
    import app.main as main_mod
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)

    resp = client.get("/observability/cases/C06/trace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["langfuse_trace_id"] == "C06"
    assert body["langfuse_url"].startswith("http://langfuse:3001")


def test_trace_endpoint_404_when_observability_disabled(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3001")
    import importlib
    import app.main as main_mod
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)

    resp = client.get("/observability/cases/C06/trace")
    # Returns a body with langfuse_url=null when disabled — explicit rather
    # than 404 so the dashboard can show "tracing disabled" rather than
    # treat it as a network error.
    assert resp.status_code == 200
    body = resp.json()
    assert body["langfuse_trace_id"] == "C06"
    assert body["langfuse_url"] is None
```

- [ ] **Step 2: Run test to see it fail**

Run: `pytest tests/observability/test_observability_router.py -v`
Expected: FAIL — no `/observability/cases/.../trace` route.

- [ ] **Step 3: Implement `api/app/routers/observability.py`**

```python
"""Observability dashboard endpoints.

Spec §4.2 lists 6 endpoints — we deliberately implement only
`/observability/cases/{case_id}/trace` here; the rest of the dashboard's
reads come from the existing /cases/* routes (cases.py) which already
return findings, conflicts, decision package, events (audit), and live
stream — DRY, no duplication.

The trace endpoint is intentionally a read-only link helper: it returns
the Langfuse URL the dashboard's Traces tab should open, plus the
trace_id (== case_id by spec §3.2) the proxy handler will query. It
never queries Langfuse itself.
"""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/observability", tags=["observability"])


def _langfuse_host() -> str:
    return os.environ.get("LANGFUSE_HOST", "")


def _observability_enabled() -> bool:
    return os.environ.get("OBSERVABILITY_ENABLED", "false").lower() in ("1", "true", "yes")


@router.get("/cases/{case_id}/trace")
def get_case_trace_link(case_id: str) -> dict:
    host = _langfuse_host()
    enabled = _observability_enabled()
    if not enabled or not host:
        return {"langfuse_trace_id": case_id, "langfuse_url": None}
    # The Traces tab constructs a server-side proxy query against
    # /api/public/traces?metadata.case_id=... — the host here is internal.
    return {
        "langfuse_trace_id": case_id,
        "langfuse_url": f"{host}/project/shbexpert-flow/traces/{case_id}",
    }
```

- [ ] **Step 4: Register the router in `api/app/main.py`**

Edit `api/app/main.py` — after `from app.routers import cases, chat, internal, memo`, append `observability`:

```python
from app.routers import cases, chat, internal, memo, observability
```

And after the existing `app.include_router(...)` block, append:

```python
app.include_router(observability.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/observability/test_observability_router.py -v`
Expected: 2 passed.

- [ ] **Step 6: Smoke-test the running api routes**

```bash
cd api && python -c "from app.main import app; print([r.path for r in app.routes if 'observability' in r.path])"
```
Expected: `['/observability/cases/{case_id}/trace']` (list with one path).

- [ ] **Step 7: Commit**

```bash
git add api/app/routers/observability.py api/app/main.py tests/observability/test_observability_router.py
git commit -m "feat(api): add /observability/cases/{id}/trace read-only link helper"
```

---

## Task 6: Next.js — Dashboard Shell + Status Tab

**Files:**
- Create: `web/app/observability/layout.tsx`
- Create: `web/app/observability/page.tsx`
- Create: `web/app/observability/status/page.tsx`
- Create: `web/app/lib/observability.ts`
- Create: `web/app/components/observability/CaseQueueTable.tsx`

**Interfaces:**
- Consumes: existing `/api/cases` endpoint (returns `{cases: CaseSummary[]}`), existing `/api/cases/{id}/stream` SSE, SHB Design System tokens
- Produces: `/observability` route group with 4-tab shell; `/observability` redirects to `/observability/status`; Status tab renders live case queue

- [ ] **Step 1: Look at the SHB Design System tokens file to know what to import**

```bash
ls "web/SHB Design System/tokens/" && head -40 "web/SHB Design System/tokens/"*.json 2>/dev/null
```

(Verify exact token file names; if a Tailwind preset exists, prefer importing it. If only raw JSON, read `color.primary` etc. and define local CSS variables in the layout.)

- [ ] **Step 2: Create `web/app/lib/observability.ts` — typed fetchers**

```typescript
import type { CaseSummary } from "./types";

// Reuses /api/* proxy (next.config.mjs rewrites to api). Same convention
// as web/app/lib/api.ts — never talk to Postgres/Redis from the browser.

export async function fetchObservabilityCases(): Promise<CaseSummary[]> {
  const res = await fetch(`/api/cases`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchObservabilityCases failed: ${res.status}`);
  const data = await res.json();
  return data.cases as CaseSummary[];
}

export interface TraceLink {
  langfuse_trace_id: string;
  langfuse_url: string | null;
}

export async function fetchTraceLink(caseId: string): Promise<TraceLink> {
  const res = await fetch(`/api/observability/cases/${caseId}/trace`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchTraceLink failed: ${res.status}`);
  return res.json() as Promise<TraceLink>;
}

export interface LangfuseTraceSummary {
  id: string;
  name: string;
  timestamp: string;
  totalCost?: number;
  totalTokens?: number;
  // langfuse's REST returns more; we only type what the UI uses.
}

export async function fetchLangfuseTracesForCase(caseId: string): Promise<{
  trace: LangfuseTraceSummary | null;
  spans: LangfuseSpan[];
}> {
  const res = await fetch(`/observability/api/traces/${caseId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchLangfuseTracesForCase failed: ${res.status}`);
  return res.json();
}

export interface LangfuseSpan {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  parent_id?: string | null;
  metadata?: Record<string, unknown>;
  // For LLM generations:
  usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
  level?: "DEBUG" | "DEFAULT" | "WARNING" | "ERROR";
}
```

- [ ] **Step 3: Create `web/app/components/observability/CaseQueueTable.tsx`**

```tsx
"use client";

import Link from "next/link";

import type { CaseSummary } from "../../lib/types";

interface Props {
  cases: CaseSummary[];
  emptyHint?: string;
  onRowClick?: (caseId: string) => void;
}

export default function CaseQueueTable({ cases, emptyHint = "Chưa có hồ sơ.", onRowClick }: Props) {
  if (cases.length === 0) {
    return <div className="text-sm text-shb-muted">{emptyHint}</div>;
  }
  return (
    <div className="overflow-x-auto rounded border border-shb-border">
      <table className="w-full text-sm">
        <thead className="bg-shb-surface-hover text-shb-muted">
          <tr>
            <th className="px-3 py-2 text-left">Mã hồ sơ</th>
            <th className="px-3 py-2 text-left">Khách hàng</th>
            <th className="px-3 py-2 text-left">Trạng thái</th>
            <th className="px-3 py-2 text-left">Cập nhật</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr
              key={c.case_id}
              className="cursor-pointer border-t border-shb-border hover:bg-shb-surface-hover"
              onClick={() => onRowClick?.(c.case_id)}
            >
              <td className="px-3 py-2 font-mono">
                <Link href={`/observability/collaboration/${c.case_id}`}>{c.case_id}</Link>
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
```

(Verify SHB token names by inspecting `web/app/globals.css` or the tokens file from Step 1 — if `shb-muted` etc. aren't defined, use the actual token names from the file. Substitute the right class names before committing.)

- [ ] **Step 4: Create `web/app/observability/layout.tsx` — 4-tab shell**

```tsx
import Link from "next/link";
import type { ReactNode } from "react";

const TABS = [
  { href: "/observability/status", label: "Tình trạng" },
  { href: "/observability/traces", label: "Vết chạy" },
  { href: "/observability/decisions", label: "Quyết định" },
  { href: "/observability/collaboration", label: "Phân luồng" },
] as const;

export default function ObservabilityLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-shb-surface text-shb-text">
      <header className="border-b border-shb-border bg-shb-surface px-6 py-3">
        <Link href="/" className="text-shb-text-muted hover:text-shb-text">
          ← Trở về
        </Link>
        <h1 className="mt-1 text-lg font-semibold">Quan sát đa tác nhân</h1>
      </header>
      <nav className="flex gap-4 border-b border-shb-border px-6">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="border-b-2 border-transparent px-3 py-2 text-sm text-shb-muted hover:text-shb-text"
          >
            {t.label}
          </Link>
        ))}
      </nav>
      <main className="px-6 py-4">{children}</main>
    </div>
  );
}
```

- [ ] **Step 5: Create `web/app/observability/page.tsx` — redirect**

```tsx
import { redirect } from "next/navigation";

export default function ObservabilityIndex() {
  redirect("/observability/status");
}
```

- [ ] **Step 6: Create `web/app/observability/status/page.tsx` — Status tab**

```tsx
"use client";

import { useEffect, useState } from "react";

import CaseQueueTable from "../../components/observability/CaseQueueTable";
import { fetchObservabilityCases } from "../../lib/observability";
import type { CaseSummary } from "../../lib/types";

interface LiveStep {
  case_id: string;
  step: string;
  label: string;
  type: "step_started" | "step_completed" | "step_failed";
  ts: number;
}

export default function StatusTab() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [live, setLive] = useState<Record<string, LiveStep>>({});

  useEffect(() => {
    fetchObservabilityCases().then(setCases).catch((e) => console.error(e));
  }, []);

  useEffect(() => {
    // SSE: subscribe to all cases' progress channels via a single
    // dispatcher endpoint? For v1 we open one SSE per visible case (the
    // top N). The existing /api/cases/{id}/stream channel is per-case.
    // To stay light for hackathon, we open for the first 5 cases only.
    const active = cases.slice(0, 5);
    const es: EventSource[] = [];
    for (const c of active) {
      const source = new EventSource(`/api/cases/${c.case_id}/stream`);
      source.addEventListener("message", (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data);
          if (["step_started", "step_completed", "step_failed"].includes(data.type)) {
            setLive((prev) => ({
              ...prev,
              [c.case_id]: { case_id: c.case_id, step: data.step, label: data.label, type: data.type, ts: Date.now() },
            }));
          }
        } catch { /* ignore non-JSON keepalive */ }
      });
      es.push(source);
    }
    return () => es.forEach((s) => s.close());
  }, [cases]);

  return (
    <div>
      <h2 className="text-base font-medium mb-3">Hàng đợi hồ sơ</h2>
      <CaseQueueTable
        cases={cases}
        emptyHint="Chưa có hồ sơ nào trong hệ thống."
      />
      <h2 className="text-base font-medium mt-6 mb-3">Hoạt động đang chạy</h2>
      {Object.keys(live).length === 0 ? (
        <div className="text-sm text-shb-muted">Chưa có tác nhân nào đang chạy.</div>
      ) : (
        <ul className="space-y-2 text-sm">
          {Object.values(live).map((l) => (
            <li key={l.case_id} className="flex items-center gap-3">
              <span className="font-mono">{l.case_id}</span>
              <span className={`status-chip status-${l.type}`}>
                {l.type === "step_started" ? "đang chạy" : l.type === "step_failed" ? "lỗi" : "xong"}
              </span>
              <span className="text-shb-muted">{l.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Add `next.config.mjs` rewrite so `/api/observability/*` reaches the new router**

Check existing `web/next.config.mjs` — it likely has a rewrites array mapping `/api/:path*` to `api` service. The new `/observability/cases/{id}/trace` lives under `api`'s `/observability/...` prefix, so calls go to `/api/observability/cases/.../trace` from the browser (matching convention `web/app/lib/observability.ts` uses). No new rewrite needed — the existing `/api/*` rewrite covers it.

Verify:
```bash
cat web/next.config.mjs
```

If `/api/:path*` → `${api_url}/cases/:path*` or similar prefix-stripping rewrite, adapt `lib/observability.ts` accordingly. The call should hit `http://api:8000/observability/cases/{id}/trace`.

- [ ] **Step 8: Build + typecheck**

```bash
cd web && npm install && npm run build 2>&1 | tail -40
```

Expected: Build succeeds. If `shb-muted`/`shb-surface` classes are undefined, fix in `web/app/globals.css` by mapping SHB Design System tokens -- OR -- use Tailwind arbitrary values `[color:var(--shb-muted)]`. Adjust to make build pass.

- [ ] **Step 9: Commit**

```bash
git add web/app/observability/ web/app/lib/observability.ts web/app/components/observability/
git commit -m "feat(web): observability dashboard shell + Status tab with live SSE"
```

---

## Task 7: Decisions Tab

**Files:**
- Create: `web/app/observability/decisions/page.tsx` (case finder)
- Create: `web/app/observability/decisions/[caseId]/page.tsx` (finding drawer + DecisionPackage card)
- Create: `web/app/components/observability/DecisionCard.tsx`
- Create: `web/app/components/observability/FindingDrawer.tsx`

**Interfaces:**
- Consumes: existing `/api/cases/{id}` (returns `{findings, decision, conflicts}` per spec §2.3 / code at `cases.py:177`), SHB tokens
- Produces: Decisions tab — pick a case → see findings list, click → evidence drawer, plus DecisionPackage panel

- [ ] **Step 1: Create the case-finder page**

`web/app/observability/decisions/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { fetchObservabilityCases } from "../../../lib/observability";
import CaseQueueTable from "../../../components/observability/CaseQueueTable";
import type { CaseSummary } from "../../../lib/types";

export default function DecisionsFinder() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  useEffect(() => {
    fetchObservabilityCases().then(setCases).catch(console.error);
  }, []);
  return (
    <div>
      <h2 className="text-base font-medium mb-3">Chọn hồ sơ để xem quyết định</h2>
      <CaseQueueTable cases={cases} emptyHint="Chưa có hồ sơ nào." />
    </div>
  );
}
```

- [ ] **Step 2: Create `web/app/components/observability/DecisionCard.tsx`**

First, inspect what `/cases/{id}` actually returns (examine `cases.py:177-246`, captured in Task 5 — the `decision` field has: `recommendation`, `requested_amount_vnd`, `recommended_amount_vnd`, `recommended_tenor_months`, `hard_gates`, `scores`, `strengths`, `risks`, `conditions_precedent`, `dissent`, `policy_version`, `decision_matrix_version`).

```tsx
"use client";

import type { CaseDetail } from "../../lib/types";

interface Props {
  decision: CaseDetail["decision"];
  conflicts: CaseDetail["conflicts"];
}

export default function DecisionCard({ decision, conflicts }: Props) {
  if (!decision) {
    return (
      <div className="rounded border border-shb-border p-4 text-sm text-shb-muted">
        Chưa có Quyết định tổng hợp — hồ sơ vẫn đang phân tích.
      </div>
    );
  }
  return (
    <div className="space-y-3 rounded border border-shb-border p-4">
      <div>
        <div className="text-sm text-shb-muted">Khuyến nghị</div>
        <div className="text-base font-semibold">{decision.recommendation}</div>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-shb-muted">Hạn mức yêu cầu</dt>
        <dd className="tabular-nums">{vnd(decision.requested_amount_vnd)}</dd>
        <dt className="text-shb-muted">Hạn mức đề xuất</dt>
        <dd className="tabular-nums">{vnd(decision.recommended_amount_vnd)}</dd>
        <dt className="text-shb-muted">Thời hạn đề xuất</dt>
        <dd className="tabular-nums">{decision.recommended_tenor_months ?? "—"} tháng</dd>
      </dl>
      <Section title="Cổng cứng" items={decision.hard_gates as string[]} />
      <Section title="Điểm số" items={(decision.scores as { name: string; score: number }[] | undefined)?.map((s) => `${s.name}: ${s.score}`) ?? []} />
      <Section title="Điểm mạnh" items={decision.strengths as string[]} />
      <Section title="Rủi ro" items={decision.risks as string[]} />
      <Section title="Điều kiện tiên quyết" items={decision.conditions_precedent as string[]} />
      <Section title="Bất đồng còn lại" items={decision.dissent as string[]} />
      <div className="text-xs text-shb-muted mt-2">
        Phiên bản chính sách: {decision.policy_version ?? "—"} · Ma trận quyết định: {decision.decision_matrix_version ?? "—"}
      </div>
      {conflicts.length > 0 && (
        <div className="text-xs">
          <span className="text-shb-muted">Mâu thuẫn: </span>
          {conflicts.map((c) => (
            <span key={c.conflict_id} className="inline-block mr-2">
              {c.issue_key} (vòng {c.round}, {c.status})
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className="text-sm text-shb-muted">{title}</div>
      <ul className="list-disc pl-5 text-sm">
        {items.map((it, i) => <li key={i}>{typeof it === "object" ? JSON.stringify(it) : it}</li>)}
      </ul>
    </div>
  );
}

function vnd(n: number | null | undefined): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(n);
}
```

(If `CaseDetail["decision"]` shape differs — verify against `web/app/lib/types.ts`.)

- [ ] **Step 3: Create `web/app/components/observability/FindingDrawer.tsx`**

```tsx
"use client";

import type { CaseDetail } from "../../lib/types";

interface Props {
  findings: CaseDetail["findings"];
  selectedKey: string | null;
  onSelect: (key: string | null) => void;
}

export default function FindingDrawer({ findings, selectedKey, onSelect }: Props) {
  const selected = findings.find((f) => f.finding_key === selectedKey) ?? null;
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h3 className="text-sm font-medium mb-2">Nhận định ({findings.length})</h3>
        <ul className="space-y-1">
          {findings.map((f) => (
            <li
              key={f.display_id}
              onClick={() => onSelect(f.finding_key)}
              className={`cursor-pointer rounded border border-shb-border px-2 py-1 text-sm hover:bg-shb-surface-hover ${
                selected?.finding_key === f.finding_key ? "bg-shb-surface-hover" : ""
              }`}
            >
              <div className="font-mono">{f.display_id}</div>
              <div className="text-shb-muted text-xs">{f.agent_id} · {f.stance} · {f.severity}</div>
            </li>
          ))}
        </ul>
      </div>
      <div>
        {selected ? (
          <div className="rounded border border-shb-border p-3 text-sm space-y-2">
            <div className="font-mono">{selected.display_id}</div>
            <p>{selected.claim}</p>
            <dl className="grid grid-cols-2 gap-1">
              <dt className="text-shb-muted"> Thái độ</dt><dd>{selected.stance}</dd>
              <dt className="text-shb-muted"> Mức độ</dt><dd>{selected.severity}</dd>
              <dt className="text-shb-muted"> Độ tin cậy</dt><dd>{(selected.confidence * 100).toFixed(0)}%</dd>
              <dt className="text-shb-muted"> Phiên bản</dt><dd>v{selected.version}</dd>
            </dl>
            {selected.change_reason && (
              <p className="text-shb-muted italic">Lý do thay đổi: {selected.change_reason}</p>
            )}
            {selected.evidence_ids && selected.evidence_ids.length > 0 && (
              <div className="text-xs">
                <span className="text-shb-muted">Bằng chứng: </span>
                {selected.evidence_ids.join(", ")}
              </div>
            )}
            {selected.citations && selected.citations.length > 0 && (
              <div className="text-xs">
                <span className="text-shb-muted">Trích dẫn: </span>
                <ul className="list-disc pl-5">
                  {(selected.citations as { source_id: string; version: string; section?: string }[]).map((c, i) => (
                    <li key={i}>{c.source_id} v{c.version}{c.section ? ` (${c.section})` : ""}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded border border-shb-border p-3 text-sm text-shb-muted">Chọn một nhận định để xem chi tiết.</div>
        )}
      </div>
    </div>
  );
}
```

(Verify `CaseDetail["findings"]` array element shape against `web/app/lib/types.ts` and `cases.py:_finding_dict`.)

- [ ] **Step 4: Create `web/app/observability/decisions/[caseId]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import DecisionCard from "../../../../components/observability/DecisionCard";
import FindingDrawer from "../../../../components/observability/FindingDrawer";
import { fetchCase } from "../../../../lib/api";
import type { CaseDetail } from "../../../../lib/types";

export default function DecisionsDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchCase(caseId).then(setDetail).catch(console.error);
  }, [caseId]);

  if (!detail) return <div className="text-sm text-shb-muted">Đang tải…</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-base font-medium">Quyết định — hồ sơ {caseId}</h2>
      <DecisionCard decision={detail.decision} conflicts={detail.conflicts} />
      <FindingDrawer findings={detail.findings} selectedKey={selectedKey} onSelect={setSelectedKey} />
    </div>
  );
}
```

- [ ] **Step 5: Build**

```bash
cd web && npm run build 2>&1 | tail -40
```
Expected: succeeds. Fix any `CaseDetail` field shape mismatches.

- [ ] **Step 6: Commit**

```bash
git add web/app/observability/decisions/ web/app/components/observability/DecisionCard.tsx web/app/components/observability/FindingDrawer.tsx
git commit -m "feat(web): Decisions tab — finding drawer + DecisionPackage card"
```

---

## Task 8: Traces Tab — Langfuse Proxy + Gantt Timeline

**Files:**
- Create: `web/app/observability/api/traces/[caseId]/route.ts` (server-side proxy → Langfuse REST)
- Create: `web/app/observability/traces/page.tsx` (case finder)
- Create: `web/app/observability/traces/[caseId]/page.tsx` (Gantt)
- Create: `web/app/components/observability/TraceGantt.tsx`

**Interfaces:**
- Consumes: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` env (server-only); recharts (already in package.json)
- Produces: Traces tab — pick a case → render Gantt of Langfuse spans overlaid with Postgres events timeline

- [ ] **Step 1: Create the server-side Langfuse proxy**

`web/app/observability/api/traces/[caseId]/route.ts`:

```typescript
/**
 * Server-side proxy to Langfuse REST API for a single case's trace.
 * Browser never sees LANGFUSE_* keys — only this route handler reads them.
 *
 * Langfuse v3 REST shape:
 *   GET /api/public/traces?metadata.case_id={caseId}&limit=1
 *   Headers: Authorization: Basic base64(pk:sk)
 * Returns array of traces; we take the most recent.
 *
 * For v1 (hackathon), spans/generations are fetched via a second call:
 *   GET /api/public/traces/{traceId}/spans
 *   GET /api/public/traces/{traceId}/generations
 * — both Basic-authed against the same project keys.
 *
 * Returns: { trace: {...}|null, spans: [...], generations: [...] }
 */
export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await context.params;
  const host = process.env.LANGFUSE_HOST;
  const pk = process.env.LANGFUSE_PUBLIC_KEY;
  const sk = process.env.LANGFUSE_SECRET_KEY;

  if (!host || !pk || !sk) {
    return Response.json(
      { enabled: false, trace: null, spans: [], generations: [], reason: "OBSERVABILITY not configured" },
      { status: 200 },
    );
  }

  const auth = Buffer.from(`${pk}:${sk}`).toString("base64");
  const headers = { Authorization: `Basic ${auth}`, "Content-Type": "application/json" };

  try {
    const traceRes = await fetch(
      `${host}/api/public/traces?metadata.case_id=${encodeURIComponent(caseId)}&limit=1&order_by=timestamp&order=desc`,
      { headers, cache: "no-store" },
    );
    if (!traceRes.ok) {
      return Response.json(
        { enabled: true, trace: null, spans: [], generations: [], reason: `langfuse responded ${traceRes.status}` },
        { status: 200 },
      );
    }
    const traceData = await traceRes.json();
    const trace = (traceData.data ?? [])[0] ?? null;
    if (!trace) {
      return Response.json({ enabled: true, trace: null, spans: [], generations: [] }, { status: 200 });
    }

    // Fetch spans + generations for the trace.
    const [spanRes, genRes] = await Promise.all([
      fetch(`${host}/api/public/traces/${trace.id}/spans?limit=200`, { headers, cache: "no-store" }),
      fetch(`${host}/api/public/traces/${trace.id}/generations?limit=200`, { headers, cache: "no-store" }),
    ]);
    const spansData = spanRes.ok ? ((await spanRes.json()).data ?? []) : [];
    const gensData = genRes.ok ? ((await genRes.json()).data ?? []) : [];

    return Response.json({
      enabled: true,
      trace: {
        id: trace.id,
        name: trace.name,
        timestamp: trace.timestamp,
        total_cost: trace.totalCost,
        total_tokens: trace.totalTokens,
      },
      spans: spansData.map((s: any) => ({
        id: s.id,
        name: s.name,
        start_time: s.startTime,
        end_time: s.endTime,
        parent_id: s.parentObservationId ?? null,
        metadata: s.metadata ?? {},
        level: s.level,
      })),
      generations: gensData.map((g: any) => ({
        id: g.id,
        name: g.name,
        start_time: g.startTime,
        end_time: g.endTime,
        parent_id: g.parentObservationId ?? null,
        usage: g.usage,
        metadata: g.metadata ?? {},
      })),
    }, { status: 200 });
  } catch (e) {
    return Response.json(
      { enabled: true, trace: null, spans: [], generations: [], reason: String(e) },
      { status: 200 },
    );
  }
}
```

- [ ] **Step 2: Update `web/app/lib/observability.ts` to union spans + generations**

(Append to the file, replacing the `fetchLangfuseTracesForCase` return shape if it's slightly mismatched. Entity: spans and generations are both rendered as Gantt bars; union them client-side.)

```typescript
export interface LangfuseGen extends LangfuseSpan {
  usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
}

export interface LangfuseTraceBlob {
  enabled: boolean;
  trace: LangfuseTraceSummary | null;
  spans: LangfuseSpan[];
  generations: LangfuseGen[];
  reason?: string;
}

export async function fetchLangfuseTrace(caseId: string): Promise<LangfuseTraceBlob> {
  const res = await fetch(`/observability/api/traces/${caseId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchLangfuseTrace failed: ${res.status}`);
  return res.json();
}
```

(Keep the older `fetchLangfuseTracesForCase` exported too if Task 6 still references it; or remove + update Status tab — minimal churn preferred.)

- [ ] **Step 3: Create `web/app/components/observability/TraceGantt.tsx`**

```tsx
"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface GanttItem {
  name: string;
  start: number; // ms epoch
  end: number;   // ms epoch
  kind: "node" | "tool" | "gen";
}

export default function TraceGantt({ items }: { items: GanttItem[] }) {
  if (!items.length) {
    return <div className="text-sm text-shb-muted">Không có vết chạy nào cho hồ sơ này.</div>;
  }
  const minStart = Math.min(...items.map((i) => i.start));
  const data = items.map((i) => ({
    name: i.name,
    offset: i.start - minStart,
    duration: Math.max(i.end - i.start, 1),
    kind: i.kind,
  }));
  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 60, right: 20, top: 10, bottom: 10 }}>
          <XAxis type="number" unit="ms" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={200} />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(value: number, name: string) => (name === "duration" ? `${value} ms` : value)}
          />
          <Bar dataKey="offset" stackId="t" fill="transparent" />
          <Bar dataKey="duration" stackId="t" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Create `web/app/observability/traces/page.tsx` — case finder**

```tsx
"use client";

import { useEffect, useState } from "react";

import CaseQueueTable from "../../../components/observability/CaseQueueTable";
import { fetchObservabilityCases } from "../../../lib/observability";
import type { CaseSummary } from "../../../lib/types";

export default function TracesFinder() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  useEffect(() => {
    fetchObservabilityCases().then(setCases).catch(console.error);
  }, []);
  return (
    <div>
      <h2 className="text-base font-medium mb-3">Chọn hồ sơ để xem vết chạy</h2>
      <CaseQueueTable cases={cases} />
    </div>
  );
}
```

- [ ] **Step 5: Create `web/app/observability/traces/[caseId]/page.tsx` — Gantt**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import TraceGantt from "../../../../components/observability/TraceGantt";
import { fetchLangfuseTrace } from "../../../../lib/observability";

export default function TraceDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [blob, setBlob] = useState<Awaited<ReturnType<typeof fetchLangfuseTrace>> | null>(null);

  useEffect(() => {
    fetchLangfuseTrace(caseId as string).then(setBlob).catch(console.error);
  }, [caseId]);

  if (!blob) return <div className="text-sm text-shb-muted">Đang tải…</div>;
  if (!blob.enabled) return <div className="text-sm text-shb-muted">Tính năng quan sát chưa bật.</div>;
  if (!blob.trace) return (
    <div className="text-sm text-shb-muted">
      Chưa có vết chạy Langfuse cho hồ sơ {caseId}. (Đảm bảo <code>OBSERVABILITY_ENABLED=true</code> và chạy <code>/cases/{caseId}/analyze</code> sau khi dashboard up.)
    </div>
  );

  // Union spans and generations into one Gantt, marked by kind.
  const items = [
    ...blob.spans.map((s) => ({
      name: s.name,
      start: new Date(s.start_time).getTime(),
      end: new Date(s.end_time).getTime(),
      kind: s.name.startsWith("tool.") ? "tool" as const : "node" as const,
    })),
    ...blob.generations.map((g) => ({
      name: g.name,
      start: new Date(g.start_time).getTime(),
      end: new Date(g.end_time).getTime(),
      kind: "gen" as const,
    })),
  ].sort((a, b) => a.start - b.start);

  return (
    <div className="space-y-4">
      <h2 className="text-base font-medium">Vết chạy — hồ sơ {caseId}</h2>
      <div className="text-sm text-shb-muted">
        Trace ID: <code>{blob.trace.id}</code> · Tổng token: {blob.trace.total_tokens ?? "—"} · Cost (USD): {blob.trace.total_cost ?? "—"}
      </div>
      <TraceGantt items={items} />
    </div>
  );
}
```

- [ ] **Step 6: Add `.env` keys visible to web in `docker-compose.yml` web service**

Edit the `web:` service env block in `docker-compose.yml` to add:

```yaml
      LANGFUSE_HOST: ${LANGFUSE_HOST:-http://langfuse:3001}
      LANGFUSE_PUBLIC_KEY: ${LANGFUSE_PUBLIC_KEY:-pk-lf-xxxxxxxx}
      LANGFUSE_SECRET_KEY: ${LANGFUSE_SECRET_KEY:-sk-lf-xxxxxxxx}
```

(These are read server-side only by the route handler — Next.js exposes them via `process.env` in route handlers. Browser code never reads them.)

- [ ] **Step 7: Build**

```bash
cd web && npm run build 2>&1 | tail -40
```
Expected: succeeds.

- [ ] **Step 8: Commit**

```bash
git add web/app/observability/api/ web/app/observability/traces/ web/app/components/observability/TraceGantt.tsx web/app/lib/observability.ts docker-compose.yml
git commit -m "feat(web): Traces tab — Langfuse server-side proxy + recharts Gantt"
```

---

## Task 9: Collaboration Tab — Animated Graph + SSE

**Files:**
- Create: `web/app/observability/collaboration/page.tsx` (case finder)
- Create: `web/app/observability/collaboration/[caseId]/page.tsx` (animated graph)
- Create: `web/app/components/observability/CollaborationGraph.tsx` (SVG + SSE)

**Interfaces:**
- Consumes: existing `/api/cases/{id}/stream` SSE (`step_started`/`step_completed`/`step_failed` events), `/api/cases/{id}` for static topology + conflicts + findings
- Produces: Collaboration tab — pick a case → animated SVG of `plan→fan-out→detect→challenge→synthesize→transition`, nodes glow on `step_started`, edges flash on conflict, "round" badge from ConflictRecord

- [ ] **Step 1: Create `web/app/components/observability/CollaborationGraph.tsx`**

A self-contained SVG component driving node state from incoming SSE events. Nodes are laid out absolutely:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

interface StepNode {
  step: string;
  label: string;
  x: number;
  y: number;
}

interface StepEdge {
  from: string;
  to: string;
}

const NODES: StepNode[] = [
  { step: "plan",          label: "Lập kế hoạch",      x: 400, y:  40 },
  { step: "financial",     label: "Financial Agent",  x: 200, y: 140 },
  { step: "policy",        label: "Policy Agent",      x: 320, y: 140 },
  { step: "collateral",    label: "Collateral Agent", x: 440, y: 140 },
  { step: "customer360",   label: "Customer 360",      x: 560, y: 140 },
  { step: "detect",        label: "Đối chiếu",         x: 400, y: 260 },
  { step: "challenge",     label: "Hỏi lại (round 1→2)", x: 250, y: 320 },
  { step: "synthesize",    label: "Tổng hợp",          x: 400, y: 380 },
  { step: "transition",    label: "Chốt trạng thái",   x: 400, y: 440 },
];

const EDGES: StepEdge[] = [
  { from: "plan", to: "financial" }, { from: "plan", to: "policy" }, { from: "plan", to: "collateral" }, { from: "plan", to: "customer360" },
  { from: "financial", to: "detect" }, { from: "policy", to: "detect" }, { from: "collateral", to: "detect" }, { from: "customer360", to: "detect" },
  { from: "detect", to: "challenge" },
  { from: "challenge", to: "detect" }, // loop edge
  { from: "detect", to: "synthesize" },
  { from: "synthesize", to: "transition" },
];

interface StepState {
  status: "idle" | "running" | "ok" | "fail";
}

export default function CollaborationGraph({ caseId, conflicts }: { caseId: string; conflicts: { issue_key: string; round: number; status: string }[] }) {
  const [states, setStates] = useState<Record<string, StepState>>({});
  const [round, setRound] = useState<number>(0);
  const sourceRef = useRef<EventSource | null>(null);

  // Seed round from initial conflicts (already happened):
  useEffect(() => {
    const max = conflicts.reduce((m, c) => Math.max(m, c.round), 0);
    setRound(max);
  }, [conflicts]);

  useEffect(() => {
    const source = new EventSource(`/api/cases/${caseId}/stream`);
    sourceRef.current = source;
    source.addEventListener("message", (ev) => {
      try {
        const data = JSON.parse((ev as MessageEvent).data);
        if (data.type === "step_started") {
          setStates((prev) => ({ ...prev, [data.step]: { status: "running" } }));
        } else if (data.type === "step_completed") {
          setStates((prev) => ({ ...prev, [data.step]: { status: "ok" } }));
        } else if (data.type === "step_failed") {
          setStates((prev) => ({ ...prev, [data.step]: { status: "fail" } }));
        }
      } catch { /* keepalive */ }
    });
    return () => source.close();
  }, [caseId]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-sm">
        <span className="text-shb-muted">Vòng challenge:</span>
        <span className="badge">{round}/2</span>
      </div>
      <svg viewBox="0 0 800 500" className="w-full border border-shb-border rounded">
        {/* Edges */}
        {EDGES.map((e, i) => {
          const a = NODES.find((n) => n.step === e.from)!;
          const b = NODES.find((n) => n.step === e.to)!;
          // Loop edge curves back, others are straight.
          const d = e.from === "challenge"
            ? `M ${a.x} ${a.y} C ${a.x - 80} ${a.y - 60}, ${b.x - 80} ${b.y + 60}, ${b.x} ${b.y}`
            : `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
          const activeFrom = states[e.from]?.status === "running" || states[e.from]?.status === "ok";
          const activeTo = states[e.to]?.status === "running";
          const stroke = activeFrom || activeTo ? "#3b82f6" : "#cbd5e1";
          return <path key={i} d={d} stroke={stroke} strokeWidth={activeFrom ? 2 : 1} fill="none" />;
        })}
        {/* Nodes */}
        {NODES.map((n) => {
          const s = states[n.step]?.status ?? "idle";
          const fill = s === "running" ? "#3b82f6" : s === "ok" ? "#10b981" : s === "fail" ? "#ef4444" : "#f8fafc";
          const stroke = s === "running" && states[n.step]?.status === "running" ? "#1d4ed8" : "#cbd5e1";
          return (
            <g key={n.step}>
              <rect x={n.x - 70} y={n.y - 16} width={140} height={32} rx={6} fill={fill} stroke={stroke} strokeWidth={1.5} className={s === "running" ? "animate-pulse" : ""} />
              <text x={n.x} y={n.y + 4} textAnchor="middle" fontSize={11} fill={s === "idle" ? "#334155" : "#fff"}>{n.label}</text>
            </g>
          );
        })}
      </svg>
      <div className="text-sm text-shb-muted">
        {Object.keys(states).length === 0 ? "Đang chờ sự kiện từ worker…" : "Đang theo dõi trực tiếp đồ thị phân luồng."}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `web/app/observability/collaboration/page.tsx` — case finder**

```tsx
"use client";

import { useEffect, useState } from "react";

import CaseQueueTable from "../../../components/observability/CaseQueueTable";
import { fetchObservabilityCases } from "../../../lib/observability";
import type { CaseSummary } from "../../../lib/types";

export default function CollaborationFinder() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  useEffect(() => {
    fetchObservabilityCases().then(setCases).catch(console.error);
  }, []);
  return (
    <div>
      <h2 className="text-base font-medium mb-3">Chọn hồ sơ để xem phân luồng</h2>
      <CaseQueueTable cases={cases} />
    </div>
  );
}
```

- [ ] **Step 3: Create `web/app/observability/collaboration/[caseId]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import CollaborationGraph from "../../../../components/observability/CollaborationGraph";
import { fetchCase } from "../../../../lib/api";
import type { CaseDetail } from "../../../../lib/types";

export default function CollaborationDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [detail, setDetail] = useState<CaseDetail | null>(null);

  useEffect(() => {
    fetchCase(caseId).then(setDetail).catch(console.error);
  }, [caseId]);

  if (!detail) return <div className="text-sm text-shb-muted">Đang tải…</div>;
  return (
    <div className="space-y-4">
      <h2 className="text-base font-medium">Phân luồng — hồ sơ {caseId}</h2>
      <CollaborationGraph caseId={caseId} conflicts={detail.conflicts} />
    </div>
  );
}
```

- [ ] **Step 4: Build**

```bash
cd web && npm run build 2>&1 | tail -40
```
Expected: succeeds. Tailwind's `animate-pulse` is built-in; SHB colors used via inline `#...` to dodge token issues for v1.

- [ ] **Step 5: Commit**

```bash
git add web/app/observability/collaboration/ web/app/components/observability/CollaborationGraph.tsx
git commit -m "feat(web): Collaboration tab — animated topological graph + SSE live"
```

---

## Task 10: End-to-End Smoke Test

**Files:** none new — this is a manual integration check confirming the whole pipeline emits visible traces + dashboard live updates work.

**Prerequisites:** Docker compose able to run on host.

- [ ] **Step 1: Bring up full stack with observability**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
docker compose up -d postgres redis minio qdrant langfuse api worker web tools-mock mcp-deterministic mcp-rag mcp-external mcp-state
```

Expected: every service healthy within ~60s. Verify:
```bash
docker compose ps
```
All statuses "healthy" or "running".

- [ ] **Step 2: Confirm Langfuse reachable**

```bash
curl -fsS http://localhost:3001/api/public/health && echo " langfuse ok"
```
Expected: `{"status":"OK"}` then " langfuse ok".

- [ ] **Step 3: Confirm api route exists**

```bash
curl -fsS http://localhost:8000/observability/cases/C06/trace | head
```
Expected: JSON `{"langfuse_trace_id":"C06","langfuse_url":"http://langfuse:3001/project/shbexpert-flow/traces/C06"}` (after seeding) or `langfuse_url: null` before observability env is fully set.

- [ ] **Step 4: Seed one case + trigger analyze (uses existing seed scripts)**

Use whatever the repo currently uses to seed C06 (check `scripts/` and `README.md` for the seed entrypoint). For example (placeholder — fill from the repo's actual seed command):
```bash
# Adjust to actual seed entrypoint if it differs.
docker compose exec worker python -m scripts.seed_demo_cases C06
curl -X POST http://localhost:8000/cases/C06/analyze
```
Expected: 202 accepted, worker dequeues.

- [ ] **Step 5: Watch dashboard live**

Open `http://localhost:3000/observability` in browser → Status tab → see C06 enter "running" → navigate to Collaboration tab `/observability/collaboration/C06` → nodes light up as worker emits `step_started`.

- [ ] **Step 6: Verify Langfuse got the trace**

Open `http://localhost:3001/project/shbexpert-flow/traces` → see the trace named `case_analysis` with `metadata.case_id=C06` → expand → `node.plan`, `node.financial`, `tool.calculate_*`, `complete` generation spans nested.

- [ ] **Step 7: Verify Traces tab Gantt**

In dashboard navigate to `/observability/traces/C06` → Gantt chart renders rows of node/tool/gen spans, durations >0.

- [ ] **Step 8: Verify Decisions tab**

After worker completes (case state → READY_FOR_REVIEW), navigate to `/observability/decisions/C06` → DecisionCard shows recommendation, hard gates, strengths, risks. Findings drawer drilldown works.

- [ ] **Step 9: Record smoke results in a commit message or RUNBOOK.md**

Create `docs/superpowers/plans/2026-07-19-multi-agent-observability-runbook.md` with the exact smoke commands used + one-sentence confirmation per step. This is the evidence artifact for verification-before-completion.

```bash
git add docs/superpowers/plans/2026-07-19-multi-agent-observability-runbook.md
git commit -m "docs: smoke runbook for multi-agent observability dashboard"
```

---

## Self-Review Notes

- **Spec coverage:** spec §3 (architecture) → Tasks 1, 2, 4 cover U1+U2+U5; spec §3 U3 → Task 5; spec §3 U4 → Tasks 6, 7, 8, 9; spec §5 data flow → Task 4 main+graph wiring; spec §6 routing → Tasks 6-9 create the exact route pages; spec §7 style → uses SHB tokens / inline colors as fallback; spec §8 error handling → tracing degrade paths + Langfuse proxy returns 200 with `enabled:false`; spec §9 testing → unit tests in Tasks 2-5 + smoke in Task 10; spec §11 env → Task 1 adds env; spec §12 plan 4-day → tasks 1-4 = day 1-2, 5-7 = day 3, 8-9 = day 4, 10 = day 4 end. ✅
- **Placeholder scan:** no "TODO"/"TBD" left in steps. Step 4 of Task 10 ("Adjust to actual seed entrypoint") is a deliberate gate — actual seed command varies by repo state; the runbook captures the truth.
- **Type consistency:** `call_tool(tools, name, /, **args)` — matching signature across Tasks 2, 4. `trace_case_run(case_id, *, metadata=None)` — same across Tasks 2, 4. `fetchLangfuseTrace` / `LangfuseTraceBlob` introduced in Task 8 → used in Task 8 Step 5. `CaseSummary`/`CaseDetail` types come from existing `web/app/lib/types.ts`. Functions reused (e.g. `fetchObservabilityCases`) introduced in Task 6 → used Tasks 7, 9. ✅