import io

from docx import Document as DocxDocument

from shared.extraction.office import parse_docx


def _build_docx() -> bytes:
    doc = DocxDocument()
    doc.add_paragraph("Kế hoạch kinh doanh năm 2026")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Mã số thuế"
    table.rows[0].cells[1].text = "0102030405"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_docx_includes_paragraph_text():
    anchors = parse_docx(_build_docx())
    assert any("Kế hoạch kinh doanh" in a.text for a in anchors)


def test_parse_docx_includes_table_cells_with_structural_line_id():
    anchors = parse_docx(_build_docx())
    label = next(a for a in anchors if a.text == "Mã số thuế")
    value = next(a for a in anchors if a.text == "0102030405")
    assert label.line_id == "t0.0.0"
    assert value.line_id == "t0.0.1"


def test_parse_docx_skips_empty_paragraphs():
    anchors = parse_docx(_build_docx())
    assert all(a.text.strip() for a in anchors)


def test_parse_docx_anchors_have_no_bbox():
    anchors = parse_docx(_build_docx())
    assert all(a.bbox is None and a.cell_ref is None for a in anchors)
