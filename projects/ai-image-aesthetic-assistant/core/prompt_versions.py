PROMPT_VERSIONS = {
    "v1": {
        "label": "基础五维审美评分",
        "prompt": (
            "你是图片审美评测助手。请从构图、色彩、主体、清晰度、视觉层次"
            "五个维度给出 1-10 分评分，并返回 JSON：scores、issues、suggestions、summary。"
        ),
    }
}


def get_prompt(version="v1"):
    return PROMPT_VERSIONS[version]

