import csv
from pathlib import Path

from core.analyzer import analyze_image_bytes

DIMENSIONS = ["构图", "色彩", "主体", "清晰度", "视觉层次"]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "test_set" / "manifest.csv"
IMAGE_DIR = ROOT / "data" / "test_set" / "images"
OUTPUT = ROOT / "data" / "eval_results" / "round1.csv"


def _manifest_fieldnames():
    return [
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
    ]


def _result_fieldnames():
    return [
        "image_id",
        "file_name",
        "source",
        "category",
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
        "manual_summary",
        "summary",
        "notes",
    ]


def scaffold_manifest(image_dir=IMAGE_DIR, manifest_path=MANIFEST):
    image_dir = Path(image_dir)
    manifest_path = Path(manifest_path)

    image_paths = sorted(
        [path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda item: item.name.lower(),
    )

    rows = []
    for index, image_path in enumerate(image_paths, start=1):
        rows.append(
            {
                "image_id": f"img-{index:03d}",
                "file_name": image_path.name,
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

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_manifest_fieldnames())
        writer.writeheader()
        writer.writerows(rows)
    return rows


def run_eval(manifest_path=MANIFEST, image_dir=IMAGE_DIR, output_path=OUTPUT):
    manifest_path = Path(manifest_path)
    image_dir = Path(image_dir)
    output_path = Path(output_path)

    rows = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            image_path = image_dir / row["file_name"]
            payload = analyze_image_bytes(image_path.read_bytes(), row["file_name"])
            rows.append(
                {
                    "image_id": row["image_id"],
                    "file_name": row["file_name"],
                    "source": row.get("source", ""),
                    "category": row.get("category", ""),
                    "ai_构图": payload["scores"]["构图"],
                    "ai_色彩": payload["scores"]["色彩"],
                    "ai_主体": payload["scores"]["主体"],
                    "ai_清晰度": payload["scores"]["清晰度"],
                    "ai_视觉层次": payload["scores"]["视觉层次"],
                    "manual_构图": row.get("manual_构图", ""),
                    "manual_色彩": row.get("manual_色彩", ""),
                    "manual_主体": row.get("manual_主体", ""),
                    "manual_清晰度": row.get("manual_清晰度", ""),
                    "manual_视觉层次": row.get("manual_视觉层次", ""),
                    "manual_summary": row.get("manual_summary", ""),
                    "summary": payload["summary"],
                    "notes": row.get("notes", ""),
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_result_fieldnames())
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    run_eval()
