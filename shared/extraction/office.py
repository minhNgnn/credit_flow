"""Parser DOCX — python-docx đọc đoạn văn và ô bảng. `line_id` mã hoá vị
trí cấu trúc (số thứ tự đoạn văn, hoặc bảng.hàng.cột) vì Word không có khái
niệm trang/bbox cố định như PDF (nội dung dàn lại khi render, không phải
layout cố định) — Anchor.bbox luôn None với nguồn này (design spec §4).
"""
from __future__ import annotations

import io

from docx import Document as DocxDocument

from .schema import Anchor


def parse_docx(data: bytes) -> list[Anchor]:
    doc = DocxDocument(io.BytesIO(data))
    anchors: list[Anchor] = []

    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if text:
            anchors.append(Anchor(line_id=f"p{i}", text=text))

    for t, table in enumerate(doc.tables):
        for r, row in enumerate(table.rows):
            for c, cell in enumerate(row.cells):
                text = cell.text.strip()
                if text:
                    anchors.append(Anchor(line_id=f"t{t}.{r}.{c}", text=text))

    return anchors
