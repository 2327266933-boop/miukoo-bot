from __future__ import annotations

import json
import time
from typing import Any

import httpx


class FeishuClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, *, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: str | None = None
        self._token_expires_at = 0.0

    async def send_text(self, chat_id: str, text: str) -> None:
        if not chat_id:
            return
        token = await self._get_tenant_access_token()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.BASE_URL}/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": text}, ensure_ascii=False),
                },
            )
            response.raise_for_status()

    async def reply_text(self, message_id: str, text: str) -> None:
        if not message_id:
            return
        token = await self._get_tenant_access_token()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.BASE_URL}/im/v1/messages/{message_id}/reply",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "msg_type": "text",
                    "content": json.dumps({"text": text}, ensure_ascii=False),
                },
            )
            response.raise_for_status()

    async def download_image(self, image_key: str) -> bytes:
        token = await self._get_tenant_access_token()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.BASE_URL}/im/v1/images/{image_key}",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.content

    async def _get_tenant_access_token(self) -> str:
        if self._tenant_access_token and time.time() < self._token_expires_at:
            return self._tenant_access_token
        if not self.app_id or not self.app_secret:
            raise RuntimeError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        if payload.get("code") != 0:
            raise RuntimeError(f"获取飞书 tenant_access_token 失败：{payload}")

        self._tenant_access_token = payload["tenant_access_token"]
        self._token_expires_at = time.time() + int(payload.get("expire", 7200)) - 300
        return self._tenant_access_token
