from core.image_utils import image_to_base64
from core.model_client import ModelClient
from core.prompt_versions import get_prompt
from core.rubric import validate_result


def normalize_model_payload(raw):
    return validate_result(raw)


def analyze_image_bytes(image_bytes, filename):
    prompt = get_prompt("v1")["prompt"]
    image_b64 = image_to_base64(image_bytes)
    raw = ModelClient().analyze(image_b64, filename, prompt)
    return normalize_model_payload(raw)

