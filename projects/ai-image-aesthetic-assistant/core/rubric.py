DIMENSIONS = ["构图", "色彩", "主体", "清晰度", "视觉层次"]


def score_schema():
    return {
        "dimensions": DIMENSIONS,
        "scale": {"min": 1, "max": 10},
    }


def validate_result(result):
    if not isinstance(result, dict):
        raise ValueError("结果必须为对象")

    scores = result.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("scores 必须为对象")
    missing = [name for name in DIMENSIONS if name not in scores]
    if missing:
        raise ValueError(f"缺少评分维度: {', '.join(missing)}")

    normalized_scores = {}
    for name in DIMENSIONS:
        try:
            value = int(scores[name])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} 分值必须为整数") from exc
        if value < 1 or value > 10:
            raise ValueError(f"{name} 分值超出范围")
        normalized_scores[name] = value

    issues = result.get("issues")
    suggestions = result.get("suggestions")
    summary = result.get("summary")
    if not isinstance(issues, list):
        raise ValueError("issues 必须为列表")
    if not all(isinstance(item, str) for item in issues):
        raise ValueError("issues 每项必须为字符串")
    if not isinstance(suggestions, list):
        raise ValueError("suggestions 必须为列表")
    if not all(isinstance(item, str) for item in suggestions):
        raise ValueError("suggestions 每项必须为字符串")
    if not isinstance(summary, str):
        raise ValueError("summary 必须为字符串")

    issues = [item.strip() for item in issues if item.strip()]
    suggestions = [item.strip() for item in suggestions if item.strip()]
    summary = summary.strip()
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

