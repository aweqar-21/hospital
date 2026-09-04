"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """聊天请求。"""

    session_id: str | None = Field(default=None, description="会话 ID，不传则创建新会话")
    user_id: str | None = Field(default=None, description="用户标识")
    message: str = Field(..., min_length=1, max_length=4096, description="用户消息")
    stream: bool = Field(default=False, description="是否流式返回")

    @field_validator("message")
    @classmethod
    def strip_and_require_message(cls, value: str) -> str:
        """去除首尾空白，并拒绝只包含空白的消息。"""
        value = value.strip()
        if not value:
            raise ValueError("用户消息不能为空")
        return value


class ChatResponse(BaseModel):
    """聊天响应（非流式）。"""

    session_id: str
    reply: str
    intent: str | None = None
    confidence: float | None = None


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = "ok"
    version: str = "0.1.0"


class ServiceUnavailableResponse(BaseModel):
    """AI 服务不可用时的标准错误响应。"""

    detail: str
