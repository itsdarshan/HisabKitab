"""Ollama vision adapter – uses /api/generate with image support."""

import base64
import os
import requests

from config import Config
from src.llm.base import VisionAdapter, EXTRACTION_PROMPT


class OllamaAdapter(VisionAdapter):
    def __init__(self):
        self.base_url = Config.OLLAMA_BASE_URL.rstrip("/")
        self.model = Config.OLLAMA_MODEL

    def extract_transactions(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": self.model,
            "prompt": EXTRACTION_PROMPT,
            "images": [img_b64],
            "stream": False,
        }

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
