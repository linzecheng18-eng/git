import csv
from pathlib import Path

DIMENSIONS = ["构图", "色彩", "主体", "清晰度", "视觉层次"]


def _to_int(value):
    text = str(value).strip()
    if not text:
        return None
    return int(text)


def build_report(round_csv_path, report_path):
    round_csv_path = Path(round_csv_path)
    report_path = Path(report_path)

    with round_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    completed_rows = []
    gap_cases = []
    dimension_diffs = {name: [] for name in DIMENSIONS}

    for row in rows:
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

    total_rows = len(rows)
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

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "total_rows": total_rows,
        "completed_rows": len(completed_rows),
        "missing_manual_rows": missing_manual_rows,
        "completion_rate": completion_rate,
        "dimension_mae": dimension_mae,
        "largest_gap_cases": gap_cases[:5],
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    build_report(
        root / "data" / "eval_results" / "round1.csv",
        root / "docs" / "round1-report.md",
    )
