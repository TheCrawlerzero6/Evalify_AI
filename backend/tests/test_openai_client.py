from __future__ import annotations

import app.integrations.openai_client as openai_client


class _DummyChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_build_llm_omits_temperature_for_o_series(monkeypatch):
    monkeypatch.setattr(openai_client, "OPENAI_MODEL", "o4-mini")
    monkeypatch.setattr(openai_client, "ChatOpenAI", _DummyChatOpenAI)

    client = openai_client.build_llm()

    assert client.kwargs["model"] == "o4-mini"
    assert "temperature" not in client.kwargs


def test_build_llm_sets_temperature_for_non_o_series(monkeypatch):
    monkeypatch.setattr(openai_client, "OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(openai_client, "ChatOpenAI", _DummyChatOpenAI)

    client = openai_client.build_llm()

    assert client.kwargs["model"] == "gpt-4o-mini"
    assert client.kwargs["temperature"] == 0


def test_build_llm_uses_override_model(monkeypatch):
    monkeypatch.setattr(openai_client, "OPENAI_MODEL", "o4-mini")
    monkeypatch.setattr(openai_client, "ChatOpenAI", _DummyChatOpenAI)

    client = openai_client.build_llm(model_name="gpt-4.1-mini")

    assert client.kwargs["model"] == "gpt-4.1-mini"
    assert client.kwargs["temperature"] == 0
