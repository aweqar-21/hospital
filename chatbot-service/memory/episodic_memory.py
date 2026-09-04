"""情景记忆 —— 记录和检索用户与助手之间的重要交互事件。"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Episode:
    """一条情景记忆。"""

    user_id: str
    content: str  # 记忆摘要
    importance: float = 0.5  # 重要性评分 0-1
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    episode_id: str = ""

    def __post_init__(self) -> None:
        if not self.episode_id:
            import uuid
            self.episode_id = uuid.uuid4().hex[:12]


class EpisodicMemory:
    """情景记忆存储与检索。"""

    def __init__(self, max_episodes_per_user: int = 100) -> None:
        self.max_episodes = max_episodes_per_user
        self._store: dict[str, list[Episode]] = {}  # user_id -> episodes

    def add(self, episode: Episode) -> None:
        """添加一条情景记忆。"""
        if episode.user_id not in self._store:
            self._store[episode.user_id] = []
        self._store[episode.user_id].append(episode)

        # 按重要性排序，保留 top-N
        self._store[episode.user_id].sort(key=lambda e: e.importance, reverse=True)
        if len(self._store[episode.user_id]) > self.max_episodes:
            self._store[episode.user_id] = self._store[episode.user_id][: self.max_episodes]

    def recall(
        self,
        user_id: str,
        top_k: int = 5,
        min_importance: float = 0.3,
        tags: Optional[list[str]] = None,
    ) -> list[Episode]:
        """检索用户的情景记忆。"""
        episodes = self._store.get(user_id, [])

        # 过滤重要性
        results = [e for e in episodes if e.importance >= min_importance]

        # 按标签过滤
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]

        return results[:top_k]

    def recall_recent(self, user_id: str, n: int = 5) -> list[Episode]:
        """获取最近的 N 条记忆。"""
        episodes = self._store.get(user_id, [])
        sorted_by_time = sorted(episodes, key=lambda e: e.timestamp, reverse=True)
        return sorted_by_time[:n]

    def format_context(self, episodes: list[Episode]) -> str:
        """将情景记忆格式化为上下文字符串。"""
        if not episodes:
            return ""
        lines = ["## 相关历史事件"]
        for ep in episodes:
            lines.append(f"- [{ep.timestamp}] {ep.content}（重要性：{ep.importance:.0%}）")
        return "\n".join(lines)
