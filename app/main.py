from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from app.config import settings
from app.jobs.scheduler import build_scheduler
from app.services.bot_service import BotService
from app.services.feishu import FeishuClient
from app.services.ocr import FeishuOcrClient, InternalOcrClient
from app.services.storage import JsonlRecordStore
from app.services.table_exporter import DailyTableExporter
from app.version import build_version_info

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def build_bot_service() -> BotService:
    store = JsonlRecordStore(settings.data_dir)
    table_exporter = DailyTableExporter(
        settings.data_dir,
        daily_sheet_url_template=settings.daily_sheet_url_template,
        reason_zero_sheet_url_template=settings.reason_zero_sheet_url_template,
    )
    feishu = FeishuClient(app_id=settings.feishu_app_id, app_secret=settings.feishu_app_secret)
    if settings.internal_ocr_endpoint:
        ocr = InternalOcrClient(
            endpoint=settings.internal_ocr_endpoint,
            token=settings.internal_ocr_token,
            timeout_seconds=settings.internal_ocr_timeout_seconds,
        )
    else:
        ocr = FeishuOcrClient(
            access_token_provider=feishu.get_tenant_access_token,
            timeout_seconds=settings.internal_ocr_timeout_seconds,
        )
    return BotService(
        settings=settings,
        feishu=feishu,
        ocr=ocr,
        store=store,
        table_exporter=table_exporter,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_service = build_bot_service()
    scheduler = build_scheduler(settings, bot_service)
    scheduler.start()
    app.state.bot_service = bot_service
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
async def version() -> dict[str, Any]:
    return build_version_info()


@app.get("/feishu/events")
async def feishu_events_probe(request: Request) -> dict[str, Any]:
    """Probe endpoint for deployment checks.

    Feishu's URL verification normally uses POST, but keeping GET available
    makes browser and gateway checks easier during deployment.
    """

    challenge = request.query_params.get("challenge")
    token = request.query_params.get("token")
    if challenge:
        _verify_token(token)
        return {"challenge": challenge}
    return {"status": "ok", "endpoint": "/feishu/events", "method": "POST"}


@app.post("/feishu/events")
async def feishu_events(request: Request) -> dict[str, Any]:
    payload = await request.json()

    if payload.get("type") == "url_verification":
        _verify_token(payload.get("token"))
        return {"challenge": payload.get("challenge")}

    if "encrypt" in payload:
        raise HTTPException(status_code=400, detail="当前MVP未开启飞书加密事件，请先在飞书后台关闭加密或补充解密密钥")

    header = payload.get("header", {})
    _verify_token(header.get("token") or payload.get("token"))

    await request.app.state.bot_service.handle_feishu_event(payload)
    return {"code": 0}


@app.post("/jobs/daily-report")
async def trigger_daily_report(request: Request) -> dict[str, int]:
    await request.app.state.bot_service.send_daily_report()
    return {"code": 0}


def _verify_token(token: str | None) -> None:
    if settings.feishu_verification_token and token != settings.feishu_verification_token:
        raise HTTPException(status_code=403, detail="invalid feishu verification token")
