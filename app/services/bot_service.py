from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import Settings
from app.core.calculator import build_price_record
from app.core.extractor import ExtractionError, extract_price_inputs
from app.core.formatter import format_daily_summary, format_ingest_success, format_records
from app.services.feishu import FeishuClient
from app.services.ocr import InternalOcrClient
from app.services.storage import JsonlRecordStore
from app.services.table_exporter import DailyTableExporter


class BotService:
    def __init__(
        self,
        *,
        settings: Settings,
        feishu: FeishuClient,
        ocr: InternalOcrClient,
        store: JsonlRecordStore,
        table_exporter: DailyTableExporter,
    ) -> None:
        self.settings = settings
        self.feishu = feishu
        self.ocr = ocr
        self.store = store
        self.table_exporter = table_exporter
        self.tz = ZoneInfo(settings.timezone)

    async def handle_feishu_event(self, payload: dict[str, Any]) -> None:
        event = payload.get("event", {})
        message = event.get("message", {})
        if not message:
            return

        message_id = message.get("message_id", "")
        chat_id = message.get("chat_id", "")
        sender_id = event.get("sender", {}).get("sender_id", {}).get("user_id")
        message_text, image_keys = self._extract_message_parts(message)

        if await self._handle_command(message_text, message_id=message_id):
            return

        if not message_text and not image_keys:
            return

        try:
            combined_text = message_text
            confidence: float | None = None
            for image_key in image_keys:
                image_bytes = await self.feishu.download_image(image_key)
                ocr_result = await self.ocr.recognize_image(image_bytes)
                combined_text = "\n".join(part for part in [combined_text, ocr_result.text] if part)
                confidence = _merge_confidence(confidence, ocr_result.confidence)

            extracted_inputs = extract_price_inputs(combined_text, confidence=confidence)
            records = [
                build_price_record(
                    extracted,
                    record_date=datetime.now(self.tz).date(),
                    source_message_id=message_id,
                    source_message_link=self._build_message_link(chat_id, message_id),
                    source_user_id=sender_id,
                )
                for extracted in extracted_inputs
            ]
        except ExtractionError as exc:
            await self.feishu.reply_text(message_id, f"这条消息暂时无法完整结构化，原因：{exc}\n请补充缺失字段后重发或回复标准模板。")
            return
        except Exception as exc:
            await self.feishu.reply_text(message_id, f"处理消息时遇到异常：{exc}")
            return

        for record in records:
            self.store.append(record)

        await self.feishu.reply_text(message_id, format_ingest_success(records))

    async def send_daily_report(self) -> None:
        today = datetime.now(self.tz).date()
        records = self.store.list_by_date(today)
        summary = self.table_exporter.export(records, today)
        await self.feishu.send_text(self.settings.feishu_target_chat_id, format_daily_summary(summary))

    async def _handle_command(self, text: str, *, message_id: str) -> bool:
        clean_text = _strip_bot_mentions(text)
        if not clean_text:
            return False

        merchant_match = re.search(r"查询商家\s*([A-Za-z0-9_-]+)", clean_text)
        if merchant_match:
            merchant_id = merchant_match.group(1)
            records = self.store.find_by_merchant(merchant_id)
            await self.feishu.reply_text(message_id, format_records(records, title=f"商家 {merchant_id} 查询结果"))
            return True

        product_match = re.search(r"查询商品\s*([A-Za-z0-9_-]+)", clean_text)
        if product_match:
            product_id = product_match.group(1)
            records = self.store.find_by_product(product_id)
            await self.feishu.reply_text(message_id, format_records(records, title=f"商品 {product_id} 查询结果"))
            return True

        if "今日lose" in clean_text:
            today = datetime.now(self.tz).date()
            records = [record for record in self.store.list_by_date(today) if record.is_lose]
            await self.feishu.reply_text(message_id, format_records(records, title="今日lose记录"))
            return True

        if "原因0" in clean_text or "原因标记=0" in clean_text:
            today = datetime.now(self.tz).date()
            records = [
                record
                for record in self.store.list_by_date(today)
                if record.is_lose and record.reason_flag == 0
            ]
            await self.feishu.reply_text(message_id, format_records(records, title="今日原因标记=0记录"))
            return True

        return False

    def _extract_message_parts(self, message: dict[str, Any]) -> tuple[str, list[str]]:
        message_type = message.get("message_type", "")
        content = _loads_json_object(message.get("content", "{}"))
        if message_type == "text":
            return content.get("text", ""), []
        if message_type == "image":
            return "", [content.get("image_key", "")]
        if message_type == "post":
            return _extract_post_text(content), _extract_image_keys(content)
        return _extract_post_text(content), _extract_image_keys(content)

    def _build_message_link(self, chat_id: str, message_id: str) -> str | None:
        if not chat_id or not message_id:
            return None
        return f"feishu://message?chat_id={chat_id}&message_id={message_id}"


def _loads_json_object(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_post_text(content: dict[str, Any]) -> str:
    texts: list[str] = []
    post = content.get("post", {})
    for locale_payload in post.values() if isinstance(post, dict) else []:
        for line in locale_payload.get("content", []):
            for item in line:
                if item.get("tag") == "text":
                    texts.append(item.get("text", ""))
    return "\n".join(texts)


def _extract_image_keys(content: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    post = content.get("post", {})
    for locale_payload in post.values() if isinstance(post, dict) else []:
        for line in locale_payload.get("content", []):
            for item in line:
                if item.get("tag") == "img" and item.get("image_key"):
                    keys.append(item["image_key"])
    return keys


def _strip_bot_mentions(text: str) -> str:
    return re.sub(r"@\S+\s*", "", text or "").strip()


def _merge_confidence(left: float | None, right: float | None) -> float | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)
