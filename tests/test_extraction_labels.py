from shared.extraction.labels import match_labels
from shared.extraction.schema import Anchor


def test_matches_label_then_next_anchor_as_value():
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))

    assert len(claims) == 1
    assert claims[0].field_key == "total_assets"
    assert claims[0].line_id == "a2"
    assert claims[0].raw_value == "8000000000"
    assert claims[0].value_type == "number"
    assert claims[0].confidence == 1.0


def test_matches_same_line_label_colon_value():
    anchors = [Anchor(line_id="a1", text="Tổng tài sản: 8000000000")]
    claims = match_labels(anchors, frozenset({"total_assets"}))

    assert len(claims) == 1
    assert claims[0].line_id == "a1"
    assert claims[0].raw_value == "8000000000"


def test_tolerant_to_missing_diacritics_and_case():
    anchors = [
        Anchor(line_id="a1", text="TONG TAI SAN"),
        Anchor(line_id="a2", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert len(claims) == 1


def test_ignores_field_keys_not_requested():
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"net_revenue"}))
    assert claims == []


def test_keeps_only_first_match_per_field_key():
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="8000000000"),
        Anchor(line_id="a3", text="Tổng tài sản"),
        Anchor(line_id="a4", text="9000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert len(claims) == 1
    assert claims[0].raw_value == "8000000000"


def test_classifies_date_values():
    anchors = [Anchor(line_id="a1", text="Ngày định giá: 15/03/2026")]
    claims = match_labels(anchors, frozenset({"valuation_date"}))
    assert claims[0].value_type == "date"


def test_no_match_when_label_is_last_anchor():
    anchors = [Anchor(line_id="a1", text="Tổng tài sản")]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert claims == []


def test_skips_bctc_ma_so_code_column_finds_real_value():
    """Tái hiện layout BCDKT_NTE_2025.xlsx thật: nhãn | Mã số | Số tiền
    (kỳ trước, 2 chữ số) | % | Số tiền (kỳ này, 4 chữ số). '130' là Mã số
    — không phải giá trị; giá trị kỳ này (3094) đủ dài để nhận ra là số
    tiền thật, không giống mã code."""
    anchors = [
        Anchor(line_id="b9", text="Các khoản phải thu"),
        Anchor(line_id="c9", text="130"),
        Anchor(line_id="d9", text="13"),
        Anchor(line_id="e9", text="1.3"),
        Anchor(line_id="f9", text="3094"),
    ]
    claims = match_labels(anchors, frozenset({"accounts_receivable"}))
    assert len(claims) == 1
    assert claims[0].raw_value not in ("130",), "không được lấy Mã số làm giá trị"


def test_ambiguous_short_value_in_scaled_unit_report_is_not_matched():
    """GIỚI HẠN THẬT, không giải được bằng heuristic hình dạng số: báo cáo
    dùng đơn vị 'Triệu đồng' (BCDKT_NTE_2025.xlsx thật) có số tiền thật
    NGẮN Y HỆT mã code (2-3 chữ số trần) — '110' là mã, '962' là 962 triệu
    đồng thật, không thể phân biệt bằng hình dạng. Thà không khớp (rơi
    xuống LLM ở worker/app/agents/extraction.py, có ngữ cảnh để hiểu) còn
    hơn khớp liều — an toàn hơn cho quyết định tín dụng."""
    anchors = [
        Anchor(line_id="b8", text="Tiền và các khoản tương đương tiền"),
        Anchor(line_id="c8", text="110"),
        Anchor(line_id="d8", text="962"),
    ]
    claims = match_labels(anchors, frozenset({"cash_and_equivalents"}))
    assert claims == []


def test_skips_ma_so_code_even_when_real_value_has_thousand_separator():
    """Tái hiện đúng layout NTE_BCTC_B01a_2025.pdf thật: nhãn | mã | số
    tiền có dấu chấm phân cách."""
    anchors = [
        Anchor(line_id="l1", text="TỔNG CỘNG TÀI SẢN"),
        Anchor(line_id="l2", text="200"),
        Anchor(line_id="l3", text="4.175.150.068"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert len(claims) == 1
    assert claims[0].raw_value == "4.175.150.068"


def test_stops_at_next_known_label_without_finding_value_in_window():
    """Nếu trong cửa sổ quét chỉ toàn mã code rồi gặp luôn nhãn khác (dòng
    kế tiếp), không được lấy bừa giá trị của dòng khác — trả về không
    khớp cho field này."""
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="200"),  # chỉ có mã, không có giá trị thật
        Anchor(line_id="a3", text="Tổng nợ phải trả"),  # nhãn khác
        Anchor(line_id="a4", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets", "total_liabilities"}))
    matched = {c.field_key: c.raw_value for c in claims}
    assert "total_assets" not in matched
    assert matched["total_liabilities"] == "8000000000"
