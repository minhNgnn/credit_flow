import io

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

from scripts.pdf_utils import render_document_pdf
from shared.extraction.pdf import parse_pdf


def test_parse_pdf_reads_real_text_layer_without_ocr():
    pdf_bytes, _ = render_document_pdf("Test", [("Tổng tài sản", "8000000000", "total_assets")])
    anchors = parse_pdf(pdf_bytes)

    assert any("8000000000" in a.text for a in anchors)
    assert all(a.page == 1 for a in anchors)


def test_parse_pdf_bbox_is_close_to_known_drawn_position():
    """render_document_pdf tự ghi lại bbox nó vẽ (bottom-left origin, PDF
    point) — dùng làm ground truth độc lập để kiểm chứng công thức lật
    trục trong _parse_text_page, thay vì so với số tự tính tay."""
    pdf_bytes, expected_bboxes = render_document_pdf(
        "Test", [("Tổng tài sản", "8000000000", "total_assets")]
    )
    anchors = parse_pdf(pdf_bytes)
    expected = expected_bboxes["total_assets"]

    match = next(a for a in anchors if "8000000000" in a.text)

    assert match.bbox["x0"] == pytest.approx(expected["x0"], abs=2)
    assert match.bbox["y0"] == pytest.approx(expected["y0"], abs=5)
    assert match.bbox["y1"] == pytest.approx(expected["y1"], abs=5)


def test_parse_pdf_groups_words_on_same_line_into_one_anchor():
    pdf_bytes, _ = render_document_pdf("Test", [("Tổng tài sản", "8000000000", "total_assets")])
    anchors = parse_pdf(pdf_bytes)
    matching = [a for a in anchors if "8000000000" in a.text]
    assert len(matching) == 1
    assert "Tổng tài sản" in matching[0].text  # nhãn + giá trị cùng dòng gộp lại


def test_parse_pdf_falls_back_to_ocr_for_scanned_page():
    image = Image.new("RGB", (800, 400), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=48)
    draw.text((40, 40), "HOA DON", fill="black", font=font)
    img_buf = io.BytesIO()
    image.save(img_buf, format="PNG")

    scan_doc = fitz.open()
    page = scan_doc.new_page(width=800 * 72 / 200, height=400 * 72 / 200)
    page.insert_image(page.rect, stream=img_buf.getvalue())
    pdf_bytes = scan_doc.tobytes()
    scan_doc.close()

    anchors = parse_pdf(pdf_bytes)

    assert anchors, "trang không có text layer phải rơi vào nhánh OCR"
    for anchor in anchors:
        assert anchor.page == 1
        assert 0 <= anchor.bbox["x0"] < anchor.bbox["x1"]
        assert 0 <= anchor.bbox["y0"] < anchor.bbox["y1"]
