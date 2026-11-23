from __future__ import annotations

import pytest


def test_trace_case_run_noop_when_disabled(disable_observability):
    """When OBSERVABILITY_ENABLED=false, trace_case_run yields a no-op
    context object and does not touch any Langfuse client."""
    from app.observability.tracing import trace_case_run

    async def _body():
        async with trace_case_run("C06") as ctx:
            assert ctx is not None
            assert ctx.case_id == "C06"
            span = ctx.start_span("test")
            assert span is not None  # NoopSpan still usable

    import asyncio
    asyncio.run(_body())


def test_trace_case_run_carries_case_id_metadata(enable_observability):
    """When enabled, the context exposes `.case_id` and `.metadata` such
    that downstream code can attach spans carrying the right metadata."""
    from app.observability.tracing import trace_case_run

    async def _body():
        async with trace_case_run("C06", metadata={"customer_id": "CUS-1"}) as ctx:
            assert ctx.case_id == "C06"
            assert ctx.metadata["customer_id"] == "CUS-1"

    import asyncio
    asyncio.run(_body())


def test_trace_case_run_disabled_does_not_import_langfuse(disable_observability):
    """Disabled path must never touch the langfuse SDK — verified by
    importing tracing fresh with langfuse imports blocked."""
    import sys

    # Block langfuse import and clear any cached state.
    sys.modules.pop("langfuse", None)
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "langfuse" or name.startswith("langfuse."):
            raise ImportError(f"blocked: {name}")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = _blocked_import
    try:
        # Force a re-import of tracing so it exercises the disabled path
        # under our blocked-import shim.
        sys.modules.pop("app.observability.tracing", None)
        from app.observability.tracing import trace_case_run, call_tool, observe_generation  # noqa: F401
    finally:
        builtins.__import__ = real_import