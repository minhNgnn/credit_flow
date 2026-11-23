"""core-banking-mock — hạn mức thấu chi, phía GHI.

Tách khỏi slink-mock (chỉ đọc) chứ không gộp: quyền đọc dòng tiền và quyền
đổi hạn mức là hai thứ khác nhau, và trong hệ thống thật cũng là hai hệ
khác nhau. Gộp lại thì một service có cả quyền xem lẫn quyền cấp tiền.

Service này là NGUỒN SỰ THẬT của hạn mức. Postgres của hệ thống ghi lại đã
yêu cầu gì và nhận về gì, không tự tuyên bố hạn mức hiện tại — hai bên lệch
nhau thì bên này đúng.

⚠️ Trạng thái giữ trong bộ nhớ process: restart là mất sạch. Chấp nhận được
cho mock demo, nhưng nó nghĩa là DB có thể trỏ tới một hạn mức mà service
này đã quên. Hành vi đó được kiểm chứng có chủ đích (spec §9 bước 8) để
chắc hệ thống không sập khi trạng thái lệch, chứ không phải để giả vờ rằng
nó không xảy ra.

Spec: docs/superpowers/specs/2026-07-19-slink-operations-design.md §2
"""
from __future__ import annotations

import datetime as dt

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="core-banking-mock")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# customer_id -> trạng thái hạn mức
_OVERDRAFTS: dict[str, dict] = {}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class IssueRequest(BaseModel):
    limit_vnd: int = Field(gt=0)
    interest_rate_pct: float = Field(gt=0)
    reason: str = ""


class AdjustRequest(BaseModel):
    new_limit_vnd: int = Field(ge=0)
    reason: str = ""


class SuspendRequest(BaseModel):
    reason: str


@app.get("/core-banking/accounts/{customer_id}/overdraft")
def get_overdraft(customer_id: str) -> dict:
    record = _OVERDRAFTS.get(customer_id)
    if record is None:
        raise HTTPException(404, f"tài khoản {customer_id!r} chưa có hạn mức thấu chi")
    return record


@app.post("/core-banking/accounts/{customer_id}/overdraft", status_code=201)
def issue_overdraft(customer_id: str, body: IssueRequest) -> dict:
    """Cấp hạn mức mới.

    409 nếu đã có hạn mức đang hoạt động — chống cấp chồng. Bên gọi đã có
    guard riêng ở tầng DB (spec §3), nhưng service cũng phải tự bảo vệ:
    một mock dễ dãi sẽ che mất lỗi idempotency của bên gọi.
    """
    existing = _OVERDRAFTS.get(customer_id)
    if existing is not None and existing["status"] == "active":
        raise HTTPException(
            409,
            f"tài khoản {customer_id!r} đã có hạn mức {existing['limit_vnd']} đang hoạt động",
        )

    record = {
        "customer_id": customer_id,
        "status": "active",
        "limit_vnd": body.limit_vnd,
        "available_vnd": body.limit_vnd,
        "interest_rate_pct": body.interest_rate_pct,
        "issued_at": _now(),
        "last_adjusted_at": None,
        "reason": body.reason,
    }
    _OVERDRAFTS[customer_id] = record
    return record


@app.patch("/core-banking/accounts/{customer_id}/overdraft-limit")
def adjust_limit(customer_id: str, body: AdjustRequest) -> dict:
    record = _OVERDRAFTS.get(customer_id)
    if record is None:
        raise HTTPException(404, f"tài khoản {customer_id!r} chưa có hạn mức thấu chi")

    old_limit = record["limit_vnd"]
    record["limit_vnd"] = body.new_limit_vnd
    record["available_vnd"] = body.new_limit_vnd
    record["status"] = "reduced" if body.new_limit_vnd < old_limit else "active"
    record["last_adjusted_at"] = _now()
    record["reason"] = body.reason
    return record


@app.post("/core-banking/accounts/{customer_id}/overdraft/suspend")
def suspend_overdraft(customer_id: str, body: SuspendRequest) -> dict:
    record = _OVERDRAFTS.get(customer_id)
    if record is None:
        raise HTTPException(404, f"tài khoản {customer_id!r} chưa có hạn mức thấu chi")

    record["status"] = "suspended"
    record["available_vnd"] = 0
    record["last_adjusted_at"] = _now()
    record["reason"] = body.reason
    return record
