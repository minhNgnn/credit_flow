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
