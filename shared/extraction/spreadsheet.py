"""Parser XLSX — openpyxl trả địa chỉ ô thật miễn phí, nên đây là nguồn
anchor rẻ và chính xác nhất trong 4 định dạng (design spec §4).
"""
from __future__ import annotations

import io

import openpyxl

from .schema import Anchor


def parse_xlsx(data: bytes) -> list[Anchor]:
    """Trả một Anchor cho mỗi ô không rỗng, theo thứ tự hàng trong từng
    sheet. `line_id` là `{sheet}!{cell}` — trùng với `cell_ref`, vì với
    spreadsheet định danh anchor và vị trí có thể tra ngược là một."""
    workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    anchors: list[Anchor] = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                text = str(cell.value).strip()
                if not text:
                    continue
                ref = f"{sheet.title}!{cell.coordinate}"
                anchors.append(Anchor(line_id=ref, text=text, cell_ref=ref))
    return anchors
