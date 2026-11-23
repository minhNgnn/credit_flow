> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# Operations — real limit issuance + dynamic risk control — slice (c) (English)

> Design spec. The English section below summarises context, decisions and scope; the full original (Vietnamese) follows.

**Date:** 2026-07-19 · **Branch:** `feat/lms-rm-upload` · **Status:** awaiting approval

## 1. Context
Slice (b) built the scoring engine but stops at a **recommendation**: `slink_applications` has `recommended_limit_vnd` and nothing outside the system changes. This is the **first slice with external side effects** — a difference in kind, not size: in earlier slices a mistake meant fixing the DB; here a mistake means a merchant holds an overdraft limit they should not have. Two paths: **Operations** (after the engine approves, really grant the limit through core-banking) and **Dynamic Risk Control** (cash flow drops → re-score → reduce the active limit).

## 2. `core-banking-mock` is the source of truth for limits
A new service, **write side** — unlike `slink-mock`, which is read-only. They are separate: the right to read cash flow and the right to change limits are different things, and are different systems in reality. **The actual limit is owned by core-banking**: our Postgres records what was *requested* and what was *received*, and never declares the current limit; if they differ, core-banking is right.

| Endpoint | Purpose |
|---|---|
| `POST /core-banking/accounts/{customer_id}/overdraft` | Grant |
| `PATCH /core-banking/accounts/{customer_id}/overdraft-limit` | Adjust |
| `POST /core-banking/accounts/{customer_id}/overdraft/suspend` | Suspend |
| `GET /core-banking/accounts/{customer_id}/overdraft` | Read state |

State is held in process memory: a restart loses it — acceptable for a mock but it means our DB may point at a limit core-banking has forgotten (verification §9 step 8 watches for exactly this).

## 3. Preventing a double grant — the real risk of this slice
A Redis job can be redelivered (worker dies midway, or someone re-queues by hand); if Operations ran twice, the merchant would get the limit twice. **The guard is a state transition in the DB, not an in-memory flag:** `APPROVED → ISSUING → ISSUED` (or `ISSUE_FAILED`). Operations only runs if it can move `APPROVED → ISSUING`, in a single `UPDATE … WHERE status = 'APPROVED'`; the loser of a race sees 0 rows changed and **exits at once** without calling core-banking. `ISSUING` exists for this — it is the lock, not a UI decoration.

## 6–7. Operations agent and Dynamic Risk Control
The Operations agent runs right after the engine, in the same scoring job (splitting it would require protecting against job loss between two stages for no gain). It is the **sixth** agent and the only one that *acts*; it still writes a `slink_agent_decisions` row so the trace is complete.

**Dynamic Risk Control** — `POST /slink/customers/{customer_id}/shock`, triggered by hand for demos: read the merchant from `slink-mock` with a shock parameter (`?shock_pct=`) → re-run `cashflow` + `risk_compliance` + `sizing_pricing` → if the new limit is lower, `PATCH` it down; if risk blocks, `POST suspend` → record a `slink_overdraft_events` row. It **does not create a new `SlinkApplication`** (it adjusts an existing limit; putting it in that table would corrupt the "number of applications" in reports). `slink-mock` accepts `shock_pct` to scale the last 30 days of cash flow, deterministically (no randomness).

Sections 4, 5, 8–10 (the full `slink_applications` states, the `slink_overdraft_events` table, out of scope, verification, decisions) are in the Vietnamese section.

---

<a id="vi"></a>

## 🇻🇳 Tiếng Việt

# Operations — cấp hạn mức thật + kiểm soát rủi ro động — lát (c)

Ngày: 2026-07-19
Nhánh: `feat/lms-rm-upload`
Trạng thái: chờ duyệt

## 1. Bối cảnh

Lát (b) dựng engine chấm điểm nhưng dừng ở **khuyến nghị**: `slink_applications`
có `recommended_limit_vnd` mà không có gì ngoài hệ thống thay đổi.

Lát này là lát đầu tiên **gây side effect ra ngoài**. Đó là khác biệt về bản
chất, không phải về khối lượng: mọi lát trước sai thì sửa DB là xong; lát này
sai thì một merchant có hạn mức thấu chi mà lẽ ra không được có.

Hai đường:

- **Operations** — sau khi engine duyệt, thực sự cấp hạn mức qua core-banking
- **Dynamic Risk Control** — dòng tiền sụt → chấm lại → giảm hạn mức đang hoạt động

## 2. `core-banking-mock` là nguồn sự thật của hạn mức

Service mới, **phía ghi** — khác `slink-mock` vốn chỉ đọc. Tách hai service chứ
không gộp: quyền đọc dòng tiền và quyền đổi hạn mức là hai thứ khác nhau, và
trong hệ thống thật cũng là hai hệ khác nhau.

**Hạn mức thực tế do core-banking nắm.** Postgres của ta ghi lại *đã yêu cầu gì*
và *nhận về gì*, không tự tuyên bố hạn mức hiện tại. Nếu hai bên lệch nhau thì
core-banking đúng.

| Endpoint | Việc |
|---|---|
| `POST /core-banking/accounts/{customer_id}/overdraft` | Cấp mới |
| `PATCH /core-banking/accounts/{customer_id}/overdraft-limit` | Điều chỉnh |
| `POST /core-banking/accounts/{customer_id}/overdraft/suspend` | Tạm khoá |
| `GET /core-banking/accounts/{customer_id}/overdraft` | Đọc trạng thái |

Trạng thái giữ trong bộ nhớ process. Restart là mất — chấp nhận được cho mock
demo, nhưng **phải ghi rõ** vì nó nghĩa là DB của ta có thể trỏ tới một hạn mức
mà core-banking đã quên. Kiểm chứng §9 bước 8 canh đúng chuyện đó.

## 3. Chống cấp hạn mức hai lần

Rủi ro thật của lát này. Job trong Redis có thể bị giao lại (worker chết giữa
chừng, hoặc ai đó đẩy lại tay). Nếu Operations chạy hai lần, merchant được cấp
hạn mức hai lần.

**Guard là chuyển trạng thái trong DB, không phải cờ trong bộ nhớ.**

```
APPROVED ──► ISSUING ──► ISSUED
                  └────► ISSUE_FAILED
```

Operations chỉ chạy khi chuyển được `APPROVED → ISSUING`, và phép chuyển đó nằm
trong một `UPDATE ... WHERE status = 'APPROVED'` — ai thua cuộc đua sẽ thấy 0
dòng bị đổi và **thoát ngay**, không gọi core-banking.

Đây là lý do trạng thái `ISSUING` tồn tại. Nó không phải bước trang trí cho UI;
nó là chỗ khoá.

### 3.1 Cấp thất bại thì KHÔNG được ghi là đã cấp

`ISSUE_FAILED` khác `REJECTED`: engine đã duyệt, chỉ là chưa cấp được. Phân biệt
hai cái vì cách xử lý khác nhau — `REJECTED` là kết luận cuối, `ISSUE_FAILED` là
thứ cần thử lại.

## 4. Trạng thái đầy đủ của `slink_applications`

```
QUEUED → SCORING → REJECTED                     (engine từ chối)
                 → APPROVED → ISSUING → ISSUED
                                      → ISSUE_FAILED
                 → FAILED                        (không đọc được dữ liệu)
```

`ISSUED` là trạng thái cuối của đường hạnh phúc — **không phải** `APPROVED`. Sau
lát này, một application dừng ở `APPROVED` nghĩa là có gì đó chưa xong.

## 5. Bảng `slink_overdraft_events`

Append-only, ghi mọi lần chạm vào hạn mức. Không sửa dòng cũ — cùng nguyên tắc
`events` của luồng đỏ (FR-12).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `event_id` | String PK | |
| `customer_id` | String | |
| `slink_application_id` | FK nullable | null với sự kiện không sinh từ một đề nghị (vd. sốc dòng tiền) |
| `action` | String | `ISSUE` \| `ADJUST` \| `SUSPEND` |
| `limit_before_vnd` / `limit_after_vnd` | BigInteger nullable | |
| `interest_rate_pct` | Float nullable | |
| `reason` | Text | |
| `succeeded` | Boolean | |
| `core_banking_response` | JSONB | nguyên văn phản hồi, để đối chiếu khi lệch |
| `created_at` | DateTime(tz) | |

Lưu nguyên văn phản hồi vì §2 đã nói core-banking là nguồn sự thật — khi hai bên
lệch, ta cần biết nó đã trả về đúng cái gì chứ không chỉ biết ta đã diễn giải ra
sao.

## 6. Operations agent

Chạy nối tiếp engine, trong cùng job chấm điểm. Không tách job riêng: tách ra thì
lại phải chống mất job giữa hai chặng, mà chẳng được gì.

Nó là agent thứ **sáu** và là agent duy nhất *hành động* — năm agent kia chỉ đọc
và tính. Ghi một dòng `slink_agent_decisions` như các agent khác để vết chạy đầy
đủ.

## 7. Dynamic Risk Control — sốc dòng tiền

`POST /slink/customers/{customer_id}/shock` — kích hoạt tay, phục vụ demo.

1. Đọc merchant từ `slink-mock` kèm tham số sốc (`?shock_pct=`)
2. Chạy lại `cashflow` + `risk_compliance` + `sizing_pricing`
3. Hạn mức mới < hạn mức hiện tại → `PATCH` giảm; risk chặn → `POST suspend`
4. Ghi `slink_overdraft_events`

**Không tạo `SlinkApplication` mới.** Đây là điều chỉnh hạn mức đang có, không
phải đề nghị mới. Nhét vào cùng bảng sẽ làm "số đề nghị" của báo cáo sai.

`slink-mock` nhận thêm tham số `shock_pct` để nhân dòng tiền 30 ngày gần nhất —
giữ tất định, không random.

## 8. Ngoài phạm vi

- Tự động quét định kỳ phát hiện sốc (cron). Lát này chỉ có kích hoạt tay.
- Console SLINK đầy đủ như prototype. `/lms` hiện kết quả là đủ.
- Hoàn tác việc cấp hạn mức.

## 9. Kiểm chứng

1. Luồng xanh đủ điều kiện → `status=ISSUED`, `GET /core-banking/.../overdraft`
   trả `active` đúng hạn mức, có 1 dòng `ISSUE` trong `slink_overdraft_events`
2. Có 6 dòng `slink_agent_decisions` (5 + operations)
3. **Đẩy lại đúng job đó lần hai → không có dòng `ISSUE` thứ hai**, hạn mức ở
   core-banking không đổi
4. Engine từ chối → `REJECTED`, **không gọi core-banking lần nào**, không có
   dòng overdraft event
5. Tắt `core-banking-mock` rồi nộp hồ sơ đủ điều kiện → `ISSUE_FAILED` (không
   phải `ISSUED`, cũng không phải `REJECTED`), event có `succeeded=false`
6. Sốc dòng tiền −60% trên merchant đang có hạn mức → hạn mức giảm, có dòng
   `ADJUST`, **không** sinh `SlinkApplication` mới
7. Sốc mạnh tới mức risk chặn → `SUSPEND`, core-banking trả `suspended`
8. Restart `core-banking-mock` → hạn mức mất; `GET /slink/applications/{id}` vẫn
   nói `ISSUED`. Đây là hành vi đã biết của mock, không phải bug — kiểm để chắc
   hệ thống không sập vì lệch trạng thái
9. Toàn bộ test lát (a)(b) vẫn xanh; `shared/routing.py` vẫn không đổi

## 10. Quyết định đã chốt

1. `core-banking-mock` là service **riêng**, phía ghi (§2)
2. Hạn mức thật do **core-banking** nắm; DB ta ghi yêu cầu + phản hồi (§2)
3. Chống cấp hai lần bằng **chuyển trạng thái có điều kiện trong DB**, không
   phải cờ bộ nhớ (§3)
4. `ISSUE_FAILED` **khác** `REJECTED` (§3.1)
5. `ISSUED` là trạng thái cuối của đường hạnh phúc, không phải `APPROVED` (§4)
6. Operations chạy **trong cùng job** chấm điểm (§6)
7. Sốc dòng tiền **không tạo** `SlinkApplication` mới (§7)
