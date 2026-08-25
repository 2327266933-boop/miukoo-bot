# BML价格Lose飞书机器人

用于监听“BML问题反馈群”的新消息，识别 KA 发送的文字、图片或图文混合价格信息，自动计算抖音/美团到手价、判断是否 lose，并在每天 20:30 推送摘要。

## 一期能力

- 监听飞书群新消息
- 支持标准文本字段抽取
- 支持飞书图片下载，并调用飞书 OCR 接口识别图片文字
- 计算抖音到手价、美团到手价、是否 lose、原因标记
- 到手价与公式计算不一致时自动进入人工复核
- 按天生成本地 CSV 明细和原因标记=0清单
- 每天 20:30 推送日报
- 支持群内查询命令

## 计算口径

```text
抖音到手价 = 抖音商促价 - 抖音超值券补贴 - 抖音其他补贴
美团到手价 = 美团商促价 - 美团神券补贴 - 美团其他补贴

抖音到手价 > 美团到手价，则 lose = 是
否则 lose = 否
```

原因标记只在 `lose = 是` 时判断：

```text
若 抖音超值券 < 美团神券
且 美团神券 - 抖音超值券 >= 抖音到手价 - 美团到手价
则 原因标记 = 1

否则 原因标记 = 0
```

## 推荐 KA 输入模板

```text
商家ID：
商家名称：
商品ID：
SKU ID：
商品名称：
抖音商促价：
抖音超值券补贴：
抖音其他补贴：
抖音最终到手价：
美团商促价：
美团神券补贴：
美团其他补贴：
美团最终到手价：
```

其中 `抖音最终到手价`、`美团最终到手价` 可选。如果 KA 填写的最终到手价与机器人按公式计算的结果不一致，该记录会进入人工复核。

## 群内命令

```text
@机器人 查询商家 123456
@机器人 查询商品 987654
@机器人 今日lose
@机器人 原因0
```

## 本地启动

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

手动触发日报：

```bash
curl -X POST http://127.0.0.1:8000/jobs/daily-report
```

## 部署

推荐先使用 Docker 部署，内部服务器不走容器时可以使用 systemd。完整步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 飞书配置

需要创建飞书自建应用，并配置：

- 机器人能力
- 事件订阅地址：`https://你的域名/feishu/events`
- 事件订阅 verification token，填入 `.env` 的 `FEISHU_VERIFICATION_TOKEN`
- 读取群消息事件权限
- 发送消息权限
- 下载消息图片权限
- 图片识别 OCR 权限
- 机器人加入“BML问题反馈群”

`.env` 至少需要：

```text
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=
FEISHU_TARGET_CHAT_ID=
```

图片识别默认使用飞书 OCR：

```text
POST https://open.feishu.cn/open-apis/optical_char_recognition/v1/image/basic_recognize
```

鉴权复用 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 换取的 `tenant_access_token`。如果后续要切换成内部 OCR/多模态服务，再配置 `INTERNAL_OCR_ENDPOINT` 和 `INTERNAL_OCR_TOKEN`。

## 当前实现说明

一期先使用本地 JSONL 和 CSV 做数据沉淀：

- 原始记录：`data/records-YYYY-MM-DD.jsonl`
- 全量明细：`data/exports/bml-price-lose-YYYY-MM-DD.csv`
- 原因0清单：`data/exports/bml-price-lose-reason0-YYYY-MM-DD.csv`

如果已有飞书表格或多维表格 API，可以替换 `app/services/table_exporter.py`，把 CSV 写入改成写飞书表格；业务计算和查询逻辑不用改。

## 注意事项

当前 MVP 未实现飞书事件加密解密。如果飞书后台开启了事件加密，需要补充解密逻辑，或先关闭事件加密进行联调。
