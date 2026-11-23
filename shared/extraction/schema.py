"""Kiểu dữ liệu dùng chung giữa parser (spreadsheet/office/pdf/ocr), khớp
nhãn tất định (labels.py) và LLM structured-output. `Anchor` là hình dạng
DUY NHẤT mọi parser phải trả về — labels.py và prompt builder chỉ nhìn thấy
hình dạng này, không quan tâm nó đến từ định dạng file nào.

docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md §3, §6.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class Anchor(BaseModel):
    """Một đoạn text với vị trí THẬT, không phải số LLM tự bịa. `line_id`
    do parser sinh ra anchor này gán, phải duy nhất trong danh sách anchor
    của một document."""

    line_id: str
    text: str
    page: int | None = None
    bbox: dict[str, float] | None = None  # {"x0","y0","x1","y1"}, đơn vị PDF-point, gốc dưới-trái
    cell_ref: str | None = None  # vd "BCKQHDKD!C9" — chỉ có khi nguồn là spreadsheet


class ExtractedFieldClaim(BaseModel):
    field_key: str
    line_id: str  # trỏ vào Anchor.line_id có sẵn — KHÔNG phải toạ độ tự sinh
    value_type: Literal["number", "string", "date"]
    raw_value: str
    confidence: float = Field(ge=0, le=1)


class ExtractionResult(BaseModel):
    # Cả hai field đều có default rỗng — bắt buộc để complete_json()'s
    # LLM_MOCK path gọi ExtractionResult() không tham số vẫn hợp lệ.
    fields: list[ExtractedFieldClaim] = []
    unresolved: list[str] = []  # field_key model không tìm thấy

    @field_validator("fields", mode="before")
    @classmethod
    def _drop_malformed_claims(cls, raw: Any) -> Any:
        """LLM thật (verify 2026-07-19 trên NTE_BCTC_B01a_2025.pdf) thỉnh
        thoảng trả 11-12/13 field đúng hoàn toàn, nhưng 1 phần tử lẻ tẻ
        thiếu field (vd `line_id`/`raw_value` là null) — không tất định,
        không tránh được chỉ bằng prompt. Nếu để nguyên default validation
        của Pydantic, MỘT phần tử hỏng làm rớt validate cả list, vứt luôn
        11 field đúng cùng với nó. Bỏ qua phần tử hỏng, giữ phần tử tốt."""
        if not isinstance(raw, list):
            return raw
        claims = []
        for item in raw:
            try:
                claims.append(ExtractedFieldClaim.model_validate(item))
            except ValidationError:
                continue
        return claims
