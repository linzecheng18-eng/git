DIMENSIONS = ["构图", "色彩", "主体", "清晰度", "视觉层次"]


def score_schema():
    return {
        "dimensions": DIMENSIONS,
        "scale": {"min": 1, "max": 10},
    }


def validate_result(result):
    scores = dict(result.get("scores", {}))
    missing = [name for name in DIMENSIONS if name not in scores]
    if missing:
        raise ValueError(f"缺少评分维度: {', '.join(missing)}")

    normalized_scores = {}
    for name in DIMENSIONS:
        value = int(scores[name])
        if value < 1 or value > 10:
            raise ValueError(f"{name} 分值超出范围")
        normalized_scores[name] = value

    return {
        "scores": normalized_scores,
        "issues": list(result.get("issues", [])),
        "suggestions": list(result.get("suggestions", [])),
        "summary": str(result.get("summary", "")).strip(),
    }

