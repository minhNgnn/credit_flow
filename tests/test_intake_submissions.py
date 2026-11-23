"""POST /intake/submissions — cửa vào chung, phân luồng ngay khi tiếp nhận.

Kiểm chứng §8 của spec 2026-07-19-intake-routing-design.md.
"""
import json

import pytest

from shared.db import get_session
from shared.models import Case, RoutingDecision


@pytest.fixture(autouse=True)
def _stub_green_lane_deps(monkeypatch):
    """Giả lập slink-mock + Redis cho mọi test trong file này.

    Từ lát (b), nhánh xanh hỏi slink-mock xem khách có lịch sử SLINK không
    rồi đẩy job chấm điểm lên Redis. Hai thứ đó không phải chủ đề của file
    này (nó kiểm LUẬT phân luồng), và từ host thì slink-mock:8400 không tới
    được. Ca "service chết" và ca "không có merchant" nằm ở
    tests/test_slink_intake.py.
    """
    monkeypatch.setattr("app.routers.routing.merchant_exists", lambda _cid: True)

    class _FakeRedis:
        async def lpush(self, _queue, raw):
            json.loads(raw)  # vẫn kiểm payload là JSON hợp lệ

        async def aclose(self):
            pass

    monkeypatch.setattr("app.routers.routing.aioredis.from_url", lambda _url: _FakeRedis())


def _payload(**overrides):
    base = {
        "channel": "RM_LMS",
        "customer_id": "CUST-NTE",
        "segment": "SME",
        "product": "SME_WC",
        "requested_facility": {"amount_vnd": 800_000_000, "tenor_months": 36},
        "owner": "rm1",
    }
    base.update(overrides)
    return base


def _green(**overrides):
    """Hồ sơ đủ điều kiện luồng xanh; override chồng lên để tạo ca lệch."""
    green = {
        "segment": "MICROSME",
        "product": "MICRO_OD",
        "requested_facility": {"amount_vnd": 150_000_000, "tenor_months": 12},
    }
    green.update(overrides)
    return _payload(**green)


def test_green_lane_creates_no_case(client):
    """Điểm cốt lõi: luồng xanh KHÔNG sinh ra case nào."""
    body = client.post("/intake/submissions", json=_green()).json()

    assert body["lane"] == "GREEN"
    assert body["case_id"] is None

    with get_session() as session:
        assert session.query(Case).count() == 0
        decision = session.get(RoutingDecision, body["routing_decision_id"])
        assert decision.lane == "GREEN"
        assert decision.case_id is None
        assert decision.amount_vnd == 150_000_000


def test_red_lane_creates_case_in_draft(client):
    response = client.post("/intake/submissions", json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["lane"] == "RED"
    assert body["case_id"] is not None

    with get_session() as session:
        case = session.get(Case, body["case_id"])
        assert case.state == "DRAFT"
        assert case.product == "SME_WC"

        decision = session.get(RoutingDecision, body["routing_decision_id"])
        assert decision.case_id == body["case_id"]


def test_over_ceiling_falls_to_red(client):
    body = client.post(
        "/intake/submissions",
        json=_green(requested_facility={"amount_vnd": 350_000_000, "tenor_months": 12}),
    ).json()

    assert body["lane"] == "RED"
    assert body["case_id"] is not None
    assert "vượt hạn mức" in body["reason"]


def test_wrong_segment_falls_to_red(client):
    body = client.post("/intake/submissions", json=_green(segment="SME")).json()
    assert body["lane"] == "RED"


def test_exactly_at_ceiling_is_green(client):
    body = client.post(
        "/intake/submissions",
        json=_green(requested_facility={"amount_vnd": 300_000_000, "tenor_months": 12}),
    ).json()
    assert body["lane"] == "GREEN"


def test_mobile_channel_routes_identically(client):
    """Luật không phụ thuộc kênh — KHDN tự khởi tạo cũng ra luồng xanh."""
    body = client.post("/intake/submissions", json=_green(channel="MOBILE_KHDN")).json()

    assert body["lane"] == "GREEN"
    with get_session() as session:
        decision = session.get(RoutingDecision, body["routing_decision_id"])
        assert decision.channel == "MOBILE_KHDN"


def test_red_lane_case_continues_through_slice_1(client):
    """Luồng đỏ phải đi tiếp được toàn bộ đường của lát 1."""
    case_id = client.post("/intake/submissions", json=_payload()).json()["case_id"]

    upload = client.post(
        f"/cases/{case_id}/documents",
        files={"file": ("bctc.pdf", b"%PDF-1.4\ntest\n%%EOF\n", "application/pdf")},
        data={"doc_type": "financial_statement"},
    )
    assert upload.status_code == 201

    status = client.get(f"/cases/{case_id}/intake-status").json()
    assert len(status["submitted"]) == 1
    assert len(status["missing"]) == 3

    submitted = client.post(f"/cases/{case_id}/submit").json()
    assert submitted["state"] == "INTAKE_VALIDATION"


def test_can_read_decision_back(client):
    created = client.post("/intake/submissions", json=_green()).json()

    fetched = client.get(f"/intake/routing-decisions/{created['routing_decision_id']}").json()

    assert fetched["lane"] == "GREEN"
    assert fetched["product"] == "MICRO_OD"
    assert fetched["amount_vnd"] == 150_000_000


def test_unknown_decision_returns_404(client):
    assert client.get("/intake/routing-decisions/khong-ton-tai").status_code == 404


@pytest.mark.parametrize(
    "override",
    [
        {"channel": "FAX"},
        {"segment": "ENTERPRISE"},
        {"product": "KHONG_CO"},
        {"requested_facility": {"amount_vnd": 0, "tenor_months": 12}},
        {"requested_facility": {"amount_vnd": -1, "tenor_months": 12}},
    ],
)
def test_rejects_invalid_input(client, override):
    assert client.post("/intake/submissions", json=_payload(**override)).status_code == 422
