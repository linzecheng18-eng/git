import csv
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MANUAL_FIELDS = [
    "manual_构图",
    "manual_色彩",
    "manual_主体",
    "manual_清晰度",
    "manual_视觉层次",
]


def audit_readiness(manifest_path, image_dir, report_path, target_count=50):
    manifest_path = Path(manifest_path)
    image_dir = Path(image_dir)
    report_path = Path(report_path)

    image_names = []
    if image_dir.exists():
        image_names = sorted(
            path.name for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    manual_completed_rows = 0
    missing_images = []
    for row in rows:
        if row.get("file_name", "") not in image_names:
            missing_images.append(row.get("file_name", ""))
        if all(str(row.get(field, "")).strip() for field in MANUAL_FIELDS):
            manual_completed_rows += 1

    manifest_rows = len(rows)
    image_count = len(image_names)
    manual_missing_rows = manifest_rows - manual_completed_rows
    meets_target_count = image_count >= target_count
    report_lines = [
        "# Image Eval Readiness",
        "",
        f"- 图片数量：{image_count}",
        f"- manifest 条数：{manifest_rows}",
        f"- 人工评分完成：{manual_completed_rows} / {manifest_rows}",
        f"- 待补人工评分：{manual_missing_rows}",
        f"- 距离 {target_count} 张目标还差：{max(target_count - image_count, 0)}",
        "",
        "## 缺失图片",
        "",
    ]
    if missing_images:
        for name in missing_images:
            report_lines.append(f"- {name}")
    else:
        report_lines.append("- 无")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "image_count": image_count,
        "manifest_rows": manifest_rows,
        "manual_completed_rows": manual_completed_rows,
        "manual_missing_rows": manual_missing_rows,
        "missing_images": missing_images,
        "meets_target_count": meets_target_count,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    audit_readiness(
        root / "data" / "test_set" / "manifest.csv",
        root / "data" / "test_set" / "images",
        root / "docs" / "readiness-report.md",
    )
