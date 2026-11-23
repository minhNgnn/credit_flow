> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# RM Case Intake — backend layer (slice 1) (English)

> Design spec. The English section below summarises context, decisions and scope; the full original (Vietnamese) follows.

**Date:** 2026-07-19 · **Branch:** `feat/lms-rm-upload` (from `main`) · **Status:** awaiting approval

## 1. Context
The system stores data for real (Postgres + MinIO, real reportlab-generated PDFs) but **the path into the database is fake**: `scripts/seed_case_c06.py` writes `documents` + `extracted_fields` directly and admits in its docstring that it stands in for the whole Document Processing Pipeline. `api/app/routers/cases.py` has only the read side — no endpoint lets an RM submit a case. This slice builds the missing link toward a real LOS.

## 3. API contract (summary)
A new router, `api/app/routers/intake.py` (write side), kept apart from `cases.py` (read side, already 350+ lines). Four endpoints reuse existing infrastructure unchanged (`upload_bytes()`, `transition_state()`, `emit_event()`, `REQUIRED_DOC_TYPES`):
- `POST /cases` — create a case in `DRAFT`
- `POST /cases/{case_id}/documents` — upload a document
- `GET /cases/{case_id}/intake-status` — document checklist
- `POST /cases/{case_id}/submit` — submit for appraisal

**Key rules:** `doc_type` is chosen by the RM, never guessed (classification is slice 2); **write MinIO first, Postgres second** so a `documents` row never points to a missing object; no migration needed (only `cases` and `documents`, which already have the columns). Sections on write invariants, reused infrastructure, the slice-2 seam, verification, risks and decisions are in the Vietnamese section.

---

<a id="vi"></a>

## 🇻🇳 Tiếng Việt

# Tiếp nhận hồ sơ RM — tầng backend (lát 1)

Ngày: 2026-07-19
Nhánh: `feat/lms-rm-upload` (tách từ `main`)
Trạng thái: chờ duyệt

## 1. Bối cảnh

Hệ thống hiện lưu trữ thật (Postgres + MinIO, PDF thật do reportlab sinh) nhưng
**đường đi vào cơ sở dữ liệu là giả**: `scripts/seed_case_c06.py` ghi thẳng
`documents` + `extracted_fields`, tự nhận trong docstring rằng nó đứng thay cho
toàn bộ Document Processing Pipeline. `api/app/routers/cases.py` chỉ có phía đọc
— không tồn tại endpoint nào cho phép RM nộp hồ sơ.

Mắt xích còn thiếu để thành LOS thật:

```
RM nộp hồ sơ → MinIO → OCR/trích xuất → extracted_fields → checklist → routing
└──────── lát 1 ────────┘└──── lát 2 ────┘└────── lát 3 ──────┘
```

`documents`, `extracted_fields`, MinIO và toàn bộ phía đọc đã có sẵn.

### 1.1 Quan hệ với `2026-07-18-rm-intake-design.md`

Nhánh `feat/nos_agent` đã có một spec cùng chủ đề. Tài liệu này **kế thừa phần
backend của spec đó** (§3, §4) gần như nguyên vẹn và **bỏ toàn bộ phần frontend**
(§5, §6) vì hai lý do:

1. Spec cũ nhắm vào app Vite ở `src/`, thứ **không tồn tại trên `main`** — `main`
   chỉ có `web/` (Next.js). Mục §5, §6 của spec cũ không áp dụng được ở đây.
2. Nhóm chia việc theo tầng: frontend do người khác làm. Tầng backend phải độc
   lập với UI bên dưới, hai bên gặp nhau ở hợp đồng API tại §3.

Khác biệt có chủ đích so với spec cũ: **thêm `GET /cases/{id}/intake-status`**
(§3.3) và **nói rõ `doc_type` do RM chọn** (§4).

## 2. Phạm vi

Chỉ tầng API + storage + state.

**Xong lát 1 khi:** gọi được bằng `curl`, dữ liệu vào đúng Postgres + MinIO, case
mới hiện trong hàng đợi qua `GET /cases` sẵn có.

### Ngoài phạm vi

- Mọi thay đổi trong `web/` hoặc `src/` — frontend là việc của nhóm khác
- Trích xuất trường dữ liệu (lát 2)
- Checklist tự động và routing xanh/đỏ (lát 3)
- Xác thực / phân quyền
- LOS mock — spec cũ §3.1 chốt nó là service riêng; lát này không cần nó để đóng
  vòng demo, nên để lại cho lát sau

## 3. Hợp đồng API

Router mới `api/app/routers/intake.py`. Không nhét vào `cases.py`: file đó đã hơn
350 dòng và thuần phía đọc, còn tiếp nhận hồ sơ là phía ghi.

### 3.1 `POST /cases`

Tạo case ở `DRAFT`.

```json
// request
{
  "customer_id": "CUST-NTE",
  "product": "SME_WC",
  "requested_facility": {"amount_vnd": 8000000000, "tenor_months": 12},
  "owner": "rm1"
}
// 201
{"case_id": "C09", "state": "DRAFT"}
```

**`case_id` do server sinh, client không gửi.** `Case.case_id` là primary key
`String` **không có default** (`shared/models.py:56`) — khác `Document.document_id`
vốn có `default=_uuid` — nên tới giờ mọi `case_id` đều do script seed đặt tay
(`C06`, `C07`, `C08`, `CASE-CUS-00001`). Endpoint phải tự sinh, theo khuôn
`C{nn}` nối tiếp số lớn nhất đang có, trong cùng transaction để tránh đua.

Emit event qua `emit_event` (`shared/state.py:196`).

### 3.2 `POST /cases/{case_id}/documents`

Multipart. Dùng chung cho nộp mới và bổ sung.

| Trường | Bắt buộc | Ghi chú |
|---|---|---|
| `file` | có | PDF, PNG, JPEG |
| `doc_type` | có | Một trong `REQUIRED_DOC_TYPES`, do RM chọn (§4) |

```json
// 201
{"document_id": "...", "sha256": "...", "doc_type": "financial_statement", "deduplicated": false}
```

`deduplicated: true` khi `(case_id, sha256)` đã tồn tại — trả `document_id` cũ,
không tạo row mới.

### 3.3 `GET /cases/{case_id}/intake-status`

Endpoint này **không có trong spec cũ**. Nhóm frontend cần nó để vẽ checklist mà
không phải nhân bản `REQUIRED_DOC_TYPES` ở phía client — giữ hằng số
single-sourced trong `shared/constants.py:10` đúng như lý do file đó tồn tại.

```json
// 200
{
  "state": "DRAFT",
  "submitted": [{"doc_type": "financial_statement", "document_id": "...", "uploaded_at": "..."}],
  "missing": ["tax_filing", "valuation_certificate", "business_registration"],
  "can_submit": true
}
```

`can_submit` phản ánh `ALLOWED_TRANSITIONS` (state hiện tại có đi được sang
`INTAKE_VALIDATION` không), **không** phản ánh checklist đủ hay thiếu — gate
checklist thuộc lát 3. RM vẫn nộp được hồ sơ thiếu; `INTAKE_VALIDATION` sẽ trả về
`NEED_INFO`.

### 3.4 `POST /cases/{case_id}/submit`

`transition_state` → `INTAKE_VALIDATION`. Chạy được từ cả `DRAFT` lẫn `NEED_INFO`
nên **một endpoint phục vụ cả hai luồng**:

```
Nộp mới:    DRAFT ─────────► INTAKE_VALIDATION
Bổ sung:    NEED_INFO ─────► INTAKE_VALIDATION
```

`ALLOWED_TRANSITIONS` (`shared/state.py:244`) đã dựng sẵn cả hai. Không thêm state
mới.

## 4. `doc_type` do RM chọn, không tự đoán

Muốn biết một PDF là `financial_statement` hay `tax_filing` thì phải đọc nội dung
— mà đọc nội dung chính là trích xuất, tức lát 2. Nên `doc_type` là **tham số bắt
buộc** trong form multipart, RM chọn từ dropdown.

Checklist khi đó chỉ là phép so tập hợp với `REQUIRED_DOC_TYPES`, không có tí LLM
nào. Nếu lát 1 tự phân loại thì nó đã nuốt mất lát 2 và việc chia lát sụp đổ.

`REQUIRED_DOC_TYPES` = `financial_statement`, `tax_filing`,
`valuation_certificate`, `business_registration`.

## 5. Bất biến khi ghi

**Ghi MinIO trước, Postgres sau.** Không bao giờ có row `documents` trỏ tới object
không tồn tại. Chiều ngược lại (object mồ côi khi ghi DB lỗi) vô hại và dọn được
bằng job quét sau.

**Không ghi đè** (FR-02, `data-flow.md` §1). `minio_key` =
`{case_id}/{document_id}/{filename}`. Có `document_id` trong key nên nộp lại cùng
một loại giấy tờ tạo bản ghi mới, không đè bản cũ. `sha256` lưu cùng để chống
thay thế âm thầm.

**Chống trùng bằng `(case_id, sha256)`.** `Document.sha256` là `NOT NULL` nên
endpoint phải tính hash — tận dụng luôn làm cơ chế chống trùng.

`review_status` để mặc định `PENDING`. Giới hạn kích thước và whitelist kiểu file
kiểm tra tại endpoint.

### 5.1 Xử lý lỗi

| Tình huống | Phản hồi |
|---|---|
| `InvalidTransitionError` (`shared/state.py:257`) | `409` kèm state hiện tại |
| Case không tồn tại | `404` |
| `doc_type` không thuộc `REQUIRED_DOC_TYPES` | `422` |
| File sai kiểu hoặc quá lớn | `422` |
| MinIO lỗi | `502`, không tạo row `documents` |

## 6. Hạ tầng đã có, dùng lại nguyên vẹn

Lượng code mới rất nhỏ vì các mảnh sau đã tồn tại:

| Có sẵn | Dùng cho |
|---|---|
| `shared/storage.py:65` `upload_bytes(key, data, content_type) -> sha256` | Ghi file lên MinIO |
| `shared/storage.py:59` `ensure_bucket()` | Khởi tạo bucket |
| `shared/state.py:261` `transition_state(...)` | Chuyển state khi submit |
| `shared/state.py:196` `emit_event(...)` | Ghi audit trail |
| `shared/models.py:55,75` `Case`, `Document` | Bảng dữ liệu |
| `shared/constants.py:10` `REQUIRED_DOC_TYPES` | Xác định giấy tờ còn thiếu |

**Không cần migration.** Lát 1 chỉ ghi vào `cases` và `documents`, cả hai đã có
đủ cột.

## 7. Seam cho lát 2

Extraction cắm vào ở biên `INTAKE_VALIDATION`: đọc `documents`, ghi
`extracted_fields`. Hết.

`ExtractedField.bbox` đã là JSONB nullable nên không cần migration để đón lát 2;
lát 1 không ghi gì vào đó.

**Không thiết kế trước hình dạng anchor.** Khảo sát data mẫu NTE
(`~/Downloads/AIC/nos_agent/NTE/`, 130 PDF + 19 DOCX + 18 XLS/XLSX) cho thấy
anchor tự nhiên khác nhau theo định dạng: với spreadsheet là địa chỉ ô
(`BCKQHDKD!C9` — chính xác và miễn phí vì parser vốn đã biết), với PDF scan thì
phải OCR kèm toạ độ thật. Đó là quyết định của lát 2 khi đã có extractor thật,
không phải của lát 1.

## 8. Kiểm chứng

Lát 1 xong khi chạy được end-to-end trên máy thật, không phải chỉ qua test:

1. `docker compose up` — Postgres, MinIO, api lên
2. `POST /cases` → nhận `case_id`, xác nhận row ở state `DRAFT`
3. `POST /documents` 2 lần với 2 `doc_type` khác nhau → 2 row `documents` có
   `sha256` + `minio_key`, 2 object trong bucket MinIO
4. `GET /intake-status` → `submitted` có 2 loại vừa nộp, `missing` có 2 loại còn
   lại, tổng đúng 4
5. Nộp lại đúng file đã nộp → `deduplicated: true`, không sinh row thứ 3
6. `POST /submit` → state `INTAKE_VALIDATION`, có event trong bảng `events`
7. `GET /cases` → case mới có trong hàng đợi
8. `POST /submit` lần nữa → `409` (từ `INTAKE_VALIDATION` không đi tiếp được)
9. Chuyển case sang `NEED_INFO` bằng `transition_state` qua shell → nộp bổ sung →
   `POST /submit` → quay lại `INTAKE_VALIDATION`
10. Ngắt MinIO giữa chừng → `502`, xác nhận **không** sinh row `documents` mồ côi

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Hợp đồng API chốt sai, nhóm frontend làm theo rồi phải sửa | §3 là deliverable đầu tiên; đưa nhóm frontend duyệt trước khi implement |
| Hai spec cùng chủ đề (`feat/nos_agent` và nhánh này) gây nhầm | §1.1 nói rõ quan hệ kế thừa; spec cũ vẫn đúng cho phần frontend Vite nếu nhánh đó được dùng |
| `main` và `feat/nos_agent` phân kỳ tiếp, backend lát 1 khó merge | Lát 1 chỉ thêm file mới (`intake.py`) + 1 dòng đăng ký router, gần như không chạm code cũ |

## 10. Quyết định đã chốt

1. Phạm vi lát 1 là **backend thuần** — không đụng `web/` lẫn `src/`
2. `doc_type` **do RM chọn**, lát 1 không phân loại tự động (§4)
3. Thêm `GET /cases/{id}/intake-status` để frontend không nhân bản hằng số (§3.3)
4. Một endpoint `submit` phục vụ cả nộp mới lẫn bổ sung (§3.4)
5. `can_submit` phản ánh state machine, **không** phản ánh checklist — gate
   checklist thuộc lát 3 (§3.3)
6. Không thiết kế trước hình dạng anchor của lát 2 (§7)
