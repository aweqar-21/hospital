"""Slack 适配器。"""
from typing import Any

import httpx

from connectors.base import AdapterMessage, BaseAdapter


class SlackAdapter(BaseAdapter):
    """接入 Slack 消息。"""

    channel_name = "slack"

    def __init__(self, bot_token: str = "", signing_secret: str = "") -> None:
        self.bot_token = bot_token
        self.signing_secret = signing_secret

    async def send_message(self, message: AdapterMessage, reply: str) -> bool:
        """通过 Slack Web API 发送回复。"""
        channel = message.extra.get("channel", "")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json={"channel": channel, "text": reply},
            )
            return resp.json().get("ok", False)

    async def parse_message(self, raw: Any) -> AdapterMessage:
        """解析 Slack 事件回调。"""
        if isinstance(raw, dict):
            event = raw.get("event", raw)
            return AdapterMessage(
                content=event.get("text", ""),
                user_id=event.get("user", ""),
                channel=self.channel_name,
                extra={"channel": event.get("channel", ""), "ts": event.get("ts", "")},
            )
        return AdapterMessage(content=str(raw), channel=self.channel_name)
