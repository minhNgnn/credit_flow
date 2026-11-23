> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# OCR/LLM Data Extraction — backend layer (slice 2) (English)

> Design spec. The English section below summarises context, decisions and scope; the full original (Vietnamese) follows.

**Date:** 2026-07-19 · **Branch:** `feat/lms-rm-upload` · **Status:** awaiting approval

## 1. Context
Slice 1 built the red lane's write path (RM submits a case → `Case` + `Document` in Postgres/MinIO) but left `extracted_fields` empty — until now only seed scripts populate it. Target pipeline: *RM submits → MinIO → OCR/extraction → `extracted_fields` → checklist → routing.*

## 3. Architecture
Each successful `POST /cases/{id}/documents` enqueues a job on `EXTRACTION_QUEUE`. The worker has its own consumer, `_consume_extraction_jobs()` (same pattern as `_consume_slink_jobs()`, separate queue so one bad job cannot block others), which calls `run_extraction()` in `worker/app/agents/extraction.py`:
1. download the bytes from MinIO (`shared/storage.py::get_object_bytes`)
2. parse by format → `list[Anchor(line_id, text, page, bbox | cell_ref)]`
3. deterministic label matching (`labels.py`) — matched fields **skip the LLM**
4. fields still missing → `complete_json()` (tier `extraction`)
5. write `ExtractedField` using the `field_id` resolved from real anchors

`extracted_fields` then feeds `financial.py` and the other agents as before.

**Key point: the LLM never invents coordinates or cell references.** Real anchors (bbox from PyMuPDF/Tesseract, cell_ref from openpyxl) get a numbered `line_id` before going into the prompt; the LLM only answers "field X is at line_id Y", and backend code maps `line_id → bbox/cell_ref` from the parser's own data. This is the only way to honour slice 1 §7 ("scanned PDFs must be OCR'd with real coordinates") without relying on an LLM's unreliable coordinates.

Sections 4–11 (parsing per format, field catalog per `doc_type`, structured LLM output, new infrastructure, error handling, risks, verification, decisions) are in the Vietnamese section.

---

<a id="vi"></a>

## 🇻🇳 Tiếng Việt

# Trích xuất dữ liệu bằng OCR/LLM — tầng backend (lát 2)

Ngày: 2026-07-19
Nhánh: `feat/lms-rm-upload`
Trạng thái: chờ duyệt

## 1. Bối cảnh

Lát 1 (`2026-07-19-rm-intake-backend-design.md`) đã dựng xong đường ghi của
luồng đỏ (RM nộp hồ sơ → `Case` + `Document` trong Postgres/MinIO) nhưng để
lại `extracted_fields` trống — bảng đó tới giờ chỉ được nạp bằng seed script
(`scripts/seed_case_c06.py`), tự nhận trong docstring là đứng thay cho toàn
bộ Document Processing Pipeline.

```
RM nộp hồ sơ → MinIO → OCR/trích xuất → extracted_fields → checklist → routing
└──────── lát 1 ────────┘└──── lát 2 (tài liệu này) ────┘└────── lát 3 ──────┘
```

Lát 1 §7 cố tình **không thiết kế trước hình dạng anchor**, chỉ khảo sát data
mẫu NTE (`~/Downloads/AIC/nos_agent/NTE/`: 130 PDF, 19 DOCX, 18 XLS/XLSX) và
ghi nhận anchor tự nhiên khác nhau theo định dạng — quyết định đó dành cho
lát này.

**Phạm vi luồng:** chỉ luồng đỏ (LMS). Luồng xanh (ACAS-SLINK) không có
`Case`/`Document` gì cả — input của nó là chuỗi giao dịch/cashflow, xử lý
bởi `shared/slink_engine.py`, không đi qua pipeline này.

## 2. Phạm vi

**Trong phạm vi:**
- Mở `ALLOWED_MIME` (`api/app/routers/intake.py:32`) nhận thêm DOCX/XLSX
  bên cạnh PDF/PNG/JPEG đã có.
- Trích xuất tự động, kích hoạt **ngay khi từng tài liệu được upload**
  (không chờ RM bấm nộp), chạy song song hoàn toàn độc lập với checklist.
- Field catalog cho cả 4 `doc_type` trong `REQUIRED_DOC_TYPES`.
- Ghi kết quả vào `extracted_fields` (bảng đã có từ lát 1, không cần
  migration — `ExtractedField.bbox` vốn đã là JSONB nullable).

**Ngoài phạm vi:**
- Mọi thay đổi trong `web/` — frontend không thuộc lát này.
- Checklist tự động và routing xanh/đỏ dựa trên kết quả trích xuất (lát 3).
- Cập nhật `Document.review_status` — vẫn giữ `PENDING`, việc duyệt là của
  con người ở lát sau.
- File nén (`.rar`/`.zip`) và các định dạng khác thấy trong data mẫu NTE
  nhưng không nằm trong 4 `doc_type` — không xử lý.

## 3. Kiến trúc tổng quan

```
POST /cases/{id}/documents (đã có, lát 1)
  → ghi MinIO + Postgres (đã có)
  → enqueue EXTRACTION_QUEUE {document_id}          ← MỚI
                    ↓
worker: _consume_extraction_jobs()                   ← MỚI, cùng pattern
  (worker/app/main.py, song song                        _consume_slink_jobs()
   _consume_jobs / _consume_slink_jobs)                 (queue riêng, một
                    ↓                                     job hỏng không
worker/app/agents/extraction.py :: run_extraction()      chặn job khác)
  1. tải bytes từ MinIO (shared/storage.py::get_object_bytes — đã có)
  2. parse theo định dạng → list[Anchor(line_id, text, page, bbox|cell_ref)]
  3. khớp nhãn tất định (labels.py) → field khớp thẳng, KHÔNG qua LLM
  4. field còn thiếu → complete_json() (gemma, tier "extraction")
  5. ghi ExtractedField theo field_id đã resolve từ anchor thật
                    ↓
extracted_fields (Postgres) → financial.py và các agent khác đọc như cũ
```

Điểm mấu chốt: **LLM không bao giờ tự bịa toạ độ/cell_ref.** Anchor thật
(bbox từ PyMuPDF/Tesseract, cell_ref từ openpyxl) được đánh số `line_id`
trước khi đưa vào prompt; LLM chỉ trả về "field X nằm ở line_id Y", code
backend tra ngược `line_id → bbox/cell_ref` từ chính dữ liệu parser đã có.
Đây là cách duy nhất giữ đúng yêu cầu lát 1 §7 ("PDF scan thì phải OCR kèm
toạ độ thật") mà không phụ thuộc độ chính xác toạ độ của LLM — vốn không
đáng tin cậy.

## 4. Parse theo định dạng

| Định dạng | Công cụ | Anchor |
|---|---|---|
| XLSX | `openpyxl` | `{sheet}!{cell}` — chính xác, miễn phí |
| DOCX (bảng + văn xuôi) | `python-docx` | `{table_idx}.{row}.{col}` hoặc đoạn văn thứ N |
| PDF có text layer | PyMuPDF `page.get_text("words")` | bbox thật, đơn vị PDF-point — khớp thẳng quy ước `scripts/pdf_utils.py` |
| PDF scan (không có text) | Raster hoá trang (PyMuPDF, DPI cố định) + Tesseract OCR | bbox pixel → quy đổi sang PDF-point bằng DPI và chiều cao trang |
| PNG/JPEG | Tesseract OCR trực tiếp | bbox pixel (không có khái niệm trang) |

Một trang PDF được coi là "scan" khi `page.get_text().strip()` rỗng/quá
ngắn — thử text layer thật trước luôn, chỉ OCR khi bắt buộc, vì text layer
thật vừa miễn phí vừa chính xác tuyệt đối.

**Khớp nhãn tất định (§3 bước 3) áp dụng cho MỌI nguồn, không riêng
XLSX/DOCX** — `labels.py` quét toàn bộ anchor list (bất kể đến từ
`openpyxl`, `python-docx`, PyMuPDF hay Tesseract) tìm nhãn tiếng Việt biết
trước (`"Tổng tài sản"`, `"Mã số thuế"`...) nằm cạnh một giá trị, không
phân biệt định dạng nguồn. XLSX/DOCX-bảng có tỷ lệ khớp cao nhất vì nhãn và
giá trị tách bạch theo ô/cột; OCR có tỷ lệ khớp thấp hơn do nhiễu ký tự —
field nào không khớp được mới rơi xuống bước LLM (§3 bước 4), bất kể định
dạng nguồn.

`ExtractedField.value` (JSONB, không cần migration) mang thêm `cell_ref` khi
nguồn là spreadsheet: `{"type": "number", "raw": "8000000000", "cell_ref":
"BCKQHDKD!C9"}` — không cần cột mới vì bảng vốn đã linh hoạt theo JSONB.

## 5. Field catalog theo `doc_type`

`financial_statement` dùng nguyên `REQUIRED_STATEMENT_FIELDS`
(`shared/constants.py:29`, 14 field) — đã có và đang được `financial.py`
tiêu thụ, không đổi tên hằng số này (tránh vỡ agent đang chạy).

Thêm `shared/constants.py::DOC_TYPE_FIELD_CATALOG: dict[str, frozenset[str]]`
gồm cả 4 loại, single-sourced cho `worker/app/agents/extraction.py` biết cần
tìm field gì theo từng `doc_type`:

- `financial_statement` → `REQUIRED_STATEMENT_FIELDS` (đã có)
- `tax_filing`: `tax_id`, `tax_period`, `revenue_declared`, `tax_payable`,
  `tax_paid`, `filing_date`, `tax_authority`
- `valuation_certificate`: `asset_description`, `asset_address`,
  `valuation_amount_vnd`, `valuation_date`, `valuer_name`,
  `valuation_method`
- `business_registration`: `business_registration_number`,
  `business_name`, `legal_representative`, `registered_address`,
  `charter_capital_vnd`, `registration_date`

3 catalog mới là bản nháp đầu tiên dựa trên khảo sát tên file/thư mục data
mẫu NTE (`bctc/`, `HỒ SƠ PHÁP LÝ NTE/`, `tai san *.pdf`...), **chưa có agent
nào tiêu thụ** — giữ vai trò tương tự `REQUIRED_STATEMENT_FIELDS` làm đích
ngắm cho lát này, sẽ tinh chỉnh khi có agent đọc thật (giống cách
`STATEMENT_BENCHMARK_VERSION` tự nhận là số liệu demo, không phải chính
sách thật).

## 6. Structured output — LLM

Thêm `worker/app/llm/adapter.py::complete_json()` cạnh `complete()` sẵn có:

```python
async def complete_json(*, tier: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
```

- Gọi qua OpenAI SDK với `response_format={"type": "json_object"}`.
- Validate bằng Pydantic; JSON sai hình dạng → retry 1 lần kèm thông báo lỗi
  trong prompt; vẫn hỏng thì trả kết quả rỗng (field đó rơi vào
  `unresolved`, không crash consumer).
- `LLM_MOCK=true` → trả thẳng `schema()` rỗng (không gọi mạng) — các field
  khớp tất định (XLSX/DOCX bảng) vẫn có dữ liệu thật; chỉ phần cần LLM (PDF,
  DOCX văn xuôi) rỗng trong demo mock, đúng tinh thần LLM_MOCK hiện tại
  (deterministic, không cần key).

Schema:

```python
class ExtractedFieldClaim(BaseModel):
    field_key: str
    line_id: str          # trỏ vào anchor list, KHÔNG phải toạ độ tự sinh
    value_type: Literal["number", "string", "date"]
    raw_value: str
    confidence: float = Field(ge=0, le=1)

class ExtractionResult(BaseModel):
    fields: list[ExtractedFieldClaim] = []
    unresolved: list[str] = []   # field_key model không tìm thấy
```

Cả hai field đều có default rỗng — bắt buộc để `schema()` (gọi không tham
số) hợp lệ ở nhánh `LLM_MOCK=true` của `complete_json()`.

`worker/config/models.yaml` thêm tier mới, tái dùng `OPENAI_BASE_URL`/
`OPENAI_API_KEY` đã trỏ sẵn tới FPT AI Factory (`https://mkp-api.fptcloud.com/v1`
— xác nhận trong `.env`), **không cần biến môi trường mới**:

```yaml
tiers:
  extraction:
    provider: openai
    model: gemma-4-26B-A4B-it
    max_tokens: 2048
```

## 7. Hạ tầng mới

| File | Thay đổi |
|---|---|
| `shared/queue.py` | thêm `EXTRACTION_QUEUE = "extraction_queue"` |
| `shared/constants.py` | thêm `DOC_TYPE_FIELD_CATALOG` (§5) |
| `api/app/routers/intake.py` | mở `ALLOWED_MIME` thêm DOCX/XLSX mime type; sau khi ghi `Document` thành công, `lpush` job vào `EXTRACTION_QUEUE` |
| `worker/app/agents/extraction.py` | `run_extraction(document_id)` — điều phối parse → khớp nhãn → LLM → ghi |
| `worker/app/extraction/{pdf,spreadsheet,office,ocr}.py` | parser theo định dạng (§4) |
| `worker/app/extraction/labels.py` | từ điển nhãn tiếng Việt → field_key, dùng cho khớp tất định |
| `worker/app/main.py` | thêm `_consume_extraction_jobs()`, cùng khuôn `_consume_slink_jobs()` (queue riêng, try/except quanh từng job, `asyncio.create_task()` trong `main()`) |
| `worker/requirements.txt` | `pytesseract`, `PyMuPDF`, `python-docx`, `openpyxl`, `Pillow` |
| `worker/Dockerfile` | `apt-get install tesseract-ocr tesseract-ocr-vie` (cùng khuôn `fonts-dejavu-core` trong `api/Dockerfile`) |

Không cần Alembic migration — `extracted_fields` đã đủ cột từ lát 1.

## 8. Xử lý lỗi

| Tình huống | Xử lý |
|---|---|
| Parser không đọc được file (corrupt, mã hoá lạ) | Log lỗi, không ghi `ExtractedField` nào cho document đó, job coi như xong (không retry vô hạn) |
| LLM trả JSON sai hình dạng | Retry 1 lần kèm lỗi; vẫn hỏng → field vào `unresolved`, không chặn các field khác |
| MinIO/Postgres lỗi giữa chừng | Job thất bại, log lỗi — job KHÔNG tự động retry (nhất quán với `_consume_slink_jobs`: một job hỏng không giết vòng lặp, nhưng cũng không có cơ chế requeue ở lát này) |
| Tesseract không cài/lỗi binary | Container worker crash khi start nếu thiếu — bắt lỗi sớm ở giai đoạn build Docker image, không phải runtime |

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Model `gemma-4-26B-A4B-it` không hỗ trợ `response_format=json_object` trên vLLM/FPT | Xác minh bằng 1 lệnh `curl` thủ công tới endpoint trước khi code; nếu không hỗ trợ, fallback sang prompt "chỉ trả JSON" + regex trích JSON block |
| OCR tiếng Việt (dấu) độ chính xác thấp với bản scan mờ | Đây là giới hạn vốn có của Tesseract, không giải quyết ở lát này; `confidence` thấp giúp lát 3/con người biết field nào cần soát lại |
| 3 field catalog mới (tax_filing/valuation_certificate/business_registration) có thể sai vì chưa có agent thật kiểm chứng | Đã nêu rõ ở §5 là bản nháp đầu tiên, không phải chính sách chốt |
| Mở `ALLOWED_MIME` cho DOCX/XLSX có thể lọt file độc hại (macro) | Ngoài phạm vi bảo mật của lát này — nếu cần, thêm sau ở tầng validate riêng |

## 10. Kiểm chứng

1. `docker compose up` — Postgres, MinIO, Redis, api, worker lên; `worker`
   log cho thấy đang nghe cả `ANALYZE_QUEUE`, `SLINK_SCORING_QUEUE`,
   `EXTRACTION_QUEUE`
2. `POST /cases` → `POST /cases/{id}/documents` với 1 file XLSX
   (`doc_type=financial_statement`) → trong vài giây, `SELECT * FROM
   extracted_fields WHERE document_id=...` có field khớp nhãn tất định,
   `value->>'cell_ref'` đúng địa chỉ ô thật
3. Nộp 1 PDF scan (`doc_type=valuation_certificate`) → `extracted_fields`
   có field với `bbox` khác NULL, `page` khớp số trang thật
4. Tắt `OPENAI_API_KEY`/set `LLM_MOCK=true` → luồng vẫn chạy hết không
   crash; field khớp tất định (XLSX/DOCX bảng) vẫn có; field cần LLM rỗng/
   `unresolved`
5. Nộp file corrupt (đổi đuôi `.pdf` từ file text ngẫu nhiên) → job log lỗi,
   không có row `extracted_fields` mồ côi, consumer vẫn sống để xử lý job
   tiếp theo
6. `financial.py` (agent thẩm định tài chính) chạy trên case có field từ
   OCR thật (không phải seed script) → `REQUIRED_STATEMENT_FIELDS` guardrail
   pass bình thường, chứng minh output tương thích ngược 100% với agent
   đang có

## 11. Quyết định đã chốt

1. Phạm vi chỉ luồng đỏ — không đụng SLINK/luồng xanh
2. Mở `ALLOWED_MIME` nhận thêm DOCX/XLSX ngay trong lát này
3. Trigger trích xuất **ngay khi từng document upload**, song song hoàn
   toàn với checklist — không chờ submit
4. XLSX/DOCX-bảng ưu tiên khớp nhãn tất định, không qua LLM khi không cần
5. PDF ưu tiên đọc text layer thật (PyMuPDF) trước khi OCR (Tesseract) —
   chỉ OCR khi trang thực sự là ảnh scan
6. LLM (gemma qua FPT, tier `extraction` trong `models.yaml`, tái dùng
   `OPENAI_BASE_URL`/`OPENAI_API_KEY` có sẵn) không bao giờ tự sinh toạ độ —
   chỉ chọn `line_id` trỏ vào anchor thật đã parse
7. Output LLM có cấu trúc qua `complete_json()` mới, tách khỏi `complete()`
   dùng cho các agent thẩm định — không ảnh hưởng financial/collateral/
   policy/customer360
8. Viết field catalog nháp cho cả 4 `doc_type` ngay bây giờ, dù 3 loại
   ngoài `financial_statement` chưa có agent tiêu thụ
9. Chạy trong `worker` (consumer mới `_consume_extraction_jobs`, cùng
   khuôn `_consume_slink_jobs`), không tách service riêng
10. Không cập nhật `Document.review_status` hay state machine — lát này
    chỉ ghi `extracted_fields`, gating/routing là việc của lát 3
