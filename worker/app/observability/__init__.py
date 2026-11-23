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