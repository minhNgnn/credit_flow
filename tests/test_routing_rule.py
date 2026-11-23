"""Luật phân luồng — thuần hàm, không DB, không HTTP.

Kiểm chứng §8 bước 1-6 của spec ở mức đơn vị; test endpoint nằm ở
tests/test_intake_submissions.py.
"""
from shared.routing import GREEN, RED, classify_lane

CEILING = 300_000_000


def test_micro_od_microsme_under_ceiling_is_green():
    result = classify_lane(product="MICRO_OD", segment="MICROSME", amount_vnd=150_000_000)
    assert result.lane == GREEN


def test_exactly_at_ceiling_is_green():
    """Biên là ≤, không phải < — 300tr chẵn vẫn tự động."""
    result = classify_lane(product="MICRO_OD", segment="MICROSME", amount_vnd=CEILING)
    assert result.lane == GREEN


def test_one_dong_over_ceiling_is_red():
    result = classify_lane(product="MICRO_OD", segment="MICROSME", amount_vnd=CEILING + 1)
    assert result.lane == RED
    assert "vượt hạn mức" in result.reason


def test_wrong_product_is_red():
    result = classify_lane(product="SME_WC", segment="MICROSME", amount_vnd=100_000_000)
    assert result.lane == RED
    assert "SME_WC" in result.reason


def test_wrong_segment_is_red():
    result = classify_lane(product="MICRO_OD", segment="SME", amount_vnd=150_000_000)
    assert result.lane == RED
    assert "SME" in result.reason


def test_reason_formats_vnd_with_dots():
    """Lý do hiện ra màn hình demo nên phải đọc được, không phải 300000000."""
    result = classify_lane(product="MICRO_OD", segment="MICROSME", amount_vnd=150_000_000)
    assert "150.000.000" in result.reason
    assert "300.000.000" in result.reason
