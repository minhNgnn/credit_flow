"""Bất biến ghi MinIO trước / Postgres sau — spec §5.

Không bao giờ được tồn tại row documents trỏ tới object không có thật.
Chiều ngược lại (object mồ côi khi DB lỗi) vô hại và dọn được sau.
"""
import pytest

from shared.db import get_session
from shared.models import Document

PDF_BYTES = b"%PDF-1.4\ntest\n%%EOF\n"


@pytest.fixture()
def case_id(client) -> str:
    return client.post(
        "/cases",
        json={
            "customer_id": "CUST-NTE",
            "product": "SME_WC",
            "requested_facility": {"amount_vnd": 1_000_000_000, "tenor_months": 12},
            "owner": "rm1",
        },
    ).json()["case_id"]


def test_minio_failure_returns_502_and_leaves_no_row(client, case_id, monkeypatch):
    def boom(**kwargs):
        raise ConnectionError("MinIO không phản hồi")

    monkeypatch.setattr("app.routers.intake.upload_bytes", boom)

    response = client.post(
        f"/cases/{case_id}/documents",
        files={"file": ("bctc.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type": "financial_statement"},
    )

    assert response.status_code == 502

    with get_session() as session:
        orphans = session.query(Document).filter(Document.case_id == case_id).all()
        assert orphans == [], f"còn {len(orphans)} row documents mồ côi sau khi MinIO hỏng"


def test_case_still_usable_after_failed_upload(client, case_id, monkeypatch, fake_redis):
    """Upload hỏng không được làm hỏng case — RM phải thử lại được."""
    monkeypatch.setattr(
        "app.routers.intake.upload_bytes",
        lambda **kwargs: (_ for _ in ()).throw(ConnectionError("MinIO chết")),
    )
    client.post(
        f"/cases/{case_id}/documents",
        files={"file": ("bctc.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type": "financial_statement"},
    )

    monkeypatch.undo()
    # monkeypatch.undo() xoá TẤT CẢ patch đăng ký qua object monkeypatch
    # này, kể cả patch aioredis của fixture autouse fake_redis (conftest.py)
    # — cùng một `monkeypatch` instance cho cả test. Patch lại trước khi
    # retry, vì lần này upload thành công thật nên sẽ enqueue.
    monkeypatch.setattr("app.routers.intake.aioredis.from_url", lambda _url: fake_redis)

    retry = client.post(
        f"/cases/{case_id}/documents",
        files={"file": ("bctc.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type": "financial_statement"},
    )

    assert retry.status_code == 201
    assert retry.json()["deduplicated"] is False
