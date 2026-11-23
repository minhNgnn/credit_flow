"""slink-mock — hạ tầng SLINK của SHB, phía ĐỌC.

SLINK là rails tài khoản ảo của chính SHB, không phải tra cứu bên thứ ba
như CIC/KYC/AML — nên nó KHÔNG nằm trong tools-mock (service đó quy định
chỉ mcp-external được gọi, xem tools-mock/app/main.py:8, mà ở đây cả api
lẫn worker đều cần). Cùng lý lẽ đã chốt cho LOS mock.

Chỉ đọc. Service GHI hạn mức (core-banking-mock: issue/adjust/suspend) là
lát (c), một service khác — đừng gộp vào đây.

Tất định tuyệt đối: dòng tiền sinh bằng RNG có seed lấy từ chính
merchant_id, nên chạy lại bao nhiêu lần cũng ra cùng một chuỗi (PRD 14.4 —
demo phải sống sót khi mạng chết và phải lặp lại được).

Spec: docs/superpowers/specs/2026-07-19-slink-scoring-design.md
"""
from __future__ import annotations

import datetime as dt

from fastapi import FastAPI, HTTPException

app = FastAPI(title="slink-mock")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# RNG tất định — mulberry32, port từ shb_credit_agents/src/acas/data/
# merchants.ts. Dùng lại đúng thuật toán đó để chuỗi dòng tiền của bản port
# Python khớp về mặt tính chất (biến động, ngày im lặng) với prototype.
# ---------------------------------------------------------------------------
_U32 = 0xFFFFFFFF


def _mulberry32(seed: int):
    a = seed & _U32

    def rng() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & _U32
        t = a
        t = (t ^ (t >> 15)) * (t | 1) & _U32
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & _U32)) & _U32
        return ((t ^ (t >> 14)) & _U32) / 4294967296

    return rng


def _seed_from_id(merchant_id: str) -> int:
    h = 0
    for ch in merchant_id:
        h = (h * 31 + ord(ch)) & _U32
    return h


def _generate_cashflow(
    merchant_id: str,
    *,
    days: int,
    base_inflow_vnd: int,
    base_outflow_ratio: float,
    volatility: float,
    silent_day_chance: float,
    seasonal_peak_last_n_days: int = 0,
) -> list[dict]:
    rng = _mulberry32(_seed_from_id(merchant_id))
    today = dt.date.today()
    points: list[dict] = []

    for i in range(days - 1, -1, -1):
        is_silent = rng() < silent_day_chance
        seasonal_boost = 1.6 if seasonal_peak_last_n_days and i < seasonal_peak_last_n_days else 1.0
        noise = 1 + (rng() - 0.5) * 2 * volatility
        inflow = 0 if is_silent else round(base_inflow_vnd * seasonal_boost * noise)
        outflow = 0 if is_silent else round(inflow * base_outflow_ratio * (1 + (rng() - 0.5) * 0.2))
        points.append(
            {
                "date": (today - dt.timedelta(days=i)).isoformat(),
                "inflow_vnd": inflow,
                "outflow_vnd": outflow,
            }
        )
    return points


# ---------------------------------------------------------------------------
# Merchant tổng hợp — 5 hồ sơ phủ các kịch bản engine phải xử lý đúng:
# duyệt sạch, theo mùa, hành vi yếu, giao dịch vòng (chặn cứng), mới mở.
# Khoá theo customer_id vì đó là thứ POST /intake/submissions gửi lên.
# ---------------------------------------------------------------------------
_MERCHANTS: dict[str, dict] = {
    "CUST-SLINK": {
        "merchant_id": "slink-01",
        "name": "Quán Cà phê Bình Minh",
        "industry": "F&B",
        "seasonality": "đều quanh năm",
        "established_year": 2020,
        "slink_tenure_months": 30,
        "casa_retention_pct": 78,
        "payment_history_score": 88,
        "counterparty_quality": "tin cậy",
        "circular_transaction_flag": False,
        "night_transaction_share_pct": 10,
        "_cashflow": {"days": 60, "base_inflow_vnd": 15_000_000, "base_outflow_ratio": 0.62, "volatility": 0.15, "silent_day_chance": 0.02},
    },
    "CUST-HOAMAI": {
        "merchant_id": "slink-02",
        "name": "Cửa hàng Thời trang Hoa Mai",
        "industry": "Bán lẻ",
        "seasonality": "cao điểm cuối năm",
        "established_year": 2019,
        "slink_tenure_months": 24,
        "casa_retention_pct": 65,
        "payment_history_score": 75,
        "counterparty_quality": "trung bình",
        "circular_transaction_flag": False,
        "night_transaction_share_pct": 20,
        "_cashflow": {"days": 60, "base_inflow_vnd": 12_000_000, "base_outflow_ratio": 0.70, "volatility": 0.20, "silent_day_chance": 0.03, "seasonal_peak_last_n_days": 15},
    },
    "CUST-YEU": {
        "merchant_id": "slink-03",
        "name": "Tạp hoá Ánh Dương",
        "industry": "Bán lẻ",
        "seasonality": "đều quanh năm",
        "established_year": 2023,
        "slink_tenure_months": 8,
        "casa_retention_pct": 35,
        "payment_history_score": 48,
        "counterparty_quality": "cần xác minh",
        "circular_transaction_flag": False,
        "night_transaction_share_pct": 15,
        "_cashflow": {"days": 60, "base_inflow_vnd": 4_000_000, "base_outflow_ratio": 0.88, "volatility": 0.45, "silent_day_chance": 0.18},
    },
    "CUST-VONG": {
        "merchant_id": "slink-04",
        "name": "TM Dịch vụ Phúc Long Phát",
        "industry": "Thương mại điện tử",
        "seasonality": "đều quanh năm",
        "established_year": 2022,
        "slink_tenure_months": 14,
        "casa_retention_pct": 82,
        "payment_history_score": 91,
        "counterparty_quality": "cần xác minh",
        # Cờ này làm risk_compliance chặn cứng bất kể điểm cao — merchant
        # được dựng cố tình "đẹp" ở mọi chỉ số khác để chứng minh hard-fail
        # thắng điểm số, không phải chỉ kéo điểm xuống.
        "circular_transaction_flag": True,
        "night_transaction_share_pct": 68,
        "_cashflow": {"days": 60, "base_inflow_vnd": 40_000_000, "base_outflow_ratio": 0.97, "volatility": 0.30, "silent_day_chance": 0.01},
    },
    "CUST-LOGI": {
        "merchant_id": "slink-05",
        "name": "Vận tải Sao Mai",
        "industry": "Logistics",
        "seasonality": "theo mùa vụ",
        "established_year": 2021,
        "slink_tenure_months": 19,
        "casa_retention_pct": 70,
        "payment_history_score": 80,
        "counterparty_quality": "tin cậy",
        "circular_transaction_flag": False,
        "night_transaction_share_pct": 32,
        "_cashflow": {"days": 60, "base_inflow_vnd": 22_000_000, "base_outflow_ratio": 0.75, "volatility": 0.28, "silent_day_chance": 0.06},
    },
}


@app.get("/slink/merchants/{customer_id}")
def get_merchant(customer_id: str, shock_pct: float = 0.0) -> dict:
    """Hồ sơ merchant + chuỗi dòng tiền 60 ngày.

    404 khi khách hàng chưa có lịch sử SLINK — `api` dùng đúng mã này để
    hạ hồ sơ xuống luồng đỏ (spec §3.3). 404 là câu trả lời hợp lệ về
    nghiệp vụ, không phải lỗi.

    `shock_pct` mô phỏng cú sốc dòng tiền cho Dynamic Risk Control (lát c):
    nhân dòng tiền 30 ngày GẦN NHẤT với (1 - shock_pct/100). Áp lên nửa sau
    chứ không phải toàn chuỗi vì engine đo tăng trưởng bằng cách so nửa sau
    với nửa đầu — sốc đều cả chuỗi thì tỉ lệ không đổi và engine không thấy
    gì cả. Vẫn tất định: chỉ là phép nhân trên chuỗi đã sinh sẵn.
    """
    record = _MERCHANTS.get(customer_id)
    if record is None:
        raise HTTPException(404, f"khách hàng {customer_id!r} chưa có lịch sử giao dịch SLINK")

    spec = record["_cashflow"]
    merchant = {k: v for k, v in record.items() if k != "_cashflow"}
    merchant["customer_id"] = customer_id
    cashflow = _generate_cashflow(record["merchant_id"], **spec)

    if shock_pct > 0:
        factor = max(0.0, 1 - shock_pct / 100)
        half = len(cashflow) // 2
        for point in cashflow[half:]:
            point["inflow_vnd"] = round(point["inflow_vnd"] * factor)
            point["outflow_vnd"] = round(point["outflow_vnd"] * factor)

    merchant["cashflow"] = cashflow
    merchant["shock_pct"] = shock_pct
    return merchant
