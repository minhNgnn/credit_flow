"""LLM provider adapter — the ONLY place agent code touches an LLM SDK.

Reads worker/config/models.yaml for tier -> {provider, model, max_tokens}.
Agents call `complete(tier="reasoning", system=..., user=...)` and never
import `anthropic`/`openai` themselves — this is what makes "đổi provider
là đổi models.yaml, không đụng code agent" (the plan's Phần D) actually
true instead of aspirational.

LLM_MOCK=true short-circuits every tier to a deterministic templated
response (no network call, no API key needed) — required for the
DEMO_REPLAY fallback (PRD 14.4) and for developing without burning API
credits.

Observability: `complete()` and `stream_complete()` are decorated with
`observe_generation` (worker/app/observability/tracing.py) so each LLM
call shows up in Langfuse as a generation span — prompt, response,
tokens, cost, latency auto-captured. The decorator no-ops when
OBSERVABILITY_ENABLED=false, so mock mode and non-observability runs are
byte-identical to before.
"""
from __future__ import annotations

import asyncio
import os
import time
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)

from app.observability.tracing import observe_generation

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "models.yaml"

# Eval-harness hook (eval/common/instrumentation.py) — off by default (None),
# so normal app traffic is byte-for-byte unaffected. When an eval runner sets
# a collector list via `set_metrics_collector` before invoking agent code, every
# `complete()` call appends its {tier, provider, model, latency_ms,
# prompt_tokens, completion_tokens} here. A ContextVar (not a module global)
# because LangGraph's FanOut runs several agents as concurrent asyncio tasks
# on one event loop — asyncio copies the current context into each child
# task, so setting this once before `ainvoke()` attributes every concurrent
# agent's calls back to the same collector without threading a parameter
# through every call site.
_metrics_collector: ContextVar[list | None] = ContextVar("_metrics_collector", default=None)


def set_metrics_collector(collector: list | None) -> None:
    _metrics_collector.set(collector)


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _tier_config(tier: str) -> dict[str, Any]:
    config = _load_config()
    try:
        return config["tiers"][tier]
    except KeyError as exc:
        raise ValueError(f"unknown model tier {tier!r} — check worker/config/models.yaml") from exc


def _mock_response(tier: str, system: str, user: str) -> str:
    """Deterministic, seed-free "response" — same input always produces the
    same output, satisfying DEMO_REPLAY without needing a fixed random seed.

    Every agent prompt in this codebase follows the same shape: substantive
    data/context first, then an instruction sentence telling the model what
    to write (starting with "Viết" / "Hãy viết"). Cutting at that sentence
    keeps the mock response readable — the data, not an echoed instruction —
    without needing any actual language generation.
    """
    body = user.strip()
    for marker in ("Viết", "Hãy viết"):
        idx = body.find(marker)
        if idx != -1:
            body = body[:idx].strip()
            break
    return f"[LLM_MOCK/{tier}] {body[:400]}"


@observe_generation
async def complete(*, tier: str, system: str, user: str) -> str:
    """Returns the model's text response for one single-turn completion.
    Multi-turn / tool-calling loops belong in the agent code, not here —
    this function is intentionally as thin as `messages.create` gets."""
    if os.environ.get("LLM_MOCK", "false").lower() in ("1", "true", "yes"):
        return _mock_response(tier, system, user)

    cfg = _tier_config(tier)
    provider = cfg["provider"]
    model = cfg["model"]
    max_tokens = cfg.get("max_tokens", 4096)

    start = time.monotonic()
    if provider == "anthropic":
        text, usage = await _complete_anthropic(model=model, max_tokens=max_tokens, system=system, user=user)
    elif provider == "openai":
        text, usage = await _complete_openai(model=model, max_tokens=max_tokens, system=system, user=user)
    else:
        raise ValueError(f"unsupported provider {provider!r} for tier {tier!r}")

    collector = _metrics_collector.get()
    if collector is not None:
        collector.append(
            {
                "tier": tier,
                "provider": provider,
                "model": model,
                "latency_ms": (time.monotonic() - start) * 1000,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            }
        )
    return text


async def _complete_anthropic(*, model: str, max_tokens: int, system: str, user: str) -> tuple[str, dict]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = {"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens}
    return text, usage


async def _complete_openai(*, model: str, max_tokens: int, system: str, user: str) -> tuple[str, dict]:
    from openai import AsyncOpenAI

    # OPENAI_BASE_URL lets this point at a self-hosted OpenAI-compatible
    # server (e.g. vLLM serving DeepSeek-V4-Flash) instead of OpenAI's cloud —
    # unset/empty falls back to the SDK default (api.openai.com).
    client = AsyncOpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None)  # reads OPENAI_API_KEY from env
    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    usage = (
        {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens}
        if response.usage
        else {"prompt_tokens": None, "completion_tokens": None}
    )
    return text, usage


async def complete_json(*, tier: str, system: str, user: str, schema: type[ModelT]) -> ModelT:
    """Như `complete()` nhưng trả một instance Pydantic đã validate thay vì
    text tự do — dùng cho lát 2 (trích xuất), nơi LLM phải trả field_key +
    line_id trỏ vào anchor thật, không phải văn xuôi.

    LLM_MOCK=true trả thẳng `schema()` rỗng (không gọi mạng) — MỌI schema
    dùng với hàm này phải có toàn bộ field mang default (xem
    ExtractionResult trong shared/extraction/schema.py), đúng bất biến
    LLM_MOCK vốn có của complete()/stream_complete() ở trên: pipeline chạy
    hết không cần key/mạng.

    Retry đúng 1 lần kèm lỗi validate trong prompt nếu JSON sai hình dạng;
    vẫn hỏng thì trả `schema()` rỗng — một document lỗi không được làm
    crash consumer đang xử lý các document khác.
    """
    if os.environ.get("LLM_MOCK", "false").lower() in ("1", "true", "yes"):
        return schema()

    cfg = _tier_config(tier)
    provider = cfg["provider"]
    if provider != "openai":
        raise ValueError(f"complete_json chỉ hỗ trợ provider 'openai' cho tier {tier!r}, nhận {provider!r}")
    model = cfg["model"]
    max_tokens = cfg.get("max_tokens", 4096)

    raw = await _complete_openai_json(model=model, max_tokens=max_tokens, system=system, user=user)
    try:
        return schema.model_validate_json(raw)
    except ValidationError as exc:
        retry_user = (
            f"{user}\n\nPhản hồi trước bị lỗi: {exc}\n"
            "Hãy sửa lại và CHỈ trả JSON hợp lệ đúng schema, không thêm chữ nào khác."
        )
        raw_retry = await _complete_openai_json(model=model, max_tokens=max_tokens, system=system, user=retry_user)
        try:
            return schema.model_validate_json(raw_retry)
        except ValidationError:
            return schema()


async def _complete_openai_json(*, model: str, max_tokens: int, system: str, user: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None)
    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or "{}"


# ---------------------------------------------------------------------------
# Streaming variant — Chat Orchestrator (ai-architecture_v2.md §11.8) only.
# Every expert agent (financial.py, policy.py, ...) uses the single-shot
# `complete()` above and always will: they run inside a LangGraph node,
# write one Finding, and are done — there's no user watching text appear.
# Chat is the opposite: a human is looking at the screen waiting for a
# reply, so this yields text AS THE PROVIDER PRODUCES IT rather than
# buffering the whole answer — the actual behavior requested when "chatbot
# tự do như ChatGPT" was chosen over the earlier queued/buffered design.
# ---------------------------------------------------------------------------
@observe_generation
async def stream_complete(*, tier: str, system: str, user: str) -> AsyncIterator[str]:
    if os.environ.get("LLM_MOCK", "false").lower() in ("1", "true", "yes"):
        # No real token stream to tap in mock mode — chunk the same
        # deterministic mock text word-by-word with a tiny delay so the
        # UI exercises its streaming render path in dev/demo without an
        # API key. Never used when LLM_MOCK is off.
        text = _mock_response(tier, system, user)
        for word in text.split(" "):
            yield word + " "
            await asyncio.sleep(0.02)
        return

    cfg = _tier_config(tier)
    provider = cfg["provider"]
    model = cfg["model"]
    max_tokens = cfg.get("max_tokens", 4096)

    if provider == "anthropic":
        async for chunk in _stream_anthropic(model=model, max_tokens=max_tokens, system=system, user=user):
            yield chunk
    elif provider == "openai":
        async for chunk in _stream_openai(model=model, max_tokens=max_tokens, system=system, user=user):
            yield chunk
    else:
        raise ValueError(f"unsupported provider {provider!r} for tier {tier!r}")


async def _stream_anthropic(*, model: str, max_tokens: int, system: str, user: str) -> AsyncIterator[str]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _stream_openai(*, model: str, max_tokens: int, system: str, user: str) -> AsyncIterator[str]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None)
    stream = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        stream=True,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
