import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from scripts.build_eval_report import build_report
from scripts.run_eval import run_eval, scaffold_manifest


class RunEvalTests(unittest.TestCase):
    def test_scaffold_manifest_creates_rows_from_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()

            for name in ["b.jpg", "a.png"]:
                image = Image.new("RGB", (32, 32), "white")
                image.save(image_dir / name)

            manifest_path = root / "manifest.csv"
            rows = scaffold_manifest(image_dir, manifest_path)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["image_id"], "img-001")
            self.assertEqual(rows[0]["file_name"], "a.png")
            self.assertEqual(rows[0]["image_type"], "")
            self.assertEqual(rows[1]["file_name"], "b.jpg")
            self.assertTrue(manifest_path.exists())

    def test_run_eval_writes_output_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            image_path = image_dir / "sample.jpg"

            image = Image.new("RGB", (48, 48), "white")
            image.save(image_path, format="JPEG")

            manifest_path = root / "manifest.csv"
            output_path = root / "round1.csv"
            with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "image_id",
                        "file_name",
                        "image_type",
                        "source",
                        "category",
                        "manual_构图",
                        "manual_色彩",
                        "manual_主体",
                        "manual_清晰度",
                        "manual_视觉层次",
                        "manual_summary",
                        "notes",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "image_id": "img-001",
                        "file_name": "sample.jpg",
                        "image_type": "photography",
                        "source": "local",
                        "category": "demo",
                        "manual_构图": "7",
                        "manual_色彩": "7",
                        "manual_主体": "7",
                        "manual_清晰度": "7",
                        "manual_视觉层次": "7",
                        "manual_summary": "人工基准",
                        "notes": "测试样例",
                    }
                )

            rows = run_eval(manifest_path, image_dir, output_path)

            self.assertEqual(len(rows), 1)
            self.assertTrue(output_path.exists())
            self.assertEqual(rows[0]["image_id"], "img-001")
            self.assertIn("ai_构图", rows[0])

    def test_run_eval_rejects_empty_image_type(self):
        self._assert_invalid_image_type("")

    def test_run_eval_rejects_unknown_image_type(self):
        self._assert_invalid_image_type("other")

    def _assert_invalid_image_type(self, image_type):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            manifest_path = root / "manifest.csv"
            with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["image_id", "file_name", "image_type"])
                writer.writeheader()
                writer.writerow(
                    {"image_id": "img-001", "file_name": "missing.jpg", "image_type": image_type}
                )

            with self.assertRaisesRegex(ValueError, "image_type"):
                run_eval(manifest_path, image_dir, root / "output.csv")


    def test_scaffold_manifest_includes_empty_product_judgments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (8, 8), "white").save(image_dir / "a.png")
            rows = scaffold_manifest(image_dir, root / "manifest.csv")
            self.assertEqual(rows[0]["diagnosis_acceptable"], "")
            self.assertEqual(rows[0]["suggestion_actionable"], "")

    def test_run_eval_preserves_and_normalizes_product_judgments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "sample.jpg").write_bytes(b"image")
            manifest = root / "manifest.csv"
            with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["image_id", "file_name", "image_type", "diagnosis_acceptable", "suggestion_actionable"])
                writer.writeheader()
                writer.writerow({"image_id": "img-001", "file_name": "sample.jpg", "image_type": "photography", "diagnosis_acceptable": " yes ", "suggestion_actionable": "no"})
            payload = {"scores": {name: 7 for name in ["构图", "色彩", "主体", "清晰度", "视觉层次"]}, "summary": "mock"}
            with patch("scripts.run_eval.analyze_image_bytes", return_value=payload):
                rows = run_eval(manifest, root, root / "round.csv")
            self.assertEqual(rows[0]["diagnosis_acceptable"], "yes")
            self.assertEqual(rows[0]["suggestion_actionable"], "no")

    def test_run_eval_rejects_invalid_product_judgment_with_field_and_image_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.csv"
            with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["image_id", "file_name", "image_type", "diagnosis_acceptable", "suggestion_actionable"])
                writer.writeheader()
                writer.writerow({"image_id": "img-009", "file_name": "missing.jpg", "image_type": "photography", "diagnosis_acceptable": "YES", "suggestion_actionable": ""})
            with self.assertRaisesRegex(ValueError, "diagnosis_acceptable.*img-009"):
                run_eval(manifest, root, root / "round.csv")

    def test_manifest_to_round_to_report_preserves_product_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "sample.jpg").write_bytes(b"image")
            manifest = root / "manifest.csv"
            round_csv = root / "round.csv"
            with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["image_id", "file_name", "image_type", "diagnosis_acceptable", "suggestion_actionable"])
                writer.writeheader()
                writer.writerow({"image_id": "img-001", "file_name": "sample.jpg", "image_type": "photography", "diagnosis_acceptable": "yes", "suggestion_actionable": "no"})
            payload = {"scores": {name: 7 for name in ["构图", "色彩", "主体", "清晰度", "视觉层次"]}, "summary": "mock"}
            with patch("scripts.run_eval.analyze_image_bytes", return_value=payload):
                run_eval(manifest, root, round_csv)
            summary = build_report(round_csv, root / "report.md")
            self.assertEqual(summary["judged_count"], 1)
            self.assertEqual(summary["diagnosis_accuracy_rate"], 1.0)
            self.assertEqual(summary["suggestion_actionability_rate"], 0.0)
            self.assertFalse(summary["product_acceptance_passed"])


if __name__ == "__main__":
    unittest.main()
