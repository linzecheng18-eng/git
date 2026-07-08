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
            "Gallery Flow",
            "Gallery Story Studio",
            'class="gallery-flow-shell"',
            'data-view="landing"',
            'data-view="modes"',
            'data-view="input"',
            'data-view="result"',
            'data-mode="story"',
            'data-mode="aesthetic"',
            'data-mode="identity"',
            'id="backgroundNotes"',
            'id="resultPreview"',
            'data-target-view="modes"',
            'data-target-view="landing"',
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
            "viewTriggers.forEach",
            "URL.createObjectURL",
            "URL.revokeObjectURL",
            "view.setAttribute(\"aria-hidden\"",
            "renderDemoResult",
            "goToView",
            "setActiveMode",
            "handleInteractiveTilt",
            "textContent",
        ):
            self.assertIn(fragment, self.script)

    def test_interactive_visual_language_exists(self):
        compact = "".join(self.styles.split())
        for fragment in (
            ".gallery-flow-shell{",
            ".flow-nav-pill{",
            ".flow-nav-pillbutton{",
            ".view-stage{",
            ".flow-view{",
            ".flow-view.active{",
            ".flow-view.slide-from-right{",
            ".flow-view.slide-from-left{",
            ".floating-preview-card{",
            ".mode-card{",
            ".mode-card.active{",
            ".interactive-tilt{",
            ".progress-step.is-active{",
            ".result-card{",
            "@keyframespulse",
            "@keyframesviewIn",
            "@media(max-width:",
        ):
            self.assertIn(fragment, compact)
        self.assertIn(":focus-visible", self.styles)

    def test_views_are_sliding_panels_not_stacked_sections(self):
        compact = "".join(self.styles.split())
        for fragment in (
            ".view-stage{position:relative",
            "overflow:hidden",
            ".flow-view{position:absolute",
            "inset:0",
            "pointer-events:none",
            ".flow-view.active{position:relative",
            "pointer-events:auto",
            "will-change:transform,opacity",
        ):
            self.assertIn(fragment, compact)
        for fragment in (
            "let activeViewIndex = 0",
            "const viewOrder",
            "slide-from-right",
            "slide-from-left",
            "trigger.classList.toggle(\"active\"",
        ):
            self.assertIn(fragment, self.script)

    def test_scores_are_rendered_as_star_ratings(self):
        for fragment in (
            "createStarRating",
            'className = "rating"',
            'className = "score-row"',
            'aria-label',
            '★',
        ):
            self.assertIn(fragment, self.script)
        for fragment in (
            ".rating{",
            ".rating-star{",
            ".rating-star.filled{",
            "#ffa723",
        ):
            self.assertIn(fragment, "".join(self.styles.split()))


if __name__ == "__main__":
    unittest.main()
