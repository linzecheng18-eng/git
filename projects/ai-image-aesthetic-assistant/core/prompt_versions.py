IMAGE_TYPES = ("photography", "ai_generated", "social_media")

TYPE_GUIDANCE = {
    "photography": "额外检查光线、曝光、拍摄时机和景深是否服务主体。",
    "ai_generated": "额外检查生成瑕疵、局部结构、材质一致性和不自然细节。",
    "social_media": "额外检查信息传达、文字可读性、缩略图识别度和视觉焦点。",
}

BASE_PROMPT = """你是面向普通图片创作者的审美评测助手。
从构图、色彩、主体、清晰度、视觉层次五个维度各给出 1-10 分。
指出最重要的 1-3 个具体问题，并按相同顺序给出普通用户可以直接执行的修改建议。
语言简洁，不使用空泛的专业术语。"""


def get_prompt(image_type, version="v1"):
    if image_type not in IMAGE_TYPES:
        raise ValueError("不支持的图片类型")
    if version != "v1":
        raise ValueError("不支持的提示词版本")
    return {
        "label": "三类图片专项审美评测",
        "prompt": f"{BASE_PROMPT}\n{TYPE_GUIDANCE[image_type]}",
    }
