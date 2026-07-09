from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OcrResult:
    text: str
    confidence: float | None = None
    raw_payload: dict[str, Any] | None = None


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

    data = payload.get("data")
    if isinstance(data, dict):
        nested = _extract_text(data)
        if nested:
            return nested

    lines = payload.get("lines")
    if isinstance(lines, list):
        return "\n".join(str(item.get("text", item)) for item in lines)

    return ""


def _extract_confidence(payload: dict[str, Any]) -> float | None:
    for key in ("confidence", "score", "prob"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_confidence(data)
    return None
