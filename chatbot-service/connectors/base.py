"""外部适配器抽象基类。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class AdapterMessage:
    """适配器统一消息格式 —— 所有外部消息归一化为此结构。"""

    content: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    channel: str = "unknown"  # wechat / slack / webhook ...
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    extra: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """外部系统适配器抽象基类。

    子类需实现：
    - send_message: 发送回复到外部系统
    - parse_message: 将外部原始消息转为 AdapterMessage
    """

    channel_name: str = "base"

    @abstractmethod
    async def send_message(self, message: AdapterMessage, reply: str) -> bool:
        """发送回复到外部系统。"""
        ...

    @abstractmethod
    async def parse_message(self, raw: Any) -> AdapterMessage:
        """将外部系统原始消息解析为统一格式。"""
        ...

    async def on_message(self, raw: Any) -> Optional[str]:
        """完整处理一条外部消息：解析 → 获取回复 → 发回。
        返回助手的回复文本，失败则返回 None。
        """
        msg = await self.parse_message(raw)
        # 这里可以接核心对话引擎
        reply = f"[{self.channel_name}] 收到消息: {msg.content}"  # placeholder
        success = await self.send_message(msg, reply)
        return reply if success else None
