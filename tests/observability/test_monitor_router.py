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


def _set_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")


def test_monitor_overview_shape(monkeypatch):
    _set_env(monkeypatch)
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
    _set_env(monkeypatch)
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
    _set_env(monkeypatch)
    client = _load_api_main()

    paths = {getattr(r, "path", None) for r in client.app.routes}
    assert "/monitor/overview" in paths
    assert "/monitor/logs" in paths
    assert "/cases/{case_id}" in paths  # existing /cases router still mounted