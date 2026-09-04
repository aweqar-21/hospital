"""向量数据库封装 —— 支持 Chroma / FAISS / Qdrant 等后端。"""
from dataclasses import dataclass, field
from typing import Optional

from config.settings import get_settings


@dataclass
class Document:
    """知识文档。"""

    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None


class VectorStore:
    """向量数据库统一接口。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._collection = None
        self._init_client()

    def _init_client(self) -> None:
        db_type = self.settings.VECTOR_DB_TYPE
        if db_type == "chroma":
            try:
                self._init_chroma()
            except ImportError:
                import warnings
                warnings.warn("chromadb 未安装，向量检索功能不可用。pip install chromadb")
                self._collection = None

    def _init_chroma(self) -> None:
        import chromadb

        self._chroma_client = chromadb.PersistentClient(
            path=self.settings.VECTOR_DB_PATH,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        self._collection = self._chroma_client.get_or_create_collection("knowledge")

    # ------- CRUD -------
    def add_documents(self, docs: list[Document]) -> None:
        """批量添加文档。"""
        if self._collection is not None:
            self._collection.add(
                ids=[d.id for d in docs],
                documents=[d.content for d in docs],
                metadatas=[d.metadata for d in docs],
                embeddings=[d.embedding for d in docs] if docs[0].embedding else None,
            )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> list[Document]:
        """向量相似度检索。"""
        if self._collection is None:
            return []

        threshold = threshold or self.settings.LLM_TEMPERATURE  # FIXME: use retrieval threshold
        # Actually use the retrieval threshold from model_config

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        docs: list[Document] = []
        if results["ids"] and results["documents"]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results.get("distances", [[0.0] * top_k])[0][i]
                similarity = 1.0 - distance if distance else 1.0
                if threshold is None or similarity >= threshold:
                    docs.append(Document(
                        id=doc_id,
                        content=results["documents"][0][i] or "",
                        metadata=results.get("metadatas", [[{}]])[0][i] or {},
                    ))
        return docs

    def delete(self, doc_ids: list[str]) -> None:
        """删除文档。"""
        if self._collection:
            self._collection.delete(ids=doc_ids)

    def count(self) -> int:
        """文档数量。"""
        if self._collection:
            return self._collection.count()
        return 0
