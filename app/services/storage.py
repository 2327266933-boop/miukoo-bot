from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.models.price_record import PriceRecord


class JsonlRecordStore:
    """Small local store for MVP deployment.

    It can be replaced with an internal DB later without touching business logic.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def append(self, record: PriceRecord) -> None:
        path = self._path_for_date(record.record_date)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def list_by_date(self, record_date: date) -> list[PriceRecord]:
        path = self._path_for_date(record_date)
        if not path.exists():
            return []
        records: list[PriceRecord] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(PriceRecord.model_validate_json(line))
        return records

    def find_by_merchant(self, merchant_id: str, *, record_date: date | None = None) -> list[PriceRecord]:
        return [
            record
            for record in self._iter_records(record_date)
            if record.merchant_id == merchant_id
        ]

    def find_by_product(self, product_id: str, *, record_date: date | None = None) -> list[PriceRecord]:
        return [
            record
            for record in self._iter_records(record_date)
            if record.product_id == product_id or record.sku_id == product_id
        ]

    def _iter_records(self, record_date: date | None) -> list[PriceRecord]:
        if record_date is not None:
            return self.list_by_date(record_date)

        records: list[PriceRecord] = []
        for path in sorted(self.data_dir.glob("records-*.jsonl")):
            with path.open("r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        records.append(PriceRecord.model_validate_json(line))
        return records

    def _path_for_date(self, record_date: date) -> Path:
        return self.data_dir / f"records-{record_date.isoformat()}.jsonl"
