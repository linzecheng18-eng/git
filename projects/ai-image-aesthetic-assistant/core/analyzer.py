from core.image_utils import image_to_base64
from core.model_client import ModelClient, ModelResponseError
from core.prompt_versions import get_prompt
from core.rubric import validate_result


def normalize_model_payload(raw):
    return validate_result(raw)


def analyze_image_bytes(image_bytes, filename, image_type):
    prompt = get_prompt(image_type)["prompt"]
    image_b64 = image_to_base64(image_bytes)
    client = ModelClient()
    for attempt in range(2):
        try:
            raw = client.analyze(image_b64, filename, prompt)
            return normalize_model_payload(raw)
        except (ModelResponseError, ValueError):
            if attempt == 1:
                raise ModelResponseError("模型返回的评测结果无效") from None
