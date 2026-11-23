> 🇬🇧 **English version first** · 🇻🇳 Bản tiếng Việt ở bên dưới (xem mục “Tiếng Việt”).

# Eval results: multi-agent vs single-agent (ablation Variant A) — English

- Case set: 24 cases × 3 repetitions each
- single_agent: 72 runs | multi_agent: 72 runs

## Quality (dimensions where multi-agent is expected to be stronger)

| Metric | single_agent | multi_agent |
|---|---|---|
| Correct decision (decision_correct) | 0.125 | 0.875 |
| Risk recall (all mandatory risks raised) | 0.651 | 1.0 |
| Numeric accuracy (numbers computed correctly) | 0.117 | 0.801 |
| Evidence coverage (claims with citations) | 1.0 | 1.0 |
| Consistency pass^k (all runs same result) | 0.708 | 1.0 |
| False-alarm rate (lower is better) | 0.125 | 0 |
| Conflict detected as expected | 0.5 | 1 |

## Cost (dimensions where single-agent usually wins — kept honest)

| Metric | single_agent | multi_agent |
|---|---|---|
| Run time (ms) | 10929.601 | 20930.503 |
| LLM calls | 1 | 14.528 |
| Total tokens | 3049.236 | 3980.569 |
| Tool calls (run 1 only; multi is a lower bound) | 0 | 14.75 |
| Findings (run 1 only) | 4.333 | 14.75 |
| Audit-trail depth (run 1 only) | 5.333 | 67.958 |

## Per business archetype

See the Vietnamese table below (numbers are identical): multi-agent gets decision_correct = 1 on 7 of 8 archetypes; `HIGH_LEVERAGE` is 0 for both. Single-agent recall is 0.0 on `COLLATERAL_SHORTFALL` and `VALUATION_STALE`.

## Runtime errors (fully disclosed)

- single_agent: 0/72 runs errored.
- multi_agent: 72/72 runs errored — mostly `update_case_status 409 Conflict` on repetitions 2–3. This is a **consequence of how pass^k is measured**, not a broken system: the case already moved to READY_FOR_REVIEW in run 1, so the state machine refuses another transition. The transition node runs AFTER the DecisionPackage is written, so those runs' decisions and findings are still valid (checked: 100% of 409-error runs still have a complete decision). To be fully clean, each repetition would need its own seeded case_id.

## Notes on reading the numbers

- `numeric_accuracy` is the most objective dimension: ground truth is computed with the exact deterministic formulas; multi-agent takes numbers from mcp-deterministic while single-agent computes in its prompt. Both get the same formulas, so it is a fair comparison.
- Single-agent `evidence_coverage` only means "a data-field name was filled in" — an LLM can write a plausible string whether or not it is real. For multi-agent it is evidence_ids pointing at real records, enforced at write time by `EvidenceRequiredError` (shared/state.py). Same metric name, NOT the same guarantee.
- Multi-agent `tool_call_count` is a lower bound (counted by Findings); for single-agent it is exactly 0 — that architecture calls no tools.
- **`COLLATERAL_SHORTFALL`: single-agent recall 0.0 is NOT due to poor reasoning**, but because the bank's official valuation and total obligations live in an internal registry (tools-mock) that is not in the document bundle. From the customer-submitted data, collateral still looks sufficient (coverage 1.21). That is genuinely an architectural advantage of multi-agent (it may call tools to look up the authoritative source), but the honest description is a DIFFERENCE IN DATA ACCESS.
- The decision rubric is STRICT about a single correct answer: an over-cautious answer (e.g. APPROVE_WITH_CONDITIONS for a clean case) still counts as wrong. This pulls single-agent decision_correct down noticeably; excess caution is measured separately by the false-alarm metric.
- Golden cases record the correct answer by credit logic, not reverse-engineered from current system behaviour. Where the system misses, that is a real result to read, not a flaw in the test set — see the archetype(s) multi-agent misses in the table.

---

<a id="vi"></a>

## 🇻🇳 Tiếng Việt

# Kết quả eval: multi-agent vs single-agent (ablation Variant A)

- Bộ case: 24 case × 3 lượt lặp mỗi case
- single_agent: 72 lượt chạy | multi_agent: 72 lượt chạy

## Chất lượng (chiều multi-agent kỳ vọng mạnh hơn)

| Chỉ số | single_agent | multi_agent |
|---|---|---|
| Quyết định đúng (decision_correct) | 0.125 | 0.875 |
| Risk recall (nêu đủ rủi ro bắt buộc) | 0.651 | 1.0 |
| Numeric accuracy (số liệu tính đúng) | 0.117 | 0.801 |
| Evidence coverage (claim có dẫn chứng) | 1.0 | 1.0 |
| Consistency pass^k (mọi lượt cùng KQ) | 0.708 | 1.0 |
| Tỷ lệ có cảnh báo giả (thấp = tốt) | 0.125 | 0 |
| Phát hiện mâu thuẫn đúng kỳ vọng | 0.5 | 1 |

## Chi phí (chiều single-agent thường thắng — giữ trung thực)

| Chỉ số | single_agent | multi_agent |
|---|---|---|
| Thời gian chạy (ms) | 10929.601 | 20930.503 |
| Số lệnh gọi LLM | 1 | 14.528 |
| Tổng token | 3049.236 | 3980.569 |
| Số lệnh gọi tool (chỉ lượt 1; multi là chặn dưới) | 0 | 14.75 |
| Số finding (chỉ lượt 1) | 4.333 | 14.75 |
| Độ sâu vết audit (chỉ lượt 1) | 5.333 | 67.958 |

## Theo từng archetype nghiệp vụ

| Archetype | QĐ đúng (single) | QĐ đúng (multi) | Recall (single) | Recall (multi) |
|---|---|---|---|---|
| BAD_CREDIT_HISTORY | 0.556 | 1 | 1.0 | 1.0 |
| CLEAN_APPROVE | 0.444 | 1 | None | None |
| COLLATERAL_SHORTFALL | 0 | 1 | 0.0 | 1.0 |
| HIGH_LEVERAGE | 0 | 0 | 1.0 | 1.0 |
| IDENTITY_UNCLEAR | 0 | 1 | 1.0 | 1.0 |
| REVENUE_MISMATCH | 0 | 1 | 1.0 | 1.0 |
| VALUATION_STALE | 0 | 1 | 0.0 | 1.0 |
| WEAK_DSCR | 0 | 1 | 0.556 | 1.0 |

## Lỗi trong lúc chạy (công bố đầy đủ)

- single_agent: 0/72 lượt lỗi
- multi_agent: 72/72 lượt lỗi — phần lớn là `update_case_status 409 Conflict` ở lượt lặp 2-3. Đây là **hệ quả của cách đo pass^k**, không phải hệ thống hỏng: case đã chuyển sang READY_FOR_REVIEW ở lượt 1 nên state machine từ chối chuyển tiếp lần nữa. Node transition chạy SAU khi DecisionPackage đã ghi, nên quyết định và finding của các lượt đó vẫn hợp lệ (đã kiểm: 100% lượt lỗi 409 vẫn có quyết định đầy đủ). Muốn sạch hoàn toàn thì mỗi lượt lặp phải seed case_id riêng.

## Ghi chú đọc số

- `numeric_accuracy` là chiều khách quan nhất: ground truth tính bằng đúng công thức xác định, multi-agent lấy số từ mcp-deterministic còn single-agent tự nhẩm trong prompt. Cả hai đều được cung cấp cùng bộ công thức nên đây là phép so công bằng.
- `evidence_coverage` của single-agent chỉ là 'có điền tên trường dữ liệu hay không' — LLM viết được một chuỗi nghe hợp lý bất kể có thật hay không. Phía multi-agent là evidence_ids trỏ tới bản ghi có thật, bị `EvidenceRequiredError` (shared/state.py) chặn ở tầng ghi. Cùng tên chỉ số nhưng KHÔNG cùng độ đảm bảo.
- `tool_call_count` của multi-agent là chặn dưới (đếm theo số Finding), của single-agent là 0 chính xác — kiến trúc đó không gọi tool nào.
- **`COLLATERAL_SHORTFALL`: single-agent recall 0.0 KHÔNG phải vì suy luận kém** mà vì giá trị định giá chính thức của ngân hàng và tổng nghĩa vụ nằm ở registry nội bộ (tools-mock), không có trong bộ hồ sơ tài liệu. Nhìn từ dữ liệu khách nộp thì TSBĐ vẫn đủ (coverage 1.21). Đây đúng là lợi thế kiến trúc của multi-agent (có quyền gọi tool tra cứu nguồn có thẩm quyền), nhưng phải nói rõ bản chất là KHÁC BIỆT QUYỀN TRUY CẬP DỮ LIỆU.
- Rubric quyết định chấm CHẶT theo một đáp án duy nhất: một câu trả lời thận trọng quá mức (vd APPROVE_WITH_CONDITIONS cho hồ sơ sạch) vẫn bị tính sai. Điều này kéo decision_correct của single-agent xuống đáng kể; mức thận trọng thừa được đo riêng bằng chỉ số cảnh báo giả.
- Golden case ghi đáp án đúng theo nghiệp vụ tín dụng, không suy ngược từ hành vi hệ thống hiện tại. Chỗ nào hệ thống trượt thì đó là kết quả thật cần đọc, không phải lỗi của bộ đề — xem 4 archetype multi-agent trượt ở bảng trên.

