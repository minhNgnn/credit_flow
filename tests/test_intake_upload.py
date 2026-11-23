import pytest

from shared.db import get_session
from shared.models import Document
from shared.queue import EXTRACTION_QUEUE

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


def _upload(
    client,
    case_id,
    *,
    doc_type="financial_statement",
    content=PDF_BYTES,
    filename="bctc.pdf",
    mime="application/pdf",
):
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
    response = _upload(
        client, case_id, content=b"MZ\x90", filename="virus.exe", mime="application/x-msdownload"
    )
    assert response.status_code == 422


def test_rejects_oversized_file(client, case_id):
    response = _upload(client, case_id, content=b"x" * (20 * 1024 * 1024 + 1))
    assert response.status_code == 422


def test_unknown_case_returns_404(client):
    response = _upload(client, "C99")
    assert response.status_code == 404


def test_upload_enqueues_extraction_job(client, case_id, fake_redis):
    response = _upload(client, case_id)
    document_id = response.json()["document_id"]

    assert fake_redis.pushed == [(EXTRACTION_QUEUE, {"document_id": document_id})]


def test_deduplicated_upload_does_not_enqueue_again(client, case_id, fake_redis):
    _upload(client, case_id)
    fake_redis.pushed.clear()

    _upload(client, case_id)  # cùng nội dung -> deduplicated

    assert fake_redis.pushed == []


def test_docx_upload_is_accepted(client, case_id):
    response = _upload(
        client,
        case_id,
        content=b"PK\x03\x04fake-docx-bytes",
        filename="ke_hoach.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 201


def test_xlsx_upload_is_accepted(client, case_id):
    response = _upload(
        client,
        case_id,
        content=b"PK\x03\x04fake-xlsx-bytes",
        filename="bctc.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert response.status_code == 201
