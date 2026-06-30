# AI 图片审美评测助手 Web 部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有本地单图评测原型改造成面向普通图片创作者的响应式 Web MVP，并以可移植容器方式提供生产级部署入口。

**Architecture:** 保留现有 `core` 分析链路，将图片类型、输入校验、结构化输出和错误映射分别收口到独立模块；新增标准 WSGI 应用作为生产入口，由 Gunicorn 承载。前端继续使用原生 HTML/CSS/JavaScript，直接向同源 `/api/analyze` 上传图片，不引入账号、数据库或长期图片存储。

**Tech Stack:** Python 3.12、标准库 WSGI、Gunicorn、Pillow、OpenAI Responses API、原生 HTML/CSS/JavaScript、`unittest`、Docker

## Global Constraints

- 首版采用移动端优先的响应式 Web 应用，同时支持手机和电脑浏览器。
- 支持摄影照片、AI 生成图片、社交媒体配图三种类型，用户必须主动选择类型。
- 结果必须包含总体判断、具体问题、对应建议和构图、色彩、主体、清晰度、视觉层次五维评分。
- 无需注册，不保存个人历史，不建设排行榜、社区、付费、批量评测或自动改图。
- 默认不长期保存原图；实现不得把图片写入磁盘或日志。
- API 密钥只从服务端环境变量读取，不得进入前端、仓库、日志、测试快照或文档示例。
- 支持 JPG、PNG、WebP；单张原始图片最大 10 MiB。
- 模型超时、无效响应和额度/上游错误必须返回稳定、通俗且不泄漏内部信息的错误结构。
- 公开服务使用 Gunicorn，不直接暴露 `http.server`。
- 效果验收使用不少于 50 张真实图片；问题诊断准确率和建议可执行率目标均为 70%。

---

## File Map

- Modify: `projects/ai-image-aesthetic-assistant/core/prompt_versions.py` — 三类图片提示词与类型校验。
- Modify: `projects/ai-image-aesthetic-assistant/core/analyzer.py` — 接收图片类型并组织分析流程。
- Modify: `projects/ai-image-aesthetic-assistant/core/model_client.py` — Responses API 结构化输出、超时和上游错误归一化。
- Modify: `projects/ai-image-aesthetic-assistant/core/rubric.py` — 严格校验问题与建议数量和文本。
- Create: `projects/ai-image-aesthetic-assistant/webapp.py` — 标准 WSGI 生产应用、静态文件、健康检查和 API 错误映射。
- Modify: `projects/ai-image-aesthetic-assistant/app.py` — 仅保留本地开发启动入口，复用 WSGI 应用。
- Modify: `projects/ai-image-aesthetic-assistant/static/index.html` — 图片类型、预览、进度和语义化结果容器。
- Modify: `projects/ai-image-aesthetic-assistant/static/app.js` — 前端校验、上传、错误和结果渲染。
- Modify: `projects/ai-image-aesthetic-assistant/static/styles.css` — 移动端优先响应式样式。
- Create: `projects/ai-image-aesthetic-assistant/tests/test_prompts.py` — 图片类型与专项提示词测试。
- Modify: `projects/ai-image-aesthetic-assistant/tests/test_analyzer.py` — 类型透传、结构化结果与模型错误测试。
- Create: `projects/ai-image-aesthetic-assistant/tests/test_webapp.py` — WSGI 接口、限制、健康检查和安全响应测试。
- Create: `projects/ai-image-aesthetic-assistant/requirements.txt` — 生产依赖。
- Create: `projects/ai-image-aesthetic-assistant/Dockerfile` — 容器构建与 Gunicorn 启动。
- Create: `projects/ai-image-aesthetic-assistant/.dockerignore` — 排除密钥、缓存和测试图片。
- Modify: `projects/ai-image-aesthetic-assistant/.env.example` — 无真实凭据的运行配置模板。
- Modify: `projects/ai-image-aesthetic-assistant/README.md` — 本地、容器和云平台部署说明。
- Modify: `projects/ai-image-aesthetic-assistant/data/test_set/manifest.csv` — 增加图片类型和人工效果判断字段。
- Modify: `projects/ai-image-aesthetic-assistant/scripts/build_eval_report.py` — 计算诊断准确率和建议可执行率。
- Modify: `projects/ai-image-aesthetic-assistant/tests/test_eval_report.py` — 新验收指标测试。

### Task 1: 三类图片专项评测

**Files:**
- Modify: `projects/ai-image-aesthetic-assistant/core/prompt_versions.py`
- Modify: `projects/ai-image-aesthetic-assistant/core/analyzer.py`
- Create: `projects/ai-image-aesthetic-assistant/tests/test_prompts.py`
- Modify: `projects/ai-image-aesthetic-assistant/tests/test_analyzer.py`

**Interfaces:**
- Produces: `IMAGE_TYPES: tuple[str, ...]`
- Produces: `get_prompt(image_type: str, version: str = "v1") -> dict`
- Produces: `analyze_image_bytes(image_bytes: bytes, filename: str, image_type: str) -> dict`

- [ ] **Step 1: 写图片类型和提示词失败测试**

```python
# tests/test_prompts.py
import unittest

from core.prompt_versions import IMAGE_TYPES, get_prompt


class PromptTests(unittest.TestCase):
    def test_supported_image_types_are_fixed(self):
        self.assertEqual(IMAGE_TYPES, ("photography", "ai_generated", "social_media"))

    def test_each_type_has_specific_guidance(self):
        self.assertIn("光线", get_prompt("photography")["prompt"])
        self.assertIn("生成瑕疵", get_prompt("ai_generated")["prompt"])
        self.assertIn("信息传达", get_prompt("social_media")["prompt"])

    def test_unknown_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不支持的图片类型"):
            get_prompt("other")
```

- [ ] **Step 2: 运行测试并确认先失败**

Run: `python -m unittest tests.test_prompts -v`

Expected: FAIL，原因是 `IMAGE_TYPES` 不存在或 `get_prompt()` 不接受图片类型。

- [ ] **Step 3: 实现最小分类提示词**

```python
# core/prompt_versions.py
IMAGE_TYPES = ("photography", "ai_generated", "social_media")

TYPE_GUIDANCE = {
    "photography": "额外检查光线、曝光、拍摄时机和景深是否服务主体。",
    "ai_generated": "额外检查生成瑕疵、局部结构、材质一致性和不自然细节。",
    "social_media": "额外检查信息传达、文字可读性、缩略图识别度和视觉焦点。",
}

BASE_PROMPT = """你是面向普通图片创作者的审美评测助手。
从构图、色彩、主体、清晰度、视觉层次五个维度各给出 1-10 分。
指出最重要的 1-3 个具体问题，并按相同顺序给出普通用户可以直接执行的修改建议。
语言简洁，不使用空泛的专业术语。"""


def get_prompt(image_type, version="v1"):
    if image_type not in IMAGE_TYPES:
        raise ValueError("不支持的图片类型")
    if version != "v1":
        raise ValueError("不支持的提示词版本")
    return {
        "label": "三类图片专项审美评测",
        "prompt": f"{BASE_PROMPT}\n{TYPE_GUIDANCE[image_type]}",
    }
```

- [ ] **Step 4: 写分析器类型透传失败测试**

```python
# 追加到 tests/test_analyzer.py
from unittest.mock import patch
from core.analyzer import analyze_image_bytes

    def test_analyzer_uses_selected_image_type(self):
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze"
        ) as analyze:
            analyze.return_value = {
                "scores": {"构图": 7, "色彩": 7, "主体": 7, "清晰度": 7, "视觉层次": 7},
                "issues": ["主体不够突出"],
                "suggestions": ["裁掉右侧干扰元素"],
                "summary": "画面基本完整。",
            }
            analyze_image_bytes(b"image", "sample.jpg", "photography")
            self.assertIn("光线", analyze.call_args.args[2])
```

- [ ] **Step 5: 修改分析器并运行相关测试**

```python
# core/analyzer.py
def analyze_image_bytes(image_bytes, filename, image_type):
    prompt = get_prompt(image_type)["prompt"]
    image_b64 = image_to_base64(image_bytes)
    raw = ModelClient().analyze(image_b64, filename, prompt)
    return normalize_model_payload(raw)
```

Run: `python -m unittest tests.test_prompts tests.test_analyzer -v`

Expected: PASS。

- [ ] **Step 6: 提交**

```powershell
git add projects/ai-image-aesthetic-assistant/core/prompt_versions.py projects/ai-image-aesthetic-assistant/core/analyzer.py projects/ai-image-aesthetic-assistant/tests/test_prompts.py projects/ai-image-aesthetic-assistant/tests/test_analyzer.py
git commit -m "add image type specific evaluation"
```

### Task 2: 严格结果结构与模型错误归一化

**Files:**
- Modify: `projects/ai-image-aesthetic-assistant/core/rubric.py`
- Modify: `projects/ai-image-aesthetic-assistant/core/model_client.py`
- Modify: `projects/ai-image-aesthetic-assistant/tests/test_analyzer.py`

**Interfaces:**
- Produces: `ModelTimeoutError`, `ModelUnavailableError`, `ModelResponseError`
- Produces: `validate_result(result: dict) -> dict`，保证问题和建议各 1-3 条且数量相同。

- [ ] **Step 1: 写严格结果校验失败测试**

```python
# 追加到 tests/test_analyzer.py
from core.rubric import validate_result

    def test_result_requires_paired_issues_and_suggestions(self):
        payload = {
            "scores": {"构图": 7, "色彩": 7, "主体": 7, "清晰度": 7, "视觉层次": 7},
            "issues": ["问题一", "问题二"],
            "suggestions": ["建议一"],
            "summary": "总结",
        }
        with self.assertRaisesRegex(ValueError, "数量必须一致"):
            validate_result(payload)

    def test_result_rejects_empty_summary(self):
        payload = {
            "scores": {"构图": 7, "色彩": 7, "主体": 7, "清晰度": 7, "视觉层次": 7},
            "issues": ["问题"],
            "suggestions": ["建议"],
            "summary": " ",
        }
        with self.assertRaisesRegex(ValueError, "总结不能为空"):
            validate_result(payload)
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_analyzer -v`

Expected: FAIL，当前校验器接受数量不一致或空总结。

- [ ] **Step 3: 实现最小严格校验**

```python
# 替换 core/rubric.py 中 validate_result 的文本字段部分
issues = [str(item).strip() for item in result.get("issues", []) if str(item).strip()]
suggestions = [str(item).strip() for item in result.get("suggestions", []) if str(item).strip()]
summary = str(result.get("summary", "")).strip()
if not 1 <= len(issues) <= 3:
    raise ValueError("问题数量必须为 1-3 条")
if len(issues) != len(suggestions):
    raise ValueError("问题与建议数量必须一致")
if not summary:
    raise ValueError("总结不能为空")
return {"scores": normalized_scores, "issues": issues, "suggestions": suggestions, "summary": summary}
```

- [ ] **Step 4: 写模型错误映射失败测试**

```python
# 追加到 tests/test_analyzer.py
from urllib.error import HTTPError, URLError
from core.model_client import ModelClient, ModelTimeoutError, ModelUnavailableError

    def test_timeout_is_normalized(self):
        client = ModelClient()
        client.mode = "real"
        client.api_key = "test-placeholder"
        with patch("core.model_client.request.urlopen", side_effect=TimeoutError):
            with self.assertRaises(ModelTimeoutError):
                client.analyze("encoded", "a.jpg", "prompt")

    def test_upstream_http_error_is_normalized(self):
        client = ModelClient()
        client.mode = "real"
        client.api_key = "test-placeholder"
        error = HTTPError("https://api.openai.com", 429, "rate", {}, None)
        with patch("core.model_client.request.urlopen", side_effect=error):
            with self.assertRaises(ModelUnavailableError):
                client.analyze("encoded", "a.jpg", "prompt")
```

- [ ] **Step 5: 实现异常类型、结构化输出和一次无效响应重试**

```python
# core/model_client.py 新增
from urllib.error import HTTPError, URLError

class ModelTimeoutError(RuntimeError):
    pass

class ModelUnavailableError(RuntimeError):
    pass

class ModelResponseError(RuntimeError):
    pass

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {name: {"type": "integer", "minimum": 1, "maximum": 10} for name in ("构图", "色彩", "主体", "清晰度", "视觉层次")},
            "required": ["构图", "色彩", "主体", "清晰度", "视觉层次"],
            "additionalProperties": False,
        },
        "issues": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
        "suggestions": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
        "summary": {"type": "string", "minLength": 1},
    },
    "required": ["scores", "issues", "suggestions", "summary"],
    "additionalProperties": False,
}
```

在请求体加入：

```python
"text": {
    "format": {
        "type": "json_schema",
        "name": "image_aesthetic_evaluation",
        "strict": True,
        "schema": RESULT_SCHEMA,
    }
},
```

将网络调用包裹为：

```python
try:
    with request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
except (TimeoutError, URLError) as exc:
    raise ModelTimeoutError("模型请求超时") from exc
except HTTPError as exc:
    raise ModelUnavailableError("模型服务暂时不可用") from exc

try:
    text = payload["output"][0]["content"][0]["text"]
    return json.loads(text)
except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
    raise ModelResponseError("模型返回无效结果") from exc
```

由 `analyzer.py` 捕获 `ModelResponseError` 后仅重试一次，第二次仍失败则继续抛出；不得重试超时和额度错误：

```python
def analyze_image_bytes(image_bytes, filename, image_type):
    prompt = get_prompt(image_type)["prompt"]
    image_b64 = image_to_base64(image_bytes)
    client = ModelClient()
    for attempt in range(2):
        try:
            return normalize_model_payload(client.analyze(image_b64, filename, prompt))
        except ModelResponseError:
            if attempt == 1:
                raise
```

- [ ] **Step 6: 运行分析链路测试并提交**

Run: `python -m unittest tests.test_analyzer tests.test_rubric -v`

Expected: PASS。

```powershell
git add projects/ai-image-aesthetic-assistant/core/rubric.py projects/ai-image-aesthetic-assistant/core/model_client.py projects/ai-image-aesthetic-assistant/core/analyzer.py projects/ai-image-aesthetic-assistant/tests/test_analyzer.py
git commit -m "harden model result handling"
```

### Task 3: 生产 WSGI API 与安全边界

**Files:**
- Create: `projects/ai-image-aesthetic-assistant/webapp.py`
- Modify: `projects/ai-image-aesthetic-assistant/app.py`
- Create: `projects/ai-image-aesthetic-assistant/tests/test_webapp.py`
- Modify: `projects/ai-image-aesthetic-assistant/tests/test_app.py`

**Interfaces:**
- Produces: WSGI callable `application(environ, start_response)`
- Produces: `GET /healthz`, `GET /`, `GET /styles.css`, `GET /app.js`, `POST /api/analyze`
- API error shape: `{"error": {"code": str, "message": str}}`
- Produces: 单进程内按来源 IP 限制为每分钟 10 次分析请求。

- [ ] **Step 1: 写 WSGI 健康检查与请求校验失败测试**

```python
# tests/test_webapp.py
import io
import json
import unittest
from wsgiref.util import setup_testing_defaults

from webapp import application


def call_app(path, method="GET", body=b"", headers=None):
    environ = {}
    setup_testing_defaults(environ)
    environ.update({"PATH_INFO": path, "REQUEST_METHOD": method, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)})
    for key, value in (headers or {}).items():
        environ[key] = value
    captured = {}
    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)
    payload = b"".join(application(environ, start_response))
    return captured, payload


class WebAppTests(unittest.TestCase):
    def test_healthz(self):
        response, payload = call_app("/healthz")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(json.loads(payload), {"status": "ok"})

    def test_rejects_unknown_image_type(self):
        response, payload = call_app("/api/analyze", "POST", b"image", {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "other"})
        self.assertEqual(response["status"], "400 Bad Request")
        self.assertEqual(json.loads(payload)["error"]["code"], "invalid_image_type")

    def test_rejects_body_over_ten_mebibytes_without_reading_it(self):
        response, payload = call_app("/api/analyze", "POST", b"", {"CONTENT_LENGTH": str(10 * 1024 * 1024 + 1), "CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"})
        self.assertEqual(response["status"], "413 Payload Too Large")

    def test_rate_limit_rejects_eleventh_request(self):
        from webapp import RateLimiter
        limiter = RateLimiter(limit=10, window_seconds=60)
        for _ in range(10):
            self.assertTrue(limiter.allow("127.0.0.1", now=1000))
        self.assertFalse(limiter.allow("127.0.0.1", now=1000))
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m unittest tests.test_webapp -v`

Expected: FAIL，原因是 `webapp` 不存在。

- [ ] **Step 3: 实现 WSGI 路由、JSON 响应和输入限制**

`webapp.py` 必须定义以下常量和辅助函数：

```python
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

def json_response(start_response, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")])
    return [body]

def error_response(start_response, status, code, message):
    return json_response(start_response, status, {"error": {"code": code, "message": message}})
```

增加最小进程内限流器；首版固定单个 Gunicorn worker，因此无需引入 Redis：

```python
import time
from collections import defaultdict, deque

class RateLimiter:
    def __init__(self, limit=10, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)

    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now
        queue = self.requests[key]
        while queue and queue[0] <= now - self.window_seconds:
            queue.popleft()
        if len(queue) >= self.limit:
            return False
        queue.append(now)
        return True

rate_limiter = RateLimiter()
```

`POST /api/analyze` 在读取请求体前用 `REMOTE_ADDR` 检查限流；拒绝时返回 `429 Too Many Requests`、代码 `rate_limited` 和提示“请求过于频繁，请稍后再试。”。

`POST /api/analyze` 按以下顺序校验：请求长度、内容类型、`X-Image-Type`、图片解码；只在全部通过后调用 `analyze_image_bytes(body, filename, image_type)`。异常映射固定为：

```python
ValueError -> 400 / invalid_image / "图片无法识别，请重新选择。"
ModelTimeoutError -> 504 / analysis_timeout / "分析超时，请稍后重试。"
ModelUnavailableError -> 503 / analysis_unavailable / "评测服务暂时不可用，请稍后重试。"
ModelResponseError -> 502 / invalid_analysis / "评测结果异常，请重新尝试。"
其他异常 -> 500 / internal_error / "服务暂时出现问题，请稍后重试。"
```

所有错误只记录错误类型和请求 ID，不记录图片、认证头、完整请求体或模型原文。

- [ ] **Step 4: 增加接口成功和异常映射测试**

```python
# 追加到 tests/test_webapp.py
from unittest.mock import patch
from core.model_client import ModelTimeoutError

    def test_success_passes_image_type(self):
        result = {"scores": {"构图": 7, "色彩": 7, "主体": 7, "清晰度": 7, "视觉层次": 7}, "issues": ["问题"], "suggestions": ["建议"], "summary": "总结"}
        with patch("webapp.analyze_image_bytes", return_value=result) as analyze:
            response, payload = call_app("/api/analyze", "POST", b"image", {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography", "HTTP_X_FILENAME": "sample.jpg"})
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(analyze.call_args.args[2], "photography")

    def test_timeout_returns_safe_error(self):
        with patch("webapp.analyze_image_bytes", side_effect=ModelTimeoutError):
            response, payload = call_app("/api/analyze", "POST", b"image", {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"})
        self.assertEqual(response["status"], "504 Gateway Timeout")
        self.assertNotIn("traceback", payload.decode("utf-8").lower())
```

- [ ] **Step 5: 将 `app.py` 改为本地 WSGI 启动器**

```python
# app.py
from wsgiref.simple_server import make_server
from webapp import application

if __name__ == "__main__":
    with make_server("127.0.0.1", 8000, application) as server:
        print("Serving on http://127.0.0.1:8000")
        server.serve_forever()
```

删除旧 `ThreadingHTTPServer` 接口测试，改为直接测试 WSGI callable，避免端口冲突。

- [ ] **Step 6: 运行 Web 测试并提交**

Run: `python -m unittest tests.test_webapp tests.test_app -v`

Expected: PASS。

```powershell
git add projects/ai-image-aesthetic-assistant/webapp.py projects/ai-image-aesthetic-assistant/app.py projects/ai-image-aesthetic-assistant/tests/test_webapp.py projects/ai-image-aesthetic-assistant/tests/test_app.py
git commit -m "add production WSGI API"
```

### Task 4: 普通创作者响应式交互

**Files:**
- Modify: `projects/ai-image-aesthetic-assistant/static/index.html`
- Modify: `projects/ai-image-aesthetic-assistant/static/app.js`
- Modify: `projects/ai-image-aesthetic-assistant/static/styles.css`

**Interfaces:**
- Consumes: `POST /api/analyze` 与统一错误结构。
- Produces: 类型选择、图片预览、加载状态、问题与建议配对展示、重新评测。

- [ ] **Step 1: 在 HTML 中加入明确的类型选择和结果语义结构**

```html
<fieldset id="imageTypeGroup">
  <legend>这是什么类型的图片？</legend>
  <label><input type="radio" name="imageType" value="photography" checked> 摄影照片</label>
  <label><input type="radio" name="imageType" value="ai_generated"> AI 生成图</label>
  <label><input type="radio" name="imageType" value="social_media"> 社交媒体配图</label>
</fieldset>
<label class="upload-box" for="fileInput">选择一张 JPG、PNG 或 WebP 图片</label>
<input id="fileInput" type="file" accept="image/jpeg,image/png,image/webp">
<img id="preview" alt="待评测图片预览" hidden>
<button id="analyzeBtn" type="button">开始评测</button>
<p id="status" role="status" aria-live="polite"></p>
<section id="result" hidden>
  <h2>评测结果</h2>
  <p id="summary"></p>
  <div id="diagnosis"></div>
  <div id="scores"></div>
  <button id="resetBtn" type="button">评测另一张</button>
</section>
```

- [ ] **Step 2: 实现上传前校验和预览**

```javascript
const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function validateFile(file) {
  if (!file) throw new Error("请先选择图片。");
  if (!ALLOWED_TYPES.has(file.type)) throw new Error("仅支持 JPG、PNG 和 WebP 图片。");
  if (file.size > MAX_BYTES) throw new Error("图片不能超过 10 MiB。");
}

fileInput.addEventListener("change", () => {
  URL.revokeObjectURL(preview.dataset.url || "");
  const file = fileInput.files[0];
  try {
    validateFile(file);
    const url = URL.createObjectURL(file);
    preview.dataset.url = url;
    preview.src = url;
    preview.hidden = false;
    statusText.textContent = "";
  } catch (error) {
    preview.hidden = true;
    statusText.textContent = error.message;
  }
});
```

- [ ] **Step 3: 实现请求、错误和安全结果渲染**

必须使用 `textContent` 创建结果节点，不把模型文本插入 `innerHTML`：

```javascript
function renderResult(payload) {
  summary.textContent = payload.summary;
  diagnosis.replaceChildren(...payload.issues.map((issue, index) => {
    const card = document.createElement("article");
    const title = document.createElement("h3");
    const advice = document.createElement("p");
    title.textContent = issue;
    advice.textContent = payload.suggestions[index];
    card.append(title, advice);
    return card;
  }));
  scores.replaceChildren(...Object.entries(payload.scores).map(([name, score]) => {
    const item = document.createElement("p");
    item.textContent = `${name}：${score}/10`;
    return item;
  }));
  result.hidden = false;
}
```

请求头必须包含：

```javascript
"Content-Type": file.type,
"X-Filename": file.name,
"X-Image-Type": document.querySelector('input[name="imageType"]:checked').value,
```

`response.ok === false` 时读取 `payload.error.message`；网络错误显示“网络连接失败，请检查后重试。”；失败时保留预览并重新启用按钮。

- [ ] **Step 4: 完成移动端优先样式**

样式至少覆盖 360 px 宽度、720 px 内容最大宽度、44 px 最小点击高度、可见焦点、加载禁用态、问题卡片和桌面双列类型选择。不得引入 CSS 框架。

- [ ] **Step 5: 手工验证关键流程并提交**

Run: `python app.py`

Expected:

- 访问 `http://127.0.0.1:8000` 能选择三类图片。
- 无文件、错误格式和超过 10 MiB 时不发送请求。
- 成功结果按“总结 → 问题与对应建议 → 五维评分”展示。
- 模型错误不清空图片预览，可直接重试。
- 360 px 和桌面宽度均无横向滚动。

```powershell
git add projects/ai-image-aesthetic-assistant/static/index.html projects/ai-image-aesthetic-assistant/static/app.js projects/ai-image-aesthetic-assistant/static/styles.css
git commit -m "build responsive creator evaluation flow"
```

### Task 5: 容器部署、文档与效果验收

**Files:**
- Create: `projects/ai-image-aesthetic-assistant/requirements.txt`
- Create: `projects/ai-image-aesthetic-assistant/Dockerfile`
- Create: `projects/ai-image-aesthetic-assistant/.dockerignore`
- Modify: `projects/ai-image-aesthetic-assistant/.env.example`
- Modify: `projects/ai-image-aesthetic-assistant/README.md`
- Modify: `projects/ai-image-aesthetic-assistant/data/test_set/manifest.csv`
- Modify: `projects/ai-image-aesthetic-assistant/scripts/build_eval_report.py`
- Modify: `projects/ai-image-aesthetic-assistant/tests/test_eval_report.py`

**Interfaces:**
- Produces: 容器端口 `8000`，启动命令 `gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 4 webapp:application`
- Produces: 报告指标 `diagnosis_accuracy_rate` 与 `suggestion_actionability_rate`。

- [ ] **Step 1: 写效果指标失败测试**

```python
# 追加到 tests/test_eval_report.py
    def test_report_calculates_product_success_rates(self):
        rows = [
            {"diagnosis_acceptable": "yes", "suggestion_actionable": "yes"},
            {"diagnosis_acceptable": "yes", "suggestion_actionable": "no"},
            {"diagnosis_acceptable": "no", "suggestion_actionable": "yes"},
        ]
        metrics = calculate_product_metrics(rows)
        self.assertAlmostEqual(metrics["diagnosis_accuracy_rate"], 2 / 3)
        self.assertAlmostEqual(metrics["suggestion_actionability_rate"], 2 / 3)
```

- [ ] **Step 2: 实现指标并更新测试集表头**

`manifest.csv` 表头增加：

```csv
image_type,diagnosis_acceptable,suggestion_actionable
```

其中 `image_type` 只允许 `photography`、`ai_generated`、`social_media`；两个人工判断字段只允许 `yes`、`no` 或空值。

```python
def calculate_product_metrics(rows):
    judged = [row for row in rows if row.get("diagnosis_acceptable") in {"yes", "no"} and row.get("suggestion_actionable") in {"yes", "no"}]
    total = len(judged)
    return {
        "judged_count": total,
        "diagnosis_accuracy_rate": sum(row["diagnosis_acceptable"] == "yes" for row in judged) / total if total else 0.0,
        "suggestion_actionability_rate": sum(row["suggestion_actionable"] == "yes" for row in judged) / total if total else 0.0,
    }
```

报告必须显示样本数、已人工判断数、两项比例及是否达到 70%；未满 50 张时明确显示未达标，不得输出“验收通过”。

- [ ] **Step 3: 添加可复现生产依赖与容器入口**

```text
# requirements.txt
gunicorn==23.0.0
Pillow==12.2.0
```

```dockerfile
# Dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 60 webapp:application"]
```

```text
# .dockerignore
.env
.git
__pycache__/
*.pyc
data/test_set/images/
data/eval_results/
```

- [ ] **Step 4: 更新无密钥配置模板和部署文档**

```dotenv
OPENAI_API_KEY=YOUR_API_KEY_HERE
AI_IMAGE_EVAL_MODE=mock
AI_IMAGE_EVAL_MODEL=gpt-5.4-mini
PORT=8000
```

README 必须分别给出：本地 mock 启动、真实 API 启动、Docker 构建、Docker 运行、`/healthz` 检查、云平台环境变量清单。示例只能使用 `YOUR_API_KEY_HERE`，不得出现真实密钥。

Docker 验证命令：

```powershell
docker build -t ai-image-aesthetic-assistant .
docker run --rm -p 8000:8000 -e AI_IMAGE_EVAL_MODE=mock ai-image-aesthetic-assistant
```

Expected: `http://127.0.0.1:8000/healthz` 返回 `{"status":"ok"}`。

- [ ] **Step 5: 运行完整验证**

Run: `python -m unittest discover -s tests -v`

Expected: 全部测试 PASS，0 failures，0 errors。

Run: `docker build -t ai-image-aesthetic-assistant .`

Expected: 构建成功。

Run: `docker run --rm -d --name ai-image-aesthetic-assistant-test -p 8000:8000 -e AI_IMAGE_EVAL_MODE=mock ai-image-aesthetic-assistant`

Run: `curl.exe --fail http://127.0.0.1:8000/healthz`

Expected: `{"status":"ok"}`。

Run: `docker stop ai-image-aesthetic-assistant-test`

- [ ] **Step 6: 提交**

```powershell
git add projects/ai-image-aesthetic-assistant/requirements.txt projects/ai-image-aesthetic-assistant/Dockerfile projects/ai-image-aesthetic-assistant/.dockerignore projects/ai-image-aesthetic-assistant/.env.example projects/ai-image-aesthetic-assistant/README.md projects/ai-image-aesthetic-assistant/data/test_set/manifest.csv projects/ai-image-aesthetic-assistant/scripts/build_eval_report.py projects/ai-image-aesthetic-assistant/tests/test_eval_report.py
git commit -m "package web MVP for deployment"
```

## Final Verification

- [ ] `python -m unittest discover -s tests -v` 返回 0 failures、0 errors。
- [ ] `git grep -n "sk-\|gho_\|OPENAI_API_KEY=" -- . ":(exclude).env.example"` 不返回任何真实凭据。
- [ ] Docker 健康检查返回 `{"status":"ok"}`。
- [ ] 以 360 px 与桌面宽度人工完成上传闭环。
- [ ] 三种图片类型各完成至少一次 mock 请求，并确认服务端收到正确类型。
- [ ] 真实模型验证仅在用户自行配置环境变量后执行，输出不得记录图片或密钥。
- [ ] 评测集达到 50 张且两项人工指标均达到 70% 后，才能声明产品效果验收通过。

## Self-Review

- 五个任务分别覆盖分类评测、模型稳定性、生产 API、响应式体验、部署与效果验证。
- 文件职责和接口名称在前后任务中保持一致。
- 计划没有引入账号、数据库、小程序、排行榜、付费、批量评测或自动改图。
- 所有密钥示例均为占位符；日志和错误响应明确禁止暴露敏感信息。
- 真实 50 张图片和人工判断属于验收数据，不伪造、不用 mock 结果替代。
