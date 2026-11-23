"""Parser XML tờ khai thuế HTKK — phần mềm Hỗ trợ Kê khai thuế (HTKK) của
Tổng cục Thuế xuất tờ khai ra XML có namespace
`http://kekhaithue.gdt.gov.vn/TKhaiThue`, tag tên đã tự mang ngữ nghĩa
(`mst`, `ngayLapTKhai`, `tenCQTNoiNop`...) — khác PDF/ảnh, không cần OCR
hay LLM để biết một con số là gì.

Chiến lược: đổi tag đã biết sang text "Nhãn: Giá trị" rồi TÁI DÙNG THẲNG
`labels.py` (không sửa gì ở đó) — nhãn đã có sẵn trong LABEL_TO_FIELD khớp
ngay. Chỉ map các tag cần cho REQUIRED_TAX_FILING_FIELDS
(shared/constants.py); tag khác trong tờ khai (có hàng chục "ct" code
riêng của mẫu 03/TNDN) không map vì chưa có field_key nào cần tới.

Xác minh bằng tờ khai quyết toán thuế TNDN thật (mẫu 03/TNDN, MST
0110621095) — khớp đúng cả 7/7 field, không cần LLM (2026-07-19).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .schema import Anchor

# Tag HTKK (đã bỏ namespace) -> nhãn tiếng Việt khớp thẳng LABEL_TO_FIELD
# trong labels.py. ct04 nằm trong PLuc_03_1A_TNDN (doanh thu tính thuế);
# ctE là "Thuế TNDN phải nộp" đã tính; thueTNDN_tamnop_sxkd là số đã tạm
# nộp trong kỳ — cả hai đặc thù mẫu 03/TNDN, có thể khác ở mẫu tờ khai khác
# (chưa gặp mẫu khác trong data mẫu để tổng quát hoá thêm).
TAG_TO_LABEL: dict[str, str] = {
    "mst": "Mã số thuế",
    "kyKKhai": "Kỳ tính thuế",
    "tenCQTNoiNop": "Cơ quan thuế",
    "ngayLapTKhai": "Ngày nộp tờ khai",
    "ct04": "Doanh thu tính thuế",
    "ctE": "Thuế phải nộp",
    "thueTNDN_tamnop_sxkd": "Thuế đã nộp",
}


def _local_tag(tag: str) -> str:
    """Bỏ namespace URI khỏi tag ElementTree kiểu '{uri}tagname'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_htkk_xml(data: bytes) -> list[Anchor]:
    root = ET.fromstring(data)
    anchors: list[Anchor] = []
    for element in root.iter():
        tag = _local_tag(element.tag)
        label = TAG_TO_LABEL.get(tag)
        if label is None:
            continue
        text = (element.text or "").strip()
        if not text:
            continue
        anchors.append(Anchor(line_id=tag, text=f"{label}: {text}"))
    return anchors
