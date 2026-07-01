import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

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


if __name__ == "__main__":
    unittest.main()
