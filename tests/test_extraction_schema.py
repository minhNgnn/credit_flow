import pytest
from pydantic import ValidationError

from shared.extraction.schema import Anchor, ExtractedFieldClaim, ExtractionResult


def test_extraction_result_defaults_are_empty():
    result = ExtractionResult()
    assert result.fields == []
    assert result.unresolved == []


def test_anchor_minimal_construction_has_no_spatial_info():
    anchor = Anchor(line_id="p1", text="Tổng tài sản")
    assert anchor.page is None
    assert anchor.bbox is None
    assert anchor.cell_ref is None


def test_anchor_with_bbox():
    anchor = Anchor(line_id="p1l0", text="8000000000", page=1, bbox={"x0": 50.0, "y0": 748.9, "x1": 195.1, "y1": 762.9})
    assert anchor.bbox["x0"] == 50.0


def test_extracted_field_claim_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        ExtractedFieldClaim(field_key="x", line_id="a", value_type="number", raw_value="1", confidence=1.5)


def test_extracted_field_claim_rejects_unknown_value_type():
    with pytest.raises(ValidationError):
        ExtractedFieldClaim(field_key="x", line_id="a", value_type="currency", raw_value="1", confidence=0.9)


def test_extraction_result_drops_malformed_claims_keeps_valid_ones():
    """LLM thật thỉnh thoảng trả 1 phần tử null lẫn trong mảng fields hợp
    lệ — xem shared/extraction/schema.py::_drop_malformed_claims. Phải giữ
    lại các phần tử tốt thay vì vứt cả batch vì một phần tử hỏng."""
    raw = {
        "fields": [
            {"field_key": "total_assets", "line_id": "p1l136", "value_type": "number", "raw_value": "4175150068", "confidence": 0.95},
            {"field_key": "current_assets_total", "line_id": None, "value_type": "number", "raw_value": None, "confidence": 0.9},
            {"field_key": "total_equity", "line_id": "p2l26", "value_type": "number", "raw_value": "3463386695", "confidence": 0.95},
        ],
        "unresolved": [],
    }
    result = ExtractionResult.model_validate(raw)
    assert {f.field_key for f in result.fields} == {"total_assets", "total_equity"}
