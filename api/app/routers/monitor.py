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
import base64
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from shared.db import get_session
from shared.models import Case, ConflictRecord, DecisionPackage, Event, Finding

router = APIRouter(prefix="/monitor", tags=["monitor"])


def _langfuse_enabled() -> bool:
    return (
        bool(os.environ.get("LANGFUSE_HOST"))
        and bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))
        and bool(os.environ.get("LANGFUSE_SECRET_KEY"))
    )


def _langfuse_headers() -> dict[str, str]:
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
        select(
            ConflictRecord.issue_key,
            func.max(ConflictRecord.round),
            func.count(),
        ).group_by(ConflictRecord.issue_key)
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
        r = httpx.get(
            f"{host}/api/public/traces?limit=100&order_by=timestamp&order=desc",
            headers=headers,
            timeout=8,
        )
        if not r.is_success:
            return [], [], 0, 0
        traces = r.json().get("data", []) or []
        total_traces = len(traces)
        # Map trace_id → case_id BEFORE iterating observations — observation
        # metadata only carries resourceAttributes, NOT case_id; trace-level
        # metadata.case_id is what we set in worker/app/observability/tracing.py.
        trace_case_map: dict[str, str | None] = {
            t.get("id"): (t.get("metadata") or {}).get("case_id") for t in traces if t.get("id")
        }
        for tid in trace_case_map:
            or_resp = httpx.get(
                f"{host}/api/public/observations?traceId={tid}&limit=100",
                headers=headers,
                timeout=8,
            )
            if not or_resp.is_success:
                continue
            obs_list = or_resp.json().get("data", []) or []
            case_id_for_trace = trace_case_map.get(tid)
            for o in obs_list:
                if o.get("type") != "SPAN":
                    if o.get("type") == "GENERATION":
                        total_llm_calls += 1
                        if case_id_for_trace:
                            llm_calls_by_case[case_id_for_trace] += 1
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
        llm = [
            {"case_id": c, "n": n}
            for c, n in sorted(llm_calls_by_case.items(), key=lambda i: i[1], reverse=True)
        ]
        return latency, llm, total_traces, total_llm_calls
    except Exception:  # noqa: BLE001 — Langfuse down/timeout is a degrade path, not a crash
        return [], [], 0, 0


@router.get("/overview")
def get_overview() -> dict:
    """Single-shot aggregate endpoint. If Postgres fails, raise 503 — the
    web UI displays a banner. Langfuse failures are NOT surfaced here,
    they degrade to empty default."""
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
        raise HTTPException(status_code=503, detail=f"aggregation query failed: {exc}") from exc

    latency, llm_calls, total_traces, total_llm_calls = _langfuse_latency_and_llm_calls()
    kpi["total_traces"] = total_traces
    kpi["total_llm_calls"] = total_llm_calls

    return {
        "kpi": kpi,
        "findings_distribution": findings_dist,
        "severity_distribution": severity_dist,
        "event_distribution": event_dist,
        "conflict_distribution": conflict_dist,
        "conflict_round_distribution": conflict_rounds,
        "decision_distribution": decision_dist,
        "latency": latency,
        "llm_calls_per_case": llm_calls,
    }


def _parse_docker_stream(raw: bytes) -> list[str]:
    """Docker /containers/{id}/logs stream format: every chunk is prefixed
    with an 8-byte header (1 byte stream type, 3 bytes padding, 4 bytes
    big-endian payload length) followed by the payload bytes. Multiple
    chunks concatenate; we strip headers and split on newlines."""
    out_lines: list[str] = []
    i = 0
    n = len(raw)
    while i + 8 <= n:
        length = int.from_bytes(raw[i + 4 : i + 8], "big")
        i += 8
        if i + length > n:
            break
        payload = raw[i : i + length]
        out_lines.extend(payload.decode("utf-8", errors="replace").splitlines())
        i += length
    return out_lines


@router.get("/logs")
def get_logs(lines: int = Query(200, ge=1, le=2000)) -> dict:
    """Tail worker container logs via the Docker Engine HTTP API over a
    mounted Unix socket (compose mounts /var/run/docker.sock into the api
    container). Always returns 200 with an `error` field set if the
    socket is missing / the container name is wrong / the API call fails —
    never raises, so the dashboard can render the rest of the page."""
    container = os.environ.get("MONITOR_WORKER_CONTAINER", "shbexpert-flow-obs-worker-1")
    fetched_at = datetime.now(timezone.utc).isoformat()
    socket_path = os.environ.get("DOCKER_SOCK", "/var/run/docker.sock")
    if not os.path.exists(socket_path):
        return {
            "container": container,
            "fetched_at": fetched_at,
            "lines": [],
            "error": (
                "docker socket unavailable — /var/run/docker.sock not present in this "
                "container (api service in shbexpert-flow-obs compose doesn't mount it)."
            ),
        }
    try:
        # httpx talks to the Unix socket directly; no `docker` CLI needed.
        with httpx.Client(transport=httpx.HTTPTransport(uds=socket_path), base_url="http://localhost") as client:
            # encodeURIComponent on container name (safe even for plain names):
            resp = client.get(
                f"/v1.41/containers/{container}/logs?stdout=true&stderr=true&tail={lines}",
                timeout=5,
            )
            if resp.status_code != 200:
                return {
                    "container": container,
                    "fetched_at": fetched_at,
                    "lines": [],
                    "error": f"docker API returned {resp.status_code}: {resp.text[:200]}",
                }
            out_lines = _parse_docker_stream(resp.content)[-lines:]
            return {"container": container, "fetched_at": fetched_at, "lines": out_lines, "error": None}
    except httpx.ConnectError as exc:
        return {"container": container, "fetched_at": fetched_at, "lines": [], "error": f"docker socket connect failed: {exc}"}
    except httpx.TimeoutException as exc:
        return {"container": container, "fetched_at": fetched_at, "lines": [], "error": f"docker API timeout: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surfaced as error field, not raised
        return {"container": container, "fetched_at": fetched_at, "lines": [], "error": f"unexpected: {exc}"}