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

import contextvars
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
    return _env_flag("OBSERVABILITY_ENABLED")


def _env_flag(name: str) -> bool:
    import os

    return os.environ.get(name, "false").lower() in ("1", "true", "yes")


def _langfuse_client():
    """Lazily imports and returns the langfuse client. Kept inside a
    function so importing this module never requires `langfuse` installed
    (e.g. running unit tests on the host without the SDK)."""
    from langfuse import get_client

    return get_client()


class _NoopSpan:
    """Drop-in span that swallows __enter__/__exit__ and `.event()`. Used
    when tracing is disabled OR when langfuse isn't installed — keeps
    caller code unconditional. Mirrors the subset of the Langfuse span
    API the graph + agents rely on (__enter__/__exit__/update)."""

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

    def start_span(self, name: str, metadata: dict | None = None) -> Any:
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
    span = ctx.start_span(name="case_analysis", metadata={"case_id": case_id, **(metadata or {})})
    try:
        with span:
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
    span_ctx = (
        ctx.start_span(
            name=f"tool.{name}",
            metadata={"tool": name, "case_id": ctx.case_id},
        )
        if ctx is not None
        else _NoopSpan(f"tool.{name}", {"tool": name})
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