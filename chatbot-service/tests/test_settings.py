from pathlib import Path

import yaml

from config.settings import Settings


def test_default_llm_model_is_current_deepseek_model(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.LLM_PROVIDER == "deepseek"
    assert settings.LLM_MODEL == "deepseek-v4-flash"
    assert settings.LLM_BASE_URL == "https://api.deepseek.com/v1"


def test_model_config_matches_the_unified_deepseek_chat_defaults():
    config_path = Path(__file__).resolve().parents[1] / "config" / "model_config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    for name in ("default", "fast", "reasoning"):
        assert config["models"][name]["provider"] == "deepseek"
        assert config["models"][name]["model_name"] == "deepseek-v4-flash"
    assert config["intent"]["provider"] == "deepseek"
    assert config["intent"]["model_name"] == "deepseek-v4-flash"
    assert config["embedding"]["provider"] == "openai"


def test_shared_root_env_ignores_non_chatbot_settings(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_API_KEY=test-deepseek-key\n"
        "MYSQL_DATABASE=hospital\n"
        "JWT_SECRET=test-jwt-secret\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.LLM_API_KEY == "test-deepseek-key"
