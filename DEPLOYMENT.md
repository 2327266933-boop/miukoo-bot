# 部署指南

推荐先按容器部署。如果内部服务器暂时不走容器，可以用 systemd 方式。

## 上线前需要准备

1. 飞书自建应用：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_VERIFICATION_TOKEN`
   - 机器人加入“BML问题反馈群”
   - 获取群 `chat_id`，填入 `FEISHU_TARGET_CHAT_ID`

2. 飞书应用权限：
   - 接收群消息事件
   - 发送消息
   - 回复消息
   - 下载消息图片
   - 图片识别 OCR

3. 图片识别：
   - 默认使用飞书 OCR 接口
   - 需要在飞书开放平台开通图片识别 OCR 相关权限
   - `INTERNAL_OCR_ENDPOINT` 和 `INTERNAL_OCR_TOKEN` 仅作为切换内部 OCR/多模态服务时的备用配置

4. 网络和域名：
   - 服务需要被飞书开放平台回调访问
   - 对外地址配置为 `https://你的域名/feishu/events`
   - 服务器需要能访问飞书开放平台

## 环境变量

在服务器上创建 `.env`：

```text
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
FEISHU_TARGET_CHAT_ID=oc_xxx
FEISHU_DEBUG_LOG_RAW_EVENTS=false

INTERNAL_OCR_ENDPOINT=
INTERNAL_OCR_TOKEN=
INTERNAL_OCR_TIMEOUT_SECONDS=20

DAILY_REPORT_HOUR=20
DAILY_REPORT_MINUTE=30
DAILY_SHEET_URL_TEMPLATE=
REASON_ZERO_SHEET_URL_TEMPLATE=

DATA_DIR=data
TIMEZONE=Asia/Shanghai
```

## 方式一：Docker 部署

构建镜像：

```bash
docker build -t bml-price-lose-bot:latest .
```

启动容器：

```bash
docker run -d \
  --name bml-price-lose-bot \
  --restart always \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  bml-price-lose-bot:latest
```

验证：

```bash
curl http://127.0.0.1:8000/health
```

查看日志：

```bash
docker logs -f bml-price-lose-bot
```

重启：

```bash
docker restart bml-price-lose-bot
```

## 方式二：systemd 部署

建议部署目录为 `/opt/bml-price-lose-bot`。

```bash
sudo mkdir -p /opt/bml-price-lose-bot
sudo cp -R app pyproject.toml setup.py README.md .env /opt/bml-price-lose-bot/
cd /opt/bml-price-lose-bot
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install .
```

安装服务：

```bash
sudo cp deploy/bml-price-lose-bot.service /etc/systemd/system/bml-price-lose-bot.service
sudo systemctl daemon-reload
sudo systemctl enable bml-price-lose-bot
sudo systemctl start bml-price-lose-bot
```

验证：

```bash
systemctl status bml-price-lose-bot
curl http://127.0.0.1:8000/health
journalctl -u bml-price-lose-bot -f
```

## 飞书后台配置

1. 在飞书开放平台进入自建应用。
2. 打开机器人能力。
3. 在事件订阅中配置请求地址：

```text
https://你的域名/feishu/events
```

4. 先关闭事件加密，或后续补充解密逻辑。
5. 添加消息相关事件，并发布应用版本。
6. 把机器人拉入“BML问题反馈群”。

## 上线验收

1. `GET /health` 返回 `{"status":"ok"}`。
2. 飞书事件订阅 URL 校验通过。
3. 群里发送一条标准模板消息，机器人能回复“已完成价格信息识别并入库”。
4. 群里发送 `@机器人 查询商家 123456`，机器人能返回记录。
5. 手动触发日报：

```bash
curl -X POST http://127.0.0.1:8000/jobs/daily-report
```

6. 群里收到日报摘要。

## 调试消息格式

如果机器人没有回复，可以在 Railway 环境变量里临时设置：

```text
FEISHU_DEBUG_LOG_RAW_EVENTS=true
```

重新部署后，在群里发 `@机器人 帮助`，然后查看 Railway Logs。日志里会出现：

```text
RAW_FEISHU_SENDER=...
RAW_FEISHU_MESSAGE=...
RAW_FEISHU_MESSAGE_CONTENT=...
```

排查完成后建议改回：

```text
FEISHU_DEBUG_LOG_RAW_EVENTS=false
```

## 生产注意事项

- 当前版本先使用本地 `data/` 存储，需要挂载持久化目录。
- 多实例部署前，需要先把本地 JSONL 换成数据库，避免数据分散。
- 飞书事件加密如果开启，需要补充解密逻辑。
- 如果要写入真实飞书表格，需要替换 `app/services/table_exporter.py`。
