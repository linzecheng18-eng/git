import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticTests(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    def test_image_type_controls_and_request_header_exist(self):
        for image_type in ("photography", "ai_generated", "social_media"):
            self.assertIn(f'value="{image_type}"', self.html)
        self.assertEqual(self.html.count('name="imageType"'), 3)
        self.assertNotIn(" checked", self.html)
        self.assertIn('"X-Image-Type"', self.script)

    def test_semantic_upload_status_and_result_structure_exist(self):
        for fragment in (
            '<fieldset id="imageTypeGroup">',
            '<legend>这是什么类型的图片？</legend>',
            'accept="image/jpeg,image/png,image/webp"',
            'id="preview"',
            'role="status" aria-live="polite"',
            '<section id="result"',
            'class="result" hidden',
            'id="summary"',
            'id="diagnosis"',
            'id="scores"',
            'id="resetBtn"',
        ):
            self.assertIn(fragment, self.html)

    def test_script_validates_upload_and_handles_errors_without_html_injection(self):
        self.assertNotIn("innerHTML", self.script)
        for fragment in (
            "10 * 1024 * 1024",
            '"image/jpeg"',
            '"image/png"',
            '"image/webp"',
            "response.ok",
            "payload.error.message",
            "网络连接失败，请检查后重试。",
            "button.disabled = true",
            "button.disabled = false",
            "document.createElement",
            "textContent",
        ):
            self.assertIn(fragment, self.script)

    def test_preview_object_urls_are_released_on_change_and_reset(self):
        self.assertIn("URL.createObjectURL", self.script)
        self.assertIn("URL.revokeObjectURL", self.script)
        self.assertGreaterEqual(self.script.count("releasePreview()"), 3)
        self.assertIn('fileInput.addEventListener("change"', self.script)
        self.assertIn('resetButton.addEventListener("click"', self.script)

    def test_mobile_first_accessibility_constraints_exist(self):
        compact = "".join(self.styles.split())
        self.assertIn("max-width:720px", compact)
        self.assertIn("min-height:44px", compact)
        self.assertIn(":focus-visible", self.styles)
        self.assertIn("overflow-wrap:anywhere", compact)
        self.assertIn("@media(min-width:", compact)


if __name__ == "__main__":
    unittest.main()
