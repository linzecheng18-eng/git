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
