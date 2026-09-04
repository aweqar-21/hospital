"""用户画像管理 —— 存储和更新用户的长期偏好与属性。"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserProfile:
    """用户画像。"""

    user_id: str
    name: Optional[str] = None
    preferences: dict = field(default_factory=dict)  # 偏好设置
    interests: list[str] = field(default_factory=list)  # 兴趣标签
    history_topics: list[str] = field(default_factory=list)  # 历史话题
    metadata: dict = field(default_factory=dict)  # 扩展字段
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_interest(self, topic: str) -> None:
        """记录用户感兴趣的话题。"""
        if topic not in self.interests:
            self.interests.append(topic)
        if len(self.interests) > 50:
            self.interests = self.interests[-50:]
        self._touch()

    def add_history_topic(self, topic: str) -> None:
        """记录历史对话话题。"""
        self.history_topics.append(topic)
        if len(self.history_topics) > 100:
            self.history_topics = self.history_topics[-100:]
        self._touch()

    def set_preference(self, key: str, value: object) -> None:
        """设置偏好项。"""
        self.preferences[key] = value
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now().isoformat()


class UserProfileManager:
    """用户画像持久化管理。"""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def get(self, user_id: str) -> UserProfile:
        """获取用户画像，不存在则创建。"""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    def update(self, profile: UserProfile) -> None:
        """更新用户画像。"""
        self._profiles[profile.user_id] = profile

    def delete(self, user_id: str) -> bool:
        """删除用户画像。"""
        if user_id in self._profiles:
            del self._profiles[user_id]
            return True
        return False

    def list_all(self) -> list[UserProfile]:
        """列出所有用户画像。"""
        return list(self._profiles.values())
