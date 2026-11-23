# Phân luồng xanh/đỏ khi tiếp nhận hồ sơ — lát (a)

Ngày: 2026-07-19
Nhánh: `feat/lms-rm-upload`
Trạng thái: chờ duyệt

## 1. Bối cảnh

Ảnh nghiệp vụ (`~/Pictures/lms_router.jpeg`) mô tả LMS là **điểm bắt đầu chung
cho cả hai kênh khởi tạo**, và một Planner Agent phân luồng ngay khi tiếp nhận:

```
Credit Application (RM)  ─┐
                          ├─► Planner Agent (sản phẩm + hạn mức)
Mobile Banking KHDN      ─┘         │
                                    ├─► Luồng đỏ  → checklist → Credit Officer
                                    └─► Luồng xanh → ACAS-SLINK (tự động 100%)
```

Hệ thống hiện tại chỉ có luồng đỏ. `POST /cases` tạo thẳng một `Case` ở `DRAFT`
mà không hỏi hồ sơ này có thuộc diện tự động phê duyệt hay không.

### 1.1 Quan hệ với các lát trước

Lát 1 (`2026-07-19-rm-intake-backend-design.md`) đã dựng xong đường ghi của luồng
đỏ: tạo case, upload tài liệu, checklist, nộp thẩm định. Lát này thêm **cái ngã
ba phía trước nó**.

Hai lát sau, ngoài phạm vi tài liệu này:

| Lát | Nội dung |
|---|---|
| (b) | Domain SLINK + engine quyết định tự động (Profile, Cashflow, Behavioural, Sizing, Risk) |
| (c) | Lớp Operations cấp/điều chỉnh/treo hạn mức qua core-banking mock |

## 2. Quyết định kiến trúc: luồng xanh KHÔNG phải một `Case`

Đây là quyết định quan trọng nhất của lát này, và nó ngược với cách đặt vấn đề
ban đầu ("thêm state để bỏ qua Credit Officer").

`ALLOWED_TRANSITIONS` (`shared/state.py:244`) không có đường nào bỏ qua
`READY_FOR_REVIEW`, mà state đó thuộc sở hữu của Credit Officer (`data-flow.md`
§2). Nhưng vấn đề sâu hơn chuyện thiếu một transition: **luồng xanh không có
hình dạng của một đơn vay.** Nó không có tài liệu, không finding, không thẩm
định. Thực thể của nó là merchant + hạn mức thấu chi + chuỗi dòng tiền.

Nếu nhét vào `cases`, mọi cột của bảng đó (`requested_facility`, `owner`, và cả
`state`) đều vô nghĩa với luồng xanh.

**Quyết định: quyết định phân luồng nằm *phía trên* cả hai loại thực thể.**

```
submission ──► classify ──┬─► RED   → tạo Case (DRAFT), như lát 1
                          └─► GREEN → thực thể SLINK (lát b)
```

`ALLOWED_TRANSITIONS` **không đổi một dòng nào** ở lát này.

Bản prototype tham khảo đã đi tới cùng kết luận — `src/acas/types.ts` giữ
`SlinkMerchant` thành cây type riêng, không dùng chung `CreditCase`, vì "the
domain — merchant cashflow time series, overdraft limits — doesn't fit the
loan-application shape".

### 2.1 Không có view gộp

Luồng xanh không hiện trong hàng đợi Credit Officer, đúng tinh thần "không qua
Credit Officer" của ảnh nghiệp vụ. `GET /cases` giữ nguyên, chỉ trả luồng đỏ.

## 3. Phạm vi lát (a)

**Trong phạm vi:** điểm tiếp nhận chung, luật phân luồng, bảng `routing_decisions`,
và cái ngã ba — luồng đỏ tạo `Case` như cũ, luồng xanh ghi nhận quyết định.

**Ngoài phạm vi:** thực thể SLINK và engine chấm điểm (lát b); cấp hạn mức thật
(lát c); giao diện hai kênh (làm ở bước nối frontend, không phải backend).

Luồng xanh ở lát này **dừng ở chỗ ghi nhận** — `routing_decisions` có dòng
`lane=GREEN` nhưng chưa có thực thể SLINK nào được tạo. Đó là ranh giới có chủ
đích: lát (b) đọc chính những dòng đó làm đầu vào.

## 4. Luật phân luồng — tất định, không LLM

"Planner Agent" trong ảnh nghiệp vụ là một luật phân loại, không phải mô hình
ngôn ngữ. Giữ nó tất định để demo lặp lại được (PRD 14.4).

```
GREEN  ⟺  product == "MICRO_OD"
      AND segment == "MICROSME"
      AND amount_vnd <= 300_000_000

RED    ⟺  mọi trường hợp còn lại
```

Ba ngưỡng lấy từ `registries.ts` của bản tham khảo:
`AUTO_APPROVAL_ELIGIBLE_PRODUCTS = ['Thấu chi doanh nghiệp']`,
`AUTO_APPROVAL_CEILING_VND = 300_000_000`, và điều kiện `segment === 'MicroSME'`
trong `classifyRoutingLane`.

### 4.1 Taxonomy sản phẩm — dùng mã máy

Bản tham khảo dùng chuỗi tiếng Việt (`'Thấu chi doanh nghiệp'`) làm khóa so sánh.
Lát này **dùng mã** (`MICRO_OD`) vì chuỗi tiếng Việt làm khóa thì đổi chính tả
hay dấu là vỡ so sánh, mà lỗi đó lại im lặng — hồ sơ rơi nhầm luồng thay vì báo
lỗi. Tên tiếng Việt chỉ để hiển thị ở UI.

| Mã | Tên hiển thị | Luồng xanh? |
|---|---|---|
| `MICRO_OD` | Thấu chi doanh nghiệp | Có, nếu MicroSME và ≤ 300tr |
| `SME_WC` | Vay vốn lưu động SME | Không |
| `SME_TERM` | Vay đầu tư tài sản cố định | Không |

Hằng số đặt trong `shared/constants.py` cạnh `REQUIRED_DOC_TYPES`, cùng lý do:
một nguồn duy nhất để api và worker không lệch nhau.

## 5. Hợp đồng API

### 5.1 `POST /intake/submissions`

Cửa vào chung cho cả hai kênh. Thay thế việc gọi thẳng `POST /cases`.

```json
// request
{
  "channel": "RM_LMS",              // hoặc "MOBILE_KHDN"
  "customer_id": "CUST-NTE",
  "segment": "SME",                 // hoặc "MICROSME"
  "product": "SME_WC",
  "requested_facility": {"amount_vnd": 800000000, "tenor_months": 36},
  "owner": "rm1"
}
```

```json
// 201 — luồng đỏ
{
  "routing_decision_id": "...",
  "lane": "RED",
  "reason": "product SME_WC không thuộc diện tự động phê duyệt",
  "case_id": "C03"
}
```

```json
// 201 — luồng xanh
{
  "routing_decision_id": "...",
  "lane": "GREEN",
  "reason": "MICRO_OD, MicroSME, 150.000.000 ≤ 300.000.000",
  "case_id": null
}
```

`case_id` là `null` ở luồng xanh — **không phải thiếu sót, mà là điểm cốt lõi**:
luồng xanh không sinh ra case nào.

`reason` là chuỗi người đọc được, dựng từ chính luật ở §4. Nó phục vụ audit và
màn hình demo ("Planner Agent — phân luồng theo sản phẩm vay + hạn mức"), nên
phải nói rõ *vì sao*, không chỉ trả về nhãn.

### 5.2 `GET /intake/routing-decisions/{routing_decision_id}`

Đọc lại một quyết định phân luồng. Lát (b) dùng để lấy đầu vào cho engine SLINK.

### 5.3 `POST /cases` giữ nguyên

Không xoá, không đổi. Nó vẫn là đường tạo case trực tiếp cho luồng đỏ, và test
lát 1 vẫn phải xanh. `POST /intake/submissions` gọi lại chính logic đó ở nhánh
đỏ thay vì nhân bản.

## 6. Bảng `routing_decisions`

Migration mới `0009_intake_routing`.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `routing_decision_id` | String PK | default uuid |
| `channel` | String | `RM_LMS` \| `MOBILE_KHDN` |
| `lane` | String | `GREEN` \| `RED` |
| `customer_id` | String | |
| `segment` | String | `SME` \| `MICROSME` |
| `product` | String | mã sản phẩm |
| `amount_vnd` | BigInteger | 8 tỷ vượt Integer 32-bit → phải BigInteger |
| `tenor_months` | Integer | |
| `reason` | String | chuỗi người đọc được |
| `case_id` | FK cases, nullable | chỉ có ở luồng đỏ |
| `decided_at` | DateTime(tz) | |

`case_id` nullable là biểu hiện trực tiếp của quyết định ở §2 — luồng xanh
không trỏ tới case nào.

Giữ `lane`/`channel`/`segment` là `String` chứ không phải Postgres ENUM, cùng lý
do `Case.state` đã chọn (`shared/models.py:62`): thêm giá trị sau là sửa code,
không phải migration.

## 7. Xử lý lỗi

| Tình huống | Phản hồi |
|---|---|
| `channel` không thuộc 2 giá trị hợp lệ | `422` |
| `segment` không thuộc 2 giá trị hợp lệ | `422` |
| `product` không có trong bảng sản phẩm | `422` |
| `amount_vnd` ≤ 0 | `422` |

Không có lỗi 409/404 ở endpoint này — nó luôn tạo mới, không đụng thực thể sẵn có.

## 8. Kiểm chứng

1. `POST /intake/submissions` với `MICRO_OD` + `MICROSME` + 150tr → `lane: GREEN`,
   `case_id: null`, **không có row `cases` nào sinh ra**
2. Cùng như trên nhưng 350tr → `lane: RED`, có `case_id`, row `cases` ở `DRAFT`
3. `MICRO_OD` + `SME` (không phải MicroSME) + 150tr → `lane: RED`
4. `SME_WC` + `MICROSME` + 100tr → `lane: RED` (sản phẩm không đủ điều kiện)
5. Đúng ngưỡng 300.000.000 → `GREEN` (biên là ≤, không phải <)
6. `channel: MOBILE_KHDN` chạy đúng như `RM_LMS` — luật không phụ thuộc kênh
7. Luồng đỏ đi tiếp được: lấy `case_id` trả về, upload tài liệu, `intake-status`,
   `submit` — toàn bộ lát 1 vẫn chạy
8. `ALLOWED_TRANSITIONS` không đổi — test lát 1 xanh nguyên

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Ngưỡng 300tr là số của prototype, không phải chính sách SHB thật | Đặt trong `shared/constants.py` một chỗ, đổi là một dòng; ghi rõ nguồn trong comment |
| Lát (b) phát hiện `routing_decisions` thiếu cột nó cần | Chấp nhận — thêm cột là migration nhỏ, rẻ hơn đoán trước cột chưa dùng |
| `POST /cases` và `POST /intake/submissions` cùng tạo case, dễ lệch | Nhánh đỏ gọi lại đúng hàm tạo case của lát 1, không nhân bản logic |

## 10. Quyết định đã chốt

1. Luồng xanh là **domain riêng**, không thêm state vào `cases` (§2)
2. `ALLOWED_TRANSITIONS` **không đổi** ở lát này
3. **Không có view gộp** — `GET /cases` chỉ trả luồng đỏ (§2.1)
4. Phân luồng **tất định**, không LLM (§4)
5. Taxonomy dùng **mã máy** `MICRO_OD`/`SME_WC`/`SME_TERM`, tiếng Việt chỉ ở UI (§4.1)
6. Luồng xanh ở lát (a) **dừng ở ghi nhận**, chưa tạo thực thể SLINK (§3)
7. `POST /cases` **giữ nguyên**, không phá test lát 1 (§5.3)
