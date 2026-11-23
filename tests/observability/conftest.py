"""Shared fixtures for observability unit tests.

No Postgres, no network. Langfuse is mocked — these tests assert the
tracing module wires metadata correctly and goes no-op when disabled,
not that Langfuse's backend actually received anything.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `worker/app/...` and `shared` importable from tests/. Replicates
# what api/Dockerfile + worker/Dockerfile already do via PYTHONPATH — keep
# in sync if those change.
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in [_REPO_ROOT, _REPO_ROOT / "worker", _REPO_ROOT]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture()
def enable_observability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3001")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")


@pytest.fixture()
def disable_observability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")


@pytest.fixture(autouse=True)
def _default_observability_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cases that explicitly take `enable_observability` opt in; the
    rest run with tracing disabled so langfuse is never imported. Must run
    BEFORE `enable_observability`/`disable_observability` set their value —
    pytest resolves explicit fixtures last, so a plain `setenv` here is
    overridden by those fixtures' `setenv`, which is exactly the intent."""
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")