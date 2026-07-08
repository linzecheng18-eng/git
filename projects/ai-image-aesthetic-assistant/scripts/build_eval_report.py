import csv
import json
from pathlib import Path

PRODUCT_THRESHOLD = 0.7
MINIMUM_SAMPLE_COUNT = 50

DIMENSIONS = ["构图", "色彩", "主体", "清晰度", "视觉层次"]
IMAGE_TYPES = {"photography", "ai_generated", "social_media"}


def _to_int(value):
    text = str(value).strip()
    if not text:
        return None
    if not text.isdecimal():
        return None
    number = int(text)
    return number if 1 <= number <= 10 else None


def _evidence_errors(row):
    errors = []
    if not str(row.get("image_id", "")).strip():
        errors.append("missing image_id")
    if row.get("image_type") not in IMAGE_TYPES:
        errors.append("invalid image_type")
    if any(_to_int(row.get(f"ai_{name}")) is None for name in DIMENSIONS):
        errors.append("invalid AI scores")
    parsed = {}
    for field in ("issues", "suggestions"):
        try:
            value = json.loads(row.get(field, ""))
        except (TypeError, json.JSONDecodeError):
            value = None
        if not isinstance(value, list) or not 1 <= len(value) <= 3 or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            errors.append(f"invalid {field}")
        parsed[field] = value
    if isinstance(parsed["issues"], list) and isinstance(parsed["suggestions"], list):
        if len(parsed["issues"]) != len(parsed["suggestions"]):
            errors.append("issues/suggestions count mismatch")
    if not str(row.get("summary", "")).strip():
        errors.append("missing summary")
    for field in ("diagnosis_acceptable", "suggestion_actionable"):
        if row.get(field) not in {"yes", "no"}:
            errors.append(f"invalid {field}")
    return errors


def calculate_product_metrics(rows):
    judged = [
        row
        for row in rows
        if row.get("diagnosis_acceptable") in {"yes", "no"}
        and row.get("suggestion_actionable") in {"yes", "no"}
    ]
    total = len(judged)
    return {
        "judged_count": total,
        "diagnosis_accuracy_rate": (
            sum(row["diagnosis_acceptable"] == "yes" for row in judged) / total
            if total
            else 0.0
        ),
        "suggestion_actionability_rate": (
            sum(row["suggestion_actionable"] == "yes" for row in judged) / total
            if total
            else 0.0
        ),
    }


def build_report(round_csv_path, report_path):
    round_csv_path = Path(round_csv_path)
    report_path = Path(report_path)

    with round_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    invalid_evidence = []
    valid_rows = []
    for index, row in enumerate(rows, 1):
        errors = _evidence_errors(row)
        if errors:
            invalid_evidence.append((index, errors))
        else:
            valid_rows.append(row)

    completed_rows = []
    gap_cases = []
    dimension_diffs = {name: [] for name in DIMENSIONS}

    for row in valid_rows:
        row_gap = 0
        has_manual_scores = True
        for name in DIMENSIONS:
            ai_value = _to_int(row.get(f"ai_{name}", ""))
            manual_value = _to_int(row.get(f"manual_{name}", ""))
            if ai_value is None or manual_value is None:
                has_manual_scores = False
                continue
            diff = abs(ai_value - manual_value)
            dimension_diffs[name].append(diff)
            row_gap += diff
        if has_manual_scores:
            completed_rows.append(row)
            gap_cases.append(
                {
                    "image_id": row.get("image_id", ""),
                    "file_name": row.get("file_name", ""),
                    "gap_total": row_gap,
                    "notes": row.get("notes", ""),
                }
            )

    total_rows = len(valid_rows)
    product_metrics = calculate_product_metrics(valid_rows)
    sample_count_passed = total_rows >= MINIMUM_SAMPLE_COUNT
    judged_count_passed = product_metrics["judged_count"] >= MINIMUM_SAMPLE_COUNT
    diagnosis_threshold_passed = (
        product_metrics["diagnosis_accuracy_rate"] >= PRODUCT_THRESHOLD
    )
    suggestion_threshold_passed = (
        product_metrics["suggestion_actionability_rate"] >= PRODUCT_THRESHOLD
    )
    product_acceptance_passed = (
        not invalid_evidence
        and sample_count_passed
        and judged_count_passed
        and diagnosis_threshold_passed
        and suggestion_threshold_passed
    )
    missing_manual_rows = total_rows - len(completed_rows)
    completion_rate = round(len(completed_rows) / total_rows, 2) if total_rows else 0.0

    gap_cases.sort(key=lambda item: item["gap_total"], reverse=True)
    dimension_mae = {
        name: round(sum(values) / len(values), 2) if values else None
        for name, values in dimension_diffs.items()
    }

    report_lines = [
        "# Round Evaluation Report",
        "",
        f"- 总样本数：{total_rows}",
        f"- 已完成人工评分：{len(completed_rows)} / {total_rows}",
        f"- 待补人工评分：{missing_manual_rows}",
        f"- 人工评分完成率：{completion_rate}",
        "",
        "## Product acceptance metrics",
        "",
        f"- Sample count: {total_rows} / {MINIMUM_SAMPLE_COUNT} ({'MET' if sample_count_passed else 'NOT MET'})",
        f"- Judged count: {product_metrics['judged_count']} / {MINIMUM_SAMPLE_COUNT} ({'MET' if judged_count_passed else 'NOT MET'})",
        f"- Diagnosis accuracy rate: {product_metrics['diagnosis_accuracy_rate']:.2%} ({'MET' if diagnosis_threshold_passed else 'NOT MET'})",
        f"- Suggestion actionability rate: {product_metrics['suggestion_actionability_rate']:.2%} ({'MET' if suggestion_threshold_passed else 'NOT MET'})",
        f"- Product acceptance: {'PASSED' if product_acceptance_passed else 'NOT PASSED'}",
        f"- Invalid evidence: {len(invalid_evidence)}",
        "",
        "## 各维度平均绝对误差",
        "",
    ]
    for name in DIMENSIONS:
        value = dimension_mae[name]
        report_lines.append(f"- {name}：{'待补人工评分' if value is None else value}")

    report_lines.extend(["", "## 偏差最大的样本", ""])
    if gap_cases:
        for item in gap_cases[:5]:
            notes = item["notes"] or "无备注"
            report_lines.append(
                f"- {item['image_id']} / {item['file_name']}：总偏差 {item['gap_total']}，备注：{notes}"
            )
    else:
        report_lines.append("- 暂无可计算样本")

    report_lines.extend(["", "## Invalid evidence rows", ""])
    if invalid_evidence:
        report_lines.extend(
            f"- Row {index}: {', '.join(errors)}" for index, errors in invalid_evidence
        )
    else:
        report_lines.append("- None")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "total_rows": total_rows,
        "invalid_evidence_count": len(invalid_evidence),
        "completed_rows": len(completed_rows),
        "missing_manual_rows": missing_manual_rows,
        "completion_rate": completion_rate,
        "dimension_mae": dimension_mae,
        "largest_gap_cases": gap_cases[:5],
        **product_metrics,
        "sample_count_passed": sample_count_passed,
        "judged_count_passed": judged_count_passed,
        "diagnosis_threshold_passed": diagnosis_threshold_passed,
        "suggestion_threshold_passed": suggestion_threshold_passed,
        "product_acceptance_passed": product_acceptance_passed,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    build_report(
        root / "data" / "eval_results" / "round1.csv",
        root / "docs" / "round1-report.md",
    )
