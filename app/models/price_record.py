from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ExtractedPriceInput(BaseModel):
    merchant_id: str
    merchant_name: str | None = None
    product_id: str | None = None
    sku_id: str | None = None
    product_name: str | None = None

    douyin_promo_price: Decimal
    douyin_super_coupon_subsidy: Decimal
    douyin_other_subsidy: Decimal = Decimal("0")
    douyin_final_price_claimed: Decimal | None = None

    meituan_promo_price: Decimal
    meituan_magic_coupon_subsidy: Decimal
    meituan_other_subsidy: Decimal = Decimal("0")
    meituan_final_price_claimed: Decimal | None = None

    raw_payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None


class PriceRecord(ExtractedPriceInput):
    record_id: str = Field(default_factory=lambda: uuid4().hex)
    record_date: date
    source_message_id: str
    source_message_link: str | None = None
    source_user_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    douyin_final_price: Decimal
    meituan_final_price: Decimal
    price_gap: Decimal
    is_lose: bool
    reason_flag: int
    needs_manual_review: bool
    review_reason: str | None = None


class DailySummary(BaseModel):
    record_date: date
    total_records: int
    lose_count: int
    reason_flag_1_count: int
    reason_flag_0_count: int
    manual_review_count: int
    daily_sheet_url: str | None = None
    reason_zero_sheet_url: str | None = None
