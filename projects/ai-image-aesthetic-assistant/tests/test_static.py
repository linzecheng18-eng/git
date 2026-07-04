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

    def test_non_ascii_filename_is_encoded_before_being_used_as_header(self):
        self.assertIn('"X-Filename": encodeURIComponent(file.name)', self.script)
        self.assertNotIn('"X-Filename": file.name', self.script)

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
            "网络连接失败，请检查后重试。",
            "button.disabled = true",
            "button.disabled = false",
            "document.createElement",
            "textContent",
        ):
            self.assertIn(fragment, self.script)

    def test_response_errors_are_safely_parsed_and_use_stable_messages(self):
        for fragment in (
            "async function parseJsonResponse(response)",
            "await response.json()",
            "function isValidPayload(payload)",
            "服务器返回的数据异常，请稍后重试。",
            "评测失败，请稍后重试。",
            "网络连接失败，请检查后重试。",
        ):
            self.assertIn(fragment, self.script)
        self.assertNotIn("error instanceof TypeError", self.script)
        self.assertNotIn("throw new Error(payload", self.script)

    def test_request_locks_and_restores_every_mutable_input(self):
        for fragment in (
            'document.querySelectorAll(\'input[name="imageType"]\')',
            "fileInput.disabled = true",
            "fileInput.disabled = false",
            "control.disabled = true",
            "control.disabled = false",
        ):
            self.assertIn(fragment, self.script)

    def test_result_and_reset_move_focus_programmatically(self):
        self.assertIn('id="resultTitle" tabindex="-1"', self.html)
        self.assertIn('document.getElementById("resultTitle")', self.script)
        self.assertIn("resultTitle.focus()", self.script)
        self.assertIn("fileInput.focus()", self.script)

    def test_preview_object_urls_are_released_on_change_and_reset(self):
        self.assertIn("URL.createObjectURL", self.script)
        self.assertIn("URL.revokeObjectURL", self.script)
        self.assertGreaterEqual(self.script.count("clearPreview()"), 3)
        self.assertIn('fileInput.addEventListener("change"', self.script)
        self.assertIn('resetButton.addEventListener("click"', self.script)
        self.assertIn("无法预览图片，请重新选择。", self.script)
        self.assertIn("preview.removeAttribute(\"src\")", self.script)
        self.assertNotIn("statusText.textContent = error.message;\n  }\n});", self.script)

    def test_mobile_first_accessibility_constraints_exist(self):
        compact = "".join(self.styles.split())
        self.assertIn("max-width:720px", compact)
        self.assertIn("min-height:44px", compact)
        self.assertIn(":focus-visible", self.styles)
        self.assertIn("overflow-wrap:anywhere", compact)
        self.assertIn("@media(min-width:", compact)


if __name__ == "__main__":
    unittest.main()
