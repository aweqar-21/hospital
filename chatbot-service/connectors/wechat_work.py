"""企业微信适配器。"""
from typing import Any

import httpx

from connectors.base import AdapterMessage, BaseAdapter


class WechatWorkAdapter(BaseAdapter):
    """接入企业微信消息推送。"""

    channel_name = "wechat_work"

    def __init__(
        self,
        corp_id: str = "",
        corp_secret: str = "",
        agent_id: str = "",
        token: str = "",
        encoding_aes_key: str = "",
    ) -> None:
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.token = token
        self.encoding_aes_key = encoding_aes_key
        self._access_token: str = ""

    async def get_access_token(self) -> str:
        """获取企业微信 access_token。"""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={
                    "corpid": self.corp_id,
                    "corpsecret": self.corp_secret,
                },
            )
            data = resp.json()
            self._access_token = data.get("access_token", "")
            return self._access_token

    async def send_message(self, message: AdapterMessage, reply: str) -> bool:
        """通过企业微信发送回复。"""
        token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}",
                json={
                    "touser": message.user_id,
                    "msgtype": "text",
                    "agentid": self.agent_id,
                    "text": {"content": reply},
                },
            )
            return resp.json().get("errcode") == 0

    async def parse_message(self, raw: Any) -> AdapterMessage:
        """解析企业微信回调消息。"""
        # raw 为企微 XML 消息体（需 xmltodict 解析）
        if isinstance(raw, dict):
            return AdapterMessage(
                content=raw.get("Content", raw.get("text", {}).get("content", "")),
                user_id=raw.get("FromUserName", raw.get("user_id", "")),
                channel=self.channel_name,
                extra=raw,
            )
        return AdapterMessage(content=str(raw), channel=self.channel_name)
