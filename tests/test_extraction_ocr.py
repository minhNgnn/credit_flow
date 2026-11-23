import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from shared.extraction.ocr import ocr_image

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract binary không có trên host — cài bằng: sudo apt-get install tesseract-ocr tesseract-ocr-vie",
)


def _build_image(text: str = "HOA DON") -> bytes:
    image = Image.new("RGB", (600, 200), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=48)
    draw.text((20, 20), text, fill="black", font=font)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_ocr_image_returns_nonempty_anchors():
    anchors = ocr_image(_build_image())
    assert anchors, "Tesseract phải đọc được text vẽ rõ ràng trên nền trắng"


def test_ocr_image_anchors_have_pixel_bbox():
    anchors = ocr_image(_build_image())
    for anchor in anchors:
        assert anchor.bbox is not None
        assert 0 <= anchor.bbox["x0"] < anchor.bbox["x1"]
        assert 0 <= anchor.bbox["y0"] < anchor.bbox["y1"]


def test_ocr_image_sets_page_and_line_prefix():
    anchors = ocr_image(_build_image(), page=3, line_prefix="p3ocr")
    assert all(a.page == 3 for a in anchors)
    assert all(a.line_id.startswith("p3ocr") for a in anchors)


def test_ocr_image_groups_words_into_lines_not_one_anchor_per_word():
    anchors = ocr_image(_build_image("HOA DON BAN LE"))
    # 4 từ trên CÙNG một dòng phải gộp thành ít anchor hơn số từ — nếu
    # không, khớp nhãn nhiều-từ (vd "Tổng tài sản") sẽ không bao giờ khớp.
    assert len(anchors) < 4
