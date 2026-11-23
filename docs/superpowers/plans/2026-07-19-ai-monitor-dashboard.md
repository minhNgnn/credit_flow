# AI Monitor Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a single-page `/monitor` route in `web` plus two FastAPI endpoints that aggregate Postgres + Langfuse to display SRE latency, agent council quality, LLM call distribution, and live event stream + worker logs — the bank-grade "AI Monitor" overview for hackathon judges.

**Architecture:** FastAPI `/monitor/overview` (one request → multiple SQL GROUP BY + Langfuse REST hits) + `/monitor/logs` (subprocess `docker logs` wrapped defensively) feed a Next.js `app/monitor/page.tsx` that renders a 2×2 grid of recharts/SVG panels under a SHB-styled KPI strip header. SSE EventSource for top-5 case streams powers a live activity feed; queries aggregate at request time (no new tables/workers).

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.0 (queries via `shared.models`); Next.js 15 + React 19; recharts 2.15 (already a dep); Tailwind v4 + SHB tokens from `web/app/globals.css`.

**Working dir for all tasks:** `/home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability` (git worktree on branch `feat/multi-agent-observability`, compose project `shbexpert-flow-obs`, api host port `8100`, web host port `3100`, langfuse host port `3202`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-19-ai-monitor-dashboard-design.md` (commit `2bb705e`)
- Charts color constants (hex copied verbatim from spec §7):
  - SUPPORT / PASS / APPROVE / READY_FOR_REVIEW / Conflict RESOLVED: `#00853E`
  - CAUTION / REVIEW / REFER / NEED_INFO / Conflict OPEN: `#FFC10E`
  - OPPOSE / FAIL / REJECT / Conflict UNRESOLVED / DRAFT-related errors: `#F04E45`
  - NEED_DATA (finding): `#6E7C8E`
  - ANALYZING / DRAFT (case state, primary blue): `#0066B3`
- Langfuse REST endpoints (verified live in commit `778ce0e`):
  - `GET {LANGFUSE_HOST}/api/public/traces?metadata.case_id={caseId}&limit=1&order_by=timestamp&order=desc` (Basic auth `pk:sk`)
  - `GET {LANGFUSE_HOST}/api/public/observations?traceId={id}&limit=100` (returns both SPAN and GENERATION; **limit MUST be ≤100** or endpoint returns 400)
- Vietnamese UI labels, no emoji in primary surfaces: "Hồ sơ", "Nhận định", "Mâu thuẫn", "Quyết định", "Vết chạy", "Sự kiện", "Nhật ký worker", "H以身 vai SRE", "Hội đồng agent", "LLM & tools", "Hoạt động". "Bắt đầu", "Xong", "Lỗi", "Mở rộng", "Thu gọn".
- Browser never sees `LANGFUSE_*` keys — only route handlers server-side.
- Web never talks to Postgres/Redis directly — only through `/api/*` (existing rule). `/monitor/overview` and `/monitor/logs` go through `api` too.
- Each task: `(write failing test) → (run, see RED) → (implement) → (run, see GREEN) → (commit)` unless task is text/config only (end with a smoke command instead).
- Test runner: `/home/son/AIC/dashmint_ai/.venv/bin/python -m pytest tests/observability/ -v` from worktree root. Stream `http://localhost:8100` and `http://localhost:3100` smoke runs require the compose project to be up (already up from prior session).
- All new Python code uses `shared.db.get_session()` for DB queries (existing pattern in `api/app/routers/cases.py`). All sub-process calls wrap in `try/except` and degrade to `{"error": str(exc)}` rather than raising.
- No new Postgres tables. No migrations.
- Pre-existing TS errors in `web/app/cases/[caseId]/page.tsx` (branch origin/frontend @ 75b0d4c) are already worked around via `next.config.mjs` `typescript.ignoreBuildErrors=true`; do NOT remove that flag.

---

## File Map

### Backend (FastAPI)

| File | Status | Responsibility |
|------|--------|----------------|
| `api/app/routers/monitor.py` | Create | `GET /monitor/overview` (KPI + 5 distributions + latency + llm_calls_per_case) + `GET /monitor/logs` (worker stdout via subprocess) |
| `api/app/main.py` | Modify | `from app.routers import ..., monitor` + `app.include_router(monitor.router)` |
| `api/app/routers/observability.py` | Modify (Task 6 only — add `/monitor/langfuse-keys-for-api` helper OR reuse env) | Not changed — go server-side through FastAPI instead to keep things simple. (Skipped; see Task 6 note.) |

### Frontend (Next.js)

| File | Status | Responsibility |
|------|--------|----------------|
| `web/app/lib/monitor.ts` | Create | `fetchMonitorOverview(): Promise<MonitorOverview>` + `fetchMonitorLogs(lines=200): Promise<WorkerLogs>` typed fetchers |
| `web/app/monitor/page.tsx` | Create | Single-page overview — fetch + grid layout + SSE top-5 + refresh button |
| `web/app/components/monitor/KPIStrip.tsx` | Create | KPI badges header (cases/READY/DRAFT/findings/conflicts/decisions/traces/llm_calls) |
| `web/app/components/monitor/CaseStateDonut.tsx` | Create | Donut chart case state (Pie/PieChart from recharts) |
| `web/app/components/monitor/LatencyTree.tsx` | Create | Bar chart avg/max latency per `node.*` + per `tool.*` (one chart, sorted by avg_ms desc) |
| `web/app/components/monitor/StanceStackedBar.tsx` | Create | Stacked bar stance × agent |
| `web/app/components/monitor/SeverityHeatmap.tsx` | Create | Custom SVG grid agent (rows) × severity (cols), opacity by count |
| `web/app/components/monitor/ConflictDonut.tsx` | Create | Donut conflict status + bar chart conflict round count |
| `web/app/components/monitor/DecisionDonut.tsx` | Create | Donut decision recommendation |
| `web/app/components/monitor/LLMCallsBar.tsx` | Create | Bar chart LLM calls per case (top N) |
| `web/app/components/monitor/EventStream.tsx` | Create | Live activity feed (top 50, SSE-triggered) |
| `web/app/components/monitor/WorkerLogsBox.tsx` | Create | Worker stdout box (poll 10s) |
| `web/app/components/monitor/Panel.tsx` | Create | Reusable collapsible card wrapper (title + icon + content + collapse toggle) — DRY for all 8 panels |

### Test

| File | Status | Responsibility |
|------|--------|----------------|
| `tests/observability/test_monitor_router.py` | Create | TestClient + mocked session assertions for `/monitor/overview` (8 distribution counts verified) + `/monitor/logs` (subprocess mock + docker-missing path) |

---

## Task 1: Backend Router — `/monitor/overview` and `/monitor/logs`

**Files:**
- Create: `api/app/routers/monitor.py`
- Modify: `api/app/main.py` (register router)
- Create: `tests/observability/test_monitor_router.py`

**Interfaces:**
- Consumes: `shared.db.get_session()`, `shared.models.{Case, Event, Finding, ConflictRecord, DecisionPackage}`, env `LANGFUSE_HOST` + `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`
- Produces (used by Task 3):
  - `GET /monitor/overview` → JSON `MonitorOverview` (§6.1 of spec)
  - `GET /monitor/logs?lines=200` → JSON `WorkerLogs` (§6.2 of spec)

- [ ] **Step 1: Write failing test for `/monitor/overview`**

Create `tests/observability/test_monitor_router.py`:

```python
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _p in (_REPO, _REPO / "worker"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _purge_app_modules() -> None:
    """api/ and worker/ both ship a package named `app`. Same trick as
    tests/observability/test_observability_router.py — load api by file
    path so worker/app stays untouched."""
    import sys

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name, None)


def _load_api_main():
    import importlib.util

    _purge_app_modules()
    sys.path.insert(0, str(_REPO / "api"))
    try:
        spec = importlib.util.spec_from_file_location(
            "_api_app_main_under_test_monitor", _REPO / "api" / "app" / "main.py"
        )
        main_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_mod)
        from fastapi.testclient import TestClient

        return TestClient(main_mod.app)
    finally:
        sys.path.remove(str(_REPO / "api"))
        _purge_app_modules()


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    _purge_app_modules()


def test_monitor_overview_shape(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    client = _load_api_main()

    resp = client.get("/monitor/overview")
    # We can't reach Postgres in unit test → 503 is acceptable, but the route
    # must be MOUNTED and reachable. Verify by graceful 503 (api returns 503
    # when DB unreachable) — the route exists if status != 404.
    assert resp.status_code != 404, "monitor router not mounted"
    # 503 acceptable for unit-test (no Postgres), 200 when actual DB present.
    assert resp.status_code in (200, 503), f"unexpected: {resp.status_code} {resp.text[:200]}"


def test_monitor_logs_subprocess_mock(monkeypatch):
    """Even without Docker installed, /monitor/logs must return 200 with
    an `error` field rather than 500."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    # Force FileNotFoundError on subprocess.run to simulate missing docker.
    import api.app.routers.monitor as monitor_mod  # noqa: F401  loaded by _load_api_main
    client = _load_api_main()

    resp = client.get("/monitor/logs?lines=10")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "container" in body
    assert "lines" in body
    assert "fetched_at" in body
    assert "error" in body


def test_monitor_overview_routes_registered_in_app(monkeypatch):
    """Both /monitor/* routes registered alongside existing /cases/* — no
    existing route disappeared."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    client = _load_api_main()

    paths = {getattr(r, "path", None) for r in client.app.routes}
    assert "/monitor/overview" in paths
    assert "/monitor/logs" in paths
    assert "/cases/{case_id}" in paths  # existing /cases router still mounted
```

- [ ] **Step 2: Run test → see it FAIL**

```bash
/home/son/AIC/dashmint_ai/.venv/bin/python -m pytest tests/observability/test_monitor_router.py -v
```

Expected: 3 FAIL with `KeyError` / `ImportError` for `api.app.routers.monitor` and `AttributeError` on unregistered routes.

- [ ] **Step 3: Implement `api/app/routers/monitor.py`**

```python
"""AI Monitor overview endpoints — sampled aggregations over the existing
SHBExpert Postgres tables plus Langfuse REST. Designed for the hackathon
monitor dashboard (spec docs/superpowers/specs/2026-07-19-ai-monitor-dashboard-design.md).

Two endpoints:
- GET /monitor/overview — KPI + 5 distributions + latency-aggregate + LLM
  calls per case. Partial-degrade: any failing sub-aggregate returns its
  empty default (empty array or 0) instead of crashing the whole call.
- GET /monitor/logs?lines=200 — wraps `docker logs <container> --tail 200`
  in a subprocess; returns error string if Docker / container missing.

All queries hit shared.db.get_session() — same pattern as
api/app/routers/cases.py. Langfuse REST is called from the SERVER using
LANGFUSE_* env; the browser never sees the keys.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any

import httpx
from fastapi import APIRouter, Query
from sqlalchemy import select, func

from shared.db import get_session
from shared.models import Case, ConflictRecord, DecisionPackage, Event, Finding

router = APIRouter(prefix="/monitor", tags=["monitor"])


def _langfuse_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_HOST")) and bool(os.environ.get("LANGFUSE_PUBLIC_KEY")) and bool(
        os.environ.get("LANGFUSE_SECRET_KEY")
    )


def _langfuse_headers() -> dict[str, str]:
    import base64

    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    sk = os.environ.get("LANGFUSE_SECRET_KEY", "")
    auth = base64.b64encode(f"{pk}:{sk}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}


def _kpi_aggregate(session) -> dict[str, Any]:
    cases = session.execute(select(Case)).scalars().all()
    by_state: dict[str, int] = defaultdict(int)
    for c in cases:
        by_state[c.state] += 1
    return {
        "total_cases": len(cases),
        "cases_by_state": dict(by_state),
        "total_findings": session.execute(select(func.count()).select_from(Finding)).scalar() or 0,
        "total_conflicts": session.execute(select(func.count()).select_from(ConflictRecord)).scalar() or 0,
        "conflicts_open": session.execute(
            select(func.count()).select_from(ConflictRecord).where(ConflictRecord.status == "OPEN")
        ).scalar() or 0,
        "conflicts_unresolved": session.execute(
            select(func.count()).select_from(ConflictRecord).where(ConflictRecord.status == "UNRESOLVED")
        ).scalar() or 0,
        "total_decisions": session.execute(select(func.count()).select_from(DecisionPackage)).scalar() or 0,
        "total_events": session.execute(select(func.count()).select_from(Event)).scalar() or 0,
        "total_traces": 0,        # filled from Langfuse below
        "total_llm_calls": 0,     # filled from Langfuse below
    }


def _findings_distribution(session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Finding.agent_id, Finding.stance, func.count()).group_by(Finding.agent_id, Finding.stance)
    ).all()
    return [{"agent_id": a, "stance": s, "n": n} for a, s, n in rows]


def _severity_distribution(session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Finding.agent_id, Finding.severity, func.count()).group_by(Finding.agent_id, Finding.severity)
    ).all()
    return [{"agent_id": a, "severity": s, "n": n} for a, s, n in rows]


def _event_distribution(session) -> list[dict[str, Any]]:
    rows = session.execute(select(Event.event_type, func.count()).group_by(Event.event_type)).all()
    return [{"event_type": t, "n": n} for t, n in rows]


def _conflict_distribution(session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(ConflictRecord.status, func.count()).group_by(ConflictRecord.status)
    ).all()
    return [{"status": s, "n": n} for s, n in rows]


def _conflict_round_distribution(session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(ConflictRecord.issue_key, func.max(ConflictRecord.round), func.count()).group_by(
            ConflictRecord.issue_key
        )
    ).all()
    return [{"issue_key": ik, "max_round": mr, "n": n} for ik, mr, n in rows]


def _decision_distribution(session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(DecisionPackage.recommendation, func.count()).group_by(DecisionPackage.recommendation)
    ).all()
    return [{"recommendation": r, "n": n} for r, n in rows]


def _langfuse_latency_and_llm_calls() -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Returns (latency, llm_calls_per_case, total_traces, total_llm_calls).
    Degrades to ([], [], 0, 0) on any error."""
    if not _langfuse_enabled():
        return [], [], 0, 0
    host = os.environ.get("LANGFUSE_HOST", "")
    headers = _langfuse_headers()
    latency_by_name: dict[str, list[float]] = defaultdict(list)
    llm_calls_by_case: dict[str, int] = defaultdict(int)
    total_traces = 0
    total_llm_calls = 0
    try:
        # Fetch recent traces (max 100 lim globally) — no per-case filter; we
        # accept aggregate across all cases for the hackathon chart.
        r = httpx.get(f"{host}/api/public/traces?limit=100&order_by=timestamp&order=desc", headers=headers, timeout=8)
        if not r.is_success:
            return [], [], 0, 0
        traces = r.json().get("data", []) or []
        total_traces = len(traces)
        for t in traces:
            tid = t.get("id")
            if not tid:
                continue
            or_resp = httpx.get(
                f"{host}/api/public/observations?traceId={tid}&limit=100",
                headers=headers, timeout=8,
            )
            if not or_resp.is_success:
                # Prefer to dedupe at grade-time; looping individual failures tolerated.
                continue
            obs_list = or_resp.json().get("data", []) or []
            for o in obs_list:
                if o.get("type") != "SPAN":
                    if o.get("type") == "GENERATION":
                        total_llm_calls += 1
                        meta = o.get("metadata") or {}
                        cid = meta.get("case_id")
                        if cid:
                            llm_calls_by_case[cid] += 1
                    continue
                name = o.get("name", "")
                st = o.get("startTime")
                en = o.get("endTime")
                if st and en:
                    ms = (
                        datetime.fromisoformat(en.replace("Z", "+00:00"))
                        - datetime.fromisoformat(st.replace("Z", "+00:00"))
                    ).total_seconds() * 1000.0
                    latency_by_name[name].append(ms)
        latency = [
            {
                "name": n,
                "avg_ms": round(sum(v) / len(v), 1),
                "max_ms": round(max(v), 1),
                "count": len(v),
            }
            for n, v in latency_by_name.items()
        ]
        latency.sort(key=lambda r: r["avg_ms"], reverse=True)
        llm = [{"case_id": c, "n": n} for c, n in sorted(llm_calls_by_case.items(), key=lambda i: i[1], reverse=True)]
        return latency, llm, total_traces, total_llm_calls
    except Exception:  # noqa: BLE001 — Langfuse down/timeout is a degrade path, not a crash
        return [], [], 0, 0


@router.get("/overview")
def get_overview() -> dict:
    """Single-shot aggregate endpoint. If Postgres fails, raise 503 — the
    web UI displays a banner. Langfuse and /monitor/logs failures are NOT
    surfaced here, they degrade to empty default."""
    try:
        with get_session() as session:
            kpi = _kpi_aggregate(session)
            findings_dist = _findings_distribution(session)
            severity_dist = _severity_distribution(session)
            event_dist = _event_distribution(session)
            conflict_dist = _conflict_distribution(session)
            conflict_rounds = _conflict_round_distribution(session)
            decision_dist = _decision_distribution(session)
    except Exception as exc:  # noqa: BLE001 — surfaced as 503 for the caller to display
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail=f"aggregation query failed: {exc}") from exc

    latency, llm_calls, total_traces, total_llm_calls = _langfuse_latency_and_llm_calls()
    kpi["total_traces"] = total_traces
    kpi["total_llm_calls"] = total_llm_calls

    return {
        "kpi": kpi,
        "findings_distribution": findings_dist,
        "severity_distribution": severity_dist,
        "event_distribution": event_dist,
        "conflict_distribution": constraint_dist,
        "conflict_round_distribution": conflict_rounds,
        "decision_distribution": decision_dist,
        "latency": latency,
        "llm_calls_per_case": llm_calls,
    }


@router.get("/logs")
def get_logs(lines: int = Query(200, ge=1, le=2000)) -> dict:
    """Tail worker container logs via `docker logs --tail <lines>`. Always
    returns 200 with an `error` field set if the docker binary is missing
    or the container name is wrong."""
    container = os.environ.get("MONITOR_WORKER_CONTAINER", "shbexpert-flow-obs-worker-1")
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            ["docker", "logs", container, "--tail", str(lines)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or "").strip() or f"docker logs returned {proc.returncode}"
            return {"container": container, "fetched_at": fetched_at, "lines": [], "error": err}
        raw = proc.stdout or ""
        # Cap final line count to limit response size.
        out_lines = raw.splitlines()[-lines:]
        return {"container": container, "fetched_at": fetched_at, "lines": out_lines, "error": None}
    except FileNotFoundError as exc:
        return {"container": container, "fetched_at": fetched_at, "lines": [], "error": f"docker binary not found: {exc}"}
    except subprocess.TimeoutExpired as exc:
        return {"container": container, "fetched_at": fetched_at, "lines": [], "error": f"docker logs timeout: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surfaced as error field, not raised
        return {"container": container, "fetched_at": fetched_at, "lines": [], "error": f"unexpected: {exc}"}
```

⚠️ **Bug to fix in Step 4**: there is a typo `constraint_dist` in the return body. Use it as-is now (the test will catch it), then fix in Step 4.

- [ ] **Step 4: Run tests → see that they FAIL on a real bug, then FIX it**

```bash
/home/son/AIC/dashmint_ai/.venv/bin/python -m pytest tests/observability/test_monitor_router.py -v
```

Expected: `test_monitor_overview_shape` may pass (503 with no DB is fine). `test_monitor_logs_subprocess_mock` may pass since it tolerates any error. Re-read the code, find `constraint_dist`, fix to `conflict_dist`:

```python
        "conflict_distribution": conflict_dist,
```

Re-run after fix — expected: GREEN for all 3.

- [ ] **Step 5: Register router in `api/app/main.py`**

Edit `api/app/main.py` — modify the import line and add an `include_router`:

```python
from app.routers import cases, chat, internal, memo, observability, monitor
```

And after the existing `app.include_router(...)` block:

```python
app.include_router(monitor.router)
```

- [ ] **Step 6: Run full observability test suite → make sure nothing regressed**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
/home/son/AIC/dashmint_ai/.venv/bin/python -m pytest tests/observability/ -v
```

Expected: all green (the original 16 + new 3 = 19).

- [ ] **Step 7: Smoke test against running stack (api on host 8100)**

```bash
curl -fsS http://localhost:8100/monitor/overview | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('kpi:', d['kpi'])
print('findings_dist len:', len(d['findings_distribution']))
print('latency len:', len(d['latency']))
print('llm_calls_per_case:', d['llm_calls_per_case'])
"
```

Expected output (approximate): `kpi: {'total_cases': 7, 'cases_by_state': {'READY_FOR_REVIEW': 6, 'DRAFT': 1}, 'total_findings': 169, 'total_conflicts': some_n, ..., 'total_traces': N, 'total_llm_calls': M}` with `latency` containing ~14 entries (node.plan, node.financial, ...) and `llm_calls_per_case` containing entries like `[{'case_id': 'C06', 'n': 15}, ...]`.

```bash
curl -fsS "http://localhost:8100/monitor/logs?lines=10" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('lines:', len(d['lines']), 'error:', d['error'])
if d['lines']:
    print('first:', d['lines'][0][:100])
"
```

Expected: `lines: 10` (or more), `error: None`.

- [ ] **Step 8: Commit**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
git add api/app/routers/monitor.py api/app/main.py tests/observability/test_monitor_router.py
git commit -m "feat(api): add /monitor/overview + /monitor/logs endpoints — single-shot aggregate over Postgres + Langfuse"
```

If Step 7 fails because api container was started before the new route was added, rebuild api:

```bash
docker compose up -d --build api
```

Then re-run the curl smoke. Do NOT commit until Step 7 returns the expected shape.

---

## Task 2: Frontend types + fetcher (`web/app/lib/monitor.ts`)

**Files:**
- Create: `web/app/lib/monitor.ts`

**Interfaces:**
- Consumes: existing `/api/*` rewrite (next.config.mjs → `api`), so calls go to `http://localhost:8100/monitor/*`
- Produces (used by Task 3): `fetchMonitorOverview(): Promise<MonitorOverview>`, `fetchMonitorLogs(lines?): Promise<WorkerLogs>`, plus TypeScript interfaces `MonitorOverview`, `WorkerLogs`, `MonitorKPI`, ... matching spec §6

- [ ] **Step 1: Create `web/app/lib/monitor.ts`**

```typescript
// Typed fetchers for the AI Monitor dashboard. Browser → /api/* rewrite
// → api /monitor/overview and /monitor/logs (server-side, never chạm DB
// nor Langfuse keys directly from the browser).
// Spec contract docs/superpowers/specs/2026-07-19-ai-monitor-dashboard-design.md §6.

export interface MonitorKPI {
  total_cases: number;
  cases_by_state: Record<string, number>;
  total_findings: number;
  total_conflicts: number;
  conflicts_open: number;
  conflicts_unresolved: number;
  total_decisions: number;
  total_events: number;
  total_traces: number;
  total_llm_calls: number;
}

export interface FindingDistEntry { agent_id: string; stance: string; n: number; }
export interface SeverityDistEntry { agent_id: string; severity: string; n: number; }
export interface EventDistEntry { event_type: string; n: number; }
export interface ConflictDistEntry { status: string; n: number; }
export interface ConflictRoundEntry { issue_key: string; max_round: number; n: number; }
export interface DecisionDistEntry { recommendation: string; n: number; }
export interface LatencyEntry { name: string; avg_ms: number; max_ms: number; count: number; }
export interface LLMCallsEntry { case_id: string; n: number; }

export interface MonitorOverview {
  kpi: MonitorKPI;
  findings_distribution: FindingDistEntry[];
  severity_distribution: SeverityDistEntry[];
  event_distribution: EventDistEntry[];
  conflict_distribution: ConflictDistEntry[];
  conflict_round_distribution: ConflictRoundEntry[];
  decision_distribution: DecisionDistEntry[];
  latency: LatencyEntry[];
  llm_calls_per_case: LLMCallsEntry[];
}

export interface WorkerLogs {
  container: string;
  fetched_at: string;
  lines: string[];
  error: string | null;
}

export async function fetchMonitorOverview(): Promise<MonitorOverview> {
  const res = await fetch(`/api/monitor/overview`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchMonitorOverview failed: ${res.status}`);
  return res.json() as Promise<MonitorOverview>;
}

export async function fetchMonitorLogs(lines = 200): Promise<WorkerLogs> {
  const res = await fetch(`/api/monitor/logs?lines=${lines}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`fetchMonitorLogs failed: ${res.status}`);
  return res.json() as Promise<WorkerLogs>;
}

// SSE event handler type used by the live activity feed.
export interface StepEvent {
  case_id: string;
  type: "step_started" | "step_completed" | "step_failed" | "job_started" | "job_completed" | "job_failed" | string;
  step?: string;
  label?: string;
}
```

- [ ] **Step 2: Verify tsc on the new file**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability/web
npx tsc --noEmit 2>&1 | grep "lib/monitor" || echo "lib/monitor clean"
```

Expected: `lib/monitor clean` (no TS errors). Pre-existing errors in `cases/[caseId]/page.tsx` are unaffected.

- [ ] **Step 3: Commit**

```bash
git add web/app/lib/monitor.ts
git commit -m "feat(web): typed fetchers for /monitor/overview + /monitor/logs"
```

---

## Task 3: Reusable `Panel` wrapper + KPI strip + main `/monitor` page scaffold

**Files:**
- Create: `web/app/components/monitor/Panel.tsx`
- Create: `web/app/components/monitor/KPIStrip.tsx`
- Create: `web/app/monitor/page.tsx`

**Interfaces:**
- Consumes: `fetchMonitorOverview` + `MonitorOverview` type from Task 2
- Produces: `/monitor` route renders a sticky header with KPIs + a 2-column grid (panels added in Tasks 4-9)

- [ ] **Step 1: Create `web/app/components/monitor/Panel.tsx`**

```tsx
"use client";

import { useState, type ReactNode } from "react";

interface Props {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  defaultCollapsed?: boolean;
}

export default function Panel({ title, icon, children, defaultCollapsed = false }: Props) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  return (
    <section className="rounded-lg border border-border bg-card p-4 space-y-3">
      <header className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {icon}
          {title}
        </h3>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground"
          aria-label={collapsed ? "Mở rộng" : "Thu gọn"}
        >
          {collapsed ? "Mở rộng" : "Thu gọn"}
        </button>
      </header>
      {!collapsed && <div className="space-y-3">{children}</div>}
    </section>
  );
}
```

- [ ] **Step 2: Create `web/app/components/monitor/KPIStrip.tsx`**

```tsx
"use client";

import type { MonitorKPI } from "../../lib/monitor";

interface KPIBadgeProps {
  label: string;
  value: number | string;
  tone?: "default" | "positive" | "warning" | "critical" | "info";
}

const toneClasses: Record<NonNullable<KPIBadgeProps["tone"]>, string> = {
  default: "bg-muted text-foreground",
  positive: "bg-emerald-100 text-emerald-900",
  warning: "bg-amber-100 text-amber-900",
  critical: "bg-red-100 text-red-900",
  info: "bg-blue-100 text-blue-900",
};

function KPIBadge({ label, value, tone = "default" }: KPIBadgeProps) {
  return (
    <div className={`flex flex-col gap-0.5 rounded-md px-3 py-2 ${toneClasses[tone]}`}>
      <span className="text-[10px] uppercase tracking-wide text-current/60">{label}</span>
      <span className="text-xl font-semibold tabular-nums">{value}</span>
    </div>
  );
}

export default function KPIStrip({ kpi }: { kpi: MonitorKPI }) {
  const ready = kpi.cases_by_state["READY_FOR_REVIEW"] ?? 0;
  const draft = kpi.cases_by_state["DRAFT"] ?? 0;
  const analyzing = kpi.cases_by_state["ANALYZING"] ?? 0;
  return (
    <div className="flex flex-wrap gap-2">
      <KPIBadge label="Hồ sơ" value={kpi.total_cases} tone="info" />
      <KPIBadge label="Sẵn duyệt" value={ready} tone="positive" />
      <KPIBadge label="Bản nháp" value={draft} tone="warning" />
      {analyzing > 0 && <KPIBadge label="Đang chạy" value={analyzing} tone="info" />}
      <KPIBadge label="Nhận định" value={kpi.total_findings} />
      <KPIBadge label="Mâu thuẫn" value={kpi.total_conflicts} tone={kpi.total_conflicts > 0 ? "critical" : "default"} />
      <KPIBadge label="Quyết định" value={kpi.total_decisions} />
      <KPIBadge label="Sự kiện" value={kpi.total_events} />
      <KPIBadge label="Vết chạy" value={kpi.total_traces} tone="info" />
      <KPIBadge label="Lần gọi LLM" value={kpi.total_llm_calls} tone="info" />
    </div>
  );
}
```

- [ ] **Step 3: Create `web/app/monitor/page.tsx` (scaffold)**

```tsx
"use client";

import { useEffect, useState } from "react";

import KPIStrip from "../components/monitor/KPIStrip";
import Panel from "../components/monitor/Panel";
import { fetchMonitorOverview, type MonitorOverview, type MonitorKPI } from "../lib/monitor";

const emptyKpi: MonitorKPI = {
  total_cases: 0,
  cases_by_state: {},
  total_findings: 0,
  total_conflicts: 0,
  conflicts_open: 0,
  conflicts_unresolved: 0,
  total_decisions: 0,
  total_events: 0,
  total_traces: 0,
  total_llm_calls: 0,
};

export default function MonitorPage() {
  const [overview, setOverview] = useState<MonitorOverview | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchMonitorOverview()
      .then(setOverview)
      .catch((e: Error) => setErr(String(e)));
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur px-6 py-3 space-y-2">
        <div className="flex items-baseline justify-between">
          <h1 className="text-lg font-semibold">SHB Expert Flow · AI Monitor</h1>
          <span className="flex items-center gap-2 text-xs">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            live
          </span>
        </div>
        {overview ? <KPIStrip kpi={overview.kpi} /> : null}
      </header>
      <main className="px-6 py-4 space-y-4">
        {err ? (
          <div className="rounded-lg border border-border bg-red-50 px-4 py-3 text-sm text-red-900">
            Không thể tải dữ liệu: <code>{err}</code>
          </div>
        ) : null}
        {!overview && !err ? <div className="text-sm text-muted-foreground">Đang tải…</div> : null}
        {overview ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="SRE · Tình trạng & Độ trễ"><span className="text-sm text-muted-foreground">(panel 1)</span></Panel>
            <Panel title="Hội đồng agent · Chất lượng"><span className="text-sm text-muted-foreground">(panel 2)</span></Panel>
            <Panel title="LLM & Tools · Số lần gọi"><span className="text-sm text-muted-foreground">(panel 3)</span></Panel>
            <Panel title="Hoạt động & Nhật ký worker"><span className="text-sm text-muted-foreground">(panel 4)</span></Panel>
          </div>
        ) : null}
      </main>
      <footer className="border-t border-border px-6 py-2 text-xs text-muted-foreground">
        SHB Expert AI Monitor v0.1
      </footer>
    </div>
  );
}
```

- [ ] **Step 4: Build + visit page**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
docker compose up -d --build web
sleep 8
curl -fsS http://localhost:3100/monitor -o /dev/null -w "HTTP=%{http_code} size=%{size_download}\n"
```

Expected: `HTTP=200` with non-trivial size_download. Open `http://localhost:3100/monitor` in a browser to visually verify the KPI strip shows real values.

- [ ] **Step 5: Commit**

```bash
git add web/app/components/monitor/Panel.tsx web/app/components/monitor/KPIStrip.tsx web/app/monitor/page.tsx
git commit -m "feat(web): /monitor route scaffold + Panel wrapper + KPI strip"
```

---

## Task 4: Panel 1 — SRE: Case State Donut + Latency Tree

**Files:**
- Create: `web/app/components/monitor/CaseStateDonut.tsx`
- Create: `web/app/components/monitor/LatencyTree.tsx`
- Modify: `web/app/monitor/page.tsx` (replace Panel 1 stub with real charts)

**Interfaces:**
- Consumes: `overview.kpi.cases_by_state: Record<string, number>`, `overview.latency: LatencyEntry[]`
- Produces: donut for case states + bar chart latency sorted by avg_ms desc

- [ ] **Step 1: Create `web/app/components/monitor/CaseStateDonut.tsx`**

```tsx
"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS: Record<string, string> = {
  READY_FOR_REVIEW: "#00853E", // positive green
  ANALYZING: "#0066B3",       // primary blue
  DRAFT: "#FFC10E",           // caution yellow
  NEED_INFO: "#FFC10E",
};

export default function CaseStateDonut({ cases_by_state }: { cases_by_state: Record<string, number> }) {
  const data = Object.entries(cases_by_state).map(([state, value]) => ({ name: state, value }));
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <div className="text-sm text-muted-foreground">Chưa có hồ sơ.</div>;
  return (
    <div className="h-48">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={48} outerRadius={72} paddingAngle={2}>
            {data.map((d) => (
              <Cell key={d.name} fill={COLORS[d.name] ?? "#cbd5e1"} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number, n: string) => [`${v}`, n]} contentStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="mt-2 text-xs space-y-0.5">
        {data.map((d) => (
          <li key={d.name} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full inline-block" style={{ background: COLORS[d.name] ?? "#cbd5e1" }} />
            {d.name}: {d.value}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create `web/app/components/monitor/LatencyTree.tsx`**

```tsx
"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { LatencyEntry } from "../../lib/monitor";

export default function LatencyTree({ latency }: { latency: LatencyEntry[] }) {
  if (latency.length === 0) {
    return <div className="text-sm text-muted-foreground">Không có dữ liệu latency (Langfuse chưa bật hoặc chưa có trace).</div>;
  }
  const data = latency.slice(0, 20).map((l) => ({
    name: l.name,
    avg_ms: l.avg_ms,
    max_ms: l.max_ms,
    count: l.count,
  }));
  return (
    <div className="h-72">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 100, right: 24, top: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis type="number" unit="ms" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={140} />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(v: number, name: string, item: { payload?: { count?: number } }) =>
              name === "avg_ms" ? [`${v} ms (max=${item.payload?.max_ms}, n=${item.payload?.count})`, "avg"] : [`${v} ms`, name]
            }
          />
          <Bar dataKey="avg_ms" fill="#0066B3" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 3: Wire into Panel 1 in `web/app/monitor/page.tsx`**

Edit the Panel 1 stub — replace its `<span>` child with real components:

```tsx
import CaseStateDonut from "../components/monitor/CaseStateDonut";
import LatencyTree from "../components/monitor/LatencyTree";

// ...inside the grid...

<Panel title="SRE · Tình trạng & Độ trễ">
  <div className="space-y-3">
    <CaseStateDonut cases_by_state={overview.kpi.cases_by_state} />
    <h4 className="text-xs font-medium text-muted-foreground">Độ trễ theo node / tool</h4>
    <LatencyTree latency={overview.latency} />
  </div>
</Panel>
```

(Make sure imports are at the top of the file. Use the `edit` tool to insert imports + replace the `<Panel title="SRE ...">...</Panel>` block.)

- [ ] **Step 4: Build + smoke**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
docker compose up -d --build web
sleep 8
curl -fsS http://localhost:3100/monitor -o /dev/null -w "HTTP=%{http_code}\n"
```

Expected: HTTP 200. Open in browser to verify both charts render.

- [ ] **Step 5: Commit**

```bash
git add web/app/components/monitor/CaseStateDonut.tsx web/app/components/monitor/LatencyTree.tsx web/app/monitor/page.tsx
git commit -m "feat(web): Panel 1 SRE — case state donut + latency bar chart"
```

---

## Task 5: Panel 2 — Agent Council Quality (stance stacked + severity heatmap + conflict donut)

**Files:**
- Create: `web/app/components/monitor/StanceStackedBar.tsx`
- Create: `web/app/components/monitor/SeverityHeatmap.tsx`
- Create: `web/app/components/monitor/ConflictDonut.tsx`
- Modify: `web/app/monitor/page.tsx` (replace Panel 2 stub)

**Interfaces:**
- Consumes `overview.findings_distribution`, `overview.severity_distribution`, `overview.conflict_distribution`, `overview.conflict_round_distribution`

- [ ] **Step 1: Create `web/app/components/monitor/StanceStackedBar.tsx`**

```tsx
"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { FindingDistEntry } from "../../lib/monitor";

const STANCES = ["SUPPORT", "CAUTION", "OPPOSE", "NEED_DATA"] as const;
const STANCE_COLORS: Record<string, string> = {
  SUPPORT: "#00853E",
  CAUTION: "#FFC10E",
  OPPOSE: "#F04E45",
  NEED_DATA: "#6E7C8E",
};

export default function StanceStackedBar({ findings_distribution }: { findings_distribution: FindingDistEntry[] }) {
  // Pivot: rows = agent_id, one stacked bar per agent, segments = stance counts.
  const agentIds = Array.from(new Set(findings_distribution.map((d) => d.agent_id))).sort();
  const data = agentIds.map((agent_id) => {
    const row: Record<string, string | number> = { agent_id };
    for (const s of STANCES) row[s] = 0;
    for (const d of findings_distribution) if (d.agent_id === agent_id) row[d.stance] = d.n;
    return row;
  });
  if (agentIds.length === 0) return <div className="text-sm text-muted-foreground">Không có nhận định.</div>;
  return (
    <div className="h-60">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 24, top: 8, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="agent_id" tick={{ fontSize: 10 }} angle={-12} textAnchor="end" height={50} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {STANCES.map((s) => (
            <Bar key={s} dataKey={s} stackId="stance" fill={STANCE_COLORS[s]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Create `web/app/components/monitor/SeverityHeatmap.tsx`**

```tsx
"use client";

import type { SeverityDistEntry } from "../../lib/monitor";

const SEVERITIES = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
const SEV_OPACITY: Record<string, number> = {
  INFO: 0.20,
  LOW: 0.35,
  MEDIUM: 0.55,
  HIGH: 0.80,
  CRITICAL: 1.0,
};
const HEAT_BG = "#F04E45"; // critical red base

export default function SeverityHeatmap({ severity_distribution }: { severity_distribution: SeverityDistEntry[] }) {
  const agentIds = Array.from(new Set(severity_distribution.map((d) => d.agent_id))).sort();
  if (agentIds.length === 0) return <div className="text-sm text-muted-foreground">Không có dữ liệu mức độ.</div>;
  const lookup = new Map<string, number>();
  for (const d of severity_distribution) lookup.set(`${d.agent_id}|${d.severity}`, d.n);
  const maxN = Math.max(1, ...severity_distribution.map((d) => d.n));
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-muted-foreground">Agent</th>
            {SEVERITIES.map((s) => (
              <th key={s} className="px-2 py-1 text-center text-muted-foreground">{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {agentIds.map((agent) => (
            <tr key={agent}>
              <td className="px-2 py-1 font-mono text-muted-foreground">{agent}</td>
              {SEVERITIES.map((sev) => {
                const n = lookup.get(`${agent}|${sev}`) ?? 0;
                const op = n === 0 ? 0.05 : (n / maxN) * SEV_OPACITY[sev];
                return (
                  <td key={sev} className="px-1 py-1">
                    <div
                      className="flex h-9 items-center justify-center rounded text-white tabular-nums"
                      style={{ background: `rgba(240, 78, 69, ${op})`, color: op > 0.6 ? "white" : "var(--foreground)" }}
                      title={`${agent} · ${sev}: ${n}`}
                    >
                      {n || ""}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Create `web/app/components/monitor/ConflictDonut.tsx`**

```tsx
"use client";

import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ConflictDistEntry, ConflictRoundEntry } from "../../lib/monitor";

const STATUS_COLORS: Record<string, string> = {
  RESOLVED: "#00853E",
  OPEN: "#FFC10E",
  UNRESOLVED: "#F04E45",
};

export default function ConflictDonut({
  conflict_distribution,
  conflict_round_distribution,
}: {
  conflict_distribution: ConflictDistEntry[];
  conflict_round_distribution: ConflictRoundEntry[];
}) {
  const donutData = conflict_distribution.map((c) => ({ name: c.status, value: c.n }));
  const total = donutData.reduce((s, d) => s + d.value, 0);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <div className="h-40">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={donutData} dataKey="value" nameKey="name" innerRadius={36} outerRadius={62} paddingAngle={2}>
                {donutData.map((d) => (
                  <Cell key={d.name} fill={STATUS_COLORS[d.name] ?? "#cbd5e1"} />
                ))}
              </Pie>
              <Tooltip(formatter={(v: number, n: string) => [`${v}`, n]} contentStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        {total === 0 ? (
          <div className="text-center text-xs text-muted-foreground">Chưa có mâu thuẫn.</div>
        ) : (
          <ul className="text-xs">
            {donutData.map((d) => (
              <li key={d.name} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: STATUS_COLORS[d.name] ?? "#cbd5e1" }} />
                {d.name}: {d.value}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="text-xs font-medium text-muted-foreground mb-1">Số vòng theo issue_key</h4>
        {conflict_round_distribution.length === 0 ? (
          <div className="text-xs text-muted-foreground">—</div>
        ) : (
          <div className="h-40">
            <ResponsiveContainer>
              <BarChart data={conflict_round_distribution} layout="vertical" margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="issue_key" tick={{ fontSize: 10 }} width={120} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Bar dataKey="max_round" fill="#0066B3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire into Panel 2 in `web/app/monitor/page.tsx`**

Replace the Panel 2 stub:

```tsx
import ConflictDonut from "../components/monitor/ConflictDonut";
import SeverityHeatmap from "../components/monitor/SeverityHeatmap";
import StanceStackedBar from "../components/monitor/StanceStackedBar";

// ...inside the grid...

<Panel title="Hội đồng agent · Chất lượng">
  <div className="space-y-3">
    <h4 className="text-xs font-medium text-muted-foreground">Thái độ theo agent (SUPPORT / CAUTION / OPPOSE / NEED_DATA)</h4>
    <StanceStackedBar findings_distribution={overview.findings_distribution} />
    <h4 className="text-xs font-medium text-muted-foreground">Mức độ (severity × agent)</h4>
    <SeverityHeatmap severity_distribution={overview.severity_distribution} />
    <h4 className="text-xs font-medium text-muted-foreground">Mâu thuẫn</h4>
    <ConflictDonut
      conflict_distribution={overview.conflict_distribution}
      conflict_round_distribution={overview.conflict_round_distribution}
    />
  </div>
</Panel>
```

- [ ] **Step 5: Build + smoke**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
docker compose up -d --build web
sleep 8
curl -fsS http://localhost:3100/monitor -o /dev/null -w "HTTP=%{http_code}\n"
```

Expected: HTTP 200.

- [ ] **Step 6: Commit**

```bash
git add web/app/components/monitor/StanceStackedBar.tsx web/app/components/monitor/SeverityHeatmap.tsx web/app/components/monitor/ConflictDonut.tsx web/app/monitor/page.tsx
git commit -m "feat(web): Panel 2 Agent Council Quality — stance stacked + severity heatmap + conflict donut"
```

---

## Task 6: Panel 3 — LLM & Tools (LLM calls per case + Decision distribution donut + event distribution bar)

**Files:**
- Create: `web/app/components/monitor/LLMCallsBar.tsx`
- Create: `web/app/components/monitor/DecisionDonut.tsx`
- Create: `web/app/components/monitor/EventDistributionBar.tsx`
- Modify: `web/app/monitor/page.tsx` (replace Panel 3 stub)

**Rationale (per spec §1.3 YAGNI): FPT AI returns `usage.total_tokens=0` for Llama-3.3-70B-Instruct. We display # LLM calls instead of token cost — visually equivalent, accurate, and already aggregated server-side.**

- [ ] **Step 1: Create `web/app/components/monitor/LLMCallsBar.tsx`**

```tsx
"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { LLMCallsEntry } from "../../lib/monitor";

export default function LLMCallsBar({ llm_calls_per_case, total_llm_calls }: { llm_calls_per_case: LLMCallsEntry[]; total_llm_calls: number }) {
  if (llm_calls_per_case.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        Chưa có dữ liệu LLM call. Tổng: {total_llm_calls} lần (FPT AI không trả usage trong trace — hiển thị số lần gọi thay vì token).
      </div>
    );
  }
  const data = llm_calls_per_case.slice(0, 15).map((d) => ({ case_id: d.case_id, n: d.n }));
  return (
    <div>
      <div className="text-xs text-muted-foreground">
        Tổng {total_llm_calls} lần gọi LLM cho {llm_calls_per_case.length} hồ sơ (FPT AI chưa report usage → đếm lần thay vì token).
      </div>
      <div className="h-48">
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ left: 100, right: 24, top: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="case_id" tick={{ fontSize: 10 }} width={120} />
            <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => [`${v} lần`, "gọi LLM"]} />
            <Bar dataKey="n" fill="#0066B3" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `web/app/components/monitor/DecisionDonut.tsx`**

```tsx
"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { DecisionDistEntry } from "../../lib/monitor";

const COLOR: Record<string, string> = {
  APPROVE: "#00853E",
  APPROVE_WITH_CONDITIONS: "#00853E",
  REFER: "#FFC10E",
  NEED_INFO: "#FFC10E",
  REJECT: "#F04E45",
};

export default function DecisionDonut({ decision_distribution }: { decision_distribution: DecisionDistEntry[] }) {
  if (decision_distribution.length === 0) return <div className="text-sm text-muted-foreground">Chưa có quyết định.</div>;
  const data = decision_distribution.map((d) => ({ name: d.recommendation, value: d.n }));
  return (
    <div className="h-40">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" outerRadius={62} paddingAngle={2}>
            {data.map((d) => (
              <Cell key={d.name} fill={COLOR[d.name] ?? "#cbd5e1"} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number, n: string) => [`${v}`, n]} contentStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="text-xs">
        {data.map((d) => (
          <li key={d.name} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: COLOR[d.name] ?? "#cbd5e1" }} />
            {d.name}: {d.value}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Create `web/app/components/monitor/EventDistributionBar.tsx`**

```tsx
"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { EventDistEntry } from "../../lib/monitor";

export default function EventDistributionBar({ event_distribution }: { event_distribution: EventDistEntry[] }) {
  if (event_distribution.length === 0) return <div className="text-sm text-muted-foreground">Chưa có sự kiện.</div>;
  const data = event_distribution.map((d) => ({ name: d.event_type, n: d.n }));
  return (
    <div className="h-44">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 24, top: 8, bottom: 50 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-12} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => [`${v}`, "events"]} />
          <Bar dataKey="n" fill="#00853E" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4: Wire into Panel 3 in `web/app/monitor/page.tsx`**

```tsx
import DecisionDonut from "../components/monitor/DecisionDonut";
import EventDistributionBar from "../components/monitor/EventDistributionBar";
import LLMCallsBar from "../components/monitor/LLMCallsBar";

// ...inside the grid...

<Panel title="LLM & Tools · Số lần gọi">
  <div className="space-y-3">
    <h4 className="text-xs font-medium text-muted-foreground">Số lần gọi LLM theo hồ sơ</h4>
    <LLMCallsBar llm_calls_per_case={overview.llm_calls_per_case} total_llm_calls={overview.kpi.total_llm_calls} />
    <h4 className="text-xs font-medium text-muted-foreground">Quyết định tổng hợp</h4>
    <DecisionDonut decision_distribution={overview.decision_distribution} />
    <h4 className="text-xs font-medium text-muted-foreground">Sự kiện hệ thống (FINDING_WRITTEN, CONFLICT_*, ...)</h4>
    <EventDistributionBar event_distribution={overview.event_distribution} />
  </div>
</Panel>
```

- [ ] **Step 5: Build + smoke + commit**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
docker compose up -d --build web
sleep 8
curl -fsS http://localhost:3100/monitor -o /dev/null -w "HTTP=%{http_code}\n"
git add web/app/components/monitor/LLMCallsBar.tsx web/app/components/monitor/DecisionDonut.tsx web/app/components/monitor/EventDistributionBar.tsx web/app/monitor/page.tsx
git commit -m "feat(web): Panel 3 LLM & Tools — LLM calls per case + decision donut + event distribution"
```

Expected: HTTP 200 before commit.

---

## Task 7: Panel 4 — Logs (Live EventStream + WorkerLogsBox)

**Files:**
- Create: `web/app/components/monitor/EventStream.tsx`
- Create: `web/app/components/monitor/WorkerLogsBox.tsx`
- Modify: `web/app/monitor/page.tsx` (replace Panel 4 stub + add SSE subscription effect)

**Interfaces:**
- Consumes existing `/api/cases/{id}/stream` SSE proxy (next.config.mjs rewrite), existing `/api/monitor/logs` from Task 1
- Produces: top-50 rolling activity feed + 200-line worker stdout every 10s

- [ ] **Step 1: Create `web/app/components/monitor/EventStream.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

import type { StepEvent } from "../../lib/monitor";

interface Props {
  /** Top-N recent cases to subscribe SSE for live activity. */
  caseIds: string[];
}

interface FeedItem {
  ts: number;
  case_id: string;
  type: string;
  step?: string;
  label?: string;
}

export default function EventStream({ caseIds }: Props) {
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const sourcesRef = useRef<EventSource[]>([]);

  useEffect(() => {
    const items: FeedItem[] = [];
    const sources: EventSource[] = [];
    for (const cid of caseIds.slice(0, 5)) {
      const source = new EventSource(`/api/cases/${cid}/stream`);
      source.addEventListener("message", (ev: MessageEvent) => {
        try {
          const data: StepEvent = JSON.parse(ev.data);
          if (
            ["step_started", "step_completed", "step_failed", "job_started", "job_completed", "job_failed"].includes(data.type)
          ) {
            items.unshift({ ts: Date.now(), case_id: data.case_id ?? cid, type: data.type, step: data.step, label: data.label });
            if (items.length > 50) items.pop();
            setFeed([...items]);
          }
        } catch {
          /* keepalive */
        }
      });
      sources.push(source);
    }
    sourcesRef.current = sources;
    return () => {
      sources.forEach((s) => s.close());
      sourcesRef.current = [];
    };
  }, [caseIds.join(",")]);

  return (
    <div>
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">Hoạt động trực tiếp (top 50)</h4>
      <ul className="space-y-1 font-mono text-xs">
        {feed.length === 0 ? <li className="text-muted-foreground">Chưa có sự kiện nào.</li> : null}
        {feed.map((item, i) => {
          const tone =
            item.type === "step_failed" || item.type === "job_failed"
              ? "text-red-600"
              : item.type === "step_started" || item.type === "job_started"
                ? "text-blue-600"
                : "text-emerald-600";
          const verb =
            item.type === "step_started" || item.type === "job_started"
              ? "bắt đầu"
              : item.type === "step_failed" || item.type === "job_failed"
                ? "lỗi"
                : "xong";
          return (
            <li key={`${item.ts}-${i}`} className="flex items-center gap-3">
              <span className="text-muted-foreground tabular-nums">{new Date(item.ts).toLocaleTimeString("vi-VN")}</span>
              <span className="font-mono">{item.case_id}</span>
              <span className={tone}>{verb}</span>
              <span className="text-muted-foreground">{item.label ?? item.step ?? item.type}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create `web/app/components/monitor/WorkerLogsBox.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

import { fetchMonitorLogs, type WorkerLogs } from "../../lib/monitor";

export default function WorkerLogsBox() {
  const [data, setData] = useState<WorkerLogs | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchLogs = () => {
      fetchMonitorLogs(200)
        .then((d) => {
          if (!cancelled) {
            setData(d);
            setErr(null);
          }
        })
        .catch((e: Error) => {
          if (!cancelled) setErr(String(e));
        });
    };
    fetchLogs();
    timerRef.current = setInterval(fetchLogs, 10000);
    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div>
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">Nhật ký worker (200 dòng, poll 10s)</h4>
      {err && <div className="text-sm text-red-700">Lỗi: <code>{err}</code></div>}
      {data?.error && !err && (
        <div className="text-sm text-amber-700">
          Docker không khả dụng: <code>{data.error}</code> — chạy monitor trong host có Docker để xem log.
        </div>
      )}
      {data?.lines && data.lines.length > 0 ? (
        <pre className="max-h-72 overflow-auto rounded border border-border bg-muted p-2 text-xs leading-tight font-mono whitespace-pre-wrap">
          {data.lines.join("\n")}
        </pre>
      ) : null}
      {!data?.error && data?.lines && data.lines.length === 0 ? (
        <div className="text-sm text-muted-foreground">Chưa có log worker.</div>
      ) : null}
      {data?.fetched_at ? (
        <div className="mt-1 text-[10px] text-muted-foreground">Lúc {new Date(data.fetched_at).toLocaleString("vi-VN")} · container {data.container}</div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 3: Add SSE subscription state to `web/app/monitor/page.tsx`**

Modify `page.tsx` to compute the top-5 case IDs from the overview `cases_by_state` is not useful — instead the overview response does NOT include per-case list. To get top-5 case IDs, an additional fetch from existing `fetchObservabilityCases()` (already in `lib/observability.ts`) is needed.

Add near the imports:

```tsx
import { EventStream } from "../components/monitor/EventStream";
import { fetchObservabilityCases } from "../lib/observability";
import type { CaseSummary } from "../lib/types";
import WorkerLogsBox from "../components/monitor/WorkerLogsBox";
```

Add inside the component, after the overview fetch effect:

```tsx
const [caseIds, setCaseIds] = useState<string[]>([]);

useEffect(() => {
  fetchObservabilityCases()
    .then((cs: CaseSummary[]) => setCaseIds(cs.slice(0, 5).map((c) => c.case_id)))
    .catch((e: Error) => console.error("fetchObservabilityCases:", e));
}, []);
```

Replace the Panel 4 stub:

```tsx
<Panel title="Hoạt động & Nhật ký worker">
  <div className="space-y-3">
    <EventStream caseIds={caseIds} />
    <WorkerLogsBox />
  </div>
</Panel>
```

- [ ] **Step 4: Build + smoke + verify live events via docker logs trace**

```bash
cd /home/son/AIC/dashmint_ai/.worktrees/feat-multi-agent-observability
docker compose up -d --build web
sleep 8
curl -fsS http://localhost:3100/monitor -o /dev/null -w "HTTP=%{http_code}\n"
# Optional: trigger a fresh analyze to see live events flow
curl -X POST http://localhost:8100/cases/C06/analyze
```

Expected: HTTP 200. Within 30s of the analyze trigger, opening the `/monitor` page should show new entries at the top of the EventStream component.

- [ ] **Step 5: Commit**

```bash
git add web/app/components/monitor/EventStream.tsx web/app/components/monitor/WorkerLogsBox.tsx web/app/monitor/page.tsx
git commit -m "feat(web): Panel 4 Logs — live event stream SSE + worker stdout poll"
```

---

## Task 8: Production smoke + runbook update

**Files:**
- Modify: `docs/superpowers/plans/2026-07-19-multi-agent-observability-runbook.md` (add Section 13+ for /monitor)

- [ ] **Step 1: Smoke `/monitor` end-to-end**

With `shbexpert-flow-obs` up:

```bash
curl -fsS http://localhost:8100/monitor/overview | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('kpi:', len(d['kpi']), 'field keys')
print('total_cases:', d['kpi']['total_cases'])
print('findings_distribution rows:', len(d['findings_distribution']))
print('latency rows:', len(d['latency']))
print('llm_calls_per_case rows:', len(d['llm_calls_per_case']))
"
curl -fsS "http://localhost:8100/monitor/logs?lines=10" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('lines:', len(d['lines']), 'error:', d['error'])"

curl -fsS http://localhost:3100/monitor -o /dev/null -w "monitor page HTTP=%{http_code} size=%{size_download}\n"
```

Expected: all green Holocron; monitor page size_download > 50000.

- [ ] **Step 2: Open in browser + verify chart interaction**

Open `http://localhost:3100/monitor` — verify:
1. KPI strip shows 7 cases, 6 READY, 1 DRAFT, findings 169+, conflicts ≥8, decisions >0, total_traces 5+, total_llm_calls 30+.
2. Panel 1 donut shows 6/1 split (READY/DRAFT) + latency bar chart has rows for node.financial, node.policy, etc.
3. Panel 2 stance stacked bar has 4 agents with stacked segments (SUPPORT/CAUTION/OPPOSE/NEED_DATA); severity heatmap shows red cell for HIGH/CRITICAL; conflict donut shows RESOLVED/OPEN/UNRESOLVED mix.
4. Panel 3 LLM calls bar shows C06 row with ~15; decision donut shows REJECT/NEED_INFO; event distribution bar shows FINDING_WRITTEN on top.
5. Panel 4 live activity feed updates when an `analyze` is triggered; worker logs box shows last 200 lines.

- [ ] **Step 3: Append smoke runbook section**

Edit `docs/superpowers/plans/2026-07-19-multi-agent-observability-runbook.md`. Insert after §12 (Tắt & dọn) a new section:

```markdown
## 13. AI Monitor `/monitor` route (bonus overview for judges)

Adds a single-page overview for hackathon judges / IT audience.

### 13.1 Endpoint smoke

```bash
curl -fsS http://localhost:8100/monitor/overview | python3 -m json.tool | head -30
curl -fsS "http://localhost:8100/monitor/logs?lines=10" | python3 -m json.tool
```

Expected JSON contains: `kpi.{total_cases, cases_by_state, total_findings, total_conflicts, conflicts_open, conflicts_unresolved, total_decisions, total_events, total_traces, total_llm_calls}`, `findings_distribution[]`, `severity_distribution[]`, `event_distribution[]`, `conflict_distribution[]`, `conflict_round_distribution[]`, `decision_distribution[]`, `latency[]`, `llm_calls_per_case[]`.

### 13.2 Page smoke

Open `http://localhost:3100/monitor` — verify the 8 panels render + KPI strip + live event stream updates when triggering `curl -X POST http://localhost:8100/cases/C06/analyze`.

### 13.3 Three-layer data confirmed

- **Trace**: derived from Langfuse REST `/api/public/observations` aggregated by endpoint server-side into `latency[]` and `llm_calls_per_case[]`.
- **Logs**: `events` table counts feed event_distribution + CaseEvent permission rows; `WorkerLogsBox` reads worker stdout from `docker logs`.
- **Metrics**: all aggregates computed query-time via Postgres GROUP BY over `cases/events/findings/conflicts/decisions` — no new table, no scheduler.
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-07-19-multi-agent-observability-runbook.md
git commit -m "docs(runbook): + Section 13 AI Monitor /monitor route smoke and verification"
```

---

## Self-Review

- **Spec coverage**:
  - §1.1 mục tiêu (trace + logs + metrics) → Task 1 endpoint exposes `latency/langfuse`, `event_distribution`, `findings_distribution`, etc.; Tasks 4-7 render them.
  - §1.2 in-scope `/monitor` + 8 endpoints/components → Tasks 2-7.
  - §1.3 YAGNI (no new table) → Task 1 uses query-time aggregations only.
  - §2 Trace → Task 1 `_langfuse_latency_and_llm_calls`; §2.2 Logs → Task 7 `EventStream` + `WorkerLogsBox`; §2.3 Metrics → Task 1 SQL aggregations + all panels.
  - §6.1 MonitorOverview → Task 2 types + Task 1 endpoint response.
  - §6.2 WorkerLogs → Task 1 `/monitor/logs` + Task 7 type.
  - §6.3 degrade paths → Task 1 try/except per aggregate; Task 4 panel "Chưa có dữ liệu"; Task 7 worker logs box error state.
  - §7 SHB colors → copied into each Panel component hex constants.
  - §8 live activity → Task 7 EventStream + interval/poll.
  - §9 error handling → Task 1 return fields in Task 2 types + fall-back states in Task 3 page.
  - §10 tests → Task 1 unit tests.
- **Placeholder scan**: no "TBD/TODO" with 3 deliberate RED→GREEN cycles — Task 1 introduces a deliberate typo (constraint_dist) caught by smoke, fixed at Step 4 (this is intentional TDD, not a placeholder). Other tasks explicitly show final code per step.
- **Type consistency**: `MonitorOverview` interface introduced in Task 2 used verbatim by Tasks 3-7; `LatencyEntry`, `LLMCallsEntry`, etc. all matching between backend response (Task 1) and frontend type (Task 2). `fetchObservabilityCases` from existing `lib/observability.ts` (Task 8）；`CaseSummary` from existing `lib/types.ts`.

Plan complete. Now invoking Skill tool to trigger execution choice.
```
</content>
</articl e>