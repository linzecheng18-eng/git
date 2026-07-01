import unittest

from core.rubric import DIMENSIONS, validate_result


class RubricTests(unittest.TestCase):
    def test_dimensions_are_fixed(self):
        self.assertEqual(DIMENSIONS, ["构图", "色彩", "主体", "清晰度", "视觉层次"])

    def test_validate_result_accepts_complete_payload(self):
        payload = {
            "scores": {"构图": 7, "色彩": 8, "主体": 7, "清晰度": 6, "视觉层次": 7},
            "issues": ["主体不够突出"],
            "suggestions": ["提高主体与背景反差"],
            "summary": "整体完成度中等，建议强化主体。",
        }
        normalized = validate_result(payload)
        self.assertEqual(normalized["scores"]["色彩"], 8)

    def test_validate_result_rejects_missing_dimension(self):
        payload = {
            "scores": {"构图": 7, "色彩": 8},
            "issues": [],
            "suggestions": [],
            "summary": "x",
        }
        with self.assertRaisesRegex(ValueError, "缺少评分维度"):
            validate_result(payload)

    def test_validate_result_rejects_extra_dimension(self):
        payload = {
            "scores": {**{name: 7 for name in DIMENSIONS}, "extra": 7},
            "issues": ["issue"],
            "suggestions": ["suggestion"],
            "summary": "summary",
        }
        with self.assertRaisesRegex(ValueError, "额外评分维度: extra"):
            validate_result(payload)

    def test_validate_result_rejects_non_object_top_level_values(self):
        for payload in ([], "text", None):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "结果必须为对象"):
                    validate_result(payload)

    def test_validate_result_rejects_malformed_nested_values(self):
        valid = {
            "scores": {name: 7 for name in DIMENSIONS},
            "issues": ["issue"],
            "suggestions": ["suggestion"],
            "summary": "summary",
        }
        malformed_values = (
            ("scores", None),
            ("issues", None),
            ("suggestions", None),
            ("issues", [1]),
            ("issues", [None]),
            ("suggestions", [1]),
            ("summary", 1),
        )
        for field, value in malformed_values:
            with self.subTest(field=field, value=value):
                payload = dict(valid)
                payload[field] = value
                with self.assertRaises(ValueError):
                    validate_result(payload)


if __name__ == "__main__":
    unittest.main()

