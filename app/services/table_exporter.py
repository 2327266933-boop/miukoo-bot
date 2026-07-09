from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from app.models.price_record import DailySummary, PriceRecord


class DailyTableExporter:
    def __init__(
        self,
        data_dir: Path,
        *,
        daily_sheet_url_template: str = "",
        reason_zero_sheet_url_template: str = "",
    ) -> None:
        self.export_dir = data_dir / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.daily_sheet_url_template = daily_sheet_url_template
        self.reason_zero_sheet_url_template = reason_zero_sheet_url_template

    def export(self, records: list[PriceRecord], record_date: date) -> DailySummary:
        self._write_csv(self.export_dir / f"bml-price-lose-{record_date.isoformat()}.csv", records)
        reason_zero_records = [record for record in records if record.is_lose and record.reason_flag == 0]
        self._write_csv(
            self.export_dir / f"bml-price-lose-reason0-{record_date.isoformat()}.csv",
            reason_zero_records,
        )

        return DailySummary(
            record_date=record_date,
            total_records=len(records),
            lose_count=sum(record.is_lose for record in records),
            reason_flag_1_count=sum(record.is_lose and record.reason_flag == 1 for record in records),
            reason_flag_0_count=len(reason_zero_records),
            manual_review_count=sum(record.needs_manual_review for record in records),
            daily_sheet_url=self._render_url(self.daily_sheet_url_template, record_date),
            reason_zero_sheet_url=self._render_url(self.reason_zero_sheet_url_template, record_date),
        )

    def _write_csv(self, path: Path, records: list[PriceRecord]) -> None:
        fields = [
            "record_date",
            "merchant_id",
            "merchant_name",
            "product_id",
            "sku_id",
            "product_name",
            "douyin_promo_price",
            "douyin_super_coupon_subsidy",
            "douyin_other_subsidy",
            "douyin_final_price",
            "meituan_promo_price",
            "meituan_magic_coupon_subsidy",
            "meituan_other_subsidy",
            "meituan_final_price",
            "price_gap",
            "is_lose",
            "reason_flag",
            "needs_manual_review",
            "review_reason",
            "source_message_link",
            "confidence",
            "created_at",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for record in records:
                row = record.model_dump(mode="json")
                writer.writerow({field: row.get(field, "") for field in fields})

    def _render_url(self, template: str, record_date: date) -> str | None:
        if not template:
            return None
        return template.format(date=record_date.isoformat())
