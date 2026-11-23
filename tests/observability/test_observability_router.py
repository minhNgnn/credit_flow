from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
# IMPORTANT: api/ and worker/ both ship a package named `app`. They never
# coexist in production (separate containers, separate PYTHONPATH), but a
# single pytest process imports both. Loading api/app via `import app.main`
# would bind the `app` name to api/app and shadow worker/app/observability.*
# for every other test. Instead, we load api/app/main.py by file path under
# a unique module name (api_app_main) so worker's `app` package stays
# untouched throughout this test session.
for _p in (_REPO, _REPO / "worker"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
# api/app is NOT added to sys.path — load it via spec_from_file_location.

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _purge_app_modules() -> None:
    """api/ and worker/ both ship a package named `app` — one Test (router)
    imports api/app/main.py and caches `app` as the api package; that
    shadows worker/app/observability/tracing used by sibling tests. Drop
    every `app*` import from sys.modules so the next import re-resolves
    against whichever sys.path entry comes first (worker/ ahead of api/
    in our conftest).

    Call this at the start of each router test (before any reload) AND in
    an autouse teardown so residue never crosses tests.
    """
    import sys

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name, None)


def _set_env(monkeypatch, *, enabled: bool) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://x:x@localhost/x")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse:3001")


def _load_api_main():
    """Load api/app/main.py by file path under a unique module name so the
    `app` package namespace is not hijacked from worker/app/ (the api
    container's `app` and the worker container's `app` both share the
    name — coexistence in one runtime is what this shim sidesteps)."""
    import importlib.util

    _purge_app_modules()
    sys.path.insert(0, str(_REPO / "api"))
    try:
        api_main_path = _REPO / "api" / "app" / "main.py"
        spec = importlib.util.spec_from_file_location("_api_app_main_under_test", api_main_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"failed to load {api_main_path}")
        main_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_mod)
        return TestClient(main_mod.app)
    finally:
        # Best-effort: pull api/ off sys.path so the next worker import
        # doesn't accidentally resolve against it via the leaked `app.main`.
        sys.path.remove(str(_REPO / "api"))
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)


def _reload_app():
    return _load_api_main()


@pytest.fixture(autouse=True)
def _cleanup_app_modules_after():
    yield
    _purge_app_modules()


def test_trace_endpoint_returns_langfuse_link(monkeypatch):
    _set_env(monkeypatch, enabled=True)
    client = _reload_app()

    resp = client.get("/observability/cases/C06/trace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["langfuse_trace_id"] == "C06"
    assert body["langfuse_url"].startswith("http://langfuse:3001")


def test_trace_endpoint_returns_null_url_when_disabled(monkeypatch):
    _set_env(monkeypatch, enabled=False)
    client = _reload_app()

    resp = client.get("/observability/cases/C06/trace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["langfuse_trace_id"] == "C06"
    assert body["langfuse_url"] is None


def test_case_detail_endpoint_still_registered(monkeypatch):
    """Regression: existing /cases/{id} route still registered after the new
    observability router is wired in. We don't hit the DB — route
    introspection is enough proof the router is mounted."""
    client = _reload_app()

    paths = {getattr(r, "path", None) for r in client.app.routes}
    assert "/cases/{case_id}" in paths
    assert "/observability/cases/{case_id}/trace" in paths