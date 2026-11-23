"""Engine chấm điểm SLINK — thuần hàm, không DB, không HTTP.

Dựng merchant ngay trong test thay vì gọi slink-mock: engine không được
phụ thuộc service nào, và test phải chạy được cả khi container đã tắt.
"""
import pytest

from shared.constants import AUTO_APPROVAL_CEILING_VND
from shared.slink_engine import APPROVED, REJECTED, score_merchant


def _cashflow(daily_inflow: int, days: int = 60, silent_every: int = 0) -> list[dict]:
    """Chuỗi phẳng, không nhiễu — để test kiểm công thức chứ không kiểm RNG."""
    points = []
    for i in range(days):
        silent = silent_every and i % silent_every == 0
        inflow = 0 if silent else daily_inflow
        points.append({"date": f"2026-05-{i % 28 + 1:02d}", "inflow_vnd": inflow, "outflow_vnd": int(inflow * 0.7)})
    return points


def _merchant(**overrides) -> dict:
    base = {
        "merchant_id": "slink-test",
        "customer_id": "CUST-TEST",
        "name": "Quán thử nghiệm",
        "industry": "F&B",
        "seasonality": "đều quanh năm",
        "established_year": 2020,
        "slink_tenure_months": 30,
        "casa_retention_pct": 78,
        "payment_history_score": 88,
        "counterparty_quality": "tin cậy",
        "circular_transaction_flag": False,
        "night_transaction_share_pct": 10,
        "cashflow": _cashflow(15_000_000),
    }
    base.update(overrides)
    return base


def test_healthy_merchant_is_approved():
    outcome = score_merchant(_merchant())

    assert outcome.status == APPROVED
    assert outcome.recommended_limit_vnd > 0
    assert outcome.interest_rate_pct > 0
    assert len(outcome.decisions) == 5


def test_all_five_agents_run_in_order():
    outcome = score_merchant(_merchant())
    assert [d.agent_id for d in outcome.decisions] == [
        "profile",
        "cashflow",
        "behavioural",
        "sizing_pricing",
        "risk_compliance",
    ]


def test_circular_transaction_hard_fails_despite_good_numbers():
    """Cờ giao dịch vòng chặn cứng, KHÔNG chỉ trừ điểm.

    Merchant này cố tình đẹp ở mọi chỉ số khác — nếu chỉ trừ điểm thì nó
    vẫn được duyệt, và đó chính là lỗi test này canh.
    """
    outcome = score_merchant(
        _merchant(
            circular_transaction_flag=True,
            casa_retention_pct=95,
            payment_history_score=99,
            cashflow=_cashflow(50_000_000),
        )
    )

    assert outcome.status == REJECTED
    assert outcome.recommended_limit_vnd is None
    assert "giao dịch vòng" in outcome.reason


def test_night_transaction_over_threshold_blocks():
    outcome = score_merchant(_merchant(night_transaction_share_pct=68))
    assert outcome.status == REJECTED
    assert "ban đêm" in outcome.reason


def test_night_transaction_under_threshold_only_notes():
    outcome = score_merchant(_merchant(night_transaction_share_pct=35))
    assert outcome.status == APPROVED
    risk = next(d for d in outcome.decisions if d.agent_id == "risk_compliance")
    assert risk.metrics["blocked"] is False


def test_behavioural_score_formula():
    """0.5*casa + 0.5*payment + counterparty + tenure, kẹp [0,100]."""
    outcome = score_merchant(
        _merchant(casa_retention_pct=60, payment_history_score=80, counterparty_quality="trung bình", slink_tenure_months=12)
    )
    behavioural = next(d for d in outcome.decisions if d.agent_id == "behavioural")
    # 0.5*60 + 0.5*80 + 0 + 0 = 70
    assert behavioural.metrics["behavioural_score"] == 70.0


def test_counterparty_penalty_lowers_score():
    good = score_merchant(_merchant(counterparty_quality="tin cậy"))
    bad = score_merchant(_merchant(counterparty_quality="cần xác minh"))

    good_score = next(d for d in good.decisions if d.agent_id == "behavioural").metrics["behavioural_score"]
    bad_score = next(d for d in bad.decisions if d.agent_id == "behavioural").metrics["behavioural_score"]
    assert good_score - bad_score == 25  # +10 so với -15


def test_limit_never_exceeds_auto_approval_ceiling():
    """Doanh thu khổng lồ vẫn không được vượt trần tự động — vượt trần thì
    đáng lẽ hồ sơ đã không vào luồng xanh từ bước phân luồng."""
    outcome = score_merchant(_merchant(cashflow=_cashflow(500_000_000)))

    assert outcome.status == APPROVED
    assert outcome.recommended_limit_vnd <= AUTO_APPROVAL_CEILING_VND


def test_weak_merchant_gets_smaller_limit_and_higher_rate():
    strong = score_merchant(_merchant())
    weak = score_merchant(
        _merchant(casa_retention_pct=30, payment_history_score=40, counterparty_quality="cần xác minh", slink_tenure_months=6)
    )

    assert weak.recommended_limit_vnd < strong.recommended_limit_vnd
    assert weak.interest_rate_pct > strong.interest_rate_pct


def test_revenue_collapse_blocks():
    """Doanh thu nửa sau giảm >= 30% so với nửa đầu -> chặn."""
    points = _cashflow(20_000_000, days=60)
    for p in points[30:]:
        p["inflow_vnd"] = 5_000_000  # giảm 75%

    outcome = score_merchant(_merchant(cashflow=points))
    assert outcome.status == REJECTED
    assert "giảm" in outcome.reason


def test_scoring_is_deterministic():
    m = _merchant()
    first = score_merchant(m)
    second = score_merchant(m)

    assert first.status == second.status
    assert first.recommended_limit_vnd == second.recommended_limit_vnd
    assert first.interest_rate_pct == second.interest_rate_pct
    assert [d.summary for d in first.decisions] == [d.summary for d in second.decisions]
