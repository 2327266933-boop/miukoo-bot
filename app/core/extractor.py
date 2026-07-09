from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.price_record import ExtractedPriceInput


class ExtractionError(ValueError):
    pass


FIELD_ALIASES: dict[str, list[str]] = {
    "merchant_id": ["商家ID", "商家id", "门店ID", "门店id", "merchant_id"],
    "merchant_name": ["商家名称", "门店名称", "merchant_name"],
    "product_id": ["商品ID", "商品id", "product_id"],
    "sku_id": ["SKUID", "SKU ID", "sku_id", "sku"],
    "product_name": ["商品名称", "商品名", "品名", "product_name"],
    "douyin_promo_price": ["抖音商促价", "抖音活动价", "dy商促价", "douyin_promo_price"],
    "douyin_super_coupon_subsidy": ["抖音超值券补贴", "超值券补贴", "抖音超值券", "douyin_super_coupon_subsidy"],
    "douyin_other_subsidy": ["抖音其他补贴", "抖音非超值券补贴", "dy其他补贴", "douyin_other_subsidy"],
    "douyin_final_price_claimed": ["抖音最终到手价", "抖音到手价", "dy到手价", "douyin_final_price"],
    "meituan_promo_price": ["美团商促价", "美团活动价", "mt商促价", "meituan_promo_price"],
    "meituan_magic_coupon_subsidy": ["美团神券补贴", "神券补贴", "美团神券", "meituan_magic_coupon_subsidy"],
    "meituan_other_subsidy": ["美团其他补贴", "美团非神券补贴", "mt其他补贴", "meituan_other_subsidy"],
    "meituan_final_price_claimed": ["美团最终到手价", "美团到手价", "mt到手价", "meituan_final_price"],
}

MONEY_FIELDS = {
    "douyin_promo_price",
    "douyin_super_coupon_subsidy",
    "douyin_other_subsidy",
    "douyin_final_price_claimed",
    "meituan_promo_price",
    "meituan_magic_coupon_subsidy",
    "meituan_other_subsidy",
    "meituan_final_price_claimed",
}

REQUIRED_FIELDS = {
    "merchant_id",
    "douyin_promo_price",
    "douyin_super_coupon_subsidy",
    "meituan_promo_price",
    "meituan_magic_coupon_subsidy",
}


def extract_price_inputs(text: str, *, confidence: float | None = None) -> list[ExtractedPriceInput]:
    """Extract one or more price records from standard text or OCR text."""

    text = _normalize_text(text)
    json_records = _try_extract_json_records(text)
    if json_records:
        return [_build_input_from_mapping(record, confidence=confidence) for record in json_records]

    mapping: dict[str, Any] = {}
    for field, labels in FIELD_ALIASES.items():
        value = _find_labeled_value(text, labels, is_money=field in MONEY_FIELDS)
        if value is not None:
            mapping[field] = value

    return [_build_input_from_mapping(mapping, confidence=confidence)]


def _build_input_from_mapping(mapping: dict[str, Any], *, confidence: float | None) -> ExtractedPriceInput:
    normalized: dict[str, Any] = {}
    missing: list[str] = []

    for field in FIELD_ALIASES:
        value = _first_present_value(mapping, field)
        if value is None:
            if field in REQUIRED_FIELDS:
                missing.append(field)
            continue
        normalized[field] = _parse_money(value) if field in MONEY_FIELDS else str(value).strip()

    if missing:
        raise ExtractionError(f"字段缺失：{', '.join(missing)}")

    normalized.setdefault("douyin_other_subsidy", Decimal("0"))
    normalized.setdefault("meituan_other_subsidy", Decimal("0"))
    normalized["confidence"] = confidence
    normalized["raw_payload"] = mapping
    return ExtractedPriceInput(**normalized)


def _first_present_value(mapping: dict[str, Any], field: str) -> Any | None:
    if field in mapping and mapping[field] not in ("", None):
        return mapping[field]
    for alias in FIELD_ALIASES[field]:
        if alias in mapping and mapping[alias] not in ("", None):
            return mapping[alias]
    return None


def _try_extract_json_records(text: str) -> list[dict[str, Any]]:
    candidates = [text]
    json_block = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if json_block:
        candidates.insert(0, json_block.group(1))

    object_block = re.search(r"(\[.*\]|\{.*\})", text, flags=re.S)
    if object_block:
        candidates.insert(0, object_block.group(1))

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            records = payload.get("records")
            if isinstance(records, list):
                return [item for item in records if isinstance(item, dict)]
            return [payload]
    return []


def _find_labeled_value(text: str, labels: list[str], *, is_money: bool) -> str | None:
    for label in labels:
        escaped = re.escape(label)
        if is_money:
            pattern = rf"{escaped}\s*[:：=]?\s*(-?\d+(?:\.\d+)?)\s*(?:元|RMB|rmb)?"
        else:
            pattern = rf"{escaped}\s*[:：=]?\s*([^\s，,；;|]+)"
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(1).strip()
    return None


def _parse_money(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        raise ExtractionError(f"金额格式无法识别：{value}")
    try:
        return Decimal(match.group(0))
    except InvalidOperation as exc:
        raise ExtractionError(f"金额格式无法识别：{value}") from exc


def _normalize_text(text: str) -> str:
    return text.replace("\u3000", " ").strip()
