from __future__ import annotations

import asyncio

import pytest

# Module-load order: tracing.py imports nothing langfuse-related at the
# top level, so importing this module fresh uses thetkow-disabled path
# when OBSERVABILITY_ENABLED=false (the autouse default in conftest).
# The decorator evaluates lazily inside `observe_generation` at the
# moment adapter.complete is imported — which is once per session.
# To keep tests hermetic, we don't pop sys.modules; we stub via the
# langfuse module's `observe` attribute on a fresh stub module and call
# the helper directly via re-evaluation.


@pytest.fixture(autouse=True)
def _mock_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3001")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")


def test_complete_in_mock_mode_returns_templated_response():
    from app.llm.adapter import complete

    result = asyncio.run(
        complete(
            tier="reasoning",
            system="Bạn là Financial Agent.",
            user="Doanh thu 2025 = 1 tỷ VND. Viết 1 câu claim.",
        )
    )
    assert isinstance(result, str)
    # _mock_response returns the data-prefixed body, capped at 400 chars.
    # When OBSERVABILITY_ENABLED=true and langfuse is importable, observe_generation
    # wraps complete with the langfuse-decorated version that still returns the
    # underlying function's return value.
    assert "LLM_MOCK" in result or "[LLM_MOCK/reasoning]" in result


def test_observe_generation_degrades_when_langfuse_import_fails(monkeypatch):
    """Directly test observe_generation's degrade behavior. Importing the module
    under a broken langfuse module should make observe_generation fall back to
    returning `fn` unchanged — never raise."""
    import sys
    import types

    from langfuse import observe as real_observe

    # Build a fake langfuse module whose `observe` raises when called as decorator.
    fake = types.ModuleType("langfuse")
    fake.get_client = lambda: None  # type: ignore[attr-defined]

    def _broken_observe(*args, **kwargs):
        raise RuntimeError("simulated SDK failure")

    fake.observe = _broken_observe
    monkeypatch.setitem(sys.modules, "langfuse", fake)
    try:
        # Re-import tracing against the stub — observe_generation will see the
        # broken observe() and fall back to passthrough.
        import importlib

        from app.observability import tracing as tracing_mod

        importlib.reload(tracing_mod)

        async def noop():
            pass

        wrapped = tracing_mod.observe_generation(noop)
        # Decorator degrade path returns the function unchanged.
        assert wrapped is noop
    finally:
        monkeypatch.setitem(sys.modules, "langfuse", real_observe.__module__ and __import__("langfuse"))
        # Restore real tracing.
        import importlib

        import app.observability.tracing as tracing_real

        importlib.reload(tracing_real)