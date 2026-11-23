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
