from types import SimpleNamespace

import openai
import pytest

from config.settings import get_settings
from nlu.entity_extractor import EntityExtractor
from nlu.intent_classifier import IntentClassifier
from nlu.sentiment_analyzer import SentimentAnalyzer


@pytest.mark.asyncio
async def test_nlu_calls_use_the_unified_deepseek_configuration(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-flash")
    client_arguments = []
    completion_arguments = []
    responses = iter(
        [
            '{"intent":"chitchat","confidence":0.9}',
            '[]',
            '{"label":"neutral","score":0.5}',
        ]
    )

    class FakeCompletions:
        async def create(self, **kwargs):
            completion_arguments.append(kwargs)
            message = SimpleNamespace(content=next(responses))
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            client_arguments.append(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    await IntentClassifier().classify_by_llm("需要分诊")
    await EntityExtractor().extract_by_llm("明天去医院")
    await SentimentAnalyzer().analyze_by_llm("有点担心")

    settings = get_settings()
    assert settings.LLM_PROVIDER == "deepseek"
    assert len(client_arguments) == 3
    assert all(call["api_key"] == settings.LLM_API_KEY for call in client_arguments)
    assert all(call["base_url"] == settings.LLM_BASE_URL for call in client_arguments)
    assert [call["model"] for call in completion_arguments] == [settings.LLM_MODEL] * 3
