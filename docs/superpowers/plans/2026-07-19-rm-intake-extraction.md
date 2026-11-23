# Trích xuất OCR/LLM cho hồ sơ RM (lát 2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tự động trích xuất field có cấu trúc từ tài liệu RM nộp (PDF/PNG/JPEG/DOCX/XLSX) và ghi vào `extracted_fields`, để các agent thẩm định (financial.py trước, các agent khác sau) đọc được dữ liệu thật thay vì seed script.

**Architecture:** Mỗi lần `POST /cases/{id}/documents` ghi thành công, enqueue 1 job vào Redis (`EXTRACTION_QUEUE`). `worker` có consumer riêng (`_consume_extraction_jobs`, cùng khuôn `_consume_slink_jobs` đã có) gọi `run_extraction(document_id)`. Bên trong: parse theo định dạng (XLSX/DOCX qua thư viện tất định, PDF ưu tiên text-layer thật qua PyMuPDF rồi mới OCR Tesseract khi cần) ra một danh sách `Anchor` (text + vị trí thật), khớp nhãn tiếng Việt tất định trước, phần field còn thiếu mới gọi LLM (gemma qua FPT, structured output). LLM chỉ chọn `line_id` trỏ vào anchor có sẵn — không bao giờ tự sinh toạ độ.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Redis, PyMuPDF (`fitz`), `pytesseract` + hệ thống Tesseract OCR, `python-docx`, `openpyxl`, Pydantic, OpenAI SDK (trỏ FPT AI Factory), pytest + pytest-asyncio.

## Global Constraints

- Chỉ luồng đỏ (LMS) — không đụng SLINK/luồng xanh.
- Không thêm Alembic migration — `extracted_fields` đã đủ cột từ lát 1 (`ExtractedField.bbox`/`page` nullable).
- LLM chỉ dùng để CHỌN `line_id` trong anchor list đã parse — không bao giờ tự sinh bbox/toạ độ.
- `LLM_MOCK=true` phải chạy hết pipeline không lỗi, không cần mạng/API key (đúng bất biến `worker/app/llm/adapter.py` đã có).
- Model LLM: `gemma-4-26B-A4B-it`, endpoint `https://mkp-api.fptcloud.com/v1/chat/completions` — tái dùng `OPENAI_BASE_URL`/`OPENAI_API_KEY` đã có trong `.env`, đã xác minh thủ công hỗ trợ `response_format={"type":"json_object"}` (curl 2026-07-19, trả đúng JSON).
- Logic parse/schema/label-matching (không cần Redis/Postgres/LLM) đặt trong `shared/extraction/` — dùng chung được bởi test trên host mà không đụng vấn đề trùng tên package `app` giữa `api/app` và `worker/app` (không có `worker/__init__.py`, hai package cùng tên `app` không thể cùng tồn tại trên `sys.path` khi chạy pytest — xem `tests/conftest.py`). Chỉ phần thật sự cần Redis/Postgres/LLM (`worker/app/agents/extraction.py`, `worker/app/main.py`) mới nằm trong `worker/app/`.
- Spec tham chiếu: `docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md`.

---

## File Structure

```
shared/
  extraction/
    __init__.py
    schema.py        # Anchor, ExtractedFieldClaim, ExtractionResult (Pydantic)
    labels.py         # LABEL_TO_FIELD dict + match_labels() — khớp tất định
    spreadsheet.py     # parse_xlsx()
    office.py          # parse_docx()
    ocr.py             # ocr_image() — Tesseract, gộp word -> line
    pdf.py             # parse_pdf() — text layer PyMuPDF trước, OCR fallback + quy đổi toạ độ
  queue.py             # + EXTRACTION_QUEUE
  constants.py         # + DOC_TYPE_FIELD_CATALOG + 3 catalog mới

worker/
  app/
    llm/adapter.py      # + complete_json()
    agents/extraction.py  # MỚI — run_extraction(document_id), điều phối toàn bộ
    main.py             # + _consume_extraction_jobs()
    config.py           # + re-export EXTRACTION_QUEUE
  config/models.yaml    # + tier "extraction"
  requirements.txt      # + pymupdf, pytesseract, python-docx, openpyxl, pillow
  Dockerfile            # + apt tesseract-ocr, tesseract-ocr-vie

api/
  app/routers/intake.py # ALLOWED_MIME + DOCX/XLSX, enqueue sau upload thành công

pyproject.toml          # + asyncio_mode = "auto" (test async lần đầu trong repo)

tests/
  test_extraction_constants.py
  test_llm_adapter_json.py
  test_extraction_schema.py
  test_extraction_labels.py
  test_extraction_spreadsheet.py
  test_extraction_office.py
  test_extraction_ocr.py
  test_extraction_pdf.py
  test_intake_upload.py   # SỬA — thêm fake_redis autouse + 2 test enqueue
```

`worker/app/agents/extraction.py` và `worker/app/main.py` **không có unit test riêng** — cùng lý do không có unit test cho `financial.py`/`collateral.py`/`_consume_jobs`/`_consume_slink_jobs` hiện tại: chúng cần Redis+Postgres+MinIO thật và import qua package `app` bare-name chỉ đúng bên trong container (`PYTHONPATH=/app`), đụng đúng vấn đề trùng tên nêu ở Global Constraints. Xác minh bằng `docker compose` end-to-end (Task 12 + phần "Xác minh cuối" ở cuối plan) — đúng cách lát 1 đã làm.

---

## Task 1: Dependencies — Python packages + hệ thống Tesseract

**Files:**
- Modify: `worker/requirements.txt`
- Modify: `worker/Dockerfile`

**Interfaces:**
- Produces: `pymupdf` (import `fitz`), `pytesseract`, `python-docx` (import `docx`), `openpyxl`, `pillow` (import `PIL`) khả dụng cho mọi task sau, cả trong container lẫn `.venv` cục bộ.

- [ ] **Step 1: Thêm dependency vào `worker/requirements.txt`**

Thêm vào cuối file (giữ nguyên nội dung hiện có):

```
# Lát 2 — trích xuất OCR/LLM (docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md)
pymupdf>=1.24.0
pytesseract>=0.3.10
python-docx>=1.1.0
openpyxl>=3.1.0
pillow>=10.0.0
```

- [ ] **Step 2: Cài Tesseract (binary hệ thống) vào `worker/Dockerfile`**

Sửa `worker/Dockerfile` từ:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
```

thành:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Lát 2: OCR bản scan (PDF không có text layer, PNG/JPEG) — tesseract-ocr-vie
# bắt buộc vì phần lớn tài liệu RM nộp là tiếng Việt có dấu.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
```

- [ ] **Step 3: Cài cùng bộ gói vào `.venv` cục bộ để chạy test trên host**

```bash
.venv/bin/pip install pymupdf pytesseract python-docx openpyxl pillow
```

Expected: cài thành công, không lỗi biên dịch (đều có wheel sẵn cho Linux x86_64/py3.11).

- [ ] **Step 4: Cài Tesseract binary + gói tiếng Việt trên máy host (không phải chỉ trong Docker)**

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-vie
```

Expected:

```bash
tesseract --version
# tesseract 5.x...
tesseract --list-langs
# ... vie
# ... eng
```

- [ ] **Step 5: Commit**

```bash
git add worker/requirements.txt worker/Dockerfile
git commit -m "feat(worker): thêm dependency OCR/parse cho lát 2 (pymupdf, pytesseract, python-docx, openpyxl)"
```

---

## Task 2: `EXTRACTION_QUEUE` + `DOC_TYPE_FIELD_CATALOG`

**Files:**
- Modify: `shared/queue.py`
- Modify: `shared/constants.py`
- Modify: `worker/app/config.py`
- Test: `tests/test_extraction_constants.py`

**Interfaces:**
- Produces: `shared.queue.EXTRACTION_QUEUE: str`; `shared.constants.DOC_TYPE_FIELD_CATALOG: dict[str, frozenset[str]]` (khoá đúng 4 giá trị của `REQUIRED_DOC_TYPES`).

- [ ] **Step 1: Viết test trước (sẽ fail vì chưa có gì)**

Tạo `tests/test_extraction_constants.py`:

```python
from shared.constants import DOC_TYPE_FIELD_CATALOG, REQUIRED_DOC_TYPES, REQUIRED_STATEMENT_FIELDS
from shared.queue import ANALYZE_QUEUE, EXTRACTION_QUEUE, SLINK_SCORING_QUEUE


def test_doc_type_field_catalog_covers_every_required_doc_type():
    assert set(DOC_TYPE_FIELD_CATALOG) == REQUIRED_DOC_TYPES


def test_financial_statement_catalog_reuses_existing_constant():
    assert DOC_TYPE_FIELD_CATALOG["financial_statement"] is REQUIRED_STATEMENT_FIELDS


def test_every_catalog_entry_is_a_non_empty_frozenset():
    for doc_type, fields in DOC_TYPE_FIELD_CATALOG.items():
        assert isinstance(fields, frozenset), doc_type
        assert fields, doc_type


def test_extraction_queue_name_is_unique_from_other_queues():
    assert len({ANALYZE_QUEUE, EXTRACTION_QUEUE, SLINK_SCORING_QUEUE}) == 3
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_constants.py -v
```

Expected: `ImportError: cannot import name 'DOC_TYPE_FIELD_CATALOG'` (hoặc `EXTRACTION_QUEUE`).

- [ ] **Step 3: Thêm `EXTRACTION_QUEUE` vào `shared/queue.py`**

Sửa từ:

```python
ANALYZE_QUEUE = "analyze_queue"


def progress_channel(case_id: str) -> str:
```

thành:

```python
ANALYZE_QUEUE = "analyze_queue"

# Lát 2 — trích xuất OCR/LLM. Hàng đợi riêng khỏi ANALYZE_QUEUE: job trigger
# ngay khi một document được upload (không phải khi case đổi state), và một
# document lỗi không được chặn job phân tích case khác.
# docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md §7
EXTRACTION_QUEUE = "extraction_queue"


def progress_channel(case_id: str) -> str:
```

- [ ] **Step 4: Thêm 3 field catalog mới + `DOC_TYPE_FIELD_CATALOG` vào `shared/constants.py`**

Chèn ngay sau khối `REQUIRED_STATEMENT_FIELDS` hiện có (trước comment `# Mock industry-average ratio table...`):

```python
REQUIRED_TAX_FILING_FIELDS: frozenset[str] = frozenset(
    {
        "tax_id",
        "tax_period",
        "revenue_declared",
        "tax_payable",
        "tax_paid",
        "filing_date",
        "tax_authority",
    }
)

REQUIRED_VALUATION_FIELDS: frozenset[str] = frozenset(
    {
        "asset_description",
        "asset_address",
        "valuation_amount_vnd",
        "valuation_date",
        "valuer_name",
        "valuation_method",
    }
)

REQUIRED_BUSINESS_REGISTRATION_FIELDS: frozenset[str] = frozenset(
    {
        "business_registration_number",
        "business_name",
        "legal_representative",
        "registered_address",
        "charter_capital_vnd",
        "registration_date",
    }
)

# Lát 2 (trích xuất OCR/LLM) đọc bảng này để biết cần tìm field gì theo
# từng doc_type — single-sourced như REQUIRED_DOC_TYPES ở trên. 3 catalog
# ngoài financial_statement là bản nháp đầu tiên dựa trên khảo sát data mẫu
# NTE, CHƯA có agent nào tiêu thụ — xem
# docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md §5.
DOC_TYPE_FIELD_CATALOG: dict[str, frozenset[str]] = {
    "financial_statement": REQUIRED_STATEMENT_FIELDS,
    "tax_filing": REQUIRED_TAX_FILING_FIELDS,
    "valuation_certificate": REQUIRED_VALUATION_FIELDS,
    "business_registration": REQUIRED_BUSINESS_REGISTRATION_FIELDS,
}
```

- [ ] **Step 5: Re-export `EXTRACTION_QUEUE` trong `worker/app/config.py`**

Sửa:

```python
from shared.queue import (  # re-exported for worker call sites
    ANALYZE_QUEUE,
    SLINK_SCORING_QUEUE,
    progress_channel,
    slink_progress_channel,
)
```

thành:

```python
from shared.queue import (  # re-exported for worker call sites
    ANALYZE_QUEUE,
    EXTRACTION_QUEUE,
    SLINK_SCORING_QUEUE,
    progress_channel,
    slink_progress_channel,
)
```

và thêm `"EXTRACTION_QUEUE"` vào danh sách `__all__` (ngay sau `"ANALYZE_QUEUE"`).

- [ ] **Step 6: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_constants.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add shared/queue.py shared/constants.py worker/app/config.py tests/test_extraction_constants.py
git commit -m "feat(shared): thêm EXTRACTION_QUEUE và DOC_TYPE_FIELD_CATALOG cho lát 2"
```

---

## Task 3: `complete_json()` — LLM structured output

**Files:**
- Modify: `worker/app/llm/adapter.py`
- Modify: `worker/config/models.yaml`
- Modify: `pyproject.toml`
- Test: `tests/test_llm_adapter_json.py`

**Interfaces:**
- Consumes: `worker/app/llm/adapter.py::_tier_config(tier)` (đã có), `worker/config/models.yaml` tier `"extraction"`.
- Produces: `worker.app.llm.adapter.complete_json(*, tier: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel` — dùng bởi Task 10.

- [ ] **Step 1: Bật async test cho toàn repo trong `pyproject.toml`**

Sửa:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

thành:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

(Lần đầu repo có test `async def` — trước giờ toàn bộ test dùng `TestClient` đồng bộ.)

- [ ] **Step 2: Viết test trước**

Tạo `tests/test_llm_adapter_json.py`:

```python
"""complete_json() — structured LLM output, worker/app/llm/adapter.py.

Không test nào ở đây gọi endpoint FPT thật (mạng + tốn phí); việc
gemma-4-26B-A4B-it hỗ trợ response_format=json_object đã xác minh thủ công:

    curl -s -X POST "$OPENAI_BASE_URL/chat/completions" \
      -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
      -d '{"model": "gemma-4-26B-A4B-it",
           "messages": [{"role": "user", "content": "Return a JSON object with one key \"ok\" set to true."}],
           "response_format": {"type": "json_object"}}'

    -> trả {"ok": true} đúng định dạng (xác minh 2026-07-19).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from worker.app.llm import adapter  # noqa: E402


class _Sample(BaseModel):
    fields: list[str] = []
    unresolved: list[str] = []


@pytest.fixture(autouse=True)
def _mock_tier(monkeypatch):
    monkeypatch.setattr(
        adapter,
        "_load_config",
        lambda: {
            "tiers": {
                "extraction": {"provider": "openai", "model": "gemma-4-26B-A4B-it", "max_tokens": 100}
            }
        },
    )


async def test_llm_mock_returns_empty_schema_instance(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result == _Sample()


async def test_valid_json_response_is_parsed(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")

    async def _fake_call(*, model, max_tokens, system, user):
        return '{"fields": ["a", "b"], "unresolved": []}'

    monkeypatch.setattr(adapter, "_complete_openai_json", _fake_call)
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result.fields == ["a", "b"]


async def test_malformed_json_retries_once_then_returns_empty_schema(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    calls = []

    async def _fake_call(*, model, max_tokens, system, user):
        calls.append(user)
        return "not json"

    monkeypatch.setattr(adapter, "_complete_openai_json", _fake_call)
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result == _Sample()
    assert len(calls) == 2  # 1 lần gọi gốc + 1 lần retry kèm lỗi


async def test_retry_succeeds_on_second_attempt(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    responses = iter(["not json", '{"fields": ["c"], "unresolved": []}'])

    async def _fake_call(*, model, max_tokens, system, user):
        return next(responses)

    monkeypatch.setattr(adapter, "_complete_openai_json", _fake_call)
    result = await adapter.complete_json(tier="extraction", system="s", user="u", schema=_Sample)
    assert result.fields == ["c"]
```

- [ ] **Step 3: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_llm_adapter_json.py -v
```

Expected: `AttributeError: module 'worker.app.llm.adapter' has no attribute 'complete_json'`.

- [ ] **Step 4: Thêm `complete_json()` vào `worker/app/llm/adapter.py`**

Sửa phần import ở đầu file từ:

```python
import asyncio
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator

import yaml
```

thành:

```python
import asyncio
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)
```

Thêm hàm mới ngay sau `_complete_openai` (trước khối comment "Streaming variant"):

```python
async def complete_json(*, tier: str, system: str, user: str, schema: type[ModelT]) -> ModelT:
    """Như `complete()` nhưng trả một instance Pydantic đã validate thay vì
    text tự do — dùng cho lát 2 (trích xuất), nơi LLM phải trả field_key +
    line_id trỏ vào anchor thật, không phải văn xuôi.

    LLM_MOCK=true trả thẳng `schema()` rỗng (không gọi mạng) — MỌI schema
    dùng với hàm này phải có toàn bộ field mang default (xem
    ExtractionResult trong shared/extraction/schema.py), đúng bất biến
    LLM_MOCK vốn có của complete()/stream_complete() ở trên: pipeline chạy
    hết không cần key/mạng.

    Retry đúng 1 lần kèm lỗi validate trong prompt nếu JSON sai hình dạng;
    vẫn hỏng thì trả `schema()` rỗng — một document lỗi không được làm
    crash consumer đang xử lý các document khác.
    """
    if os.environ.get("LLM_MOCK", "false").lower() in ("1", "true", "yes"):
        return schema()

    cfg = _tier_config(tier)
    provider = cfg["provider"]
    if provider != "openai":
        raise ValueError(f"complete_json chỉ hỗ trợ provider 'openai' cho tier {tier!r}, nhận {provider!r}")
    model = cfg["model"]
    max_tokens = cfg.get("max_tokens", 4096)

    raw = await _complete_openai_json(model=model, max_tokens=max_tokens, system=system, user=user)
    try:
        return schema.model_validate_json(raw)
    except ValidationError as exc:
        retry_user = (
            f"{user}\n\nPhản hồi trước bị lỗi: {exc}\n"
            "Hãy sửa lại và CHỈ trả JSON hợp lệ đúng schema, không thêm chữ nào khác."
        )
        raw_retry = await _complete_openai_json(model=model, max_tokens=max_tokens, system=system, user=retry_user)
        try:
            return schema.model_validate_json(raw_retry)
        except ValidationError:
            return schema()


async def _complete_openai_json(*, model: str, max_tokens: int, system: str, user: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None)
    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or "{}"
```

- [ ] **Step 5: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_llm_adapter_json.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Thêm tier `extraction` vào `worker/config/models.yaml`**

Sửa:

```yaml
  reasoning:
    provider: openai
    model: Llama-3.3-70B-Instruct
    max_tokens: 8192

budget:
```

thành:

```yaml
  reasoning:
    provider: openai
    model: Llama-3.3-70B-Instruct
    max_tokens: 8192
  # Lát 2 — trích xuất field từ tài liệu RM nộp (structured output qua
  # complete_json()). Cùng OPENAI_BASE_URL/OPENAI_API_KEY (FPT AI Factory),
  # model riêng vì đây là tác vụ trích xuất, không phải tạo văn bản dài.
  extraction:
    provider: openai
    model: gemma-4-26B-A4B-it
    max_tokens: 2048

budget:
```

- [ ] **Step 7: Commit**

```bash
git add worker/app/llm/adapter.py worker/config/models.yaml pyproject.toml tests/test_llm_adapter_json.py
git commit -m "feat(worker): thêm complete_json() structured-output + tier extraction (gemma qua FPT)"
```

---

## Task 4: `shared/extraction/schema.py`

**Files:**
- Create: `shared/extraction/__init__.py` (rỗng)
- Create: `shared/extraction/schema.py`
- Test: `tests/test_extraction_schema.py`

**Interfaces:**
- Produces: `Anchor`, `ExtractedFieldClaim`, `ExtractionResult` (Pydantic) — dùng bởi mọi task sau (5-10).

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_extraction_schema.py`:

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_schema.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.extraction'`.

- [ ] **Step 3: Tạo `shared/extraction/__init__.py` (rỗng)**

```bash
touch shared/extraction/__init__.py
```

- [ ] **Step 4: Tạo `shared/extraction/schema.py`**

```python
"""Kiểu dữ liệu dùng chung giữa parser (spreadsheet/office/pdf/ocr), khớp
nhãn tất định (labels.py) và LLM structured-output. `Anchor` là hình dạng
DUY NHẤT mọi parser phải trả về — labels.py và prompt builder chỉ nhìn thấy
hình dạng này, không quan tâm nó đến từ định dạng file nào.

docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md §3, §6.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
```

- [ ] **Step 5: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_schema.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add shared/extraction/__init__.py shared/extraction/schema.py tests/test_extraction_schema.py
git commit -m "feat(extraction): thêm Anchor/ExtractedFieldClaim/ExtractionResult schema"
```

---

## Task 5: `shared/extraction/labels.py` — khớp nhãn tất định

**Files:**
- Create: `shared/extraction/labels.py`
- Test: `tests/test_extraction_labels.py`

**Interfaces:**
- Consumes: `shared.extraction.schema.Anchor`, `ExtractedFieldClaim` (Task 4).
- Produces: `match_labels(anchors: list[Anchor], field_keys: frozenset[str]) -> list[ExtractedFieldClaim]` — dùng bởi Task 10.

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_extraction_labels.py`:

```python
from shared.extraction.labels import match_labels
from shared.extraction.schema import Anchor


def test_matches_label_then_next_anchor_as_value():
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))

    assert len(claims) == 1
    assert claims[0].field_key == "total_assets"
    assert claims[0].line_id == "a2"
    assert claims[0].raw_value == "8000000000"
    assert claims[0].value_type == "number"
    assert claims[0].confidence == 1.0


def test_matches_same_line_label_colon_value():
    anchors = [Anchor(line_id="a1", text="Tổng tài sản: 8000000000")]
    claims = match_labels(anchors, frozenset({"total_assets"}))

    assert len(claims) == 1
    assert claims[0].line_id == "a1"
    assert claims[0].raw_value == "8000000000"


def test_tolerant_to_missing_diacritics_and_case():
    anchors = [
        Anchor(line_id="a1", text="TONG TAI SAN"),
        Anchor(line_id="a2", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert len(claims) == 1


def test_ignores_field_keys_not_requested():
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="8000000000"),
    ]
    claims = match_labels(anchors, frozenset({"net_revenue"}))
    assert claims == []


def test_keeps_only_first_match_per_field_key():
    anchors = [
        Anchor(line_id="a1", text="Tổng tài sản"),
        Anchor(line_id="a2", text="8000000000"),
        Anchor(line_id="a3", text="Tổng tài sản"),
        Anchor(line_id="a4", text="9000000000"),
    ]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert len(claims) == 1
    assert claims[0].raw_value == "8000000000"


def test_classifies_date_values():
    anchors = [Anchor(line_id="a1", text="Ngày định giá: 15/03/2026")]
    claims = match_labels(anchors, frozenset({"valuation_date"}))
    assert claims[0].value_type == "date"


def test_no_match_when_label_is_last_anchor():
    anchors = [Anchor(line_id="a1", text="Tổng tài sản")]
    claims = match_labels(anchors, frozenset({"total_assets"}))
    assert claims == []
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_labels.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.extraction.labels'`.

- [ ] **Step 3: Tạo `shared/extraction/labels.py`**

```python
"""Khớp nhãn tất định — tìm field bằng cách tìm một nhãn tiếng Việt biết
trước nằm cạnh (hoặc cùng dòng với) một giá trị, KHÔNG cần LLM. Chạy TRƯỚC
bước LLM (worker/app/agents/extraction.py) để field khớp chính xác/miễn phí
không bao giờ phải trả tiền gọi LLM, và để LLM chỉ còn phải xử lý field mà
cách này không tìm ra.

docs/superpowers/specs/2026-07-19-rm-intake-extraction-design.md §4, §5.
"""
from __future__ import annotations

import re
import unicodedata

from .schema import Anchor, ExtractedFieldClaim

# Nhãn (đã chuẩn hoá) -> field_key. Nhãn được chuẩn hoá qua _normalize()
# trước khi so khớp nên không cần liệt kê biến thể hoa/thường hay có/không
# dấu ở đây.
LABEL_TO_FIELD: dict[str, str] = {
    "tong tai san": "total_assets",
    "tong no phai tra": "total_liabilities",
    "von chu so huu": "total_equity",
    "tong nguon von": "total_capital_source",
    "tai san ngan han": "current_assets_total",
    "no ngan han": "current_liabilities",
    "tien va tuong duong tien": "cash_and_equivalents",
    "phai thu khach hang": "accounts_receivable",
    "hang ton kho": "inventory",
    "doanh thu thuan": "net_revenue",
    "gia von hang ban": "cogs",
    "loi nhuan sau thue": "net_profit_after_tax",
    "luu chuyen tien tu hoat dong kinh doanh": "cf_operating",
    "ma so thue": "tax_id",
    "ky tinh thue": "tax_period",
    "doanh thu tinh thue": "revenue_declared",
    "thue phai nop": "tax_payable",
    "thue da nop": "tax_paid",
    "ngay nop to khai": "filing_date",
    "co quan thue": "tax_authority",
    "mo ta tai san": "asset_description",
    "dia chi tai san": "asset_address",
    "gia tri dinh gia": "valuation_amount_vnd",
    "ngay dinh gia": "valuation_date",
    "don vi dinh gia": "valuer_name",
    "phuong phap dinh gia": "valuation_method",
    "so giay chung nhan dang ky kinh doanh": "business_registration_number",
    "ten doanh nghiep": "business_name",
    "nguoi dai dien phap luat": "legal_representative",
    "dia chi dang ky": "registered_address",
    "von dieu le": "charter_capital_vnd",
    "ngay dang ky": "registration_date",
}

_NUMBER_RE = re.compile(r"^-?[\d.,]+$")
_DATE_RE = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")
_LABEL_VALUE_RE = re.compile(r"^(.*?)[:\-–]\s*(.+)$")


def _normalize(text: str) -> str:
    """Hạ chữ thường + bỏ dấu tiếng Việt để khớp nhãn không phụ thuộc hoa/
    thường hay nhiễu OCR làm mất dấu."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d").strip()


def _classify_value(text: str) -> str:
    if _DATE_RE.search(text):
        return "date"
    if _NUMBER_RE.match(text.strip()):
        return "number"
    return "string"


def match_labels(anchors: list[Anchor], field_keys: frozenset[str]) -> list[ExtractedFieldClaim]:
    """Quét `anchors` theo thứ tự, thử 2 kiểu khớp cho mỗi anchor:

    1. "Nhãn: giá trị" trên CÙNG một anchor (phổ biến trong OCR/văn xuôi).
    2. Anchor là đúng một nhãn đã biết, giá trị nằm ở anchor NGAY SAU (phổ
       biến trong bảng spreadsheet/DOCX — nhãn và giá trị tách ô riêng).

    Chỉ giữ field_key nằm trong `field_keys` và chỉ giữ lần khớp ĐẦU TIÊN
    cho mỗi field_key.
    """
    claims: list[ExtractedFieldClaim] = []
    seen: set[str] = set()

    for i, anchor in enumerate(anchors):
        match = _LABEL_VALUE_RE.match(anchor.text)
        if match:
            label_part, value_part = match.group(1), match.group(2).strip()
            field_key = LABEL_TO_FIELD.get(_normalize(label_part))
            if field_key and field_key in field_keys and field_key not in seen and value_part:
                claims.append(
                    ExtractedFieldClaim(
                        field_key=field_key,
                        line_id=anchor.line_id,
                        value_type=_classify_value(value_part),
                        raw_value=value_part,
                        confidence=1.0,
                    )
                )
                seen.add(field_key)
                continue

        field_key = LABEL_TO_FIELD.get(_normalize(anchor.text))
        if field_key is None or field_key not in field_keys or field_key in seen:
            continue
        if i + 1 >= len(anchors):
            continue
        value_anchor = anchors[i + 1]
        raw = value_anchor.text.strip()
        if not raw:
            continue
        claims.append(
            ExtractedFieldClaim(
                field_key=field_key,
                line_id=value_anchor.line_id,
                value_type=_classify_value(raw),
                raw_value=raw,
                confidence=1.0,
            )
        )
        seen.add(field_key)

    return claims
```

- [ ] **Step 4: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_labels.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add shared/extraction/labels.py tests/test_extraction_labels.py
git commit -m "feat(extraction): khớp nhãn tất định (labels.py) — không qua LLM khi không cần"
```

---

## Task 6: `shared/extraction/spreadsheet.py` — parser XLSX

**Files:**
- Create: `shared/extraction/spreadsheet.py`
- Test: `tests/test_extraction_spreadsheet.py`

**Interfaces:**
- Consumes: `shared.extraction.schema.Anchor` (Task 4).
- Produces: `parse_xlsx(data: bytes) -> list[Anchor]` — dùng bởi Task 10.

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_extraction_spreadsheet.py`:

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_spreadsheet.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.extraction.spreadsheet'`.

- [ ] **Step 3: Tạo `shared/extraction/spreadsheet.py`**

```python
"""Parser XLSX — openpyxl trả địa chỉ ô thật miễn phí, nên đây là nguồn
anchor rẻ và chính xác nhất trong 4 định dạng (design spec §4).
"""
from __future__ import annotations

import io

import openpyxl

from .schema import Anchor


def parse_xlsx(data: bytes) -> list[Anchor]:
    """Trả một Anchor cho mỗi ô không rỗng, theo thứ tự hàng trong từng
    sheet. `line_id` là `{sheet}!{cell}` — trùng với `cell_ref`, vì với
    spreadsheet định danh anchor và vị trí có thể tra ngược là một."""
    workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    anchors: list[Anchor] = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                text = str(cell.value).strip()
                if not text:
                    continue
                ref = f"{sheet.title}!{cell.coordinate}"
                anchors.append(Anchor(line_id=ref, text=text, cell_ref=ref))
    return anchors
```

- [ ] **Step 4: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_spreadsheet.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add shared/extraction/spreadsheet.py tests/test_extraction_spreadsheet.py
git commit -m "feat(extraction): parser XLSX (openpyxl) — anchor = địa chỉ ô thật"
```

---

## Task 7: `shared/extraction/office.py` — parser DOCX

**Files:**
- Create: `shared/extraction/office.py`
- Test: `tests/test_extraction_office.py`

**Interfaces:**
- Consumes: `shared.extraction.schema.Anchor` (Task 4).
- Produces: `parse_docx(data: bytes) -> list[Anchor]` — dùng bởi Task 10.

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_extraction_office.py`:

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_office.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.extraction.office'`.

- [ ] **Step 3: Tạo `shared/extraction/office.py`**

```python
"""Parser DOCX — python-docx đọc đoạn văn và ô bảng. `line_id` mã hoá vị
trí cấu trúc (số thứ tự đoạn văn, hoặc bảng.hàng.cột) vì Word không có khái
niệm trang/bbox cố định như PDF (nội dung dàn lại khi render, không phải
layout cố định) — Anchor.bbox luôn None với nguồn này (design spec §4).
"""
from __future__ import annotations

import io

from docx import Document as DocxDocument

from .schema import Anchor


def parse_docx(data: bytes) -> list[Anchor]:
    doc = DocxDocument(io.BytesIO(data))
    anchors: list[Anchor] = []

    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if text:
            anchors.append(Anchor(line_id=f"p{i}", text=text))

    for t, table in enumerate(doc.tables):
        for r, row in enumerate(table.rows):
            for c, cell in enumerate(row.cells):
                text = cell.text.strip()
                if text:
                    anchors.append(Anchor(line_id=f"t{t}.{r}.{c}", text=text))

    return anchors
```

- [ ] **Step 4: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_office.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add shared/extraction/office.py tests/test_extraction_office.py
git commit -m "feat(extraction): parser DOCX (python-docx) — đoạn văn + bảng"
```

---

## Task 8: `shared/extraction/ocr.py` — Tesseract OCR

**Files:**
- Create: `shared/extraction/ocr.py`
- Test: `tests/test_extraction_ocr.py`

**Interfaces:**
- Consumes: `shared.extraction.schema.Anchor` (Task 4); binary hệ thống `tesseract` (Task 1, Step 4).
- Produces: `ocr_image(data: bytes, *, page: int | None = None, line_prefix: str = "ocr") -> list[Anchor]` — dùng bởi Task 9 (fallback bản scan) và Task 10 (PNG/JPEG trực tiếp).

**Điều kiện tiên quyết:** Task 1 Step 4 đã cài `tesseract-ocr` + `tesseract-ocr-vie` trên máy host. Nếu chưa, test ở đây fail với `pytesseract.TesseractNotFoundError`.

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_extraction_ocr.py`:

```python
import io

from PIL import Image, ImageDraw, ImageFont

from shared.extraction.ocr import ocr_image


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
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_ocr.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.extraction.ocr'`.

- [ ] **Step 3: Tạo `shared/extraction/ocr.py`**

```python
"""Tesseract OCR — nguồn anchor cho nội dung không có text layer (PDF bản
scan, PNG/JPEG upload trực tiếp). `image_to_data` trả bbox theo TỪ, gốc
trên-trái, đơn vị pixel; module này GỘP các từ cùng dòng (block/paragraph/
line) lại thành một Anchor mỗi dòng — nếu để mỗi từ một Anchor, nhãn nhiều
từ như "Tổng tài sản" (labels.py) sẽ không bao giờ khớp trọn vẹn.

Bbox trả về LUÔN ở pixel space, gốc trên-trái — pdf.py (Task 9) chịu trách
nhiệm quy đổi sang PDF-point/gốc dưới-trái khi nguồn là một trang PDF scan;
một PNG/JPEG độc lập không có khái niệm trang PDF để quy đổi về.
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
```

- [ ] **Step 4: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_ocr.py -v
```

Expected: 4 passed. (Nếu `test_ocr_image_returns_nonempty_anchors` fail vì OCR không đọc được text: tăng cỡ ảnh/font trong `_build_image`, không phải lỗi ở `ocr_image()`.)

- [ ] **Step 5: Commit**

```bash
git add shared/extraction/ocr.py tests/test_extraction_ocr.py
git commit -m "feat(extraction): OCR Tesseract (ocr.py) — gộp từ thành dòng trước khi trả anchor"
```

---

## Task 9: `shared/extraction/pdf.py` — text layer trước, OCR fallback, quy đổi toạ độ

**Files:**
- Create: `shared/extraction/pdf.py`
- Test: `tests/test_extraction_pdf.py`

**Interfaces:**
- Consumes: `shared.extraction.ocr.ocr_image` (Task 8), `shared.extraction.schema.Anchor` (Task 4), `scripts.pdf_utils.render_document_pdf` (đã có, dùng làm ground truth cho test).
- Produces: `parse_pdf(data: bytes) -> list[Anchor]` — dùng bởi Task 10.

**Ghi chú toạ độ quan trọng:** PyMuPDF (`fitz`) trả toạ độ theo gốc TRÊN-TRÁI (y tăng xuống dưới) — khác với quy ước PDF gốc/reportlab dùng gốc DƯỚI-TRÁI (y tăng lên trên) mà `scripts/pdf_utils.py` và `ExtractedField.bbox` hiện có đang dùng. Đã xác minh thực nghiệm bằng cách dựng 1 PDF qua `render_document_pdf`, đọc lại bằng PyMuPDF, và so khớp công thức lật trục `y0' = height - y1`, `y1' = height - y0` cho kết quả đúng tầm (chênh lệch ~0.4-2.6pt so với bbox reportlab tự ghi, do reportlab đệm thủ công vài điểm quanh baseline — không phải lỗi lật trục).

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_extraction_pdf.py`:

```python
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
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_extraction_pdf.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.extraction.pdf'`.

- [ ] **Step 3: Tạo `shared/extraction/pdf.py`**

```python
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
```

- [ ] **Step 4: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_extraction_pdf.py -v
```

Expected: 4 passed. (Nếu `test_parse_pdf_bbox_is_close_to_known_drawn_position` fail vượt tolerance: kiểm tra lại đúng `page.rect.height` chứ không phải `page.rect.y1` bị rotation ảnh hưởng — sample trong test không xoay trang nên không cần xử lý rotation.)

- [ ] **Step 5: Commit**

```bash
git add shared/extraction/pdf.py tests/test_extraction_pdf.py
git commit -m "feat(extraction): parser PDF — text layer PyMuPDF trước, OCR fallback, quy đổi toạ độ đúng gốc"
```

---

## Task 10: `worker/app/agents/extraction.py` — orchestrator

**Files:**
- Create: `worker/app/agents/extraction.py`

**Interfaces:**
- Consumes: `shared.extraction.{schema,labels,spreadsheet,office,ocr,pdf}` (Task 4-9), `shared.constants.DOC_TYPE_FIELD_CATALOG` (Task 2), `shared.storage.get_object_bytes` (đã có), `shared.db.get_session` (đã có), `shared.models.{Document,ExtractedField}` (đã có), `worker.app.llm.adapter.complete_json` (Task 3).
- Produces: `async def run_extraction(document_id: str) -> None` — dùng bởi Task 11.

**Không có unit test riêng cho task này** (Global Constraints + phần đầu plan giải thích lý do: cần Redis/Postgres/MinIO/LLM thật và đụng vấn đề trùng tên package `app` khi chạy trên host). Xác minh bằng bước "Xác minh cuối" ở cuối plan.

- [ ] **Step 1: Tạo `worker/app/agents/extraction.py`**

```python
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
from shared.models import Document, ExtractedField
from shared.storage import get_object_bytes

from app.llm.adapter import complete_json

_PARSERS = {
    "xlsx": parse_xlsx,
    "docx": parse_docx,
    "pdf": parse_pdf,
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

    _write_fields(document_id, deterministic_claims + llm_claims, anchors_by_id)
    print(
        f"[extraction] document {document_id}: {len(deterministic_claims)} field tất định, "
        f"{len(llm_claims)} field qua LLM",
        flush=True,
    )


async def _extract_via_llm(anchors: list[Anchor], field_keys: frozenset[str]) -> ExtractionResult:
    numbered_lines = "\n".join(f"{a.line_id}: {a.text}" for a in anchors)
    system = (
        "Bạn là trợ lý trích xuất dữ liệu tài chính. Chỉ trả lời bằng JSON đúng "
        "schema được yêu cầu. Không tự bịa toạ độ hay số liệu không có trong văn bản."
    )
    user = (
        f"Danh sách dòng văn bản (line_id: nội dung):\n{numbered_lines}\n\n"
        f"Tìm các trường sau trong danh sách trên: {sorted(field_keys)}.\n"
        "Với mỗi trường tìm được, trả field_key, line_id của dòng chứa giá trị đó "
        "(PHẢI là line_id có sẵn ở trên, không tự tạo line_id mới), value_type, "
        "raw_value đúng như trong văn bản, và confidence (0-1). Trường không tìm "
        "thấy thì liệt kê trong unresolved."
    )
    return await complete_json(tier="extraction", system=system, user=user, schema=ExtractionResult)


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
```

- [ ] **Step 2: Kiểm tra cú pháp/import bằng import thử trong container (không cần Docker build đầy đủ)**

```bash
cd worker && python3 -c "import ast; ast.parse(open('app/agents/extraction.py').read())" && cd ..
```

Expected: không lỗi (chỉ kiểm cú pháp — import thật sẽ được xác minh khi `docker compose up` ở Task 12/"Xác minh cuối", vì `from app.llm.adapter import complete_json` chỉ đúng nghĩa bên trong container).

- [ ] **Step 3: Commit**

```bash
git add worker/app/agents/extraction.py
git commit -m "feat(worker): extraction agent — điều phối parse -> khớp nhãn -> LLM -> ghi ExtractedField"
```

---

## Task 11: `worker/app/main.py` — consumer `_consume_extraction_jobs`

**Files:**
- Modify: `worker/app/main.py`

**Interfaces:**
- Consumes: `EXTRACTION_QUEUE` (Task 2, re-exported qua `app.config`), `run_extraction` (Task 10).
- Produces: consumer chạy song song `_consume_jobs`/`_consume_slink_jobs` trong `main()`.

**Không có unit test riêng** — cùng lý do Task 10 và cùng cách `_consume_jobs`/`_consume_slink_jobs` hiện tại không có test. Xác minh qua log khi `docker compose up` (Task 12/"Xác minh cuối").

- [ ] **Step 1: Thêm import**

Sửa:

```python
from app.config import ANALYZE_QUEUE, REDIS_URL, SLINK_SCORING_QUEUE, progress_channel
from app.slink.runner import process_scoring_job
from app.graph.build import Checkpointer, build_compiled_graph
```

thành:

```python
from app.agents.extraction import run_extraction
from app.config import ANALYZE_QUEUE, EXTRACTION_QUEUE, REDIS_URL, SLINK_SCORING_QUEUE, progress_channel
from app.slink.runner import process_scoring_job
from app.graph.build import Checkpointer, build_compiled_graph
```

- [ ] **Step 2: Thêm `_consume_extraction_jobs()`**

Chèn ngay sau hàm `_consume_slink_jobs()` (trước `async def main():`):

```python
async def _consume_extraction_jobs() -> None:
    """Vòng lặp tiêu thụ thứ ba — trích xuất field từ tài liệu RM nộp (lát
    2). Hàng đợi riêng khỏi ANALYZE_QUEUE/SLINK_SCORING_QUEUE: job trigger
    ngay khi upload MỘT document (không phải khi case đổi state), và một
    document lỗi không được chặn document/case khác."""
    r = aioredis.from_url(REDIS_URL)
    print(f"[worker] listening on redis list {EXTRACTION_QUEUE!r}", flush=True)
    while True:
        item = await r.brpop(EXTRACTION_QUEUE, timeout=5)
        if item is None:
            continue
        _key, raw = item
        document_id = json.loads(raw)["document_id"]
        print(f"[worker] dequeued extraction job for document {document_id}", flush=True)
        try:
            await run_extraction(document_id)
        except Exception as exc:  # noqa: BLE001 — job hỏng không được giết vòng lặp
            print(f"[worker] extraction job {document_id} failed: {exc}", flush=True)
```

- [ ] **Step 3: Gắn vào `main()`**

Sửa:

```python
    # Luồng xanh chạy song song luồng đỏ trong cùng process/event loop.
    asyncio.create_task(_consume_slink_jobs())

    async with Checkpointer() as saver:
```

thành:

```python
    # Luồng xanh chạy song song luồng đỏ trong cùng process/event loop.
    asyncio.create_task(_consume_slink_jobs())
    # Lát 2: trích xuất field, chạy song song hoàn toàn độc lập — trigger
    # theo document upload, không theo case state.
    asyncio.create_task(_consume_extraction_jobs())

    async with Checkpointer() as saver:
```

- [ ] **Step 4: Kiểm tra cú pháp**

```bash
cd worker && python3 -c "import ast; ast.parse(open('app/main.py').read())" && cd ..
```

Expected: không lỗi.

- [ ] **Step 5: Commit**

```bash
git add worker/app/main.py
git commit -m "feat(worker): gắn consumer _consume_extraction_jobs song song _consume_slink_jobs"
```

---

## Task 12: `api/app/routers/intake.py` — mở ALLOWED_MIME + enqueue

**Files:**
- Modify: `api/app/routers/intake.py`
- Modify: `tests/test_intake_upload.py`

**Interfaces:**
- Consumes: `shared.queue.EXTRACTION_QUEUE` (Task 2).
- Produces: mọi upload document mới (không phải bản trùng) đẩy 1 job `{"document_id": ...}` vào `EXTRACTION_QUEUE`.

- [ ] **Step 1: Viết test trước**

Sửa `tests/test_intake_upload.py` — thêm import và fixture `fake_redis` (autouse, theo đúng khuôn `_FakeRedis` đã dùng ở `tests/test_intake_submissions.py`), và 2 test mới. Thêm vào đầu file (sau import hiện có):

```python
import json

import pytest

from shared.db import get_session
from shared.models import Document
from shared.queue import EXTRACTION_QUEUE

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class _FakeRedis:
    def __init__(self) -> None:
        self.pushed: list[tuple[str, dict]] = []

    async def lpush(self, queue: str, raw: str) -> None:
        self.pushed.append((queue, json.loads(raw)))

    async def aclose(self) -> None:
        pass


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr("app.routers.intake.aioredis.from_url", lambda _url: fake)
    return fake
```

(Xoá dòng `PDF_BYTES = ...` cũ ở dưới nếu trùng — giữ đúng một định nghĩa duy nhất.)

Thêm 2 test vào cuối file:

```python
def test_upload_enqueues_extraction_job(client, case_id, fake_redis):
    response = _upload(client, case_id)
    document_id = response.json()["document_id"]

    assert fake_redis.pushed == [(EXTRACTION_QUEUE, {"document_id": document_id})]


def test_deduplicated_upload_does_not_enqueue_again(client, case_id, fake_redis):
    _upload(client, case_id)
    fake_redis.pushed.clear()

    _upload(client, case_id)  # cùng nội dung -> deduplicated

    assert fake_redis.pushed == []


def test_docx_upload_is_accepted():
    pass  # thay bằng test thật ở Step 4 sau khi sửa _upload/ALLOWED_MIME


def test_xlsx_upload_is_accepted():
    pass  # thay bằng test thật ở Step 4
```

Xoá 2 hàm `pass`-placeholder ở trên ngay, thay bằng bản thật (viết trước theo TDD, không để placeholder tồn tại quá 1 step):

```python
def test_docx_upload_is_accepted(client, case_id):
    response = _upload(
        client,
        case_id,
        content=b"PK\x03\x04fake-docx-bytes",
        filename="ke_hoach.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 201


def test_xlsx_upload_is_accepted(client, case_id):
    response = _upload(
        client,
        case_id,
        content=b"PK\x03\x04fake-xlsx-bytes",
        filename="bctc.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert response.status_code == 201
```

- [ ] **Step 2: Chạy test, xác nhận fail**

```bash
.venv/bin/pytest tests/test_intake_upload.py -v
```

Expected: `test_upload_enqueues_extraction_job` fail vì chưa enqueue gì (`fake_redis.pushed == []` thay vì có 1 phần tử); `test_docx_upload_is_accepted`/`test_xlsx_upload_is_accepted` fail với `422` (MIME chưa được whitelist).

- [ ] **Step 3: Mở `ALLOWED_MIME` trong `api/app/routers/intake.py`**

Sửa:

```python
ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg"}
```

thành:

```python
ALLOWED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
}
```

- [ ] **Step 4: Thêm import + enqueue sau khi upload thành công**

Sửa phần import đầu file từ:

```python
from __future__ import annotations

import hashlib
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.constants import REQUIRED_DOC_TYPES
from shared.db import get_session
from shared.models import Case, Document
from shared.schemas import Actor
from shared.state import (
    ALLOWED_TRANSITIONS,
    InvalidTransitionError,
    emit_event,
    transition_state,
)
from shared.storage import upload_bytes
```

thành:

```python
from __future__ import annotations

import hashlib
import json
import os
import re

import redis.asyncio as aioredis
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.constants import REQUIRED_DOC_TYPES
from shared.db import get_session
from shared.models import Case, Document
from shared.queue import EXTRACTION_QUEUE
from shared.schemas import Actor
from shared.state import (
    ALLOWED_TRANSITIONS,
    InvalidTransitionError,
    emit_event,
    transition_state,
)
from shared.storage import upload_bytes

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
```

Sửa cuối `upload_document` từ:

```python
        row.minio_key = key
        session.flush()

        return {
            "document_id": row.document_id,
            "sha256": digest,
            "doc_type": doc_type,
            "deduplicated": False,
        }
```

thành:

```python
        row.minio_key = key
        session.flush()
        document_id = row.document_id

    r = aioredis.from_url(REDIS_URL)
    try:
        await r.lpush(EXTRACTION_QUEUE, json.dumps({"document_id": document_id}))
    finally:
        await r.aclose()

    return {
        "document_id": document_id,
        "sha256": digest,
        "doc_type": doc_type,
        "deduplicated": False,
    }
```

(Lưu ý thụt lề: khối `return` giờ nằm NGOÀI `with get_session() as session:` — enqueue chỉ chạy sau khi transaction Postgres đã commit, không enqueue nếu ghi DB lỗi. Nhánh `deduplicated: True` ở phía trên giữ nguyên, KHÔNG đụng — tài liệu trùng không enqueue lại, tránh sinh `ExtractedField` trùng cho cùng một document đã trích xuất trước đó.)

- [ ] **Step 5: Chạy lại test, xác nhận pass**

```bash
.venv/bin/pytest tests/test_intake_upload.py -v
```

Expected: tất cả pass (10 test: 6 cũ + 4 mới).

- [ ] **Step 6: Chạy lại toàn bộ test suite intake để đảm bảo không phá gì**

```bash
.venv/bin/pytest tests/test_intake_create_case.py tests/test_intake_status.py tests/test_intake_submit.py tests/test_intake_minio_failure.py tests/test_intake_upload.py -v
```

Expected: tất cả pass.

- [ ] **Step 7: Commit**

```bash
git add api/app/routers/intake.py tests/test_intake_upload.py
git commit -m "feat(api): mở ALLOWED_MIME nhận DOCX/XLSX, enqueue EXTRACTION_QUEUE sau upload"
```

---

## Xác minh cuối (end-to-end, theo spec §10)

Không phải task riêng — chạy sau khi cả 12 task ở trên đã commit, xác minh toàn bộ pipeline thật (Task 10, 11 không có unit test nên đây là lần đầu chúng thực sự chạy):

```bash
docker compose up -d --build postgres minio redis api worker
docker compose logs worker --tail 30
# kỳ vọng thấy: "listening on redis list 'extraction_queue'"
```

```bash
CASE_ID=$(curl -s -X POST localhost:8000/cases -H 'Content-Type: application/json' -d '{
  "customer_id": "CUST-NTE", "product": "SME_WC",
  "requested_facility": {"amount_vnd": 8000000000, "tenor_months": 12}, "owner": "rm1"
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['case_id'])")

# Tạo 1 file XLSX thật có nhãn khớp tất định để kiểm nhánh không-qua-LLM
.venv/bin/python3 -c "
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'BCKQHDKD'
ws['B9'] = 'Tổng tài sản'
ws['C9'] = 8000000000
wb.save('/tmp/bctc_test.xlsx')
"

curl -s -X POST "localhost:8000/cases/$CASE_ID/documents" \
  -F "file=@/tmp/bctc_test.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  -F "doc_type=financial_statement"

sleep 3
docker compose exec postgres psql -U shbuser -d shbexpert -c \
  "SELECT field_key, value FROM extracted_fields ef JOIN documents d ON ef.document_id = d.document_id WHERE d.case_id = '$CASE_ID';"
```

Expected: có ít nhất 1 dòng `field_key = 'total_assets'`, `value->>'raw' = '8000000000'`, `value->>'cell_ref' = 'BCKQHDKD!C9'` — chứng minh nhánh khớp tất định (không qua LLM) hoạt động đúng qua toàn bộ đường ống thật (enqueue → worker consumer → parser → ghi DB).

Nếu muốn xác minh cả nhánh LLM: nộp thêm 1 PDF scan (ảnh chứa text) với `doc_type=valuation_certificate`, đợi vài giây, kiểm `extracted_fields` có field với `bbox IS NOT NULL` và `confidence < 1.0` (dấu hiệu field đến từ LLM, không phải khớp nhãn tất định).

---

## Self-Review

**Spec coverage:** đối chiếu từng mục spec `2026-07-19-rm-intake-extraction-design.md`:
- §2 phạm vi (ALLOWED_MIME + 4 doc_type) → Task 12.
- §3 kiến trúc (enqueue per-document, consumer riêng, LLM chỉ chọn line_id) → Task 2, 10, 11, 12.
- §4 parse theo định dạng + khớp nhãn áp dụng mọi nguồn → Task 5-9.
- §5 field catalog 4 doc_type → Task 2.
- §6 complete_json + tier extraction → Task 3.
- §7 hạ tầng (dependencies, Dockerfile, các file cụ thể) → Task 1, 2, 3, 10, 11, 12 (khớp đúng bảng file trong spec).
- §8 xử lý lỗi (parser lỗi không chặn job khác, LLM JSON hỏng retry-rồi-rỗng) → Task 3 (`complete_json`), Task 11 (`try/except` quanh từng job).
- §10 kiểm chứng → phần "Xác minh cuối".

**Placeholder scan:** không còn `pass`-placeholder nào trong Task 12 sau Step 1 (đã thay bằng test thật ngay trong cùng step, đúng nguyên tắc TDD — không để lại giữa các step).

**Type consistency:** `Anchor`/`ExtractedFieldClaim`/`ExtractionResult` (Task 4) dùng nhất quán tên field qua Task 5-10 (`line_id`, `field_key`, `value_type`, `raw_value`, `confidence`, `bbox`, `cell_ref`, `page`) — không có chỗ nào đổi tên giữa chừng.
