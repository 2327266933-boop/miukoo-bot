from app.models.price_record import DailySummary, PriceRecord


def format_daily_summary(summary: DailySummary) -> str:
    lines = [
        f"【BML价格Lose日报】{summary.record_date.isoformat()}",
        "",
        f"今日识别记录数：{summary.total_records}",
        f"今日lose数量：{summary.lose_count}",
        f"原因标记=1：{summary.reason_flag_1_count}",
        f"原因标记=0：{summary.reason_flag_0_count}，需人工复核",
        f"人工复核总数：{summary.manual_review_count}",
    ]
    if summary.daily_sheet_url:
        lines.append(f"明细表：{summary.daily_sheet_url}")
    if summary.reason_zero_sheet_url:
        lines.append(f"原因标记=0汇总：{summary.reason_zero_sheet_url}")
    return "\n".join(lines)


def format_records(records: list[PriceRecord], *, title: str, limit: int = 10) -> str:
    if not records:
        return f"{title}\n暂无记录"

    lines = [title, f"共 {len(records)} 条，展示前 {min(len(records), limit)} 条："]
    for index, record in enumerate(records[:limit], start=1):
        product = record.product_name or record.product_id or record.sku_id or "未知商品"
        lose_text = "是" if record.is_lose else "否"
        lines.extend(
            [
                "",
                f"{index}. 商家ID：{record.merchant_id}，商品：{product}",
                f"抖音到手价：{record.douyin_final_price}；美团到手价：{record.meituan_final_price}；价差：{record.price_gap}",
                f"是否lose：{lose_text}；原因标记：{record.reason_flag}",
            ]
        )
        if record.review_reason:
            lines.append(f"复核原因：{record.review_reason}")
        if record.source_message_link:
            lines.append(f"原始消息：{record.source_message_link}")
    return "\n".join(lines)


def format_ingest_success(records: list[PriceRecord]) -> str:
    lose_count = sum(record.is_lose for record in records)
    reason_zero_count = sum(record.is_lose and record.reason_flag == 0 for record in records)
    manual_review_count = sum(record.needs_manual_review for record in records)
    return "\n".join(
        [
            "已完成价格信息识别并入库。",
            f"识别记录数：{len(records)}",
            f"lose数量：{lose_count}",
            f"原因标记=0：{reason_zero_count}",
            f"需人工复核：{manual_review_count}",
        ]
    )

