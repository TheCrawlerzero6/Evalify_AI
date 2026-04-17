from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_MODEL


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(model=OPENAI_MODEL, temperature=0)
