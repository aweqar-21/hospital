"""全局配置管理 —— 读取环境变量，支持多环境切换。"""
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置，所有字段可从环境变量 / .env 文件中读取。"""

    # ---- 运行环境 ----
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # ---- LLM ----
    LLM_PROVIDER: str = "deepseek"
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048

    # ---- Embedding ----
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"

    # ---- 向量数据库 ----
    VECTOR_DB_TYPE: str = "chroma"
    VECTOR_DB_PATH: str = "./data/vector_store"
    VECTOR_DB_HOST: str = "127.0.0.1"
    VECTOR_DB_PORT: int = 8000
    ENABLE_RAG: bool = False

    # ---- Redis ----
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # ---- 数据库 ----
    DATABASE_URL: str = "sqlite:///./data/chatbot.db"

    # ---- API ----
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # ---- 安全 ----
    SENSITIVE_WORDS_FILE: str | None = None
    REQUEST_TIMEOUT: int = 30
    AI_PROXY_SECRET: str = ""

    # ---- 对话 ----
    MAX_HISTORY_TURNS: int = Field(default=20, ge=1)
    SESSION_TTL_SECONDS: int = Field(default=3600, ge=1)
    MAX_ACTIVE_SESSIONS: int = Field(default=10_000, ge=1)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """获取全局配置（每次调用重新读取 .env，确保配置变更即时生效）。"""
    return Settings()
