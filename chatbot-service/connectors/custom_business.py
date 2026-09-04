"""自定义业务系统适配器 —— 通过 HTTP 回调接入外部业务系统。"""
from typing import Any

import httpx

from connectors.base import AdapterMessage, BaseAdapter


class CustomBusinessAdapter(BaseAdapter):
    """通用 HTTP 回调适配器 —— 接收消息后回调业务系统获取上下文。"""

    channel_name = "custom_business"

    def __init__(self, callback_url: str = "", api_key: str = "") -> None:
        self.callback_url = callback_url
        self.api_key = api_key

    async def send_message(self, message: AdapterMessage, reply: str) -> bool:
        """向业务系统推送回复。"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.callback_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "user_id": message.user_id,
                    "reply": reply,
                    "original_message": message.content,
                },
                timeout=10,
            )
            return resp.status_code < 400

    async def parse_message(self, raw: Any) -> AdapterMessage:
        """解析业务系统推送的消息。"""
        if isinstance(raw, dict):
            return AdapterMessage(
                content=raw.get("message", raw.get("text", "")),
                user_id=raw.get("user_id"),
                session_id=raw.get("session_id"),
                channel=self.channel_name,
                extra=raw,
            )
        return AdapterMessage(content=str(raw), channel=self.channel_name)
