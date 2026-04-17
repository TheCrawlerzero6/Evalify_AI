from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

APP_TITLE = "Evalify AI API"
APP_VERSION = "0.2.0"
APP_DESCRIPTION = "API local para comparar proveedores con LangGraph + OpenAI + Tavily."

CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "comparaciones.db")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "o4-mini")
OPENAI_EXTRACTION_MODEL = os.getenv("OPENAI_EXTRACTION_MODEL", "gpt-4.1-mini")
TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
CORS_ALLOW_ORIGINS = [
	origin.strip()
	for origin in os.getenv(
		"CORS_ALLOW_ORIGINS",
		"http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173",
	).split(",")
	if origin.strip()
]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s | %(levelname)s | %(name)s | %(message)s")
