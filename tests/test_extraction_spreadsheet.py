import io

import openpyxl

from shared.extraction.spreadsheet import parse_xlsx


def _build_workbook() -> bytes:
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "BCKQHDKD"
    sheet["B9"] = "Tổng tài sản"
    sheet["C9"] = 8_000_000_000
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_xlsx_returns_one_anchor_per_nonempty_cell():
    anchors = parse_xlsx(_build_workbook())
    texts = {a.text for a in anchors}
    assert "Tổng tài sản" in texts
    assert "8000000000" in texts


def test_parse_xlsx_cell_ref_is_sheet_bang_cell():
    anchors = parse_xlsx(_build_workbook())
    value_anchor = next(a for a in anchors if a.text == "8000000000")
    assert value_anchor.cell_ref == "BCKQHDKD!C9"
    assert value_anchor.line_id == "BCKQHDKD!C9"


def test_parse_xlsx_skips_empty_cells():
    anchors = parse_xlsx(_build_workbook())
    assert all(a.text.strip() for a in anchors)


def test_parse_xlsx_anchors_have_no_page_or_bbox():
    anchors = parse_xlsx(_build_workbook())
    assert all(a.page is None and a.bbox is None for a in anchors)
