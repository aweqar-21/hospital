"""知识检索器 —— 组合 Embedding + 向量检索，提供高层检索接口。"""
from typing import Optional

from config.settings import get_settings
from knowledge.embedding_client import EmbeddingClient
from knowledge.vector_store import Document, VectorStore


class KnowledgeRetriever:
    """RAG 检索流程编排。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.vector_store = VectorStore()
        self.embedding_client = EmbeddingClient()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> list[Document]:
        """检索与查询最相关的文档。"""
        # 1. 将查询转为向量
        query_embedding = await self.embedding_client.embed_query(query)

        # 2. 向量检索
        docs = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            threshold=threshold,
        )
        return docs

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
        max_chars: int = 2000,
    ) -> str:
        """检索并拼接为上下文字符串（可直接注入 prompt）。"""
        docs = await self.retrieve(query, top_k=top_k, threshold=threshold)
        parts: list[str] = []
        total = 0
        for doc in docs:
            chunk = doc.content[: max_chars - total]
            if not chunk:
                break
            parts.append(f"【来源：{doc.metadata.get('source', '未知')}】\n{chunk}")
            total += len(chunk)
            if total >= max_chars:
                break
        return "\n\n---\n\n".join(parts)

    async def add_knowledge(
        self, contents: list[str], metadatas: Optional[list[dict]] = None
    ) -> None:
        """向知识库添加文档。"""
        if metadatas is None:
            metadatas = [{} for _ in contents]

        # 生成 embeddings
        embeddings = await self.embedding_client.embed(contents)

        # 构建文档并写入向量库
        import uuid

        docs = [
            Document(
                id=uuid.uuid4().hex,
                content=content,
                metadata=meta,
                embedding=emb,
            )
            for content, meta, emb in zip(contents, metadatas, embeddings)
        ]
        self.vector_store.add_documents(docs)
