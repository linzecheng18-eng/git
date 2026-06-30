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


if __name__ == "__main__":
    unittest.main()

