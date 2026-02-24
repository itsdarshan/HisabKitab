"""Return the configured vision adapter instance."""

from config import Config
from src.llm.base import VisionAdapter
from src.llm.ollama_adapter import OllamaAdapter
from src.llm.lmstudio_adapter import LMStudioAdapter


def get_adapter() -> VisionAdapter:
    backend = Config.LLM_BACKEND.lower()
    if backend == "lmstudio":
        return LMStudioAdapter()
    return OllamaAdapter()          # default
