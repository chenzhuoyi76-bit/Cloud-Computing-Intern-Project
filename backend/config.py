import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))
    TASK_WORKSPACE_ROOT = os.getenv(
        "TASK_WORKSPACE_ROOT",
        str(BASE_DIR / "runtime" / "workspaces"),
    ).strip()
