"""LM Studio adapter – uses the OpenAI-compatible /v1/chat/completions endpoint."""

import base64
import os
import requests

from config import Config
from src.llm.base import VisionAdapter, EXTRACTION_PROMPT


def _img_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}.get(ext, 'image/png')


class LMStudioAdapter(VisionAdapter):
    def __init__(self):
        self.base_url = Config.LMSTUDIO_BASE_URL.rstrip("/")
        self.model = Config.LMSTUDIO_MODEL

    def extract_transactions(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        mime = _img_mime(image_path)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{img_b64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 16384,
            "temperature": 0.1,
        }

        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if choices:
            return choices[0]["message"]["content"]
        return "[]"
