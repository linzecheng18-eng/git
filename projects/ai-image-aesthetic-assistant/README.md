# AI 图片审美评测助手

## 目标

上传单张图片，输出五维评分、问题说明和修改建议。

## 当前能力

- 本地网页可上传图片并返回分析结果
- 支持 `mock` 模式跑通完整链路
- 支持批量跑评测集，生成 `round1.csv`
- 支持把评测结果汇总成 Markdown 报告
- 报告会直接给出人工评分完成率和待补样本数
- 支持审计当前样本准备度，直接看到离 50 张目标还差多少

## 真实数据采集

1. 把待评测图片放进 `data/test_set/images/`
2. 先自动生成样本清单：

```powershell
& 'C:\Users\w\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "from scripts.run_eval import scaffold_manifest; scaffold_manifest()"
```

3. 在 `data/test_set/manifest.csv` 中补全人工评分
4. 运行批量评测：

```powershell
& 'C:\Users\w\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\run_eval.py
```

5. 生成评测报告：

```powershell
& 'C:\Users\w\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build_eval_report.py
```

6. 查看当前准备度：

```powershell
& 'C:\Users\w\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\audit_readiness.py
```

7. 人工评分怎么填，可直接参考：

- [manual-scoring-guide.md](C:/Users/w/OneDrive/文档/自我/projects/ai-image-aesthetic-assistant/docs/manual-scoring-guide.md)

## 当前不能声称已完成的部分

- 还没有真实 50 张图片测试集
- 还没有完成人工对照评分
- 还没有基于真实偏差的 v2 提示词迭代
- 因此还不能把“已完成数据验证迭代”写成既成事实

## 本地启动

默认使用 `mock` 模式，不需要 API 密钥。Windows 当前 bundled Python：

```powershell
$env:AI_IMAGE_EVAL_MODE='mock'
& 'C:\Users\w\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' app.py
```

通用 Python 环境：

```powershell
python -m pip install -r requirements.txt
$env:AI_IMAGE_EVAL_MODE='mock'
python app.py
```

真实 API 模式仅引用已由运行环境安全配置的 `OPENAI_API_KEY`，不要在命令行展开或打印该变量：

```powershell
$env:AI_IMAGE_EVAL_MODE='live'
python app.py
```

## 可审计评测顺序

先在 `manifest.csv` 填写每张图的 `image_type` 等客观元数据，保持 `diagnosis_acceptable` 和 `suggestion_actionable` 为空；运行 `scripts/run_eval.py` 生成 `round1.csv`；再查看该轮输出的 `issues` 和 `suggestions`，由人工直接在 `round1.csv` 填写两个判断；最后运行 `scripts/build_eval_report.py`。不要在看到 AI 输出前预填这两个判断。`issues` 和 `suggestions` 是 JSON 数组单元格，可按相同下标追溯问题与建议；`image_type` 会保留在 round 文件中。

## 代理与限流

默认忽略 `X-Forwarded-For`，只使用直连的 `REMOTE_ADDR`。只有应用确实位于反向代理之后时，才把所有能直接连接应用的代理 IP 以逗号分隔配置到 `TRUSTED_PROXY_IPS`。应用仅在直连来源位于该白名单时解析转发链，并从右向左跳过可信代理，选择第一个不可信地址作为客户端地址。不要填写客户端网段，也不要把该变量配置成任意来源。

内置限流器是单进程内存状态，适合当前单 worker 入口；多个 Gunicorn worker 或多个实例不会共享计数。公开部署更适合在负载均衡器、API 网关或其他外部平台实施统一限流。

## Docker 部署

构建并以 mock 模式运行：

```powershell
docker build -t ai-image-aesthetic-assistant .
docker run --rm -p 8000:8000 -e AI_IMAGE_EVAL_MODE=mock ai-image-aesthetic-assistant
```

在另一个终端检查健康状态：

```powershell
curl.exe --fail http://127.0.0.1:8000/healthz
```

预期响应为 `{"status":"ok"}`。

云平台需要配置以下环境变量：

- `AI_IMAGE_EVAL_MODE`：`mock` 或 `live`
- `AI_IMAGE_EVAL_MODEL`：默认 `gpt-5.4-mini`
- `OPENAI_API_KEY`：仅在 `live` 模式由平台密钥存储注入
- `PORT`：默认 `8000`

容器监听 `0.0.0.0:${PORT}`。不要提交 `.env`、测试图片或评测输出。

## 效果验收

`manifest.csv` 的 `image_type` 只允许 `photography`、`ai_generated`、`social_media`；`diagnosis_acceptable` 和 `suggestion_actionable` 只允许 `yes`、`no` 或空值。指标分母只统计两个判断字段都有效的行。

只有总样本数至少 50、两字段均完成判断的样本至少 50，且诊断准确率和建议可执行率都达到 70%，才能声明产品效果验收通过。当前真实样本和人工判断不足，不得声称通过。
