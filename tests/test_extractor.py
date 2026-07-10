from decimal import Decimal

import pytest

from app.core.extractor import ExtractionError, extract_price_inputs


def test_extract_standard_text() -> None:
    records = extract_price_inputs(
        """
        商家ID：123456
        商家名称：测试商家
        商品ID：sku001
        商品名称：测试套餐
        抖音商促价：100
        抖音超值券补贴：10
        抖音其他补贴：5
        美团商促价：100
        美团神券补贴：20
        美团其他补贴：0
        """
    )

    record = records[0]
    assert record.merchant_id == "123456"
    assert record.product_id == "sku001"
    assert record.douyin_promo_price == Decimal("100")
    assert record.meituan_magic_coupon_subsidy == Decimal("20")


def test_extract_ocr_friendly_aliases() -> None:
    records = extract_price_inputs(
        """
        商家 id：123456
        商品：测试套餐
        抖 音 商 促：￥100
        超值券金额：10元
        美团团购价：100
        神券力度：20
        """
    )

    record = records[0]
    assert record.merchant_id == "123456"
    assert record.product_name == "测试套餐"
    assert record.douyin_promo_price == Decimal("100")
    assert record.douyin_super_coupon_subsidy == Decimal("10")
    assert record.meituan_promo_price == Decimal("100")
    assert record.meituan_magic_coupon_subsidy == Decimal("20")


def test_extract_json_records() -> None:
    records = extract_price_inputs(
        """
        [
          {
            "merchant_id": "m1",
            "douyin_promo_price": 100,
            "douyin_super_coupon_subsidy": 10,
            "meituan_promo_price": 100,
            "meituan_magic_coupon_subsidy": 15
          }
        ]
        """,
        confidence=0.91,
    )

    assert records[0].merchant_id == "m1"
    assert records[0].confidence == 0.91


def test_missing_required_field() -> None:
    with pytest.raises(ExtractionError):
        extract_price_inputs("商家ID：123456 抖音商促价：100")
