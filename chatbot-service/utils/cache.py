"""缓存封装 —— 支持 Redis 和本地内存两种后端。"""
import time
from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackend(ABC):
    """缓存后端抽象基类。"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...


class LocalCache(CacheBackend):
    """本地内存缓存（进程内，适合开发环境或小规模使用）。"""

    def __init__(self, max_size: int = 1000) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self.max_size = max_size

    async def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if expire_at > 0 and time.time() > expire_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        # 超出容量时删除最旧的键
        if len(self._store) >= self.max_size:
            oldest = min(self._store.keys(), key=lambda k: self._store[k][1])
            del self._store[oldest]
        expire_at = time.time() + ttl if ttl > 0 else 0
        self._store[key] = (value, expire_at)

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None


class RedisCache(CacheBackend):
    """Redis 缓存（适合生产环境）。"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: str = "") -> None:
        import redis.asyncio as redis

        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password or None,
            decode_responses=True,
        )

    async def get(self, key: str) -> Optional[Any]:
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self._client.setex(key, ttl, value)

    async def delete(self, key: str) -> bool:
        return await self._client.delete(key) > 0

    async def exists(self, key: str) -> bool:
        return await self._client.exists(key) > 0
