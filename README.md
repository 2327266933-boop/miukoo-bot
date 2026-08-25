# BD 群发提醒机器人

面向 BD 运营场景的自动消息机器人。使用者创建群发任务后，机器人会按消息类型渲染模板，给指定 BD 发送消息，并在对方未回复时按配置自动提醒。

## 当前能力

- 创建 BD 群发任务
- 支持多个 BD 收件人
- 支持消息类型和模板变量
- 支持首发消息和提醒消息
- 支持回复 webhook 回调
- 收到回复后自动停止提醒
- SQLite 记录任务、收件人、发送日志和回复日志
- 后台 scheduler 定时扫描未回复对象
- Mock 消息适配器，本地调试时只打印消息，不真实外发
- GitHub Actions 自动运行编译检查和测试

## 核心流程

1. 创建任务，指定收件人、消息类型、模板变量和提醒策略。
2. 系统校验模板变量是否完整。
3. 机器人发送首条消息，并写入发送日志。
4. 系统监听 webhook，记录 BD 回复。
5. 如果 BD 在指定时间内未回复，scheduler 自动发送提醒。
6. 收到回复、达到最大提醒次数、任务取消或任务完成后停止提醒。

## 项目结构

```text
.
├── .github/workflows/ci.yml
├── examples/
│   └── task.inventory.json
├── miukoo_bot/
│   ├── __main__.py
│   ├── api.py
│   ├── config.py
│   ├── db.py
│   ├── messaging.py
│   ├── scheduler.py
│   ├── service.py
│   ├── templates.py
│   └── time_utils.py
├── tests/
│   └── test_service.py
├── README.md
└── pyproject.toml
```

## 本地启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m miukoo_bot --host 127.0.0.1 --port 8080
```

健康检查：

```bash
curl http://127.0.0.1:8080/health
```

## 创建群发任务

仓库提供了一个库存确认任务示例：

```bash
curl -X POST http://127.0.0.1:8080/api/tasks \
  -H 'Content-Type: application/json' \
  --data @examples/task.inventory.json
```

任务示例：

```json
{
  "task_name": "8月门店库存确认",
  "channel": "mock",
  "message_type": "inventory_check",
  "recipients": [
    {
      "bd_id": "bd_001",
      "name": "张三",
      "contact_id": "mock_user_001",
      "group": "华东一区",
      "variables": {
        "city": "上海",
        "shop_count": 12,
        "deadline": "今天 18:00"
      }
    }
  ],
  "follow_up": {
    "enabled": true,
    "first_remind_after_minutes": 1,
    "remind_interval_minutes": 2,
    "max_remind_times": 2,
    "stop_when_replied": true,
    "quiet_hours": {
      "start": "00:00",
      "end": "00:00"
    }
  }
}
```

## 查询任务

查询任务列表：

```bash
curl http://127.0.0.1:8080/api/tasks
```

查询单个任务：

```bash
curl http://127.0.0.1:8080/api/tasks/{task_id}
```

取消任务：

```bash
curl -X POST http://127.0.0.1:8080/api/tasks/{task_id}/cancel
```

## 模拟 BD 回复

```bash
curl -X POST http://127.0.0.1:8080/api/webhooks/mock/message \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"替换成任务ID","bd_id":"bd_001","content":"已确认"}'
```

收到回复后，该 BD 的 `status` 会变成 `replied`，`next_remind_at` 会被清空，后续不再提醒。

## 手动触发提醒扫描

服务启动后会自动启动后台提醒线程。调试时也可以手动触发一次扫描：

```bash
curl -X POST http://127.0.0.1:8080/api/scheduler/run-once
```

## 消息类型

当前内置模板：

| 类型 | 场景 | 关键变量 |
| --- | --- | --- |
| `inventory_check` | 门店库存确认 | `city`、`shop_count`、`deadline` |
| `price_lose_follow` | 价格 Lose 跟进 | `shop_name`、`sku_name`、`lose_reason`、`deadline` |
| `campaign_signup` | 活动报名提醒 | `campaign_name`、`signup_deadline`、`benefit` |
| `material_collect` | 资料补充 | `material_name`、`missing_fields`、`deadline` |
| `task_urge` | 通用任务催办 | `task_title`、`owner_name`、`deadline` |

## 状态说明

| 状态 | 说明 |
| --- | --- |
| `pending` | 收件人已创建，等待发送 |
| `sent` | 首条消息已发送 |
| `replied` | 已收到 BD 回复 |
| `followed_up` | 已发送提醒，仍可能继续等待回复 |
| `completed` | 已达到结束条件 |
| `cancelled` | 任务或收件人被取消 |
| `failed` | 发送失败或校验失败 |

## 环境变量

```bash
BD_BOT_DATABASE=data/bd_bot.sqlite3
BD_BOT_HOST=127.0.0.1
BD_BOT_PORT=8080
BD_BOT_SCHEDULER_INTERVAL_SECONDS=30

DEFAULT_FIRST_REMIND_AFTER_MINUTES=120
DEFAULT_REMIND_INTERVAL_MINUTES=180
DEFAULT_MAX_REMIND_TIMES=2
QUIET_HOURS_START=21:00
QUIET_HOURS_END=09:00
```

## 测试

```bash
python -m compileall app miukoo_bot tests
python -m pytest -q
```

当前测试覆盖：

- 创建任务后发送首条消息
- 未回复对象到点后发送提醒
- 收到回复后停止提醒
- 模板变量缺失时拒绝创建任务

## CI

GitHub Actions 配置在 `.github/workflows/ci.yml`。

每次 push 或 pull request 会执行：

```bash
python -m compileall app miukoo_bot tests
python -m pytest -q
```

## 后续接入真实消息平台

当前使用 `MockMessageAdapter`，只会在本地打印消息。

要接入飞书、企业微信或钉钉，需要替换 `miukoo_bot/messaging.py` 里的发送适配器，并配置真实平台的 webhook：

```text
https://你的域名/api/webhooks/{channel}/message
```

需要放到环境变量或部署平台密钥中的配置包括：

```text
LARK_APP_ID
LARK_APP_SECRET
LARK_VERIFICATION_TOKEN
LARK_ENCRYPT_KEY
```

不要把机器人密钥提交到 GitHub。
