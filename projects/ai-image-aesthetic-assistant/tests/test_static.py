import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

    def test_gallery_story_studio_structure_exists(self):
        for fragment in (
            "AI 图片审美与故事分析助手",
            "Gallery Story Studio",
            'class="app-shell"',
            'class="studio-sidebar"',
            'class="mode-card active"',
            'data-mode="story"',
            'data-mode="aesthetic"',
            'data-mode="identity"',
            'id="backgroundNotes"',
            'id="resultPreview"',
        ):
            self.assertIn(fragment, self.html)

    def test_static_prototype_keeps_existing_upload_contract_markers(self):
        for fragment in (
            'id="fileInput"',
            'accept="image/jpeg,image/png,image/webp"',
            'id="preview"',
            'role="status" aria-live="polite"',
            'name="imageType"',
            'value="photography"',
            'value="ai_generated"',
            'value="social_media"',
        ):
            self.assertIn(fragment, self.html)

    def test_interaction_script_is_local_demo_only_and_safe(self):
        self.assertNotIn("fetch(", self.script)
        self.assertNotIn("innerHTML", self.script)
        for fragment in (
            "document.querySelectorAll",
            "modeCards.forEach",
            "progressSteps.forEach",
            "URL.createObjectURL",
            "URL.revokeObjectURL",
            "resultPreview.hidden = false",
            "renderDemoResult",
            "setActiveMode",
            "textContent",
        ):
            self.assertIn(fragment, self.script)

    def test_interactive_visual_language_exists(self):
        compact = "".join(self.styles.split())
        for fragment in (
            ".app-shell{",
            ".studio-sidebar{",
            ".mode-card{",
            ".mode-card.active{",
            ".progress-step.is-active{",
            ".result-card{",
            ".inspiration-grid{",
            "@keyframespulse",
            "@media(max-width:",
        ):
            self.assertIn(fragment, compact)
        self.assertIn(":focus-visible", self.styles)


if __name__ == "__main__":
    unittest.main()
