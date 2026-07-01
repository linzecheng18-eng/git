# Task 1 实施报告：三类图片专项评测

## 实现内容

- 固定支持 `photography`、`ai_generated`、`social_media` 三类图片。
- 为三类图片分别追加摄影光线、AI 生成瑕疵、社媒信息传达专项提示。
- 未知图片类型与未知提示词版本返回明确的 `ValueError`。
- 分析器将显式选择的 `image_type` 传给 `get_prompt()`，并把对应提示词交给模型客户端。
- 为保持本任务范围外的现有 `app.py` 和 `scripts/run_eval.py` 两参数调用可用，`image_type` 默认值设为 `photography`。

## TDD 证据

### RED

1. `python -m unittest tests.test_prompts -v`
   - 失败：`ImportError: cannot import name 'IMAGE_TYPES'`。
   - 原因符合预期：分类提示词功能尚不存在。
2. `python -m unittest tests.test_analyzer.AnalyzerTests.test_analyzer_uses_selected_image_type -v`
   - 在补齐本机 Pillow 测试依赖后，失败为：`TypeError: analyze_image_bytes() takes 2 positional arguments but 3 were given`。
   - 原因符合预期：分析器尚未接收图片类型。
3. 首次完整套件暴露两个现有调用回归：`app.py` 和 `scripts/run_eval.py` 仍传两个参数；这作为兼容默认值修复的 RED。

### GREEN

- 聚焦测试：`python -m unittest tests.test_prompts tests.test_analyzer -v`
  - `Ran 6 tests`，`OK`。
- 完整测试：`python -m unittest discover -v`
  - `Ran 15 tests`，`OK`。
- `git diff --check` 与 `git diff --cached --check` 均成功，无空白错误。

## 修改文件

- `projects/ai-image-aesthetic-assistant/core/prompt_versions.py`
- `projects/ai-image-aesthetic-assistant/core/analyzer.py`
- `projects/ai-image-aesthetic-assistant/tests/test_prompts.py`
- `projects/ai-image-aesthetic-assistant/tests/test_analyzer.py`

## 提交

- `b95ff1f add image type specific evaluation`

## 自审

- 改动仅涉及简报指定的四个项目文件，报告文件除外。
- 精确采用简报给出的类型、专项中文文案、标签与错误消息。
- 未修改生产 API、前端、部署、应用入口或评测脚本。
- 新测试使用真实提示词逻辑；仅对图像编码和模型调用做必要隔离。
- 保留旧调用的最小默认行为，没有增加额外配置或抽象。

## 疑虑

- 简报示例把 `image_type` 写成必填参数，但既有入口和评测脚本不在本任务允许修改范围内，且完整测试要求它们继续工作。因此实现使用 `photography` 默认值兼容旧调用；后续入口完成类型透传后可再评估是否移除默认值。
- 本机最初缺少 Pillow，已通过用户级 `pip install Pillow` 补齐测试运行依赖；未改仓库依赖文件。

## Task 1 审查修复补充

### 修复内容

- `analyze_image_bytes(image_bytes, filename, image_type)` 移除 `image_type` 默认值，强制调用方显式选择图片类型。
- `app.py` 从 `X-Image-Type` 请求头读取类型并显式传入分析器；应用测试请求使用 `photography`。
- `scripts/run_eval.py` 从 manifest 每行必填的 `image_type` 字段读取并显式传入；脚手架及仓库 manifest 增加该列，测试数据使用 `photography`。
- 新增回归测试，锁定省略 `image_type` 时抛出 `TypeError`。

### TDD 与验证证据

- RED：`python -m unittest tests.test_analyzer.AnalyzerTests.test_analyzer_requires_image_type -v`
  - 失败为 `PIL.UnidentifiedImageError`，证明省略参数仍因默认值而进入图像解析，没有抛出预期 `TypeError`。
- GREEN（聚焦）：`python -m unittest tests.test_analyzer tests.test_app tests.test_run_eval -v`
  - `Ran 7 tests`，`OK`。
- GREEN（完整）：`python -m unittest discover -v`
  - `Ran 16 tests`，`OK`。
- `git diff --check`：通过；仅显示 Git 的 LF/CRLF 行尾转换警告。

### 疑虑

- `X-Image-Type` 与 manifest `image_type` 现在均为必填；缺失时入口会直接失败，这是本次审查裁定的显式参数约束。

## Task 1 复审 Critical/Important 修复

### 修复内容

- 最小前端增加三类图片单选控件，不预选默认值；提交前检查类型并发送 `X-Image-Type`。
- manifest 脚手架将 `image_type` 留空；`run_eval` 对空值及非 `IMAGE_TYPES` 值抛出明确 `ValueError`。
- `BASE_PROMPT` 明确仅返回 JSON，固定顶层键、五维评分键及问题与建议的顺序对应关系。
- 增加静态链路、评测输入校验和提示词契约回归测试，未实现 Task 2 结构化输出 API 或 Task 4 完整样式。

### TDD 与验证证据

- RED：`python -m unittest tests.test_static tests.test_run_eval tests.test_prompts -v`
  - `Ran 9 tests`，其中 3 failures、2 errors；分别命中缺少控件/请求头、脚手架隐式默认、空/非法类型未校验、JSON 契约缺失。
- GREEN（聚焦）：`python -m unittest tests.test_static tests.test_run_eval tests.test_prompts -v`
  - `Ran 9 tests`，`OK`。
- GREEN（完整）：`python -m unittest discover -v`
  - `Ran 20 tests`，`OK`。
- `git diff --check`：通过；仅有 Git 的 LF/CRLF 转换警告。

### 疑虑

- 本次只提供最小原生控件；完整交互和视觉样式留给 Task 4。
