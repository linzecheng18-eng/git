import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_eval_report import build_report, calculate_product_metrics


class EvalReportTests(unittest.TestCase):
    def _complete_evidence_row(self, index, diagnosis="yes", suggestion="yes"):
        row = {
            "image_id": f"img-{index:03d}", "image_type": "photography",
            "issues": json.dumps(["issue"]), "suggestions": json.dumps(["suggestion"]),
            "summary": "summary", "diagnosis_acceptable": diagnosis,
            "suggestion_actionable": suggestion,
        }
        row.update({f"ai_{name}": "8" for name in __import__("scripts.build_eval_report", fromlist=["DIMENSIONS"]).DIMENSIONS})
        return row

    def test_two_column_fifty_row_csv_is_invalid_evidence_and_not_accepted(self):
        rows = [{"diagnosis_acceptable": "yes", "suggestion_actionable": "yes"} for _ in range(50)]
        summary, content = self._build_product_report(rows, raw=True)
        self.assertEqual(summary["total_rows"], 0)
        self.assertEqual(summary["invalid_evidence_count"], 50)
        self.assertFalse(summary["product_acceptance_passed"])
        self.assertIn("Invalid evidence: 50", content)

    def test_fifty_complete_evidence_rows_can_be_accepted(self):
        rows = [self._complete_evidence_row(i) for i in range(50)]
        summary, content = self._build_product_report(rows)
        self.assertEqual(summary["total_rows"], 50)
        self.assertEqual(summary["invalid_evidence_count"], 0)
        self.assertTrue(summary["product_acceptance_passed"])
        self.assertIn("Product acceptance: PASSED", content)
    def test_report_calculates_product_success_rates(self):
        rows = [
            {"diagnosis_acceptable": "yes", "suggestion_actionable": "yes"},
            {"diagnosis_acceptable": "yes", "suggestion_actionable": "no"},
            {"diagnosis_acceptable": "no", "suggestion_actionable": "yes"},
            {"diagnosis_acceptable": "", "suggestion_actionable": "yes"},
            {"diagnosis_acceptable": "yes", "suggestion_actionable": "invalid"},
        ]

        metrics = calculate_product_metrics(rows)

        self.assertEqual(metrics["judged_count"], 3)
        self.assertAlmostEqual(metrics["diagnosis_accuracy_rate"], 2 / 3)
        self.assertAlmostEqual(metrics["suggestion_actionability_rate"], 2 / 3)

    def test_report_marks_fewer_than_fifty_samples_as_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            round_csv = Path(tmpdir) / "round1.csv"
            report_path = Path(tmpdir) / "report.md"
            row = self._complete_evidence_row(1)
            with round_csv.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            summary = build_report(round_csv, report_path)

            self.assertEqual(summary["judged_count"], 1)
            self.assertEqual(summary["diagnosis_accuracy_rate"], 1.0)
            self.assertEqual(summary["suggestion_actionability_rate"], 1.0)
            self.assertFalse(summary["sample_count_passed"])
            self.assertTrue(summary["diagnosis_threshold_passed"])
            self.assertTrue(summary["suggestion_threshold_passed"])
            self.assertFalse(summary["product_acceptance_passed"])
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("Sample count: 1 / 50 (NOT MET)", content)
            self.assertIn("Judged count: 1", content)
            self.assertIn("Diagnosis accuracy rate: 100.00% (MET)", content)
            self.assertIn("Suggestion actionability rate: 100.00% (MET)", content)
            self.assertIn("Product acceptance: NOT PASSED", content)

    def test_build_report_summarizes_completed_rows_and_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            round_csv = Path(tmpdir) / "round1.csv"
            report_path = Path(tmpdir) / "report.md"
            with round_csv.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "image_id",
                        "image_type",
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
                        "issues",
                        "suggestions",
                        "summary",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "image_id": "img-001",
                        "image_type": "photography",
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
                        "issues": '["issue"]',
                        "suggestions": '["suggestion"]',
                        "summary": "summary",
                    }
                )
                writer.writerow(
                    {
                        "image_id": "img-002",
                        "image_type": "photography",
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
                        "issues": '["issue"]',
                        "suggestions": '["suggestion"]',
                        "summary": "summary",
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


    def test_fifty_total_rows_with_only_one_judged_is_not_accepted(self):
        rows = [{"diagnosis_acceptable": "yes", "suggestion_actionable": "yes"}] + [
            {"diagnosis_acceptable": "", "suggestion_actionable": ""} for _ in range(49)
        ]
        summary, content = self._build_product_report(rows)
        self.assertTrue(summary["sample_count_passed"])
        self.assertFalse(summary["judged_count_passed"])
        self.assertFalse(summary["product_acceptance_passed"])
        self.assertIn("Judged count: 1 / 50 (NOT MET)", content)

    def test_fifty_judged_rows_at_both_thresholds_are_accepted(self):
        rows = [
            {"diagnosis_acceptable": "yes" if index < 35 else "no", "suggestion_actionable": "yes" if index >= 15 else "no"}
            for index in range(50)
        ]
        summary, content = self._build_product_report(rows)
        self.assertTrue(summary["judged_count_passed"])
        self.assertTrue(summary["product_acceptance_passed"])
        self.assertIn("Product acceptance: PASSED", content)

    def _build_product_report(self, rows, raw=False):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        round_csv = Path(tmpdir.name) / "round.csv"
        report = Path(tmpdir.name) / "report.md"
        if not raw and "image_id" not in rows[0]:
            rows = [self._complete_evidence_row(i, row["diagnosis_acceptable"], row["suggestion_actionable"])
                    for i, row in enumerate(rows)]
        with round_csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summary = build_report(round_csv, report)
        return summary, report.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
