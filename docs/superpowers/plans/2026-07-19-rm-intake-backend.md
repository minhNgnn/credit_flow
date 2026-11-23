# RM Intake Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho RM nộp hồ sơ vay qua API — tạo case, upload tài liệu lên MinIO, xem checklist giấy tờ, nộp sang thẩm định.

**Architecture:** Router mới `api/app/routers/intake.py` (phía ghi), tách khỏi `cases.py` (phía đọc, đã >350 dòng). Bốn endpoint dùng lại nguyên vẹn hạ tầng có sẵn: `upload_bytes()`, `transition_state()`, `emit_event()`, `REQUIRED_DOC_TYPES`. Không migration, không đụng frontend.

**Tech Stack:** FastAPI 0.115.6, SQLAlchemy 2.0.36, Postgres 16, MinIO, pytest + httpx (thêm mới).

## Global Constraints

- **Không đụng `web/` hay `src/`.** Frontend do nhóm khác làm; lát này là backend thuần.
- **Không migration.** Chỉ ghi vào `cases` và `documents`, cả hai đã đủ cột.
- **`doc_type` do RM gửi lên**, không phân loại tự động — phân loại là lát 2.
- **Ghi MinIO trước, Postgres sau.** Không bao giờ có row `documents` trỏ tới object không tồn tại.
- **`minio_key` = `{case_id}/{document_id}/{filename}`** — có `document_id` nên không ghi đè (FR-02).
- `REQUIRED_DOC_TYPES` = `financial_statement`, `tax_filing`, `valuation_certificate`, `business_registration` — import từ `shared/constants.py:10`, **không** hardcode lại.
- Whitelist kiểu file: `application/pdf`, `image/png`, `image/jpeg`. Giới hạn 20 MB.
- Mọi chuyển state đi qua `transition_state()` — không `UPDATE cases SET state` trực tiếp.

## ⚠️ Hazard: test phải chạy trên DB riêng

Test cô lập bằng cách truncate `documents` / `events` / `cases` giữa các test. **Chạy trên DB dev sẽ xoá sạch C06, C07, C08 và toàn bộ findings đã seed** — đúng bộ data demo mà cả dự án tồn tại vì nó.

Task 1 dựng DB riêng `shbexpert_test`. Mọi task sau đều chạy test trên DB đó. Không có bước nào trong plan này được chạy pytest với `DATABASE_URL` trỏ vào `shbexpert`.

`shared/db.py:26` tạo engine ở module level theo `DATABASE_URL` **lúc import**, và `get_session()` là `@contextmanager` thuần chứ không phải FastAPI `Depends` — nên không override được per-test. Cách duy nhất là set env var **trước khi import app**, đúng như `conftest.py` ở Task 1 làm.

## Điều kiện tiên quyết cho mọi bước chạy test

```bash
docker compose up -d postgres minio      # services phải sống
```

Nếu bỏ qua, test fail vì connection-refused chứ không phải vì lý do bạn muốn thấy.

---

### Task 1: Dựng test harness + đăng ký router

**Files:**
- Modify: `api/requirements.txt`
- Create: `tests/conftest.py`
- Create: `tests/test_harness.py`
- Create: `api/app/routers/intake.py`
- Modify: `api/app/main.py:17-21`

**Interfaces:**
- Consumes: `shared.db.engine`, `app.main.app`
- Produces: fixture `client` (httpx client đã trỏ vào app), fixture `clean_db` (truncate trước mỗi test), `intake.router` (APIRouter rỗng, prefix `/cases`)

- [ ] **Step 1: Thêm test deps**

Sửa `api/requirements.txt`, thêm 2 dòng cuối file:

```
pytest==8.3.4
pytest-asyncio==0.25.0
```

`httpx==0.28.1` đã có sẵn trong file — không thêm lại.

- [ ] **Step 2: Tạo DB test và chạy migration**

```bash
docker compose up -d postgres minio
docker compose exec -T postgres psql -U shbuser -d postgres -c "CREATE DATABASE shbexpert_test OWNER shbuser;"
DATABASE_URL="postgresql+psycopg2://shbuser:shbpass@localhost:5432/shbexpert_test" \
ADMIN_DATABASE_URL="postgresql+psycopg2://shbuser:shbpass@localhost:5432/shbexpert_test" \
  alembic -c api/alembic.ini upgrade head
```

Expected: `Running upgrade ... -> 0008_chat_domain`, không lỗi.

Nếu `CREATE DATABASE` báo `already exists` thì bỏ qua, đi tiếp.

- [ ] **Step 3: Viết conftest**

Tạo `tests/conftest.py`:

```python
"""Test harness — chạy trên Postgres + MinIO thật qua docker compose.

DATABASE_URL phải set TRƯỚC khi import bất cứ thứ gì chạm shared.db:
shared/db.py:26 tạo engine ở module level lúc import, và get_session()
là contextmanager thuần chứ không phải FastAPI Depends nên không
override được per-test.

DB riêng shbexpert_test là bắt buộc, không phải cho gọn: fixture
clean_db truncate cases/documents/events, chạy nhầm trên shbexpert sẽ
xoá C06/C07/C08 và findings đã seed.
"""
from __future__ import annotations

import os

TEST_DB_URL = "postgresql+psycopg2://shbuser:shbpass@localhost:5432/shbexpert_test"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin123")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from shared.db import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _guard_test_db() -> None:
    """Chặn cứng việc chạy test nhầm vào DB dev."""
    assert engine.url.database == "shbexpert_test", (
        f"test phải chạy trên shbexpert_test, đang trỏ vào {engine.url.database!r} "
        "— truncate trên DB dev sẽ xoá data demo"
    )


@pytest.fixture()
def clean_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE events, documents, cases CASCADE"))


@pytest.fixture()
def client(clean_db: None) -> TestClient:
    from app.main import app

    return TestClient(app)
```

- [ ] **Step 4: Viết test harness (sẽ fail)**

Tạo `tests/test_harness.py`:

```python
def test_health_endpoint_reachable(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_app_boots_with_intake_router(client):
    """App import và khởi động được sau khi mount intake.router.

    GET /cases là endpoint có sẵn của cases.router — dùng nó vì
    intake.router ở Task 1 còn rỗng, chưa có route nào để gọi. Test này
    chỉ chứng minh việc thêm include_router không làm app sập lúc import
    (trùng prefix, lỗi cú pháp, import vòng).
    """
    response = client.get("/cases")
    assert response.status_code == 200
```

- [ ] **Step 5: Chạy test, xác nhận fail**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_harness.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.routers.intake'` sau khi Step 6 sửa main.py, hoặc lỗi Redis ở `/health` nếu redis chưa chạy (nếu vậy: `docker compose up -d redis`).

- [ ] **Step 6: Tạo router rỗng + đăng ký**

Tạo `api/app/routers/intake.py`:

```python
"""Tiếp nhận hồ sơ RM — phía GHI của case (tạo case, upload tài liệu,
nộp thẩm định). Tách khỏi cases.py vì file đó đã hơn 350 dòng và thuần
phía đọc.

Spec: docs/superpowers/specs/2026-07-19-rm-intake-backend-design.md
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/cases", tags=["intake"])
```

Sửa `api/app/main.py` dòng 17 và 21:

```python
from app.routers import cases, chat, intake, internal, memo

app = FastAPI(title="SHBExpert Flow API")
app.include_router(cases.router)
app.include_router(chat.router)
app.include_router(memo.router)
app.include_router(internal.router)
app.include_router(intake.router)
```

- [ ] **Step 7: Chạy test, xác nhận pass**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_harness.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add api/requirements.txt tests/conftest.py tests/test_harness.py api/app/routers/intake.py api/app/main.py
git commit -m "test: dựng harness integration test trên DB riêng + router intake rỗng

Repo chưa từng có test nào. Harness chạy trên Postgres + MinIO thật qua
docker compose, DB riêng shbexpert_test — fixture clean_db truncate
cases/documents/events nên chạy nhầm vào shbexpert sẽ xoá C06/C07/C08.
Fixture _guard_test_db chặn cứng việc đó.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `POST /cases` — tạo case ở DRAFT

**Files:**
- Modify: `api/app/routers/intake.py`
- Create: `tests/test_intake_create_case.py`

**Interfaces:**
- Consumes: `router` (Task 1), `shared.db.get_session`, `shared.models.Case`, `shared.state.emit_event`, `shared.schemas.Actor`
- Produces: `POST /cases` trả `{"case_id": str, "state": "DRAFT"}` với status 201; helper `_next_case_id(session) -> str`

- [ ] **Step 1: Viết test (sẽ fail)**

Tạo `tests/test_intake_create_case.py`:

```python
from shared.db import get_session
from shared.models import Case, Event

PAYLOAD = {
    "customer_id": "CUST-NTE",
    "product": "SME_WC",
    "requested_facility": {"amount_vnd": 8_000_000_000, "tenor_months": 12},
    "owner": "rm1",
}


def test_creates_case_in_draft(client):
    response = client.post("/cases", json=PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "DRAFT"
    assert body["case_id"].startswith("C")

    with get_session() as session:
        row = session.get(Case, body["case_id"])
        assert row is not None
        assert row.customer_id == "CUST-NTE"
        assert row.state == "DRAFT"
        assert row.requested_facility["amount_vnd"] == 8_000_000_000


def test_emits_audit_event(client):
    case_id = client.post("/cases", json=PAYLOAD).json()["case_id"]

    with get_session() as session:
        events = session.query(Event).filter(Event.case_id == case_id).all()
        assert len(events) == 1
        assert events[0].event_type == "CASE_CREATED"


def test_case_ids_do_not_collide(client):
    first = client.post("/cases", json=PAYLOAD).json()["case_id"]
    second = client.post("/cases", json=PAYLOAD).json()["case_id"]
    assert first != second


def test_rejects_missing_customer_id(client):
    response = client.post("/cases", json={k: v for k, v in PAYLOAD.items() if k != "customer_id"})
    assert response.status_code == 422
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_create_case.py -v
```

Expected: FAIL — 4 test lỗi `405 Method Not Allowed` (router có prefix `/cases` nhưng chưa có POST).

- [ ] **Step 3: Implement**

Thêm vào `api/app/routers/intake.py`:

```python
import re

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from shared.db import get_session
from shared.models import Case
from shared.schemas import Actor
from shared.state import emit_event

_CASE_ID_PATTERN = re.compile(r"^C(\d+)$")


class CreateCaseRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    product: str = Field(min_length=1)
    requested_facility: dict = Field(default_factory=dict)
    owner: str = Field(min_length=1)


def _next_case_id(session) -> str:
    """Sinh case_id kiểu C09 nối tiếp số lớn nhất đang có.

    Case.case_id là primary key String KHÔNG có default (shared/models.py:56)
    — khác Document.document_id vốn có default=_uuid — nên tới giờ mọi
    case_id đều do script seed đặt tay. Server phải tự sinh.

    Advisory lock để hai request đồng thời không ra trùng số, cùng cơ chế
    emit_event dùng cho Event.seq (shared/state.py:212). Khoá theo hằng
    chuỗi 'case_id_seq' vì đây là bộ đếm toàn cục, không theo từng case.
    """
    session.execute(text("SELECT pg_advisory_xact_lock(hashtext('case_id_seq'))"))

    existing = session.execute(select(Case.case_id)).scalars().all()
    numbers = [int(m.group(1)) for cid in existing if (m := _CASE_ID_PATTERN.match(cid))]
    return f"C{max(numbers, default=0) + 1:02d}"


@router.post("", status_code=201)
def create_case(body: CreateCaseRequest) -> dict:
    with get_session() as session:
        case_id = _next_case_id(session)
        session.add(
            Case(
                case_id=case_id,
                customer_id=body.customer_id,
                product=body.product,
                requested_facility=body.requested_facility,
                owner=body.owner,
                state="DRAFT",
                version=1,
            )
        )
        session.flush()

        emit_event(
            session,
            case_id=case_id,
            event_type="CASE_CREATED",
            actor=Actor(type="USER", id=body.owner),
            payload={"customer_id": body.customer_id, "product": body.product},
        )

        return {"case_id": case_id, "state": "DRAFT"}
```

- [ ] **Step 4: Chạy test, xác nhận pass**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_create_case.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/intake.py tests/test_intake_create_case.py
git commit -m "feat(intake): POST /cases tạo hồ sơ ở DRAFT

case_id do server sinh theo khuôn C{nn} nối tiếp, dưới advisory lock —
Case.case_id là primary key không có default nên tới giờ chỉ script seed
đặt tay.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `POST /cases/{case_id}/documents` — upload tài liệu

**Files:**
- Modify: `api/app/routers/intake.py`
- Create: `tests/test_intake_upload.py`

**Interfaces:**
- Consumes: `create_case` (Task 2), `shared.storage.upload_bytes`, `shared.constants.REQUIRED_DOC_TYPES`, `shared.models.Document`
- Produces: `POST /cases/{case_id}/documents` trả `{"document_id": str, "sha256": str, "doc_type": str, "deduplicated": bool}` status 201

- [ ] **Step 1: Viết test (sẽ fail)**

Tạo `tests/test_intake_upload.py`:

```python
import pytest

from shared.db import get_session
from shared.models import Document

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


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


def _upload(client, case_id, *, doc_type="financial_statement", content=PDF_BYTES, filename="bctc.pdf", mime="application/pdf"):
    return client.post(
        f"/cases/{case_id}/documents",
        files={"file": (filename, content, mime)},
        data={"doc_type": doc_type},
    )


def test_uploads_document(client, case_id):
    response = _upload(client, case_id)

    assert response.status_code == 201
    body = response.json()
    assert body["doc_type"] == "financial_statement"
    assert body["deduplicated"] is False
    assert len(body["sha256"]) == 64

    with get_session() as session:
        row = session.get(Document, body["document_id"])
        assert row.case_id == case_id
        assert row.review_status == "PENDING"
        assert row.minio_key == f"{case_id}/{body['document_id']}/bctc.pdf"


def test_same_file_twice_is_deduplicated(client, case_id):
    """Chống trùng là kiểm tra ở tầng ứng dụng (đọc rồi mới ghi), KHÔNG
    phải ràng buộc DB — model Document không có unique constraint nào.
    Test này kiểm logic truy vấn; dưới tải đồng thời thật vẫn có thể lọt
    hai bản ghi. Chấp nhận được ở quy mô dự án này."""
    first = _upload(client, case_id).json()
    second = _upload(client, case_id).json()

    assert second["deduplicated"] is True
    assert second["document_id"] == first["document_id"]

    with get_session() as session:
        assert session.query(Document).filter(Document.case_id == case_id).count() == 1


def test_different_content_creates_new_row(client, case_id):
    _upload(client, case_id)
    second = _upload(client, case_id, content=PDF_BYTES + b"khac\n")

    assert second.json()["deduplicated"] is False
    with get_session() as session:
        assert session.query(Document).filter(Document.case_id == case_id).count() == 2


def test_rejects_unknown_doc_type(client, case_id):
    response = _upload(client, case_id, doc_type="giay_lung_tung")
    assert response.status_code == 422


def test_rejects_disallowed_mime(client, case_id):
    response = _upload(client, case_id, content=b"MZ\x90", filename="virus.exe", mime="application/x-msdownload")
    assert response.status_code == 422


def test_rejects_oversized_file(client, case_id):
    response = _upload(client, case_id, content=b"x" * (20 * 1024 * 1024 + 1))
    assert response.status_code == 422


def test_unknown_case_returns_404(client):
    response = _upload(client, "C99")
    assert response.status_code == 404
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_upload.py -v
```

Expected: FAIL — 7 test lỗi `405 Method Not Allowed`.

- [ ] **Step 3: Implement**

Thêm vào `api/app/routers/intake.py` (bổ sung import ở đầu file):

```python
import hashlib

from fastapi import File, Form, UploadFile

from shared.constants import REQUIRED_DOC_TYPES
from shared.models import Document
from shared.storage import upload_bytes

ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/{case_id}/documents", status_code=201)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
) -> dict:
    if doc_type not in REQUIRED_DOC_TYPES:
        raise HTTPException(422, f"doc_type không hợp lệ: {doc_type!r} (hợp lệ: {sorted(REQUIRED_DOC_TYPES)})")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(422, f"kiểu file không được chấp nhận: {file.content_type!r}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(422, f"file quá lớn: {len(content)} bytes (tối đa {MAX_UPLOAD_BYTES})")

    digest = hashlib.sha256(content).hexdigest()

    with get_session() as session:
        if session.get(Case, case_id) is None:
            raise HTTPException(404, f"case {case_id!r} không tồn tại")

        existing = session.execute(
            select(Document).where(Document.case_id == case_id, Document.sha256 == digest)
        ).scalar_one_or_none()
        if existing is not None:
            return {
                "document_id": existing.document_id,
                "sha256": existing.sha256,
                "doc_type": existing.doc_type,
                "deduplicated": True,
            }

        row = Document(
            case_id=case_id,
            doc_type=doc_type,
            minio_key="",  # điền sau khi có document_id — xem chú thích dưới
            sha256=digest,
            review_status="PENDING",
        )
        session.add(row)
        session.flush()  # sinh document_id

        # minio_key cần document_id nên chỉ dựng được sau flush. Ghi MinIO
        # TRƯỚC khi commit: nếu MinIO hỏng thì exception thoát khỏi
        # get_session(), session rollback, không còn row documents mồ côi
        # trỏ tới object không tồn tại.
        key = f"{case_id}/{row.document_id}/{file.filename}"
        try:
            upload_bytes(key=key, data=content, content_type=file.content_type)
        except Exception as exc:  # noqa: BLE001 - mọi lỗi MinIO đều là 502
            raise HTTPException(502, f"ghi MinIO thất bại: {exc}") from exc

        row.minio_key = key
        session.flush()

        return {
            "document_id": row.document_id,
            "sha256": digest,
            "doc_type": doc_type,
            "deduplicated": False,
        }
```

- [ ] **Step 4: Chạy test, xác nhận pass**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_upload.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/intake.py tests/test_intake_upload.py
git commit -m "feat(intake): POST /cases/{id}/documents upload tài liệu lên MinIO

minio_key gồm document_id nên nộp lại cùng loại giấy tờ tạo bản ghi mới,
không đè bản cũ (FR-02). Chống trùng theo (case_id, sha256) ở tầng ứng
dụng — model Document không có unique constraint.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `GET /cases/{case_id}/intake-status` — checklist giấy tờ

**Files:**
- Modify: `api/app/routers/intake.py`
- Create: `tests/test_intake_status.py`

**Interfaces:**
- Consumes: `upload_document` (Task 3), `shared.state.ALLOWED_TRANSITIONS`
- Produces: `GET /cases/{case_id}/intake-status` trả `{"state": str, "submitted": list[dict], "missing": list[str], "can_submit": bool}`

- [ ] **Step 1: Viết test (sẽ fail)**

Tạo `tests/test_intake_status.py`:

```python
import pytest

from shared.constants import REQUIRED_DOC_TYPES

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


def _upload(client, case_id, doc_type, content):
    return client.post(
        f"/cases/{case_id}/documents",
        files={"file": (f"{doc_type}.pdf", content, "application/pdf")},
        data={"doc_type": doc_type},
    )


def test_empty_case_misses_everything(client, case_id):
    body = client.get(f"/cases/{case_id}/intake-status").json()

    assert body["state"] == "DRAFT"
    assert body["submitted"] == []
    assert sorted(body["missing"]) == sorted(REQUIRED_DOC_TYPES)
    assert len(body["missing"]) == 4


def test_partial_upload_splits_submitted_and_missing(client, case_id):
    _upload(client, case_id, "financial_statement", PDF_BYTES + b"a")
    _upload(client, case_id, "tax_filing", PDF_BYTES + b"b")

    body = client.get(f"/cases/{case_id}/intake-status").json()

    assert sorted(d["doc_type"] for d in body["submitted"]) == ["financial_statement", "tax_filing"]
    assert sorted(body["missing"]) == ["business_registration", "valuation_certificate"]
    assert len(body["submitted"]) + len(body["missing"]) == 4


def test_can_submit_true_in_draft_even_when_incomplete(client, case_id):
    """can_submit phản ánh ALLOWED_TRANSITIONS, KHÔNG phản ánh checklist.
    RM vẫn nộp được hồ sơ thiếu; INTAKE_VALIDATION sẽ trả về NEED_INFO.
    Gate checklist thuộc lát 3."""
    body = client.get(f"/cases/{case_id}/intake-status").json()

    assert body["missing"], "case rỗng thì phải còn thiếu giấy tờ"
    assert body["can_submit"] is True


def test_submitted_entries_carry_document_id(client, case_id):
    uploaded = _upload(client, case_id, "financial_statement", PDF_BYTES).json()

    body = client.get(f"/cases/{case_id}/intake-status").json()

    assert body["submitted"][0]["document_id"] == uploaded["document_id"]
    assert body["submitted"][0]["uploaded_at"]


def test_unknown_case_returns_404(client):
    assert client.get("/cases/C99/intake-status").status_code == 404
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_status.py -v
```

Expected: FAIL — 5 test lỗi 404 vì route chưa tồn tại.

- [ ] **Step 3: Implement**

Thêm vào `api/app/routers/intake.py` (bổ sung import `ALLOWED_TRANSITIONS`):

```python
from shared.state import ALLOWED_TRANSITIONS


@router.get("/{case_id}/intake-status")
def intake_status(case_id: str) -> dict:
    """Checklist giấy tờ cho trang RM.

    Endpoint này tồn tại để frontend không phải nhân bản REQUIRED_DOC_TYPES
    ở phía client — giữ hằng số single-sourced trong shared/constants.py
    đúng như lý do file đó tồn tại.
    """
    with get_session() as session:
        case = session.get(Case, case_id)
        if case is None:
            raise HTTPException(404, f"case {case_id!r} không tồn tại")

        docs = session.execute(select(Document).where(Document.case_id == case_id)).scalars().all()

        submitted = [
            {
                "doc_type": d.doc_type,
                "document_id": d.document_id,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in docs
        ]

        return {
            "state": case.state,
            "submitted": submitted,
            "missing": sorted(REQUIRED_DOC_TYPES - {d.doc_type for d in docs}),
            # can_submit theo state machine, KHÔNG theo checklist đủ/thiếu —
            # gate checklist thuộc lát 3.
            "can_submit": "INTAKE_VALIDATION" in ALLOWED_TRANSITIONS.get(case.state, set()),
        }
```

- [ ] **Step 4: Chạy test, xác nhận pass**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_status.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/intake.py tests/test_intake_status.py
git commit -m "feat(intake): GET /cases/{id}/intake-status trả checklist giấy tờ

can_submit phản ánh ALLOWED_TRANSITIONS chứ không phải checklist đủ hay
thiếu — RM vẫn nộp được hồ sơ thiếu, INTAKE_VALIDATION sẽ trả NEED_INFO.
Gate checklist thuộc lát 3.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `POST /cases/{case_id}/submit` — nộp thẩm định

**Files:**
- Modify: `api/app/routers/intake.py`
- Create: `tests/test_intake_submit.py`

**Interfaces:**
- Consumes: `shared.state.transition_state`, `shared.state.InvalidTransitionError`
- Produces: `POST /cases/{case_id}/submit` trả `{"case_id": str, "state": "INTAKE_VALIDATION"}` status 200

- [ ] **Step 1: Viết test (sẽ fail)**

Tạo `tests/test_intake_submit.py`:

```python
import pytest

from shared.db import get_session
from shared.models import Event
from shared.schemas import Actor
from shared.state import transition_state


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


def test_submit_from_draft(client, case_id):
    response = client.post(f"/cases/{case_id}/submit")

    assert response.status_code == 200
    assert response.json()["state"] == "INTAKE_VALIDATION"


def test_submit_emits_event(client, case_id):
    client.post(f"/cases/{case_id}/submit")

    with get_session() as session:
        types = [e.event_type for e in session.query(Event).filter(Event.case_id == case_id).all()]
        assert "STATE_CHANGED" in types


def test_submit_twice_returns_409(client, case_id):
    client.post(f"/cases/{case_id}/submit")
    response = client.post(f"/cases/{case_id}/submit")

    assert response.status_code == 409
    assert "INTAKE_VALIDATION" in response.json()["detail"]


def test_submit_from_need_info(client, case_id):
    """Một endpoint phục vụ cả nộp mới lẫn bổ sung — ALLOWED_TRANSITIONS
    đã dựng sẵn DRAFT→INTAKE_VALIDATION và NEED_INFO→INTAKE_VALIDATION."""
    client.post(f"/cases/{case_id}/submit")
    with get_session() as session:
        transition_state(
            session, case_id=case_id, new_state="NEED_INFO", actor=Actor(type="SYSTEM", id="test")
        )

    response = client.post(f"/cases/{case_id}/submit")

    assert response.status_code == 200
    assert response.json()["state"] == "INTAKE_VALIDATION"


def test_unknown_case_returns_404(client):
    assert client.post("/cases/C99/submit").status_code == 404
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_submit.py -v
```

Expected: FAIL — 5 test lỗi 405/404 vì route chưa tồn tại.

- [ ] **Step 3: Implement**

Thêm vào `api/app/routers/intake.py` (bổ sung import `InvalidTransitionError`, `transition_state`):

```python
from shared.state import InvalidTransitionError, transition_state


@router.post("/{case_id}/submit")
def submit_case(case_id: str) -> dict:
    """Nộp hồ sơ sang thẩm định.

    Chạy được từ cả DRAFT lẫn NEED_INFO nên một endpoint phục vụ cả nộp
    mới lẫn bổ sung — ALLOWED_TRANSITIONS đã dựng sẵn cả hai.
    """
    with get_session() as session:
        case = session.get(Case, case_id)
        if case is None:
            raise HTTPException(404, f"case {case_id!r} không tồn tại")

        try:
            updated = transition_state(
                session,
                case_id=case_id,
                new_state="INTAKE_VALIDATION",
                actor=Actor(type="USER", id=case.owner),
            )
        except InvalidTransitionError as exc:
            raise HTTPException(409, str(exc)) from exc

        return {"case_id": case_id, "state": updated.state}
```

- [ ] **Step 4: Chạy test, xác nhận pass**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_submit.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add api/app/routers/intake.py tests/test_intake_submit.py
git commit -m "feat(intake): POST /cases/{id}/submit chuyển sang INTAKE_VALIDATION

Một endpoint phục vụ cả nộp mới (DRAFT) lẫn bổ sung (NEED_INFO).
InvalidTransitionError -> 409 kèm state hiện tại.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Fault injection — MinIO hỏng không được để lại row mồ côi

**Files:**
- Create: `tests/test_intake_minio_failure.py`

**Interfaces:**
- Consumes: `upload_document` (Task 3)
- Produces: không có code mới — task này chứng minh bất biến của Task 3

Đây là test quan trọng nhất của lát 1 và cũng là test dễ bị bỏ qua nhất. Nó chứng minh bất biến "ghi MinIO trước, Postgres sau": khi MinIO hỏng, API trả 502 **và** không để lại row `documents` nào trỏ tới object không tồn tại.

- [ ] **Step 1: Viết test (sẽ fail nếu bất biến sai)**

Tạo `tests/test_intake_minio_failure.py`:

```python
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


def test_case_still_usable_after_failed_upload(client, case_id, monkeypatch):
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

    retry = client.post(
        f"/cases/{case_id}/documents",
        files={"file": ("bctc.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type": "financial_statement"},
    )

    assert retry.status_code == 201
    assert retry.json()["deduplicated"] is False
```

- [ ] **Step 2: Chạy test**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/test_intake_minio_failure.py -v
```

Expected: 2 passed. Nếu `test_minio_failure_returns_502_and_leaves_no_row` fail với "còn 1 row documents mồ côi", nghĩa là Task 3 đã commit session trước khi gọi `upload_bytes` — sửa Task 3 để `upload_bytes` nằm **trong** khối `with get_session()` và trước khi thoát khối.

- [ ] **Step 3: Chạy toàn bộ test suite**

```bash
cd /home/son/AIC/dashmint_ai && PYTHONPATH=api:. pytest tests/ -v
```

Expected: 25 passed (2 harness + 4 create + 7 upload + 5 status + 5 submit + 2 fault injection).

- [ ] **Step 4: Commit**

```bash
git add tests/test_intake_minio_failure.py
git commit -m "test(intake): chứng minh MinIO hỏng không để lại row documents mồ côi

Bất biến ghi MinIO trước / Postgres sau (spec §5). Test dễ bị bỏ qua
nhất nhưng là test quan trọng nhất của lát 1.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Kiểm chứng end-to-end thủ công

**Files:** không sửa file nào — task này chạy đúng §8 của spec trên máy thật.

Test suite chạy qua `TestClient` in-process. Task này chứng minh hệ thống hoạt động qua HTTP thật, trên DB dev, với MinIO thật — thứ test suite không phủ.

- [ ] **Step 1: Dựng hệ thống**

```bash
docker compose up -d
docker compose ps
```

Expected: postgres, minio, redis, api đều `healthy` hoặc `running`.

- [ ] **Step 2: Tạo case**

```bash
curl -sS -X POST localhost:8000/cases -H 'Content-Type: application/json' -d '{
  "customer_id": "CUST-NTE", "product": "SME_WC",
  "requested_facility": {"amount_vnd": 8000000000, "tenor_months": 12}, "owner": "rm1"
}' | tee /tmp/case.json
```

Expected: `{"case_id":"C09","state":"DRAFT"}` (số có thể khác tuỳ data sẵn có).

- [ ] **Step 3: Upload 2 tài liệu khác loại**

Sinh hai file **khác nội dung** — chống trùng theo `(case_id, sha256)` không xét `doc_type`, nên nộp cùng một file hai lần sẽ ra `deduplicated: true` và chỉ có một row:

```bash
CASE=$(python3 -c "import json;print(json.load(open('/tmp/case.json'))['case_id'])")
printf '%%PDF-1.4\nbctc\n%%%%EOF\n' > /tmp/bctc.pdf
printf '%%PDF-1.4\nthue\n%%%%EOF\n' > /tmp/thue.pdf

curl -sS -X POST localhost:8000/cases/$CASE/documents \
  -F 'file=@/tmp/bctc.pdf;type=application/pdf' -F 'doc_type=financial_statement'
curl -sS -X POST localhost:8000/cases/$CASE/documents \
  -F 'file=@/tmp/thue.pdf;type=application/pdf' -F 'doc_type=tax_filing'
```

Expected: hai response 201, `sha256` khác nhau, cả hai `"deduplicated": false`.

Kiểm luôn chống trùng — nộp lại đúng file đầu:

```bash
curl -sS -X POST localhost:8000/cases/$CASE/documents \
  -F 'file=@/tmp/bctc.pdf;type=application/pdf' -F 'doc_type=financial_statement'
```

Expected: `"deduplicated": true`, `document_id` trùng với lần đầu.

- [ ] **Step 4: Xem checklist**

```bash
curl -sS localhost:8000/cases/$CASE/intake-status | python3 -m json.tool
```

Expected: `submitted` có các loại đã nộp, `missing` chứa phần còn lại, tổng đúng 4, `can_submit: true`.

- [ ] **Step 5: Kiểm chứng MinIO thật sự có object**

```bash
docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin123 2>/dev/null || true
docker compose exec -T minio mc ls --recursive local/ | grep $CASE
```

Expected: mỗi document một object, key dạng `{case_id}/{document_id}/{filename}`.

- [ ] **Step 6: Nộp và kiểm 409**

```bash
curl -sS -X POST localhost:8000/cases/$CASE/submit
curl -sS -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/cases/$CASE/submit
```

Expected: lần đầu `{"state":"INTAKE_VALIDATION"}`, lần hai `409`.

- [ ] **Step 7: Case hiện trong hàng đợi**

```bash
curl -sS localhost:8000/cases | python3 -c "import json,sys;print([c['case_id'] for c in json.load(sys.stdin)])"
```

Expected: `$CASE` có trong danh sách.

- [ ] **Step 8: Xác nhận data demo còn nguyên**

```bash
docker compose exec -T postgres psql -U shbuser -d shbexpert -tAc \
  "SELECT case_id, state FROM cases WHERE case_id IN ('C06','C07','C08') ORDER BY case_id;"
```

Expected: cả ba case còn đủ. Nếu thiếu, test đã chạy nhầm vào DB dev — xem lại `tests/conftest.py`.

- [ ] **Step 9: Commit ghi chú kiểm chứng**

```bash
git commit --allow-empty -m "chore: xác nhận lát 1 chạy end-to-end trên docker compose

Đã chạy đủ 8 bước §8 của spec: tạo case, upload, checklist, MinIO có
object thật, submit + 409, case vào hàng đợi, C06/C07/C08 còn nguyên.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Bàn giao cho nhóm frontend

Sau Task 5, hợp đồng API đã đóng băng và nhóm frontend làm song song được. Bốn endpoint:

| Method | Path | Body | Trả về |
|---|---|---|---|
| `POST` | `/cases` | JSON: `customer_id`, `product`, `requested_facility`, `owner` | `{case_id, state}` |
| `POST` | `/cases/{id}/documents` | multipart: `file`, `doc_type` | `{document_id, sha256, doc_type, deduplicated}` |
| `GET` | `/cases/{id}/intake-status` | — | `{state, submitted[], missing[], can_submit}` |
| `POST` | `/cases/{id}/submit` | — | `{case_id, state}` |

`doc_type` hợp lệ: `financial_statement`, `tax_filing`, `valuation_certificate`, `business_registration`. Frontend lấy danh sách còn thiếu từ `missing` của `intake-status`, **không** hardcode lại.

Mã lỗi: `404` case không tồn tại, `409` submit sai state (kèm state hiện tại trong `detail`), `422` doc_type/kiểu file/kích thước sai, `502` MinIO hỏng.
