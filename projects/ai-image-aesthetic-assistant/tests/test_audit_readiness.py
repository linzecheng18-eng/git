import csv
import tempfile
import unittest
from pathlib import Path

from scripts.audit_readiness import audit_readiness


class AuditReadinessTests(unittest.TestCase):
    def test_audit_readiness_counts_images_and_manual_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            (image_dir / "a.jpg").write_bytes(b"one")
            (image_dir / "b.png").write_bytes(b"two")

            manifest_path = root / "manifest.csv"
            report_path = root / "report.md"
            with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "image_id",
                        "file_name",
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
                        "file_name": "a.jpg",
                        "source": "local",
                        "category": "demo",
                        "manual_构图": "7",
                        "manual_色彩": "7",
                        "manual_主体": "7",
                        "manual_清晰度": "7",
                        "manual_视觉层次": "7",
                        "manual_summary": "完整",
                        "notes": "",
                    }
                )
                writer.writerow(
                    {
                        "image_id": "img-002",
                        "file_name": "b.png",
                        "source": "",
                        "category": "",
                        "manual_构图": "",
                        "manual_色彩": "",
                        "manual_主体": "",
                        "manual_清晰度": "",
                        "manual_视觉层次": "",
                        "manual_summary": "",
                        "notes": "",
                    }
                )

            summary = audit_readiness(manifest_path, image_dir, report_path, target_count=50)

            self.assertEqual(summary["image_count"], 2)
            self.assertEqual(summary["manifest_rows"], 2)
            self.assertEqual(summary["manual_completed_rows"], 1)
            self.assertEqual(summary["manual_missing_rows"], 1)
            self.assertEqual(summary["missing_images"], [])
            self.assertFalse(summary["meets_target_count"])
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("人工评分完成：1 / 2", content)
            self.assertIn("距离 50 张目标还差：48", content)

    def test_audit_readiness_handles_missing_image_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.csv"
            report_path = root / "report.md"
            with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "image_id",
                        "file_name",
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

            summary = audit_readiness(manifest_path, root / "missing-images", report_path, target_count=50)

            self.assertEqual(summary["image_count"], 0)
            self.assertEqual(summary["missing_images"], [])
            self.assertFalse(summary["meets_target_count"])


if __name__ == "__main__":
    unittest.main()
