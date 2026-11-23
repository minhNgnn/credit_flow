"""Operations — cấp hạn mức thật, và guard chống cấp hai lần.

Guard là thứ quan trọng nhất của lát (c): job Redis có thể bị giao lại
(worker chết giữa chừng, hoặc ai đó đẩy lại tay). Nếu Operations chạy hai
lần thì merchant được cấp hạn mức hai lần.
"""
import pytest

from shared.db import get_session
from shared.models import RoutingDecision, SlinkApplication, SlinkOverdraftEvent
from shared.slink_operations import claim_for_issuing


@pytest.fixture()
def approved_application(client) -> str:
    """Một application đã ở trạng thái APPROVED, sẵn sàng để cấp hạn mức."""
    with get_session() as session:
        decision = RoutingDecision(
            channel="MOBILE_KHDN",
            lane="GREEN",
            customer_id="CUST-SLINK",
            segment="MICROSME",
            product="MICRO_OD",
            amount_vnd=150_000_000,
            tenor_months=12,
            reason="test",
        )
        session.add(decision)
        session.flush()

        app_row = SlinkApplication(
            routing_decision_id=decision.routing_decision_id,
            customer_id="CUST-SLINK",
            amount_requested_vnd=150_000_000,
            tenor_months=12,
            status="APPROVED",
            recommended_limit_vnd=200_000_000,
            interest_rate_pct=10.5,
        )
        session.add(app_row)
        session.flush()
        return app_row.slink_application_id


def test_claim_succeeds_once(approved_application):
    with get_session() as session:
        assert claim_for_issuing(session, approved_application) is True

    with get_session() as session:
        assert session.get(SlinkApplication, approved_application).status == "ISSUING"


def test_second_claim_is_refused(approved_application):
    """Đây là guard chống cấp hạn mức hai lần.

    Lượt thứ hai phải thấy rowcount = 0 và thoát — nếu nó cũng giành được
    quyền thì core-banking sẽ bị gọi hai lần.
    """
    with get_session() as session:
        assert claim_for_issuing(session, approved_application) is True

    with get_session() as session:
        assert claim_for_issuing(session, approved_application) is False


def test_cannot_claim_a_rejected_application(approved_application):
    """Chỉ APPROVED mới cấp được — REJECTED thì không."""
    with get_session() as session:
        session.get(SlinkApplication, approved_application).status = "REJECTED"

    with get_session() as session:
        assert claim_for_issuing(session, approved_application) is False


def test_cannot_claim_an_already_issued_application(approved_application):
    with get_session() as session:
        session.get(SlinkApplication, approved_application).status = "ISSUED"

    with get_session() as session:
        assert claim_for_issuing(session, approved_application) is False


def test_claim_on_unknown_application_returns_false():
    with get_session() as session:
        assert claim_for_issuing(session, "khong-ton-tai") is False


def test_overdraft_event_is_append_only_record(approved_application):
    """Sự kiện ghi cả phản hồi nguyên văn của core-banking.

    Cần thiết vì core-banking là nguồn sự thật của hạn mức — khi hai bên
    lệch, phải biết nó trả về đúng cái gì chứ không chỉ biết ta diễn giải
    ra sao.
    """
    with get_session() as session:
        session.add(
            SlinkOverdraftEvent(
                customer_id="CUST-SLINK",
                slink_application_id=approved_application,
                action="ISSUE",
                limit_before_vnd=None,
                limit_after_vnd=200_000_000,
                interest_rate_pct=10.5,
                reason="test",
                succeeded=True,
                core_banking_response={"status": "active", "limit_vnd": 200_000_000},
            )
        )

    with get_session() as session:
        event = session.query(SlinkOverdraftEvent).one()
        assert event.action == "ISSUE"
        assert event.core_banking_response["status"] == "active"
        assert event.succeeded is True


def test_shock_event_has_no_application_link(clean_db):
    """Sốc dòng tiền điều chỉnh hạn mức đang có, không sinh từ đề nghị nào."""
    with get_session() as session:
        session.add(
            SlinkOverdraftEvent(
                customer_id="CUST-SLINK",
                slink_application_id=None,
                action="ADJUST",
                limit_before_vnd=200_000_000,
                limit_after_vnd=120_000_000,
                reason="sốc dòng tiền -60%",
                succeeded=True,
                core_banking_response={"status": "reduced"},
            )
        )

    with get_session() as session:
        event = session.query(SlinkOverdraftEvent).one()
        assert event.slink_application_id is None
        assert event.limit_after_vnd < event.limit_before_vnd


def test_scoring_claim_is_also_guarded(approved_application):
    """Job giao lại phải thoát sạch ở ĐẦU job, không chạy lại engine.

    Thiếu guard này thì job giao lại chạy lại engine rồi chết ở
    UniqueViolation của slink_agent_decisions — vẫn chống được cấp hai lần
    nhưng bằng ràng buộc của bảng khác chứ không phải bằng thiết kế.
    Phát hiện khi chạy kiểm chứng end-to-end, không phải khi viết test.
    """
    from shared.slink_operations import claim_for_scoring

    with get_session() as session:
        session.get(SlinkApplication, approved_application).status = "QUEUED"

    with get_session() as session:
        assert claim_for_scoring(session, approved_application) is True
    with get_session() as session:
        assert claim_for_scoring(session, approved_application) is False


def test_scoring_claim_refused_for_already_issued(approved_application):
    with get_session() as session:
        session.get(SlinkApplication, approved_application).status = "ISSUED"

    from shared.slink_operations import claim_for_scoring

    with get_session() as session:
        assert claim_for_scoring(session, approved_application) is False
