import io
import json
import logging
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults

from PIL import Image

from core.model_client import (
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from webapp import RateLimiter, application, _client_key


def image_bytes(image_format):
    output = io.BytesIO()
    Image.new("RGB", (1, 1)).save(output, format=image_format)
    return output.getvalue()


def call_app(path, method="GET", body=b"", headers=None):
    environ = {}
    setup_testing_defaults(environ)
    environ.update(
        {
            "PATH_INFO": path,
            "REQUEST_METHOD": method,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
            "REMOTE_ADDR": "127.0.0.1",
        }
    )
    environ.update(headers or {})
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    payload = b"".join(application(environ, start_response))
    return captured, payload


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.limiter = patch("webapp.rate_limiter", RateLimiter())
        self.limiter.start()

    def tearDown(self):
        self.limiter.stop()

    def assert_error(self, response, payload, status, code):
        self.assertEqual(response["status"], status)
        self.assertEqual(json.loads(payload)["error"]["code"], code)
        self.assertEqual(response["headers"]["Cache-Control"], "no-store")

    def test_healthz(self):
        response, payload = call_app("/healthz")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(json.loads(payload), {"status": "ok"})

    def test_serves_only_fixed_static_routes(self):
        for path, content_type in (
            ("/", "text/html; charset=utf-8"),
            ("/styles.css", "text/css; charset=utf-8"),
            ("/app.js", "application/javascript; charset=utf-8"),
        ):
            response, payload = call_app(path)
            self.assertEqual(response["status"], "200 OK")
            self.assertTrue(payload)
            self.assertEqual(response["headers"]["Content-Type"], content_type)
        response, payload = call_app("/../app.py")
        self.assert_error(response, payload, "404 Not Found", "not_found")

    def test_rejects_invalid_content_lengths(self):
        for value in (None, "abc", "-1"):
            headers = {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"}
            if value is None:
                headers["CONTENT_LENGTH"] = ""
            else:
                headers["CONTENT_LENGTH"] = value
            response, payload = call_app("/api/analyze", "POST", headers=headers)
            self.assert_error(response, payload, "400 Bad Request", "invalid_request")

    def test_rejects_body_over_ten_mebibytes_without_reading_it(self):
        class Unreadable:
            def read(self, _length):
                raise AssertionError("body must not be read")

        response, payload = call_app(
            "/api/analyze",
            "POST",
            headers={
                "CONTENT_LENGTH": str(10 * 1024 * 1024 + 1),
                "CONTENT_TYPE": "image/jpeg",
                "HTTP_X_IMAGE_TYPE": "photography",
                "wsgi.input": Unreadable(),
            },
        )
        self.assert_error(response, payload, "413 Payload Too Large", "payload_too_large")

    def test_rejects_unsupported_content_type_and_image_type(self):
        response, payload = call_app(
            "/api/analyze", "POST", b"image", {"CONTENT_TYPE": "text/plain", "HTTP_X_IMAGE_TYPE": "photography"}
        )
        self.assert_error(response, payload, "400 Bad Request", "invalid_content_type")
        response, payload = call_app(
            "/api/analyze", "POST", b"image", {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "other"}
        )
        self.assert_error(response, payload, "400 Bad Request", "invalid_image_type")

    def test_invalid_headers_do_not_consume_rate_limit(self):
        valid_body = image_bytes("JPEG")
        result = {"scores": {}, "issues": [], "suggestions": [], "summary": "ok"}
        invalid_headers = (
            ({"CONTENT_TYPE": "text/plain", "HTTP_X_IMAGE_TYPE": "photography"}, "invalid_content_type"),
            ({"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "other"}, "invalid_image_type"),
        )

        for headers, error_code in invalid_headers:
            with self.subTest(error_code=error_code), patch("webapp.rate_limiter", RateLimiter()):
                for _ in range(11):
                    response, payload = call_app("/api/analyze", "POST", b"image", headers)
                    self.assert_error(response, payload, "400 Bad Request", error_code)

                with patch("webapp.analyze_image_bytes", return_value=result):
                    response, _ = call_app(
                        "/api/analyze",
                        "POST",
                        valid_body,
                        {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"},
                    )
                self.assertEqual(response["status"], "200 OK")

    def test_success_passes_image_type(self):
        body = image_bytes("JPEG")
        result = {"scores": {}, "issues": [], "suggestions": [], "summary": "ok"}
        with patch("webapp.analyze_image_bytes", return_value=result) as analyze:
            response, payload = call_app(
                "/api/analyze",
                "POST",
                body,
                {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography", "HTTP_X_FILENAME": "sample.jpg"},
            )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(json.loads(payload), result)
        self.assertEqual(analyze.call_args.args, (body, "sample.jpg", "photography"))

    def test_rejects_gif_disguised_as_jpeg_before_analysis(self):
        with patch("webapp.analyze_image_bytes") as analyze:
            response, payload = call_app(
                "/api/analyze",
                "POST",
                image_bytes("GIF"),
                {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"},
            )
        self.assert_error(response, payload, "400 Bad Request", "invalid_image")
        analyze.assert_not_called()

    def test_supported_image_formats_reach_analysis(self):
        result = {"scores": {}, "issues": [], "suggestions": [], "summary": "ok"}
        cases = (
            ("JPEG", "image/jpeg"),
            ("PNG", "image/png"),
            ("WEBP", "image/webp"),
        )
        for image_format, content_type in cases:
            body = image_bytes(image_format)
            with self.subTest(image_format=image_format), patch(
                "webapp.analyze_image_bytes", return_value=result
            ) as analyze:
                response, _ = call_app(
                    "/api/analyze",
                    "POST",
                    body,
                    {"CONTENT_TYPE": content_type, "HTTP_X_IMAGE_TYPE": "photography"},
                )
            self.assertEqual(response["status"], "200 OK")
            analyze.assert_called_once()

    def test_unsupported_image_formats_do_not_reach_analysis(self):
        for image_format in ("GIF", "BMP"):
            with self.subTest(image_format=image_format), patch("webapp.analyze_image_bytes") as analyze:
                response, payload = call_app(
                    "/api/analyze",
                    "POST",
                    image_bytes(image_format),
                    {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"},
                )
            self.assert_error(response, payload, "400 Bad Request", "invalid_image")
            analyze.assert_not_called()

    def test_invalid_image_exceptions_return_safe_error(self):
        body = image_bytes("JPEG")
        for error in (ValueError(), OSError()):
            with self.subTest(error=type(error).__name__), patch("webapp.analyze_image_bytes", side_effect=error):
                response, payload = call_app(
                    "/api/analyze", "POST", body, {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"}
                )
                self.assert_error(response, payload, "400 Bad Request", "invalid_image")

    def test_rejects_damaged_image_before_analysis(self):
        with patch("webapp.analyze_image_bytes") as analyze:
            response, payload = call_app(
                "/api/analyze",
                "POST",
                b"not an image",
                {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"},
            )
        self.assert_error(response, payload, "400 Bad Request", "invalid_image")
        analyze.assert_not_called()

    def test_model_exceptions_are_mapped(self):
        body = image_bytes("JPEG")
        cases = (
            (ModelTimeoutError(), "504 Gateway Timeout", "analysis_timeout"),
            (ModelUnavailableError(), "503 Service Unavailable", "analysis_unavailable"),
            (ModelResponseError(), "502 Bad Gateway", "invalid_analysis"),
        )
        for error, status, code in cases:
            with self.subTest(code=code), patch("webapp.analyze_image_bytes", side_effect=error):
                response, payload = call_app(
                    "/api/analyze", "POST", body, {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"}
                )
                self.assert_error(response, payload, status, code)

    def test_invalid_rubric_results_map_to_invalid_analysis_end_to_end(self):
        body = image_bytes("JPEG")
        invalid = {
            "scores": {name: 7 for name in ("构图", "色彩", "主体", "清晰度", "视觉层次")},
            "issues": [],
            "suggestions": [],
            "summary": "summary",
        }
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze", side_effect=[invalid, invalid]
        ):
            response, payload = call_app(
                "/api/analyze", "POST", body,
                {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"},
            )
        self.assert_error(response, payload, "502 Bad Gateway", "invalid_analysis")

    def test_generic_error_log_contains_only_type_and_request_id(self):
        body = image_bytes("JPEG")
        with patch("webapp.analyze_image_bytes", side_effect=RuntimeError("secret model text")), self.assertLogs(
            "webapp", logging.ERROR
        ) as logs:
            response, payload = call_app(
                "/api/analyze",
                "POST",
                body,
                {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography", "HTTP_X_FILENAME": "secret.jpg"},
            )
        self.assert_error(response, payload, "500 Internal Server Error", "internal_error")
        logged = " ".join(logs.output)
        self.assertIn("RuntimeError", logged)
        self.assertIn("request_id=", logged)
        for secret in ("secret model text", "private image", "secret.jpg", "photography"):
            self.assertNotIn(secret, logged)

    def test_rate_limit_rejects_eleventh_request(self):
        body = image_bytes("JPEG")
        result = {"scores": {}, "issues": [], "suggestions": [], "summary": "ok"}
        headers = {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"}
        with patch("webapp.analyze_image_bytes", return_value=result):
            for _ in range(10):
                response, _ = call_app("/api/analyze", "POST", body, headers)
                self.assertEqual(response["status"], "200 OK")
            response, payload = call_app("/api/analyze", "POST", body, headers)
        self.assert_error(response, payload, "429 Too Many Requests", "rate_limited")

    def test_rate_limiter_allows_at_most_ten_concurrent_requests_per_key(self):
        limiter = RateLimiter()
        barrier = threading.Barrier(40)

        def request():
            barrier.wait()
            return limiter.allow("same-client", now=100.0)

        with ThreadPoolExecutor(max_workers=40) as pool:
            allowed = list(pool.map(lambda _: request(), range(40)))
        self.assertEqual(sum(allowed), 10)

    def test_client_key_only_trusts_forwarded_chain_from_configured_proxies(self):
        with patch.dict(os.environ, {"TRUSTED_PROXY_IPS": "10.0.0.1,10.0.0.2"}, clear=False):
            self.assertEqual(
                _client_key({"REMOTE_ADDR": "10.0.0.2", "HTTP_X_FORWARDED_FOR": "198.51.100.7, 10.0.0.1"}),
                "198.51.100.7",
            )
            self.assertEqual(
                _client_key({"REMOTE_ADDR": "203.0.113.9", "HTTP_X_FORWARDED_FOR": "198.51.100.7"}),
                "203.0.113.9",
            )

    def test_client_key_falls_back_for_missing_or_malformed_forwarding(self):
        cases = ("", "garbage", "198.51.100.7, bad")
        for forwarded in cases:
            with self.subTest(forwarded=forwarded), patch.dict(
                os.environ, {"TRUSTED_PROXY_IPS": "10.0.0.2"}, clear=False
            ):
                self.assertEqual(
                    _client_key({"REMOTE_ADDR": "10.0.0.2", "HTTP_X_FORWARDED_FOR": forwarded}),
                    "10.0.0.2",
                )

    def test_decompression_bomb_warning_and_error_are_invalid_images(self):
        body = image_bytes("JPEG")
        for error in (Image.DecompressionBombWarning("large"), Image.DecompressionBombError("large")):
            with self.subTest(error=type(error).__name__), patch("webapp.Image.open", side_effect=error):
                response, payload = call_app(
                    "/api/analyze", "POST", body,
                    {"CONTENT_TYPE": "image/jpeg", "HTTP_X_IMAGE_TYPE": "photography"},
                )
            self.assert_error(response, payload, "400 Bad Request", "invalid_image")


if __name__ == "__main__":
    unittest.main()
