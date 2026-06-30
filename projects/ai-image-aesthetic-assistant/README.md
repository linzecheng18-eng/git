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

## 本地启动

1. 使用 bundled Python
2. 先以 `mock` 模式启动
3. 打开 `http://127.0.0.1:8000`

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
