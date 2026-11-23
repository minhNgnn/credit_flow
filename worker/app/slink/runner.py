"""Consumer hàng đợi chấm điểm SLINK.

Đọc job từ SLINK_SCORING_QUEUE, lấy merchant từ slink-mock, chạy engine,
ghi kết quả + vết chạy từng agent, và publish tiến trình lên kênh pub/sub
mà api forward ra SSE — đúng khuôn luồng đỏ (overview.md §4:
worker -> redis -> api -> SSE).

Kênh khoá theo slink_application_id, KHÔNG theo case_id.

Spec: docs/superpowers/specs/2026-07-19-slink-scoring-design.md §5
"""
from __future__ import annotations

import datetime as dt
import json
import os

import httpx
import redis.asyncio as aioredis

from shared.db import get_session
from shared.models import SlinkAgentDecision, SlinkApplication
from shared.queue import slink_progress_channel

from shared.slink_engine import APPROVED, score_merchant
from shared.slink_operations import (
    CoreBankingError,
    claim_for_issuing,
    claim_for_scoring,
    issue_overdraft,
    mark_issue_failed,
    mark_issued,
    operations_summary,
    record_event,
)

SLINK_MOCK_URL = os.environ.get("SLINK_MOCK_URL", "http://slink-mock:8400")


async def _publish(r: aioredis.Redis, application_id: str, event: dict) -> None:
    await r.publish(slink_progress_channel(application_id), json.dumps(event))


def _fetch_merchant(customer_id: str) -> dict:
    """Đọc đầy đủ hồ sơ + chuỗi dòng tiền.

    Khác `api` chỉ hỏi có/không: worker cần toàn bộ số liệu để chấm.
    """
    response = httpx.get(f"{SLINK_MOCK_URL}/slink/merchants/{customer_id}", timeout=10.0)
    response.raise_for_status()
    return response.json()


async def process_scoring_job(r: aioredis.Redis, application_id: str) -> None:
    with get_session() as session:
        app_row = session.get(SlinkApplication, application_id)
        if app_row is None:
            print(f"[slink] bỏ qua job: không tìm thấy application {application_id}", flush=True)
            return
        customer_id = app_row.customer_id

        # Giành quyền chấm điểm. Job bị giao lại thấy rowcount = 0 và thoát
        # sạch — không chạy lại engine, không đâm vào UniqueViolation của
        # slink_agent_decisions.
        if not claim_for_scoring(session, application_id):
            print(
                f"[slink] {application_id} đã ở trạng thái {app_row.status} — bỏ qua job giao lại",
                flush=True,
            )
            return

    await _publish(r, application_id, {"phase": "SCORING", "message": "Bắt đầu chấm điểm tự động"})

    try:
        merchant = _fetch_merchant(customer_id)
    except Exception as exc:  # noqa: BLE001 — mọi lỗi đọc đều làm job thất bại
        with get_session() as session:
            failed = session.get(SlinkApplication, application_id)
            failed.status = "FAILED"
            failed.decision_reason = f"không đọc được dữ liệu SLINK: {exc}"
            failed.decided_at = dt.datetime.now(dt.timezone.utc)
        await _publish(r, application_id, {"phase": "FAILED", "message": str(exc)})
        return

    outcome = score_merchant(merchant)

    with get_session() as session:
        app_row = session.get(SlinkApplication, application_id)

        for seq, decision in enumerate(outcome.decisions, start=1):
            session.add(
                SlinkAgentDecision(
                    slink_application_id=application_id,
                    agent_id=decision.agent_id,
                    summary=decision.summary,
                    rationale=decision.rationale,
                    metrics=decision.metrics,
                    seq=seq,
                )
            )

        app_row.status = outcome.status
        app_row.recommended_limit_vnd = outcome.recommended_limit_vnd
        app_row.interest_rate_pct = outcome.interest_rate_pct
        app_row.decision_reason = outcome.reason
        app_row.decided_at = dt.datetime.now(dt.timezone.utc)

    # Publish từng agent sau khi đã ghi xong, để client mở SSE muộn vẫn đọc
    # được trạng thái cuối qua GET /slink/applications/{id}.
    for decision in outcome.decisions:
        await _publish(
            r,
            application_id,
            {"phase": "AGENT", "agent_id": decision.agent_id, "summary": decision.summary},
        )

    if outcome.status != APPROVED:
        await _publish(
            r,
            application_id,
            {"phase": outcome.status, "message": outcome.reason},
        )
        print(f"[slink] {application_id} -> {outcome.status}", flush=True)
        return

    await _run_operations(
        r,
        application_id=application_id,
        customer_id=customer_id,
        limit_vnd=outcome.recommended_limit_vnd,
        rate_pct=outcome.interest_rate_pct,
    )


async def _run_operations(
    r: aioredis.Redis, *, application_id: str, customer_id: str, limit_vnd: int, rate_pct: float
) -> None:
    """Biến khuyến nghị thành hạn mức thật.

    Agent thứ sáu và là agent duy nhất hành động. Chạy trong cùng job chấm
    điểm chứ không tách job riêng: tách ra thì lại phải chống mất job giữa
    hai chặng, mà chẳng được gì.
    """
    with get_session() as session:
        if not claim_for_issuing(session, application_id):
            # Thua cuộc đua (job bị giao lại) — thoát ngay, KHÔNG gọi
            # core-banking. Đây là chỗ chống cấp hạn mức hai lần.
            print(f"[slink] {application_id} đã được xử lý bởi lượt khác — bỏ qua", flush=True)
            return

    await _publish(r, application_id, {"phase": "ISSUING", "message": "Đang cấp hạn mức qua core-banking"})

    try:
        response = issue_overdraft(customer_id, limit_vnd, rate_pct, reason="ACAS-SLINK tự động phê duyệt")
    except CoreBankingError as exc:
        with get_session() as session:
            record_event(
                session,
                customer_id=customer_id,
                application_id=application_id,
                action="ISSUE",
                limit_before=None,
                limit_after=None,
                rate_pct=rate_pct,
                reason=str(exc),
                succeeded=False,
                response={},
            )
            mark_issue_failed(session, application_id, str(exc))
        await _publish(r, application_id, {"phase": "ISSUE_FAILED", "message": str(exc)})
        print(f"[slink] {application_id} -> ISSUE_FAILED: {exc}", flush=True)
        return

    summary = operations_summary(limit_vnd, rate_pct)
    with get_session() as session:
        record_event(
            session,
            customer_id=customer_id,
            application_id=application_id,
            action="ISSUE",
            limit_before=None,
            limit_after=limit_vnd,
            rate_pct=rate_pct,
            reason="ACAS-SLINK tự động phê duyệt",
            succeeded=True,
            response=response,
        )
        session.add(
            SlinkAgentDecision(
                slink_application_id=application_id,
                agent_id="operations",
                summary=summary,
                rationale=[
                    summary,
                    f"Trạng thái tài khoản sau khi cấp: {response.get('status')}.",
                    f"Hạn mức khả dụng: {response.get('available_vnd')}.",
                ],
                metrics={"limit_vnd": limit_vnd, "interest_rate_pct": rate_pct},
                seq=6,
            )
        )
        mark_issued(session, application_id)

    await _publish(
        r,
        application_id,
        {
            "phase": "ISSUED",
            "message": summary,
            "recommended_limit_vnd": limit_vnd,
            "interest_rate_pct": rate_pct,
        },
    )
    print(f"[slink] {application_id} -> ISSUED {limit_vnd}", flush=True)
