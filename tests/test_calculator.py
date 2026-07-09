from datetime import date
from decimal import Decimal

from app.core.calculator import build_price_record
from app.models.price_record import ExtractedPriceInput


def test_reason_flag_is_one_when_coupon_gap_covers_price_gap() -> None:
    extracted = ExtractedPriceInput(
        merchant_id="m1",
        product_id="p1",
        douyin_promo_price=Decimal("100"),
        douyin_super_coupon_subsidy=Decimal("10"),
        douyin_other_subsidy=Decimal("0"),
        meituan_promo_price=Decimal("100"),
        meituan_magic_coupon_subsidy=Decimal("15"),
        meituan_other_subsidy=Decimal("0"),
    )

    record = build_price_record(extracted, record_date=date(2026, 7, 9), source_message_id="msg1")

    assert record.is_lose is True
    assert record.price_gap == Decimal("5")
    assert record.reason_flag == 1


def test_reason_flag_is_zero_when_coupon_gap_does_not_cover_price_gap() -> None:
    extracted = ExtractedPriceInput(
        merchant_id="m1",
        product_id="p1",
        douyin_promo_price=Decimal("120"),
        douyin_super_coupon_subsidy=Decimal("10"),
        douyin_other_subsidy=Decimal("0"),
        meituan_promo_price=Decimal("100"),
        meituan_magic_coupon_subsidy=Decimal("15"),
        meituan_other_subsidy=Decimal("0"),
    )

    record = build_price_record(extracted, record_date=date(2026, 7, 9), source_message_id="msg1")

    assert record.is_lose is True
    assert record.price_gap == Decimal("25")
    assert record.reason_flag == 0
    assert record.needs_manual_review is True


def test_claimed_final_price_mismatch_needs_manual_review() -> None:
    extracted = ExtractedPriceInput(
        merchant_id="m1",
        douyin_promo_price=Decimal("100"),
        douyin_super_coupon_subsidy=Decimal("10"),
        douyin_other_subsidy=Decimal("0"),
        douyin_final_price_claimed=Decimal("88"),
        meituan_promo_price=Decimal("100"),
        meituan_magic_coupon_subsidy=Decimal("10"),
        meituan_other_subsidy=Decimal("0"),
    )

    record = build_price_record(extracted, record_date=date(2026, 7, 9), source_message_id="msg1")

    assert record.needs_manual_review is True
    assert "抖音最终到手价与公式计算不一致" in record.review_reason

