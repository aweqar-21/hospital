"""嵌入模型客户端 —— 统一不同 Embedding 提供商的调用接口。"""
from typing import Optional

from config.settings import get_settings


class EmbeddingClient:
    """嵌入模型客户端封装。"""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转为向量列表。"""
        provider = self.settings.EMBEDDING_PROVIDER

        if provider == "openai":
            return await self._embed_openai(texts)
        elif provider == "local":
            return await self._embed_local(texts)
        else:
            raise ValueError(f"不支持的 Embedding 提供商: {provider}")

    async def embed_query(self, text: str) -> list[float]:
        """将单条查询文本转为向量。"""
        results = await self.embed([text])
        return results[0]

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        import openai

        client = openai.AsyncOpenAI(
            api_key=self.settings.EMBEDDING_API_KEY,
            base_url=self.settings.EMBEDDING_BASE_URL,
        )

        response = await client.embeddings.create(
            model=self.settings.EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """本地嵌入模型（如通过 Ollama 或自部署服务调用）。"""
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.settings.EMBEDDING_BASE_URL}/embeddings",
                json={"texts": texts},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]
