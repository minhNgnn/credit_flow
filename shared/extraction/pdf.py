"""Parser PDF — thử đọc text layer thật bằng PyMuPDF trước (miễn phí,
chính xác tuyệt đối); chỉ raster hoá + OCR Tesseract cho trang THỰC SỰ
không có text (bản scan). design spec §4.

Quy đổi toạ độ: PyMuPDF dùng gốc TRÊN-TRÁI (y tăng xuống); ExtractedField.bbox
(và scripts/pdf_utils.py) dùng gốc DƯỚI-TRÁI kiểu PDF gốc (y tăng lên) — mọi
bbox trả ra từ module này đã được quy về gốc dưới-trái, bất kể đến từ text
layer hay OCR, để nhất quán với cách frontend/Evidence Viewer đã dùng.
"""
from __future__ import annotations

import fitz

from .ocr import ocr_image
from .schema import Anchor

RASTER_DPI = 200


def parse_pdf(data: bytes) -> list[Anchor]:
    doc = fitz.open(stream=data, filetype="pdf")
    anchors: list[Anchor] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1

        if page.get_text().strip():
            anchors.extend(_parse_text_page(page, page_number))
        else:
            anchors.extend(_ocr_scanned_page(page, page_number))

    return anchors


def _parse_text_page(page: fitz.Page, page_number: int) -> list[Anchor]:
    """`page.get_text("words")` trả (x0, y0, x1, y1, word, block_no,
    line_no, word_no) theo gốc TRÊN-TRÁI của PyMuPDF — gộp theo
    (block_no, line_no) thành từng dòng, rồi lật trục sang gốc dưới-trái."""
    page_height = page.rect.height
    words = page.get_text("words")

    lines: dict[tuple[int, int], dict] = {}
    for x0, y0, x1, y1, word, block_no, line_no, _word_no in words:
        key = (block_no, line_no)
        line = lines.setdefault(key, {"words": [], "x0": x0, "y0": y0, "x1": x1, "y1": y1})
        line["words"].append(word)
        line["x0"] = min(line["x0"], x0)
        line["y0"] = min(line["y0"], y0)
        line["x1"] = max(line["x1"], x1)
        line["y1"] = max(line["y1"], y1)

    anchors: list[Anchor] = []
    for idx, key in enumerate(sorted(lines)):
        line = lines[key]
        anchors.append(
            Anchor(
                line_id=f"p{page_number}l{idx}",
                text=" ".join(line["words"]),
                page=page_number,
                bbox={
                    "x0": line["x0"],
                    "y0": page_height - line["y1"],
                    "x1": line["x1"],
                    "y1": page_height - line["y0"],
                },
            )
        )
    return anchors


def _ocr_scanned_page(page: fitz.Page, page_number: int) -> list[Anchor]:
    page_height = page.rect.height
    pix = page.get_pixmap(dpi=RASTER_DPI)
    png_bytes = pix.tobytes("png")
    pixel_anchors = ocr_image(png_bytes, page=page_number, line_prefix=f"p{page_number}ocr")

    # pixel (RASTER_DPI, gốc trên-trái) -> point (72/inch, gốc trên-trái)
    # -> lật sang gốc dưới-trái, cùng công thức nhánh text layer ở trên.
    scale = 72.0 / RASTER_DPI
    converted: list[Anchor] = []
    for anchor in pixel_anchors:
        bbox = anchor.bbox
        x0, y0 = bbox["x0"] * scale, bbox["y0"] * scale
        x1, y1 = bbox["x1"] * scale, bbox["y1"] * scale
        converted.append(
            anchor.model_copy(
                update={"bbox": {"x0": x0, "y0": page_height - y1, "x1": x1, "y1": page_height - y0}}
            )
        )
    return converted
