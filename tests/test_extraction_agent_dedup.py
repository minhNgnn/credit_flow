"""_dedupe_claims() — worker/app/agents/extraction.py. Hàm thuần, không
đụng DB/Redis/LLM nên test được trực tiếp trên host bằng cách import qua
`worker.app...` (namespace package qua repo root, không đụng package
`app` của api — xem Global Constraints trong
docs/superpowers/plans/2026-07-19-rm-intake-extraction.md).

Ghi chú import: worker/app/agents/extraction.py có dòng
    from app.llm.adapter import complete_json
dòng này CHỈ đúng bên trong container (PYTHONPATH=/app trỏ vào /app/worker).
Trên host, conftest.py đưa api/ vào sys.path nên `app` giải thành api/app —
không có app.llm ở đó. Giải pháp: stub module types.ModuleType được gắn vào
sys.modules trước khi import worker.app.agents.extraction để import machinery
bỏ qua vấn đề trùng tên. Stub không cần implement gì vì _dedupe_claims không
gọi complete_json (hàm thuần — không có I/O).
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Stub app.llm.adapter trước khi import worker module để tránh lỗi
# ModuleNotFoundError: No module named 'app.llm' khi chạy pytest trên host.
# conftest.py đưa api/ vào sys.path khiến `app` giải thành api/app (không có
# llm subpackage). Stub đủ để import_machinery hài lòng; _dedupe_claims không
# gọi bất cứ thứ gì trong stub (hàm thuần — không I/O).
for _stub_name in ("app.llm", "app.llm.adapter"):
    if _stub_name not in sys.modules:
        _stub = types.ModuleType(_stub_name)
        _stub.complete_json = None  # type: ignore[attr-defined]
        sys.modules[_stub_name] = _stub

from worker.app.agents.extraction import _dedupe_claims  # noqa: E402
from shared.extraction.schema import ExtractedFieldClaim  # noqa: E402


def _claim(field_key: str, raw_value: str, line_id: str = "a1") -> ExtractedFieldClaim:
    return ExtractedFieldClaim(
        field_key=field_key, line_id=line_id, value_type="number", raw_value=raw_value, confidence=0.9
    )


def test_dedupe_keeps_first_occurrence_per_field_key():
    claims = [_claim("total_assets", "100"), _claim("total_assets", "200")]
    result = _dedupe_claims(claims)
    assert len(result) == 1
    assert result[0].raw_value == "100"


def test_dedupe_deterministic_wins_over_llm_when_deterministic_listed_first():
    deterministic = _claim("total_assets", "4175150068")
    llm_duplicate = _claim("total_assets", "1006198023")  # LLM lỡ trả trùng field đã khớp tất định
    result = _dedupe_claims([deterministic, llm_duplicate])
    assert len(result) == 1
    assert result[0].raw_value == "4175150068"


def test_dedupe_preserves_distinct_field_keys():
    claims = [_claim("total_assets", "100"), _claim("total_liabilities", "50")]
    result = _dedupe_claims(claims)
    assert {c.field_key for c in result} == {"total_assets", "total_liabilities"}


def test_dedupe_empty_list():
    assert _dedupe_claims([]) == []
