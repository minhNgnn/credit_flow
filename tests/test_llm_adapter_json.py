"""complete_json() — structured LLM output, worker/app/llm/adapter.py.

Không test nào ở đây gọi endpoint FPT thật (mạng + tốn phí); việc
gemma-4-26B-A4B-it hỗ trợ response_format=json_object đã xác minh thủ công:

    curl -s -X POST "$OPENAI_BASE_URL/chat/completions" \
      -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
      -d '{"model": "gemma-4-26B-A4B-it",
           "messages": [{"role": "user", "content": "Return a JSON object with one key \"ok\" set to true."}],
           "response_format": {"type": "json_object"}}'

    -> trả {"ok": true} đúng định dạng (xác minh 2026-07-19).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from worker.app.llm import adapter  # noqa: E402


class _Sample(BaseModel):
    fields: list[str] = []
    unresolved: list[str] = []


@pytest.fixture(autouse=True)
def _mock_tier(monkeypatch):
    monkeypatch.setattr(
        adapter,
        "_load_config",
        lambda: {
            "tiers": {
                "extraction": {"provider": "openai", "model": "gemma-4-26B-A4B-it", "max_tokens": 100}
            }
        },
    )


async def test_llm_mock_returns_empty_schema_instance(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result == _Sample()


async def test_valid_json_response_is_parsed(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")

    async def _fake_call(*, model, max_tokens, system, user):
        return '{"fields": ["a", "b"], "unresolved": []}'

    monkeypatch.setattr(adapter, "_complete_openai_json", _fake_call)
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result.fields == ["a", "b"]


async def test_malformed_json_retries_once_then_returns_empty_schema(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    calls = []

    async def _fake_call(*, model, max_tokens, system, user):
        calls.append(user)
        return "not json"

    monkeypatch.setattr(adapter, "_complete_openai_json", _fake_call)
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result == _Sample()
    assert len(calls) == 2  # 1 lần gọi gốc + 1 lần retry kèm lỗi


async def test_retry_succeeds_on_second_attempt(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    responses = iter(["not json", '{"fields": ["c"], "unresolved": []}'])

    async def _fake_call(*, model, max_tokens, system, user):
        return next(responses)

    monkeypatch.setattr(adapter, "_complete_openai_json", _fake_call)
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result.fields == ["c"]
