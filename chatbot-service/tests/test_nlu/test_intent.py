"""意图分类器单元测试。"""
import pytest
from nlu.intent_classifier import IntentClassifier


class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_greet_intent(self):
        result = self.classifier.classify_by_rule("你好")
        assert result is not None
        assert result.intent == "greet"
        assert result.confidence >= 0.8

    def test_farewell_intent(self):
        result = self.classifier.classify_by_rule("再见")
        assert result is not None
        assert result.intent == "farewell"

    def test_unknown_intent(self):
        result = self.classifier.classify_by_rule("今天天气真不错啊")
        assert result is None or result.confidence < 0.8


def test_default_intents_are_loaded_independently_of_working_directory(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    result = IntentClassifier().classify_by_rule("你好")

    assert result is not None
    assert result.intent == "greet"
