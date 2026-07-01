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

    issues = [str(item).strip() for item in result.get("issues", []) if str(item).strip()]
    suggestions = [str(item).strip() for item in result.get("suggestions", []) if str(item).strip()]
    summary = str(result.get("summary", "")).strip()
    if not 1 <= len(issues) <= 3:
        raise ValueError("问题数量必须为 1-3 条")
    if len(issues) != len(suggestions):
        raise ValueError("问题与建议数量必须一致")
    if not summary:
        raise ValueError("总结不能为空")

    return {
        "scores": normalized_scores,
        "issues": issues,
        "suggestions": suggestions,
        "summary": summary,
    }

