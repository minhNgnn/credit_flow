"""Entrypoint for the `worker` service (LangGraph runtime).

Consumes analyze jobs enqueued by `api` (Redis list ANALYZE_QUEUE), runs
the LangGraph graph per case (worker/app/graph/build.py), and publishes
progress to a per-case Redis pub/sub channel that `api`'s SSE endpoint
forwards to the browser (overview.md §4: worker -> redis -> api -> SSE).

Note on sync-inside-async: shared/db.py's Session and shared/state.py's
write_finding() are synchronous SQLAlchemy calls, invoked here from inside
async agent code. That's a deliberate simplification for this scope (one
case processed at a time, not high-concurrency) — it briefly blocks the
event loop per DB call rather than requiring a second async SQLAlchemy
engine. Revisit if Phase 3's parallel FanOut needs true concurrent DB
access from multiple agents at once.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time

import redis.asyncio as aioredis

from shared.db import ping as db_ping
from app.agents.extraction import run_extraction
from app.chat.server import serve as serve_chat_http
from app.config import ANALYZE_QUEUE, EXTRACTION_QUEUE, REDIS_URL, SLINK_SCORING_QUEUE, progress_channel
from app.slink.runner import process_scoring_job
from app.graph.build import Checkpointer, build_compiled_graph

HEARTBEAT_PATH = "/tmp/heartbeat"


async def wait_for_dependencies(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    r = aioredis.from_url(REDIS_URL)
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                db_ping()
                await r.ping()
                print(f"[worker] dependencies ready after {attempt} attempt(s)", flush=True)
                return
            except Exception as exc:  # noqa: BLE001
                print(f"[worker] waiting for dependencies (attempt {attempt}): {exc}", flush=True)
                await asyncio.sleep(delay_seconds)
    finally:
        await r.aclose()
    print("[worker] dependencies never became ready — exiting", flush=True)
    sys.exit(1)


async def _heartbeat_loop() -> None:
    while True:
        with open(HEARTBEAT_PATH, "w") as f:
            f.write(str(time.time()))
        await asyncio.sleep(15)


async def _publish(r: aioredis.Redis, case_id: str, event: dict) -> None:
    await r.publish(progress_channel(case_id), json.dumps(event))


async def _consume_jobs(compiled_graph) -> None:
    r = aioredis.from_url(REDIS_URL)
    print(f"[worker] listening on redis list {ANALYZE_QUEUE!r}", flush=True)
    while True:
        item = await r.brpop(ANALYZE_QUEUE, timeout=5)
        if item is None:
            continue  # timeout — loop back so the heartbeat/cancellation stay responsive
        _key, raw = item
        job = json.loads(raw)
        case_id = job["case_id"]
        print(f"[worker] dequeued analyze job for case {case_id}", flush=True)
        await _publish(r, case_id, {"type": "job_started", "case_id": case_id})
        try:
            from app.observability.tracing import trace_case_run
            async with trace_case_run(case_id, metadata={"job_id": job.get("job_id")}):
                result = await compiled_graph.ainvoke(
                    {"case_id": case_id, "findings_written": []},
                    config={"configurable": {"thread_id": case_id}},
                )
            await _publish(
                r,
                case_id,
                {"type": "job_completed", "case_id": case_id, "findings_written": result["findings_written"]},
            )
            print(f"[worker] case {case_id} done: {result['findings_written']}", flush=True)
        except Exception as exc:  # noqa: BLE001 — a bad job must not kill the consumer loop
            print(f"[worker] job for case {case_id} failed: {exc}", flush=True)
            await _publish(r, case_id, {"type": "job_failed", "case_id": case_id, "error": str(exc)})


async def _consume_slink_jobs() -> None:
    """Vòng lặp tiêu thụ thứ hai — luồng xanh (ACAS-SLINK).

    Hàng đợi riêng chứ không dùng chung ANALYZE_QUEUE: hai domain khác
    nhau, payload khác nhau (slink_application_id vs case_id), và một job
    SLINK hỏng không được làm nghẽn hàng đợi thẩm định luồng đỏ.
    """
    r = aioredis.from_url(REDIS_URL)
    print(f"[worker] listening on redis list {SLINK_SCORING_QUEUE!r}", flush=True)
    while True:
        item = await r.brpop(SLINK_SCORING_QUEUE, timeout=5)
        if item is None:
            continue
        _key, raw = item
        application_id = json.loads(raw)["slink_application_id"]
        print(f"[worker] dequeued slink scoring job {application_id}", flush=True)
        try:
            await process_scoring_job(r, application_id)
        except Exception as exc:  # noqa: BLE001 — job hỏng không được giết vòng lặp
            print(f"[worker] slink job {application_id} failed: {exc}", flush=True)


async def _consume_extraction_jobs() -> None:
    """Vòng lặp tiêu thụ thứ ba — trích xuất field từ tài liệu RM nộp (lát
    2). Hàng đợi riêng khỏi ANALYZE_QUEUE/SLINK_SCORING_QUEUE: job trigger
    ngay khi upload MỘT document (không phải khi case đổi state), và một
    document lỗi không được chặn document/case khác."""
    r = aioredis.from_url(REDIS_URL)
    print(f"[worker] listening on redis list {EXTRACTION_QUEUE!r}", flush=True)
    while True:
        item = await r.brpop(EXTRACTION_QUEUE, timeout=5)
        if item is None:
            continue
        _key, raw = item
        document_id = json.loads(raw)["document_id"]
        print(f"[worker] dequeued extraction job for document {document_id}", flush=True)
        try:
            await run_extraction(document_id)
        except Exception as exc:  # noqa: BLE001 — job hỏng không được giết vòng lặp
            print(f"[worker] extraction job {document_id} failed: {exc}", flush=True)


async def main() -> None:
    await wait_for_dependencies()
    asyncio.create_task(_heartbeat_loop())
    # Chat Orchestrator's HTTP surface (ai-architecture_v2.md §11.8) —
    # runs alongside the analyze-job consumer loop below in this same
    # process/event loop, not a separate container. See app/chat/server.py.
    asyncio.create_task(serve_chat_http())
    # Luồng xanh chạy song song luồng đỏ trong cùng process/event loop.
    asyncio.create_task(_consume_slink_jobs())
    # Lát 2: trích xuất field, chạy song song hoàn toàn độc lập — trigger
    # theo document upload, không theo case state.
    asyncio.create_task(_consume_extraction_jobs())

    async with Checkpointer() as saver:
        compiled_graph = await build_compiled_graph(saver)
        print("[worker] ready — graph compiled, checkpointer connected", flush=True)
        await _consume_jobs(compiled_graph)


if __name__ == "__main__":
    asyncio.run(main())
