"""Ba kết cục của POST /intake/submissions sau khi có luồng xanh.

Spec §3: luật không đạt -> RED; luật đạt nhưng không có merchant -> RED
(hạ luồng); luật đạt và có merchant -> GREEN + xếp hàng chấm điểm.

slink-mock được monkeypatch chứ không gọi thật: test phải chạy được cả khi
container đã tắt, và ta cần dựng được ca "service chết" một cách tất định.
"""
import pytest

from shared.db import get_session
from shared.models import Case, RoutingDecision, SlinkApplication


@pytest.fixture()
def no_enqueue(monkeypatch):
    """Chặn đẩy job lên Redis — test này kiểm ghi DB, không kiểm worker."""
    pushed: list[str] = []

    class _FakeRedis:
        async def lpush(self, _queue, raw):
            import json

            pushed.append(json.loads(raw)["slink_application_id"])

        async def aclose(self):
            pass

    monkeypatch.setattr("app.routers.routing.aioredis.from_url", lambda _url: _FakeRedis())
    return pushed


def _green_payload(customer_id="CUST-SLINK"):
    return {
        "channel": "MOBILE_KHDN",
        "customer_id": customer_id,
        "segment": "MICROSME",
        "product": "MICRO_OD",
        "requested_facility": {"amount_vnd": 150_000_000, "tenor_months": 12},
        "owner": "khdn",
    }


def test_green_when_merchant_exists(client, monkeypatch, no_enqueue):
    monkeypatch.setattr("app.routers.routing.merchant_exists", lambda _cid: True)

    body = client.post("/intake/submissions", json=_green_payload()).json()

    assert body["lane"] == "GREEN"
    assert body["case_id"] is None
    assert body["slink_application_id"] is not None
    assert body["status"] == "QUEUED"
    assert no_enqueue == [body["slink_application_id"]]

    with get_session() as session:
        assert session.query(Case).count() == 0
        app_row = session.get(SlinkApplication, body["slink_application_id"])
        assert app_row.status == "QUEUED"
        assert app_row.amount_requested_vnd == 150_000_000

        decision = session.get(RoutingDecision, body["routing_decision_id"])
        assert decision.slink_application_id == body["slink_application_id"]
        assert decision.case_id is None


def test_downgrades_to_red_when_no_slink_history(client, monkeypatch, no_enqueue):
    """Luật đạt nhưng khách chưa có lịch sử SLINK -> hạ xuống luồng đỏ."""
    monkeypatch.setattr("app.routers.routing.merchant_exists", lambda _cid: False)

    body = client.post("/intake/submissions", json=_green_payload("CUST-MOI")).json()

    assert body["lane"] == "RED"
    assert body["case_id"] is not None
    assert body["slink_application_id"] is None
    assert "chưa có lịch sử giao dịch SLINK" in body["reason"]
    assert no_enqueue == []

    with get_session() as session:
        # Dòng bị hạ luồng phải ghi RED, không phải GREEN kèm cờ phụ —
        # nếu ghi GREEN thì engine luồng xanh sẽ xử lý nhầm hồ sơ này.
        decision = session.get(RoutingDecision, body["routing_decision_id"])
        assert decision.lane == "RED"
        assert session.query(SlinkApplication).count() == 0


def test_slink_unavailable_returns_502_and_creates_nothing(client, monkeypatch, no_enqueue):
    """Service chết -> 502, KHÔNG âm thầm hạ luồng đỏ.

    Âm thầm hạ luồng sẽ làm outage vô hình: hệ thống trông vẫn đúng trong
    khi toàn bộ tự động hoá đã tắt.
    """
    from app.slink_client import SlinkUnavailableError

    def boom(_cid):
        raise SlinkUnavailableError("connection refused")

    monkeypatch.setattr("app.routers.routing.merchant_exists", boom)

    response = client.post("/intake/submissions", json=_green_payload())

    assert response.status_code == 502
    with get_session() as session:
        assert session.query(Case).count() == 0
        assert session.query(RoutingDecision).count() == 0
        assert session.query(SlinkApplication).count() == 0


def test_red_lane_never_consults_slink(client, monkeypatch, no_enqueue):
    """Hồ sơ đã trượt luật thì không được gọi slink-mock — gọi thừa là lỗi."""

    def should_not_be_called(_cid):
        raise AssertionError("luồng đỏ không được hỏi slink-mock")

    monkeypatch.setattr("app.routers.routing.merchant_exists", should_not_be_called)

    body = client.post(
        "/intake/submissions",
        json={
            "channel": "RM_LMS",
            "customer_id": "CUST-NTE",
            "segment": "SME",
            "product": "SME_WC",
            "requested_facility": {"amount_vnd": 800_000_000, "tenor_months": 36},
            "owner": "rm1",
        },
    ).json()

    assert body["lane"] == "RED"
    assert body["slink_application_id"] is None


def test_application_readable_before_scoring(client, monkeypatch, no_enqueue):
    monkeypatch.setattr("app.routers.routing.merchant_exists", lambda _cid: True)
    created = client.post("/intake/submissions", json=_green_payload()).json()

    fetched = client.get(f"/slink/applications/{created['slink_application_id']}").json()

    assert fetched["status"] == "QUEUED"
    assert fetched["recommended_limit_vnd"] is None
    assert fetched["agent_decisions"] == []


def test_unknown_application_returns_404(client):
    assert client.get("/slink/applications/khong-ton-tai").status_code == 404
