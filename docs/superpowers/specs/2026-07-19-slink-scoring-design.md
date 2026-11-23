# Domain SLINK + engine chấm điểm tự động — lát (b)

Ngày: 2026-07-19
Nhánh: `feat/lms-rm-upload`
Trạng thái: chờ duyệt

## 1. Bối cảnh

Lát (a) (`2026-07-19-intake-routing-design.md`) đã dựng ngã ba xanh/đỏ. Luồng
xanh hiện **dừng ở chỗ ghi nhận** — có dòng `routing_decisions` với `lane=GREEN`
nhưng chưa có gì chạy tiếp.

Lát này dựng đường đi của luồng xanh: thực thể SLINK, engine chấm điểm tất định,
và kết quả khuyến nghị hạn mức.

**Lát (b) kết thúc ở quyết định đã ghi + hạn mức khuyến nghị.** Việc *thực sự*
cấp/điều chỉnh/treo hạn mức qua core-banking là lát (c) — xem §8.

## 2. Khoảng trống phải lấp: engine cần dữ liệu hệ thống chưa có

`POST /intake/submissions` chỉ có `customer_id`, `segment`, `product`,
`amount_vnd`, `tenor_months`. Engine cần thêm:

| Cần | Dùng cho |
|---|---|
| `casa_retention_pct`, `payment_history_score` | Behavioural |
| `counterparty_quality`, `slink_tenure_months` | Behavioural |
| `circular_transaction_flag`, `night_transaction_share_pct` | Risk & Compliance |
| `industry`, `seasonality` | Profile |
| Chuỗi dòng tiền 60 ngày | Cashflow |

**Quyết định: service `slink-mock` riêng.** Không đặt trong `tools-mock` — file
`tools-mock/app/main.py:8` quy định chỉ `mcp-external` được gọi service đó, mà ở
đây cả `api` lẫn `worker` đều cần. Đây cũng đúng lý lẽ đã chốt cho LOS mock ở
spec `feat/nos_agent` §3.1: SLINK là hạ tầng nghiệp vụ của chính SHB, không phải
tra cứu bên thứ ba như CIC/KYC/AML.

`slink-mock` ở lát này **chỉ đọc**. Service ghi hạn mức (`core-banking-mock`) là
lát (c) — hai service khác nhau, đừng gộp.

### 2.1 Ai được gọi `slink-mock`

`api` (kiểm tồn tại lúc tiếp nhận) và `worker` (đọc đầy đủ để chấm điểm). Nêu rõ
ở đây vì đây là service mới, quy tắc phân tầng `overview.md` §4 chưa nhắc tới nó.

## 3. Ba kết cục của `POST /intake/submissions`

Quyết định "không có lịch sử SLINK thì chuyển luồng đỏ" biến endpoint từ hai
nhánh thành ba:

| # | Điều kiện | Lane ghi lại | Trả về |
|---|---|---|---|
| (a) | Luật §4 lát (a) không đạt | `RED` | `case_id`, đồng bộ |
| (b) | Luật đạt **nhưng** slink-mock trả 404 | `RED` | `case_id`, đồng bộ, `reason` ghi rõ lý do hạ luồng |
| (c) | Luật đạt **và** có merchant | `GREEN` | `slink_application_id`, **đã xếp hàng**, chưa có quyết định |

### 3.1 `classify_lane` giữ nguyên, tuyệt đối không đụng

Hàm ở `shared/routing.py` là **thuần** — không chạm DB, không gọi mạng — và đang
có 6 test xanh. Kiểm tồn tại merchant **không** được nhét vào đó.

Endpoint compose hai bước:

```
lane = classify_lane(...)          # thuần, như cũ
if lane == GREEN and not slink_mock.exists(customer_id):
    lane, reason = RED, "chưa có lịch sử giao dịch SLINK"
```

Hàm thuần và test của nó không đổi một dòng; chỉ endpoint có thêm nhánh.

### 3.2 Kiểm ở `api` lúc tiếp nhận, không hoãn xuống worker

Nếu để worker phát hiện thiếu merchant thì lúc đó đã lỡ trả `GREEN`, đã tạo thực
thể SLINK, đã mở SSE — rồi phải lật ngược sang đỏ và tạo case muộn. **Chốt luồng
trước khi cam kết nó.**

`api` chỉ cần biết có/không (200 hay 404); `worker` mới đọc đầy đủ chuỗi dòng
tiền. Một endpoint `GET /slink/merchants/{customer_id}` phục vụ cả hai.

### 3.3 Dòng bị hạ luồng ghi `lane=RED`, không phải GREEN

Luồng cuối thắng. Nếu ghi `GREEN` rồi gắn cờ phụ thì engine luồng xanh sẽ quét
trúng và xử lý một hồ sơ đáng lẽ thuộc về người. `reason` là chỗ giải thích:

```
"MICRO_OD, MICROSME, 150.000.000 ≤ 300.000.000 — nhưng chưa có lịch sử SLINK, chuyển luồng đỏ"
```

### 3.4 Sửa lại phát biểu của lát (a)

Spec lát (a) §3 viết *"lát (b) đọc chính những dòng lane=GREEN làm đầu vào"*.
Điều đó **không còn đúng** khi chạy bất đồng bộ: trigger là **job đã đẩy vào
queue**, không phải quét bảng. Quét bảng cộng với queue sẽ thành hai nguồn kích
hoạt và sinh ra bài toán idempotency không cần thiết.

### 3.5 slink-mock chết thì sao — 502, không âm thầm hạ luồng

Phân biệt hai chuyện:

- **404 (không có merchant)** — hợp lệ về nghiệp vụ → hạ luồng đỏ
- **Không gọi được service** — sự cố hạ tầng → **502**, không tạo gì cả

Chọn 502 có chủ đích: âm thầm đẩy mọi hồ sơ thấu chi sang luồng đỏ khi slink-mock
chết sẽ làm sự cố *vô hình* — hệ thống trông vẫn chạy đúng trong khi toàn bộ tự
động hoá đã tắt. Tiếp nhận thì thử lại được; một outage im lặng thì không.

## 4. Domain SLINK

Migration `0010_slink_domain`. Hai bảng, **không** đụng `cases`.

### 4.1 `slink_applications`

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `slink_application_id` | String PK | default uuid |
| `routing_decision_id` | FK routing_decisions | nguồn gốc |
| `customer_id` | String | |
| `amount_requested_vnd` | BigInteger | |
| `tenor_months` | Integer | |
| `status` | String | `QUEUED` \| `SCORING` \| `APPROVED` \| `REJECTED` \| `FAILED` |
| `recommended_limit_vnd` | BigInteger nullable | có khi APPROVED |
| `interest_rate_pct` | Float nullable | có khi APPROVED |
| `decision_reason` | String nullable | |
| `created_at` / `decided_at` | DateTime(tz) | `decided_at` nullable |

### 4.2 `slink_agent_decisions`

Vết chạy của từng agent — tương đương `findings` của luồng đỏ, nhưng phẳng hơn vì
không có phản biện hay version.

| Cột | Kiểu |
|---|---|
| `decision_id` | String PK |
| `slink_application_id` | FK |
| `agent_id` | String — `profile` \| `cashflow` \| `behavioural` \| `sizing_pricing` \| `risk_compliance` |
| `summary` | Text |
| `rationale` | JSONB (list[str]) |
| `metrics` | JSONB |
| `seq` | Integer — thứ tự chạy |
| `created_at` | DateTime(tz) |

### 4.3 Thêm cột vào `routing_decisions`

`slink_application_id` nullable, đối xứng với `case_id`: luồng đỏ set `case_id`,
luồng xanh set `slink_application_id`. Lát (a) §9 đã lường trước migration nhỏ này.

## 5. Chạy bất đồng bộ

Đi đúng khuôn luồng đỏ (`POST /cases/{id}/analyze` → Redis list → worker → pub/sub
→ SSE).

```python
# shared/queue.py
SLINK_SCORING_QUEUE = "slink_scoring_queue"

def slink_progress_channel(slink_application_id: str) -> str:
    return f"slink:{slink_application_id}:progress"
```

**Kênh tiến trình khoá theo `slink_application_id`, KHÔNG theo `case_id`** — luồng
xanh không có case nào. Đây lại là một xác nhận nữa rằng quyết định tách domain ở
lát (a) là đúng.

## 6. Engine — năm agent, đều tất định

Port từ `shb_credit_agents/src/acas/lib/agents.ts`, **chỉ phần đọc**. Không LLM,
để demo lặp lại được (PRD 14.4).

| Agent | Đầu vào | Đầu ra |
|---|---|---|
| `profile` | industry, seasonality, tenure | phân loại ngành |
| `cashflow` | chuỗi 60 ngày | doanh thu bình quân tháng, tăng trưởng MoM, biến động, số ngày im lặng |
| `behavioural` | CASA, lịch sử thanh toán, đối tác, tenure | điểm hành vi 0-100 |
| `sizing_pricing` | doanh thu bình quân + điểm hành vi | hạn mức đề xuất + lãi suất |
| `risk_compliance` | cờ giao dịch vòng, tỉ lệ giao dịch đêm | duyệt / chặn |

Công thức điểm hành vi giữ nguyên bản gốc:

```
score = 0.5*casa_retention_pct + 0.5*payment_history_score
      + counterparty_bonus   # tin cậy +10, trung bình 0, cần xác minh -15
      + tenure_bonus         # >= 24 tháng: +5
      (kẹp về [0, 100])
```

`risk_compliance` có quyền **chặn cứng**: `circular_transaction_flag` bật thì
`REJECTED` bất kể điểm bao nhiêu — giống cách agent Document Checklist của luồng
đỏ hard-fail khi phát hiện dấu hiệu giả mạo.

Đặt ở `worker/app/slink/` — cây riêng, không trộn vào `worker/app/agents/` (agent
luồng đỏ) vì hai domain khác nhau, đúng như bản tham khảo tách `src/acas/`.

## 7. Hợp đồng API

| Endpoint | Việc |
|---|---|
| `POST /intake/submissions` | Sửa: ba kết cục §3 |
| `GET /slink/applications/{id}` | Trạng thái + kết quả + vết chạy các agent |
| `GET /slink/applications/{id}/stream` | SSE tiến trình chấm điểm |
| `GET /slink/merchants/{customer_id}` | **Trên `slink-mock`**, không phải `api` |

```json
// POST /intake/submissions — kết cục (c)
{
  "routing_decision_id": "...",
  "lane": "GREEN",
  "reason": "MICRO_OD, MICROSME, 150.000.000 ≤ 300.000.000",
  "case_id": null,
  "slink_application_id": "...",
  "status": "QUEUED"
}
```

`case_id` và `slink_application_id` loại trừ nhau — đúng một cái khác null.

## 8. Ngoài phạm vi lát (b)

- **Cấp hạn mức thật.** `runOperationsAgent` gọi core-banking để issue/adjust/
  suspend là lát (c). Lát này dừng ở *khuyến nghị đã ghi*.
- **Đường sốc dòng tiền** (Dynamic Risk Control) — lát (c).
- **Màn console SLINK** đầy đủ như bản tham khảo — lát này chỉ cần `/lms` hiện
  được tiến trình và kết quả.

## 9. Kiểm chứng

1. Khách có merchant, thấu chi 150tr → `lane=GREEN`, có `slink_application_id`,
   `case_id` null, `status=QUEUED`
2. Đợi worker → `GET /slink/applications/{id}` trả `APPROVED` kèm
   `recommended_limit_vnd` > 0 và 5 dòng `slink_agent_decisions`
3. Khách **không** có merchant, cùng tham số → `lane=RED`, có `case_id`,
   `slink_application_id` null, `reason` nhắc tới lịch sử SLINK
4. Merchant có `circular_transaction_flag` → `REJECTED`, `recommended_limit_vnd`
   null, lý do nêu giao dịch vòng
5. Tắt `slink-mock` → `POST /intake/submissions` luồng xanh trả **502**, không
   tạo case lẫn application nào
6. Chạy lại cùng một khách hai lần → hai application độc lập, số liệu chấm điểm
   **giống hệt** (tất định)
7. `GET /cases` vẫn chỉ trả luồng đỏ — không có application SLINK nào lọt vào
8. `shared/routing.py` và test của nó **không đổi một dòng**

## 10. Quyết định đã chốt

1. `slink-mock` là **service riêng**, chỉ đọc; service ghi là lát (c) (§2)
2. `classify_lane` **giữ thuần**, kiểm tồn tại compose ở endpoint (§3.1)
3. Kiểm tồn tại ở **`api` lúc tiếp nhận**, không hoãn xuống worker (§3.2)
4. Dòng bị hạ luồng ghi **`lane=RED`**, `reason` giải thích (§3.3)
5. Trigger là **job trong queue**, không quét bảng — sửa phát biểu lát (a) (§3.4)
6. slink-mock chết → **502**, không âm thầm hạ luồng (§3.5)
7. Kênh tiến trình khoá theo **`slink_application_id`** (§5)
8. Engine đặt ở **`worker/app/slink/`**, tách khỏi agent luồng đỏ (§6)
9. Lát (b) dừng ở **khuyến nghị**, chưa cấp hạn mức thật (§8)
