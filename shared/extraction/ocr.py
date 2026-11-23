"""Tesseract OCR — nguồn anchor cho nội dung không có text layer (PDF bản
scan, PNG/JPEG upload trực tiếp). `image_to_data` trả bbox theo TỪ, gốc
trên-trái, đơn vị pixel; module này GỘP các từ cùng dòng (block/paragraph/
line) lại thành một Anchor mỗi dòng — nếu để mỗi từ một Anchor, nhãn nhiều
từ như "Tổng tài sản" (labels.py) sẽ không bao giờ khớp trọn vẹn.

Bbox trả về LUÔN ở pixel space, gốc trên-trái — pdf.py chịu trách nhiệm quy
đổi sang PDF-point/gốc dưới-trái khi nguồn là một trang PDF scan; một
PNG/JPEG độc lập không có khái niệm trang PDF để quy đổi về.
"""
from __future__ import annotations

import io

import pytesseract
from PIL import Image

from .schema import Anchor

TESSERACT_LANG = "vie+eng"


def ocr_image(data: bytes, *, page: int | None = None, line_prefix: str = "ocr") -> list[Anchor]:
    image = Image.open(io.BytesIO(data))
    tsv = pytesseract.image_to_data(image, lang=TESSERACT_LANG, output_type=pytesseract.Output.DICT)

    lines: dict[tuple[int, int, int], dict] = {}
    n = len(tsv["text"])
    for i in range(n):
        word = tsv["text"][i].strip()
        if not word:
            continue
        key = (tsv["block_num"][i], tsv["par_num"][i], tsv["line_num"][i])
        x, y, w, h = tsv["left"][i], tsv["top"][i], tsv["width"][i], tsv["height"][i]
        line = lines.setdefault(key, {"words": [], "x0": x, "y0": y, "x1": x + w, "y1": y + h})
        line["words"].append(word)
        line["x0"] = min(line["x0"], x)
        line["y0"] = min(line["y0"], y)
        line["x1"] = max(line["x1"], x + w)
        line["y1"] = max(line["y1"], y + h)

    anchors: list[Anchor] = []
    for idx, key in enumerate(sorted(lines)):
        line = lines[key]
        anchors.append(
            Anchor(
                line_id=f"{line_prefix}{idx}",
                text=" ".join(line["words"]),
                page=page,
                bbox={
                    "x0": float(line["x0"]),
                    "y0": float(line["y0"]),
                    "x1": float(line["x1"]),
                    "y1": float(line["y1"]),
                },
            )
        )
    return anchors
