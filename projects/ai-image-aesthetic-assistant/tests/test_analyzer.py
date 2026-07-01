import os
import unittest
from unittest.mock import patch

from core.analyzer import analyze_image_bytes, normalize_model_payload
from core.model_client import ModelClient


class AnalyzerTests(unittest.TestCase):
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

