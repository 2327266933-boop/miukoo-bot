from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass
class OcrResult:
    text: str
    confidence: float | None = None
    raw_payload: dict[str, Any] | None = None


class OcrClient(Protocol):
    async def recognize_image(self, image_bytes: bytes) -> OcrResult:
        ...


class FeishuOcrClient:
    OCR_URL = "https://open.feishu.cn/open-apis/optical_char_recognition/v1/image/basic_recognize"

    def __init__(
        self,
        *,
        access_token_provider: Callable[[], Awaitable[str]],
        timeout_seconds: float = 20.0,
    ) -> None:
        self.access_token_provider = access_token_provider
        self.timeout_seconds = timeout_seconds

    async def recognize_image(self, image_bytes: bytes) -> OcrResult:
        if not image_bytes:
            return OcrResult(text="", confidence=0.0, raw_payload={"skipped": "空图片内容"})

        token = await self.access_token_provider()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.OCR_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"image": image_base64},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        if payload.get("code") not in (None, 0):
            raise RuntimeError(f"飞书OCR识别失败：{payload}")

        return OcrResult(
            text=_extract_text(payload),
            confidence=_extract_confidence(payload),
            raw_payload=payload,
        )


class InternalOcrClient:
    def __init__(self, *, endpoint: str, token: str = "", timeout_seconds: float = 20.0) -> None:
        self.endpoint = endpoint
        self.token = token
        self.timeout_seconds = timeout_seconds

    async def recognize_image(self, image_bytes: bytes) -> OcrResult:
        if not self.endpoint:
            return OcrResult(text="", confidence=0.0, raw_payload={"skipped": "未配置内部OCR接口"})

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                files={"image": ("feishu-image.jpg", image_bytes, "image/jpeg")},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        return OcrResult(
            text=_extract_text(payload),
            confidence=_extract_confidence(payload),
            raw_payload=payload,
        )


def _extract_text(payload: dict[str, Any]) -> str:
    for key in ("text", "ocr_text", "content", "markdown"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for key in ("text_list", "texts"):
        value = payload.get(key)
        if isinstance(value, list):
            lines = [_stringify_text_item(item) for item in value]
            return "\n".join(line for line in lines if line)

    data = payload.get("data")
    if isinstance(data, dict):
        nested = _extract_text(data)
        if nested:
            return nested

    lines = payload.get("lines")
    if isinstance(lines, list):
        return "\n".join(_stringify_text_item(item) for item in lines)

    return ""


def _stringify_text_item(item: Any) -> str:
    if isinstance(item, dict):
        value = item.get("text") or item.get("content") or item.get("value")
        return str(value or "")
    return str(item)


def _extract_confidence(payload: dict[str, Any]) -> float | None:
    for key in ("confidence", "score", "prob"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_confidence(data)
    return None
