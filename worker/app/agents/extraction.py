"""Extraction agent — biến một Document đã upload thành các dòng
ExtractedField. KHÔNG phải LangGraph node: chạy từ consumer Redis thuần
(worker/app/main.py::_consume_extraction_jobs), trigger ngay khi document
được upload (design spec §3), độc lập với state machine của case và độc
lập với các agent financial/collateral/policy/customer360 sau này ĐỌC lại
những gì agent này ghi — worker/app/agents/common.py đã ghi rõ bất biến đó
(các agent thẩm định không bao giờ tự đụng OCR/extraction).
"""
from __future__ import annotations

from shared.constants import DOC_TYPE_FIELD_CATALOG
from shared.db import get_session
from shared.extraction.labels import match_labels
from shared.extraction.office import parse_docx
from shared.extraction.ocr import ocr_image
from shared.extraction.pdf import parse_pdf
from shared.extraction.schema import Anchor, ExtractedFieldClaim, ExtractionResult
from shared.extraction.spreadsheet import parse_xlsx
from shared.extraction.xml_tax import parse_htkk_xml
from shared.models import Document, ExtractedField
from shared.storage import get_object_bytes

from app.llm.adapter import complete_json

_PARSERS = {
    "xlsx": parse_xlsx,
    "docx": parse_docx,
    "pdf": parse_pdf,
    "xml": parse_htkk_xml,
}
_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}


def _extension(minio_key: str) -> str:
    return minio_key.rsplit(".", 1)[-1].lower() if "." in minio_key else ""


def _parse(data: bytes, extension: str) -> list[Anchor]:
    if extension in _IMAGE_EXTENSIONS:
        return ocr_image(data, page=None)
    parser = _PARSERS.get(extension)
    if parser is None:
        return []
    return parser(data)


async def run_extraction(document_id: str) -> None:
    with get_session() as session:
        document = session.get(Document, document_id)
        if document is None:
            print(f"[extraction] document {document_id} không tồn tại, bỏ qua", flush=True)
            return
        doc_type = document.doc_type
        minio_key = document.minio_key

    required_fields = DOC_TYPE_FIELD_CATALOG.get(doc_type, frozenset())
    if not required_fields:
        print(f"[extraction] không có field catalog cho doc_type={doc_type!r}, bỏ qua", flush=True)
        return

    data = get_object_bytes(minio_key)
    anchors = _parse(data, _extension(minio_key))
    if not anchors:
        print(f"[extraction] không parse được anchor nào cho document {document_id}", flush=True)
        return

    anchors_by_id = {a.line_id: a for a in anchors}

    deterministic_claims = match_labels(anchors, required_fields)
    matched_keys = {c.field_key for c in deterministic_claims}
    remaining_fields = required_fields - matched_keys

    llm_claims: list[ExtractedFieldClaim] = []
    if remaining_fields:
        result = await _extract_via_llm(anchors, remaining_fields)
        llm_claims = result.fields

    _write_fields(document_id, _dedupe_claims(deterministic_claims + llm_claims), anchors_by_id)
    print(
        f"[extraction] document {document_id}: {len(deterministic_claims)} field tất định, "
        f"{len(llm_claims)} field qua LLM",
        flush=True,
    )


_SHAPE_EXAMPLE = (
    '{"fields": [{"field_key": "total_assets", "line_id": "p1l136", '
    '"value_type": "number", "raw_value": "4175150068", "confidence": 0.95}], '
    '"unresolved": ["net_revenue"]}'
)


async def _extract_via_llm(anchors: list[Anchor], field_keys: frozenset[str]) -> ExtractionResult:
    numbered_lines = "\n".join(f"{a.line_id}: {a.text}" for a in anchors)
    system = (
        "Bạn là trợ lý trích xuất dữ liệu tài chính. Chỉ trả lời bằng JSON đúng "
        "schema được yêu cầu. Không tự bịa toạ độ hay số liệu không có trong văn bản."
    )
    # `_SHAPE_EXAMPLE` không phải trang trí — không có nó, model (xác minh
    # thật trên NTE_BCTC_B01a_2025.pdf, 2026-07-19) tìm đúng dữ liệu nhưng
    # gói vào object theo field_key thay vì mảng "fields" như schema yêu
    # cầu, validate fail, dữ liệu đúng bị vứt oan. Có ví dụ hình dạng cụ
    # thể: tìm đúng 12/13 field, số liệu khớp 100% với văn bản gốc.
    user = (
        f"Danh sách dòng văn bản (line_id: nội dung):\n{numbered_lines}\n\n"
        f"Tìm các trường sau: {sorted(field_keys)}.\n"
        f"Trả về ĐÚNG hình dạng JSON này (fields là MỘT MẢNG, không phải object "
        f"gồm nhiều key):\n{_SHAPE_EXAMPLE}\n"
        "Mỗi phần tử trong fields: field_key, line_id (PHẢI là line_id có sẵn ở "
        "trên, không tự tạo line_id mới), value_type, raw_value đúng như trong "
        "văn bản, confidence (0-1). Trường không tìm thấy thì liệt kê trong "
        "unresolved."
    )
    return await complete_json(tier="extraction", system=system, user=user, schema=ExtractionResult)


def _dedupe_claims(claims: list[ExtractedFieldClaim]) -> list[ExtractedFieldClaim]:
    """Giữ claim ĐẦU TIÊN cho mỗi field_key. `deterministic_claims` luôn
    đứng trước `llm_claims` ở lệnh gọi (run_extraction) nên tất định thắng
    khi trùng. Cũng chặn trường hợp LLM tự trả 2 dòng cho cùng field_key
    trong MỘT response — quan sát thật trên BCDKT_NTE_2025.xlsx: model trả
    cả giá trị kỳ này lẫn kỳ trước cho cùng field dù prompt chỉ hỏi 1 giá
    trị (2026-07-19), nếu không lọc sẽ ghi 2 row ExtractedField cho cùng
    field_key."""
    seen: set[str] = set()
    deduped: list[ExtractedFieldClaim] = []
    for claim in claims:
        if claim.field_key in seen:
            continue
        seen.add(claim.field_key)
        deduped.append(claim)
    return deduped


def _write_fields(
    document_id: str, claims: list[ExtractedFieldClaim], anchors_by_id: dict[str, Anchor]
) -> None:
    with get_session() as session:
        for claim in claims:
            anchor = anchors_by_id.get(claim.line_id)
            if anchor is None:
                # LLM trả line_id không tồn tại trong anchor list — bỏ qua
                # thay vì tin một vị trí bịa (bất biến §3 của design spec).
                continue
            value: dict = {"type": claim.value_type, "raw": claim.raw_value}
            if anchor.cell_ref:
                value["cell_ref"] = anchor.cell_ref
            session.add(
                ExtractedField(
                    document_id=document_id,
                    field_key=claim.field_key,
                    value=value,
                    confidence=claim.confidence,
                    page=anchor.page,
                    bbox=anchor.bbox,
                )
            )
