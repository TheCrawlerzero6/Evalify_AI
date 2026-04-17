from __future__ import annotations

import os

APP_TITLE = "Evalify AI API"
APP_VERSION = "0.2.0"
APP_DESCRIPTION = "API local para comparar proveedores con LangGraph + OpenAI + Tavily."

CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "comparaciones.db")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "o4-mini")
TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
