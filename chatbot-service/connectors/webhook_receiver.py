"""通用 Webhook 入口 —— 接收外部系统的消息推送。"""
from typing import Optional

from fastapi import FastAPI, Request

from connectors.base import AdapterMessage


class WebhookReceiver:
    """注册通用的 Webhook 路由，接收来自任意外部系统的消息。"""

    def __init__(self, app: FastAPI, path: str = "/webhook") -> None:
        self.app = app
        self.path = path
        self._handlers: dict[str, callable] = {}

        @app.post(path)
        async def webhook_handler(request: Request):
            return await self._handle(request)

    def register(self, channel: str, handler: callable) -> None:
        """注册某个渠道的处理器。"""
        self._handlers[channel] = handler

    async def _handle(self, request: Request) -> dict:
        """处理 Webhook 请求。"""
        channel = request.headers.get("X-Channel", "unknown")
        handler = self._handlers.get(channel)
        if handler is None:
            return {"error": f"未注册的渠道: {channel}"}

        body = await request.json()
        result = await handler(body)
        return {"status": "ok", "result": str(result)}
