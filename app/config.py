from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BML价格Lose机器人"
    timezone: str = "Asia/Shanghai"
    data_dir: Path = Path("data")

    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_target_chat_id: str = ""
    feishu_debug_log_raw_events: bool = False

    internal_ocr_endpoint: str = ""
    internal_ocr_token: str = ""
    internal_ocr_timeout_seconds: float = 20.0

    daily_report_hour: int = 20
    daily_report_minute: int = 30
    daily_sheet_url_template: str = Field(
        default="",
        description="Optional link template, for example https://.../{date}",
    )
    reason_zero_sheet_url_template: str = ""


settings = Settings()
