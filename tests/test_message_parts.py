import json

from app.services.bot_service import BotService, _strip_bot_mentions


def test_extract_image_key_from_nested_post_content() -> None:
    message = {
        "message_type": "post",
        "content": json.dumps(
            {
                "post": {
                    "zh_cn": {
                        "content": [
                            [
                                {"tag": "at", "user_id": "ou_xxx"},
                                {"tag": "img", "image_key": "img_v2_nested"},
                            ]
                        ]
                    }
                }
            }
        ),
    }

    text, image_keys = BotService._extract_message_parts(None, message)

    assert text == ""
    assert image_keys == ["img_v2_nested"]


def test_extract_image_key_from_image_message() -> None:
    message = {
        "message_type": "image",
        "content": json.dumps({"image_key": "img_v2_direct"}),
    }

    text, image_keys = BotService._extract_message_parts(None, message)

    assert text == ""
    assert image_keys == ["img_v2_direct"]


def test_strip_bot_mentions_removes_html_placeholder() -> None:
    assert _strip_bot_mentions("<p>@_user_1 </p>") == ""
