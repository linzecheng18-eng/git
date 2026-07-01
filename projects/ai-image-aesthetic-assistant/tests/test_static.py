import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticTests(unittest.TestCase):
    def test_image_type_controls_and_request_header_exist(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        for image_type in ("photography", "ai_generated", "social_media"):
            self.assertIn(f'value="{image_type}"', html)
        self.assertNotIn(" checked", html)
        self.assertIn('name="imageType"', html)
        self.assertIn('"X-Image-Type"', script)


if __name__ == "__main__":
    unittest.main()
