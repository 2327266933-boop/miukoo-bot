from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.price_record import ExtractedPriceInput, PriceRecord

PRICE_TOLERANCE = Decimal("0.01")


def calculate_final_price(promo_price: Decimal, coupon_subsidy: Decimal, other_subsidy: Decimal) -> Decimal:
    return promo_price - coupon_subsidy - other_subsidy


def build_price_record(
    extracted: ExtractedPriceInput,
    *,
    record_date: date,
    source_message_id: str,
    source_message_link: str | None = None,
    source_user_id: str | None = None,
) -> PriceRecord:
    douyin_final = calculate_final_price(
        extracted.douyin_promo_price,
        extracted.douyin_super_coupon_subsidy,
        extracted.douyin_other_subsidy,
    )
    meituan_final = calculate_final_price(
        extracted.meituan_promo_price,
        extracted.meituan_magic_coupon_subsidy,
        extracted.meituan_other_subsidy,
    )

    price_gap = douyin_final - meituan_final
    is_lose = douyin_final > meituan_final
    coupon_gap = extracted.meituan_magic_coupon_subsidy - extracted.douyin_super_coupon_subsidy
    reason_flag = int(
        is_lose
        and extracted.douyin_super_coupon_subsidy < extracted.meituan_magic_coupon_subsidy
        and coupon_gap >= price_gap
    )

    review_reasons: list[str] = []
    if _is_claimed_price_mismatched(extracted.douyin_final_price_claimed, douyin_final):
        review_reasons.append("抖音最终到手价与公式计算不一致")
    if _is_claimed_price_mismatched(extracted.meituan_final_price_claimed, meituan_final):
        review_reasons.append("美团最终到手价与公式计算不一致")
    if extracted.confidence is not None and extracted.confidence < 0.8:
        review_reasons.append("图文识别置信度低于0.8")
    if is_lose and reason_flag == 0:
        review_reasons.append("lose原因标记为0，需人工复核")

    return PriceRecord(
        **extracted.model_dump(),
        record_date=record_date,
        source_message_id=source_message_id,
        source_message_link=source_message_link,
        source_user_id=source_user_id,
        douyin_final_price=douyin_final,
        meituan_final_price=meituan_final,
        price_gap=price_gap,
        is_lose=is_lose,
        reason_flag=reason_flag,
        needs_manual_review=bool(review_reasons),
        review_reason="；".join(review_reasons) if review_reasons else None,
    )


def _is_claimed_price_mismatched(claimed: Decimal | None, calculated: Decimal) -> bool:
    if claimed is None:
        return False
    return abs(claimed - calculated) > PRICE_TOLERANCE
