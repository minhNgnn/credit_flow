from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest


def test_call_tool_returns_underlying_result(disable_observability):
    """Disabled path: just calls the tool, returns its result."""
    from app.observability.tracing import call_tool

    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"value": 42})
    tools = {"calculate_X": tool}

    result = asyncio.run(call_tool(tools, "calculate_X", financials={"a": 1}))

    assert result == {"value": 42}
    tool.ainvoke.assert_awaited_once_with({"financials": {"a": 1}})


def test_call_tool_propagates_tool_errors(disable_observability):
    """If the underlying MCP tool raises, the exception propagates —
    validation never swallows it inside the span."""
    from app.observability.tracing import call_tool

    tool = AsyncMock()
    tool.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
    tools = {"bad": tool}

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(call_tool(tools, "bad"))


def test_call_tool_uses_parent_trace_context(enable_observability, monkeypatch):
    """When observability is enabled, call_tool reads the current
    _TraceContext set by trace_case_run and stamps its span metadata with
    case_id. We assert by checking that start_span on the parent ctx
    receives the right name and metadata."""
    from app.observability import tracing
    from app.observability.tracing import call_tool

    started: list[tuple[str, dict | None]] = []

    class FakeCtx:
        case_id = "C06"
        metadata: dict = {}

        def start_span(self, name, metadata=None):
            started.append((name, metadata))

            class _S:
                def __enter__(self_):
                    return self_

                def __exit__(self_, *a):
                    return None

                def update(self_, **k):
                    # `update(input=args)` and `update(output=...)` get
                    # recorded but don't need to do anything real.
                    pass

            return _S()

    fake_var = type(
        "v",
        (),
        {
            "get": lambda self: FakeCtx(),
            "set": lambda self, v: None,
            "reset": lambda self, v: None,
        },
    )()
    monkeypatch.setattr(tracing, "_current_trace_ctx", fake_var)

    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"ok": 1})
    asyncio.run(call_tool({"X": tool}, "X", foo="bar"))

    # Find the tool.X start_span call and assert it carries case_id.
    tool_starts = [(n, m) for n, m in started if n == "tool.X"]
    assert len(tool_starts) == 1
    name, meta = tool_starts[0]
    assert meta is not None and meta.get("case_id") == "C06"
    assert meta.get("tool") == "X"