# AI 图片审美评测助手人工评分说明

## 目标

把 `data/test_set/manifest.csv` 补成可用于 AI 对照评测的人工评分表。

## 五个评分维度

- `构图`：画面组织是否稳定，主体位置是否合理
- `色彩`：颜色搭配是否协调，有没有明显脏乱或单薄问题
- `主体`：主体是否明确，观者是否能快速知道重点
- `清晰度`：画面是否清楚，是否存在明显模糊、抖动、压缩痕迹
- `视觉层次`：前后关系是否清楚，画面是否有层次感

## 评分规则

- 分值统一用 `1-10`
- `1-3`：明显较弱
- `4-6`：基础可用，但问题较明显
- `7-8`：整体较好
- `9-10`：非常突出

## 填写原则

- 一张图只填一行
- 先独立打人工分，再跑 AI 评测，避免互相影响
- `manual_summary` 只写一句最关键判断，不要写成长段分析
- `notes` 只记录最重要的问题，例如“主体不突出”“清晰度被高估”

## 一条有效评分记录示例

- `image_id`: `img-001`
- `file_name`: `sample-001.jpg`
- `source`: `个人作品`
- `category`: `静物`
- `manual_构图`: `7`
- `manual_色彩`: `8`
- `manual_主体`: `6`
- `manual_清晰度`: `7`
- `manual_视觉层次`: `6`
- `manual_summary`: `色彩较好，但主体不够突出`
- `notes`: `主体与背景太接近`

## 三个常见打分判断

### 情况 1：主体清楚，但构图普通

- 不要因为“能看懂主体”就把 `构图` 打高
- 可以是 `主体=7`，`构图=5`

### 情况 2：颜色鲜艳，但不一定协调

- 色彩饱和不等于 `色彩` 高分
- 如果颜色冲突明显，`色彩` 仍然可以低于 `6`

### 情况 3：画面内容好，但照片发糊

- 内容再好，`清晰度` 也不能高
- 有明显模糊、压缩痕迹时，`清晰度` 建议不高于 `5`

## 最低完成标准

- 至少 `50` 张图片进入 `manifest.csv`
- 至少 `50` 行都填完五个 `manual_` 评分字段
- 至少 `20` 行填写了 `manual_summary`
- 至少 `10` 行填写了 `notes`

## 采集完成后怎么检查

1. 在 `manifest.csv` 填写 `image_type`、来源和人工五维基准分；`diagnosis_acceptable` 与 `suggestion_actionable` 保持为空。
2. 运行 `scripts/run_eval.py`，生成包含 `image_type`、`issues`、`suggestions` 的 `round1.csv`。后两列是 JSON 数组，数组顺序一一对应。
3. 查看 AI 的问题与建议后，在 `round1.csv` 人工填写 `diagnosis_acceptable` 与 `suggestion_actionable`（只能为 `yes` 或 `no`）。不要预先判断尚未生成的 AI 输出。
4. 运行 `scripts/build_eval_report.py`；报告只消费人工编辑后的 round 文件来计算产品指标。
5. 运行 `scripts/audit_readiness.py`。
6. 把偏差最大的样本写进 `docs/iteration-log.md`。
