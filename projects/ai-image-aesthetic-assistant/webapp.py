import json
import ipaddress
import logging
import os
import threading
import time
import warnings
from collections import defaultdict, deque
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image

from core.analyzer import analyze_image_bytes
from core.image_utils import validate_image_dimensions
from core.model_client import (
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)


MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_TYPES = {"photography", "ai_generated", "social_media"}

STATIC_DIR = Path(__file__).parent / "static"
STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}

logger = logging.getLogger(__name__)


def json_response(start_response, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def error_response(start_response, status, code, message):
    return json_response(
        start_response, status, {"error": {"code": code, "message": message}}
    )


class RateLimiter:
    def __init__(self, limit=10, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            queue = self.requests[key]
            while queue and queue[0] <= now - self.window_seconds:
                queue.popleft()
            if len(queue) >= self.limit:
                return False
            queue.append(now)
            return True


rate_limiter = RateLimiter()


def _trusted_proxy_ips():
    trusted = set()
    for value in os.environ.get("TRUSTED_PROXY_IPS", "").split(","):
        value = value.strip()
        if not value:
            continue
        try:
            trusted.add(str(ipaddress.ip_address(value)))
        except ValueError:
            continue
    return trusted


def _client_key(environ):
    remote = environ.get("REMOTE_ADDR", "")
    trusted = _trusted_proxy_ips()
    if remote not in trusted:
        return remote
    forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
    try:
        chain = [str(ipaddress.ip_address(value.strip())) for value in forwarded.split(",")]
    except ValueError:
        return remote
    if not forwarded or not chain:
        return remote
    for address in reversed(chain):
        if address not in trusted:
            return address
    return remote


def _static_response(start_response, filename, content_type):
    body = (STATIC_DIR / filename).read_bytes()
    start_response(
        "200 OK",
        [("Content-Type", content_type), ("Content-Length", str(len(body)))],
    )
    return [body]


def _log_exception(error, request_id):
    logger.error("error_type=%s request_id=%s", type(error).__name__, request_id)


def _analyze(environ, start_response):
    request_id = uuid4().hex
    raw_length = environ.get("CONTENT_LENGTH")
    try:
        length = int(raw_length)
        if length < 0:
            raise ValueError
    except (TypeError, ValueError):
        return error_response(
            start_response, "400 Bad Request", "invalid_request", "请求格式无效。"
        )

    if length > MAX_IMAGE_BYTES:
        return error_response(
            start_response,
            "413 Payload Too Large",
            "payload_too_large",
            "图片不能超过 10 MiB。",
        )

    if environ.get("CONTENT_TYPE") not in ALLOWED_CONTENT_TYPES:
        return error_response(
            start_response,
            "400 Bad Request",
            "invalid_content_type",
            "仅支持 JPEG、PNG 或 WebP 图片。",
        )

    image_type = environ.get("HTTP_X_IMAGE_TYPE")
    if image_type not in ALLOWED_IMAGE_TYPES:
        return error_response(
            start_response,
            "400 Bad Request",
            "invalid_image_type",
            "不支持的图片类型。",
        )

    source_ip = _client_key(environ)
    if not rate_limiter.allow(source_ip):
        return error_response(
            start_response,
            "429 Too Many Requests",
            "rate_limited",
            "请求过于频繁，请稍后再试。",
        )

    body = environ["wsgi.input"].read(length)
    if len(body) != length:
        return error_response(
            start_response, "400 Bad Request", "invalid_request", "请求格式无效。"
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(body)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("unsupported image format")
                validate_image_dimensions(image)
                image.verify()
    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
        ValueError,
        OSError,
    ) as error:
        _log_exception(error, request_id)
        return error_response(
            start_response,
            "400 Bad Request",
            "invalid_image",
            "图片无法识别，请重新选择。",
        )

    filename = environ.get("HTTP_X_FILENAME", "upload.jpg")
    try:
        result = analyze_image_bytes(body, filename, image_type)
    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
        ValueError,
        OSError,
    ) as error:
        _log_exception(error, request_id)
        return error_response(
            start_response,
            "400 Bad Request",
            "invalid_image",
            "图片无法识别，请重新选择。",
        )
    except ModelTimeoutError as error:
        _log_exception(error, request_id)
        return error_response(
            start_response,
            "504 Gateway Timeout",
            "analysis_timeout",
            "分析超时，请稍后重试。",
        )
    except ModelUnavailableError as error:
        _log_exception(error, request_id)
        return error_response(
            start_response,
            "503 Service Unavailable",
            "analysis_unavailable",
            "评测服务暂时不可用，请稍后重试。",
        )
    except ModelResponseError as error:
        _log_exception(error, request_id)
        return error_response(
            start_response,
            "502 Bad Gateway",
            "invalid_analysis",
            "评测结果异常，请重新尝试。",
        )
    except Exception as error:
        _log_exception(error, request_id)
        return error_response(
            start_response,
            "500 Internal Server Error",
            "internal_error",
            "服务暂时出现问题，请稍后重试。",
        )

    return json_response(start_response, "200 OK", result)


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "")

    if method == "GET" and path == "/healthz":
        return json_response(start_response, "200 OK", {"status": "ok"})
    if method == "GET" and path in STATIC_ROUTES:
        return _static_response(start_response, *STATIC_ROUTES[path])
    if method == "POST" and path == "/api/analyze":
        return _analyze(environ, start_response)
    return error_response(
        start_response, "404 Not Found", "not_found", "请求的资源不存在。"
    )
