import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_eval_report import build_report


class EvalReportTests(unittest.TestCase):
    def test_build_report_summarizes_completed_rows_and_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            round_csv = Path(tmpdir) / "round1.csv"
            report_path = Path(tmpdir) / "report.md"
            with round_csv.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "image_id",
                        "file_name",
                        "ai_构图",
                        "ai_色彩",
                        "ai_主体",
                        "ai_清晰度",
                        "ai_视觉层次",
                        "manual_构图",
                        "manual_色彩",
                        "manual_主体",
                        "manual_清晰度",
                        "manual_视觉层次",
                        "notes",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "image_id": "img-001",
                        "file_name": "a.jpg",
                        "ai_构图": "8",
                        "ai_色彩": "7",
                        "ai_主体": "7",
                        "ai_清晰度": "6",
                        "ai_视觉层次": "5",
                        "manual_构图": "6",
                        "manual_色彩": "7",
                        "manual_主体": "8",
                        "manual_清晰度": "5",
                        "manual_视觉层次": "5",
                        "notes": "主体略弱",
                    }
                )
                writer.writerow(
                    {
                        "image_id": "img-002",
                        "file_name": "b.jpg",
                        "ai_构图": "7",
                        "ai_色彩": "7",
                        "ai_主体": "6",
                        "ai_清晰度": "6",
                        "ai_视觉层次": "6",
                        "manual_构图": "",
                        "manual_色彩": "",
                        "manual_主体": "",
                        "manual_清晰度": "",
                        "manual_视觉层次": "",
                        "notes": "",
                    }
                )

            summary = build_report(round_csv, report_path)

            self.assertEqual(summary["total_rows"], 2)
            self.assertEqual(summary["completed_rows"], 1)
            self.assertEqual(summary["missing_manual_rows"], 1)
            self.assertEqual(summary["completion_rate"], 0.5)
            self.assertEqual(summary["dimension_mae"]["构图"], 2.0)
            self.assertEqual(summary["largest_gap_cases"][0]["image_id"], "img-001")
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("已完成人工评分：1 / 2", content)
            self.assertIn("待补人工评分：1", content)
            self.assertIn("构图", content)


if __name__ == "__main__":
    unittest.main()
