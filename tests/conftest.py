"""Test harness — chạy trên Postgres + MinIO thật qua docker compose.

DATABASE_URL phải set TRƯỚC khi import bất cứ thứ gì chạm shared.db:
shared/db.py:26 tạo engine ở module level lúc import, và get_session() là
contextmanager thuần chứ không phải FastAPI Depends nên không override
được per-test.

DB riêng shbexpert_test là bắt buộc, không phải cho gọn: fixture clean_db
truncate cases/documents/events, chạy nhầm trên shbexpert sẽ xoá
C06/C07/C08 và findings đã seed.

Tiền đề: `docker compose up -d postgres minio redis` và DB test đã được
migrate (xem docs/superpowers/plans/2026-07-19-rm-intake-backend.md Task 1).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# `worker` không phải package cài đặt — thêm vào sys.path để test import
# được worker.app.slink.runner mà không phải nhớ nối
# PYTHONPATH thủ công ở mỗi lần chạy.
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT, _REPO_ROOT / "api"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

TEST_DB_URL = "postgresql+psycopg2://shbuser:shbpass@localhost:5432/shbexpert_test"
os.environ["DATABASE_URL"] = TEST_DB_URL
# Tên biến khớp shared/storage.py:14,23,24 — default đã trùng docker-compose.yml,
# set tường minh để test không phụ thuộc .env của máy đang chạy.
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ROOT_USER", "minioadmin")
os.environ.setdefault("MINIO_ROOT_PASSWORD", "minioadmin123")

import json  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from shared.db import engine  # noqa: E402


class FakeRedis:
    """Redis chỉ chạy trên internal Docker network (không publish port ra
    host — xem docker-compose.yml), nên POST /cases/{id}/documents (lát 2:
    enqueue EXTRACTION_QUEUE, api/app/routers/intake.py) không thể gọi
    Redis thật khi test chạy trên host. Autouse toàn session để MỌI test
    gọi tới endpoint đó — không chỉ test_intake_upload.py — đều được mock,
    không phải tự khai báo lại fixture này."""

    def __init__(self) -> None:
        self.pushed: list[tuple[str, dict]] = []

    async def lpush(self, queue: str, raw: str) -> None:
        self.pushed.append((queue, json.loads(raw)))

    async def aclose(self) -> None:
        pass


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("app.routers.intake.aioredis.from_url", lambda _url: fake)
    return fake


@pytest.fixture(scope="session", autouse=True)
def _guard_test_db() -> None:
    """Chặn cứng việc chạy test nhầm vào DB dev."""
    assert engine.url.database == "shbexpert_test", (
        f"test phải chạy trên shbexpert_test, đang trỏ vào {engine.url.database!r} "
        "— truncate trên DB dev sẽ xoá data demo"
    )


@pytest.fixture()
def clean_db() -> None:
    """Dọn sạch mọi bảng test có ghi vào.

    Nêu tên đủ các bảng SLINK chứ không dựa vào CASCADE từ `cases`: chuỗi
    khoá ngoại cases -> routing_decisions -> slink_applications -> ... có
    thật, nhưng dựa vào nó thì một bảng SLINK tương lai không nối vào chuỗi
    đó sẽ âm thầm không được dọn, và test rò dữ liệu sang nhau.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE slink_overdraft_events, slink_agent_decisions, "
                "slink_applications, routing_decisions, events, documents, cases CASCADE"
            )
        )


@pytest.fixture()
def client(clean_db: None) -> TestClient:
    from app.main import app

    return TestClient(app)
