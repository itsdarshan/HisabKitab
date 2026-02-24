import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "hisabkitab.db")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    CONVERTED_IMAGES_FOLDER = os.getenv("CONVERTED_IMAGES_FOLDER", "converted_images")

    # LLM backend
    LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")  # "ollama" or "lmstudio"

    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")

    # LM Studio
    LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")
    LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")

    # Worker
    WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "2"))

    # JWT
    JWT_EXPIRY_HOURS = 24
