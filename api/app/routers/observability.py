"""Observability dashboard endpoints.

Spec docs/superpowers/specs/2026-07-19-multi-agent-observability-design.md
§4.2 lists 6 endpoints — we deliberately implement only
`/observability/cases/{case_id}/trace` here. The rest of the dashboard's
reads come from existing /cases/* routes (cases.py) which already return
findings, conflicts, the decision package, events (audit), and live
stream — DRY, no duplication.

The trace endpoint is a read-only link helper: it returns the Langfuse URL
the dashboard's Traces tab should open, plus the trace_id (== case_id by
spec §3.2) the proxy handler will query. It never queries Langfuse itself.
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