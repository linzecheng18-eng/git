import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from core.analyzer import analyze_image_bytes, normalize_model_payload
from core.model_client import (
    ModelClient,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from core.rubric import DIMENSIONS, validate_result


class AnalyzerTests(unittest.TestCase):
    def valid_payload(self):
        return {
            "scores": {name: 7 for name in DIMENSIONS},
            "issues": ["issue"],
            "suggestions": ["suggestion"],
            "summary": "summary",
        }

    def test_second_invalid_rubric_result_becomes_safe_model_response_error(self):
        invalid = self.valid_payload()
        invalid["issues"] = []
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze", side_effect=[invalid, invalid]
        ):
            with self.assertRaisesRegex(ModelResponseError, "模型返回的评测结果无效"):
                analyze_image_bytes(b"image", "sample.jpg", "photography")

    def test_result_requires_paired_issues_and_suggestions(self):
        payload = self.valid_payload()
        payload["issues"] = ["issue one", "issue two"]
        with self.assertRaisesRegex(ValueError, "数量必须一致"):
            validate_result(payload)

    def test_result_rejects_empty_summary(self):
        payload = self.valid_payload()
        payload["summary"] = " "
        with self.assertRaisesRegex(ValueError, "总结不能为空"):
            validate_result(payload)

    def test_timeout_is_normalized(self):
        client = ModelClient()
        client.mode = "real"
        client.api_key = "test-placeholder"
        with patch("core.model_client.request.urlopen", side_effect=TimeoutError):
            with self.assertRaises(ModelTimeoutError):
                client.analyze("encoded", "a.jpg", "prompt")

    def test_url_error_is_normalized_as_unavailable(self):
        client = ModelClient()
        client.mode = "real"
        client.api_key = "test-placeholder"
        with patch("core.model_client.request.urlopen", side_effect=URLError("down")):
            with self.assertRaises(ModelUnavailableError):
                client.analyze("encoded", "a.jpg", "prompt")

    def test_upstream_http_error_is_normalized_as_unavailable(self):
        client = ModelClient()
        client.mode = "real"
        client.api_key = "test-placeholder"
        error = HTTPError("https://api.openai.com", 429, "rate", {}, None)
        self.addCleanup(error.close)
        with patch("core.model_client.request.urlopen", side_effect=error):
            with self.assertRaises(ModelUnavailableError):
                client.analyze("encoded", "a.jpg", "prompt")

    def test_invalid_model_json_is_normalized(self):
        client = ModelClient()
        client.mode = "real"
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"output": [{"content": [{"text": "not-json"}]}]}
        ).encode()
        with patch("core.model_client.request.urlopen", return_value=response):
            with self.assertRaises(ModelResponseError):
                client.analyze("encoded", "a.jpg", "prompt")

    def test_invalid_http_response_body_is_normalized(self):
        client = ModelClient()
        client.mode = "real"
        for body in (b"\xff", b"not-json"):
            with self.subTest(body=body):
                response = unittest.mock.MagicMock()
                response.__enter__.return_value.read.return_value = body
                with patch("core.model_client.request.urlopen", return_value=response):
                    with self.assertRaises(ModelResponseError):
                        client.analyze("encoded", "a.jpg", "prompt")

    def test_invalid_http_response_body_is_retried_once(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"not-json"
        with patch.dict(os.environ, {"AI_IMAGE_EVAL_MODE": "real"}), patch(
            "core.analyzer.image_to_base64", return_value="encoded"
        ), patch(
            "core.model_client.request.urlopen", return_value=response
        ) as urlopen:
            with self.assertRaises(ModelResponseError):
                analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(urlopen.call_count, 2)

    def test_request_uses_strict_result_schema(self):
        client = ModelClient()
        client.mode = "real"
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"output": [{"content": [{"text": json.dumps(self.valid_payload())}]}]}
        ).encode()
        with patch("core.model_client.request.urlopen", return_value=response) as urlopen:
            client.analyze("encoded", "a.jpg", "prompt")
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertFalse(body["text"]["format"]["schema"]["additionalProperties"])

    def test_invalid_model_response_is_retried_once(self):
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze",
            side_effect=[ModelResponseError("bad"), self.valid_payload()],
        ) as analyze:
            result = analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(result["summary"], "summary")
        self.assertEqual(analyze.call_count, 2)

    def test_invalid_validated_result_is_retried_once(self):
        invalid = self.valid_payload()
        invalid["summary"] = " "
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze",
            side_effect=[invalid, self.valid_payload()],
        ) as analyze:
            analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(analyze.call_count, 2)

    def test_malformed_nested_result_is_retried_once(self):
        invalid = self.valid_payload()
        invalid["issues"] = None
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze",
            side_effect=[invalid, self.valid_payload()],
        ) as analyze:
            result = analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(result["summary"], "summary")
        self.assertEqual(analyze.call_count, 2)

    def test_extra_score_dimension_is_retried_once(self):
        invalid = self.valid_payload()
        invalid["scores"]["extra"] = 7
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze", return_value=invalid
        ) as analyze:
            with self.assertRaisesRegex(ModelResponseError, "模型返回的评测结果无效"):
                analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(analyze.call_count, 2)

    def test_non_object_result_is_retried_once(self):
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze", return_value=None
        ) as analyze:
            with self.assertRaisesRegex(ModelResponseError, "模型返回的评测结果无效"):
                analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(analyze.call_count, 2)

    def test_timeout_is_not_retried(self):
        with patch("core.analyzer.image_to_base64", return_value="encoded"), patch(
            "core.analyzer.ModelClient.analyze", side_effect=ModelTimeoutError("timeout")
        ) as analyze:
            with self.assertRaises(ModelTimeoutError):
                analyze_image_bytes(b"image", "sample.jpg", "photography")
        self.assertEqual(analyze.call_count, 1)

    def test_analyzer_requires_image_type(self):
        with self.assertRaises(TypeError):
            analyze_image_bytes(b"image", "sample.jpg")

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

    def test_normalize_model_payload_maps_scores_and_text(self):
        raw = {
            "scores": {"构图": "8", "色彩": 7, "主体": 6, "清晰度": 8, "视觉层次": 7},
            "issues": ["背景干扰主体"],
            "suggestions": ["简化背景元素"],
            "summary": "主体明确，但背景信息偏多。",
        }
        result = normalize_model_payload(raw)
        self.assertEqual(result["scores"]["构图"], 8)
        self.assertEqual(result["issues"][0], "背景干扰主体")

    def test_model_client_uses_mock_mode_when_env_set(self):
        original_mode = os.environ.get("AI_IMAGE_EVAL_MODE")
        try:
            os.environ["AI_IMAGE_EVAL_MODE"] = "mock"
            client = ModelClient()
            payload = client.analyze("fake-base64", "sample.jpg", "prompt")
            self.assertGreaterEqual(payload["scores"]["构图"], 1)
        finally:
            if original_mode is None:
                os.environ.pop("AI_IMAGE_EVAL_MODE", None)
            else:
                os.environ["AI_IMAGE_EVAL_MODE"] = original_mode


if __name__ == "__main__":
    unittest.main()

