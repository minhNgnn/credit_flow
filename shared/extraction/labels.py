"""Khớp nhãn tất định — tìm field bằng cách tìm một nhãn tiếng Việt biết
trước nằm cạnh (hoặc cùng dòng với) một giá trị, KHÔNG cần LLM. Chạy TRƯỚC
bước LLM (worker/app/agents/extraction.py) để field khớp chính xác/miễn phí
không bao giờ phải trả tiền gọi LLM, và để LLM chỉ còn phải xử lý field mà
cách này không tìm ra.

docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md §4, §5.
"""
from __future__ import annotations

import re
import unicodedata

from .schema import Anchor, ExtractedFieldClaim

# Nhãn (đã chuẩn hoá) -> field_key. Nhãn được chuẩn hoá qua _normalize()
# trước khi so khớp nên không cần liệt kê biến thể hoa/thường hay có/không
# dấu ở đây.
LABEL_TO_FIELD: dict[str, str] = {
    "tong tai san": "total_assets",
    # "Tổng CỘNG tài sản" — cách ghi thật trên mẫu B01a-DNN (Thông tư
    # 133/2016), khác "Tổng tài sản" ngắn gọn — xác minh trên
    # NTE_BCTC_B01a_2025.pdf thật (2026-07-19).
    "tong cong tai san": "total_assets",
    "tong no phai tra": "total_liabilities",
    "von chu so huu": "total_equity",
    "tong nguon von": "total_capital_source",
    "tong cong nguon von": "total_capital_source",
    "tai san ngan han": "current_assets_total",
    "no ngan han": "current_liabilities",
    "tien va tuong duong tien": "cash_and_equivalents",
    # "Tiền và CÁC KHOẢN tương đương tiền" — cách ghi thật, xác minh trên
    # BCDKT_NTE_2025.xlsx thật (2026-07-19).
    "tien va cac khoan tuong duong tien": "cash_and_equivalents",
    "phai thu khach hang": "accounts_receivable",
    "cac khoan phai thu": "accounts_receivable",
    "hang ton kho": "inventory",
    "doanh thu thuan": "net_revenue",
    "gia von hang ban": "cogs",
    "loi nhuan sau thue": "net_profit_after_tax",
    "luu chuyen tien tu hoat dong kinh doanh": "cf_operating",
    "ma so thue": "tax_id",
    "ky tinh thue": "tax_period",
    "doanh thu tinh thue": "revenue_declared",
    "thue phai nop": "tax_payable",
    "thue da nop": "tax_paid",
    "ngay nop to khai": "filing_date",
    "co quan thue": "tax_authority",
    "mo ta tai san": "asset_description",
    "dia chi tai san": "asset_address",
    "gia tri dinh gia": "valuation_amount_vnd",
    "ngay dinh gia": "valuation_date",
    "don vi dinh gia": "valuer_name",
    "phuong phap dinh gia": "valuation_method",
    "so giay chung nhan dang ky kinh doanh": "business_registration_number",
    "ten doanh nghiep": "business_name",
    "nguoi dai dien phap luat": "legal_representative",
    "dia chi dang ky": "registered_address",
    "von dieu le": "charter_capital_vnd",
    "ngay dang ky": "registration_date",
}

_NUMBER_RE = re.compile(r"^-?[\d.,]+$")
_DATE_RE = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")
_LABEL_VALUE_RE = re.compile(r"^(.*?)[:\-–]\s*(.+)$")
_VALUE_SCAN_WINDOW = 5


def _normalize(text: str) -> str:
    """Hạ chữ thường + bỏ dấu tiếng Việt để khớp nhãn không phụ thuộc hoa/
    thường hay nhiễu OCR làm mất dấu."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d").strip()


def _classify_value(text: str) -> str:
    if _DATE_RE.search(text):
        return "date"
    if _NUMBER_RE.match(text.strip()):
        return "number"
    return "string"


def _looks_like_value(text: str) -> bool:
    """Số tiền thật: có dấu phân cách nghìn (',', '.') HOẶC dài >= 4 chữ số.
    Mã số dòng BCTC ("Mã số" — cột chuẩn của mọi mẫu B01/B02) luôn là số
    trần 2-3 chữ số (100, 110, 200, 300...), không bao giờ có dấu phân cách
    — phân biệt được bằng đúng điều kiện này, xác minh trên
    NTE_BCTC_B01a_2025.pdf và BCDKT_NTE_2025.xlsx thật (2026-07-19)."""
    stripped = text.strip()
    if not _NUMBER_RE.match(stripped):
        return False
    has_separator = "." in stripped or "," in stripped
    digit_count = len(re.sub(r"[^\d]", "", stripped))
    return has_separator or digit_count >= 4


def _find_value_in_window(anchors: list[Anchor], start: int) -> Anchor | None:
    """Quét tối đa `_VALUE_SCAN_WINDOW` anchor kể từ `start`, tìm giá trị
    thật đầu tiên — bỏ qua cột "Mã số" (`_looks_like_value` loại các số
    trần 2-3 chữ số). Dừng sớm nếu gặp anchor trùng một nhãn đã biết khác
    (nghĩa là đã lạc sang dòng/field kế tiếp mà dòng hiện tại không có giá
    trị nào khớp).

    GIỚI HẠN CHƯA GIẢI QUYẾT: khi một dòng có CẢ giá trị kỳ này lẫn kỳ
    trước (bảng 2 kỳ so sánh), hàm này lấy giá trị thật ĐẦU TIÊN tìm được
    trong cửa sổ — có thể là kỳ trước thay vì kỳ này, tuỳ thứ tự cột của
    từng mẫu biểu. Khảo sát 2 file BCTC thật cho thấy thứ tự NGƯỢC NHAU
    giữa hai mẫu (PDF: kỳ này trước, kỳ trước sau; XLSX: ngược lại) — phân
    biệt đúng kỳ hiện tại cần đọc dòng header ("Năm 2024"/"Năm 2025"), nằm
    ngoài phạm vi sửa lỗi này.
    """
    for j in range(start, min(start + _VALUE_SCAN_WINDOW, len(anchors))):
        text = anchors[j].text.strip()
        if not text:
            continue
        if _normalize(text) in LABEL_TO_FIELD:
            return None  # đụng nhãn khác trước khi thấy giá trị thật — dừng
        if _looks_like_value(text):
            return anchors[j]
    return None


def match_labels(anchors: list[Anchor], field_keys: frozenset[str]) -> list[ExtractedFieldClaim]:
    """Quét `anchors` theo thứ tự, thử 2 kiểu khớp cho mỗi anchor:

    1. "Nhãn: giá trị" trên CÙNG một anchor (phổ biến trong OCR/văn xuôi).
    2. Anchor là đúng một nhãn đã biết, giá trị nằm ở anchor NGAY SAU (phổ
       biến trong bảng spreadsheet/DOCX — nhãn và giá trị tách ô riêng).

    Chỉ giữ field_key nằm trong `field_keys` và chỉ giữ lần khớp ĐẦU TIÊN
    cho mỗi field_key.
    """
    claims: list[ExtractedFieldClaim] = []
    seen: set[str] = set()

    for i, anchor in enumerate(anchors):
        match = _LABEL_VALUE_RE.match(anchor.text)
        if match:
            label_part, value_part = match.group(1), match.group(2).strip()
            field_key = LABEL_TO_FIELD.get(_normalize(label_part))
            if field_key and field_key in field_keys and field_key not in seen and value_part:
                claims.append(
                    ExtractedFieldClaim(
                        field_key=field_key,
                        line_id=anchor.line_id,
                        value_type=_classify_value(value_part),
                        raw_value=value_part,
                        confidence=1.0,
                    )
                )
                seen.add(field_key)
                continue

        field_key = LABEL_TO_FIELD.get(_normalize(anchor.text))
        if field_key is None or field_key not in field_keys or field_key in seen:
            continue
        value_anchor = _find_value_in_window(anchors, i + 1)
        if value_anchor is None:
            continue
        raw = value_anchor.text.strip()
        claims.append(
            ExtractedFieldClaim(
                field_key=field_key,
                line_id=value_anchor.line_id,
                value_type=_classify_value(raw),
                raw_value=raw,
                confidence=1.0,
            )
        )
        seen.add(field_key)

    return claims
