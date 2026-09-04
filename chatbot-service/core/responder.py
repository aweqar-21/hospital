"""最终响应生成器 —— 调用 LLM 获取回复。"""
from typing import AsyncGenerator, Optional

from config.settings import get_settings


class LLMError(Exception):
    """LLM 调用异常。"""
    pass


class Responder:
    """封装模型调用，支持流式与非流式输出。"""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_client(self) -> object:
        import openai

        return openai.AsyncOpenAI(
            api_key=self.settings.LLM_API_KEY,
            base_url=self.settings.LLM_BASE_URL,
            timeout=30.0,
            max_retries=1,
        )

    def _check_api_key(self) -> None:
        if not self.settings.LLM_API_KEY or self.settings.LLM_API_KEY == "sk-your-api-key-here":
            raise LLMError("LLM_API_KEY 未配置，请在 .env 文件中填入有效的 API Key")

    async def generate(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """非流式生成回复。"""
        self._check_api_key()

        try:
            client = self._build_client()
            response = await client.chat.completions.create(
                model=model or self.settings.LLM_MODEL,
                messages=messages,
                temperature=temperature or self.settings.LLM_TEMPERATURE,
                max_tokens=max_tokens or self.settings.LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"LLM 调用失败: {e}") from e

    async def generate_stream(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成回复，逐 token yield。"""
        self._check_api_key()

        try:
            client = self._build_client()
            stream = await client.chat.completions.create(
                model=model or self.settings.LLM_MODEL,
                messages=messages,
                temperature=temperature or self.settings.LLM_TEMPERATURE,
                max_tokens=max_tokens or self.settings.LLM_MAX_TOKENS,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            raise LLMError(f"LLM 流式调用失败: {e}") from e
