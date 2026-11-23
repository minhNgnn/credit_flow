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
        # transition_state() phát STATE_TRANSITION (shared/state.py:279),
        # không phải STATE_CHANGED.
        assert types == ["CASE_CREATED", "STATE_TRANSITION"]


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
