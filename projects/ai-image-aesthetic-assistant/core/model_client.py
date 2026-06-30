import json
import os
from urllib import request


class ModelClient:
    def __init__(self):
        self.mode = os.getenv("AI_IMAGE_EVAL_MODE", "mock")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("AI_IMAGE_EVAL_MODEL", "gpt-4.1-mini")

    def analyze(self, image_b64, filename, prompt_text):
        if self.mode == "mock":
            return {
                "scores": {"构图": 7, "色彩": 8, "主体": 7, "清晰度": 7, "视觉层次": 6},
                "issues": ["视觉层次略弱"],
                "suggestions": ["增加主体与背景的亮度对比"],
                "summary": f"{filename} 整体协调，但层次表现还有提升空间。",
            }

        body = json.dumps(
            {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt_text},
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image_b64}"},
                        ],
                    }
                ],
            }
        ).encode("utf-8")
        req = request.Request(
            url="https://api.openai.com/v1/responses",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["output"][0]["content"][0]["text"]
        return json.loads(text)

