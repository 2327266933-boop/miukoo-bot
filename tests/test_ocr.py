from app.services.ocr import _extract_text


def test_extract_feishu_ocr_text_list() -> None:
    payload = {
        "code": 0,
        "msg": "success",
        "data": {
            "text_list": [
                "商家ID：123456",
                "抖音商促价：100",
                "美团神券补贴：20",
            ]
        },
    }

    assert _extract_text(payload) == "商家ID：123456\n抖音商促价：100\n美团神券补贴：20"
