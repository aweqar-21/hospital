"""兜底策略处理器 —— 当意图识别置信度低或未知意图时使用。"""
from typing import Optional

from core.context_builder import ContextBuilder
from core.conversation_manager import Session
from core.responder import Responder


FALLBACK_PROMPT = """你是一个友好的助手。用户的问题意图不太明确，请礼貌地要求用户澄清，
同时尝试给出一个通用的有帮助的回答。"""


class FallbackHandler:
    """兜底处理：不确定时如何回复。"""

    def __init__(self) -> None:
        self.context_builder = ContextBuilder(system_prompt=FALLBACK_PROMPT)
        self.responder = Responder()

    async def handle(
        self,
        session: Session,
        user_input: str,
        *,
        reason: str = "低置信度意图",
    ) -> str:
        """生成兜底回复。"""
        messages = self.context_builder.build_messages(
            session,
            user_input,
            extra_context=f"注意：上一轮意图识别失败，原因：{reason}。请引导用户澄清意图。",
        )
        response = await self.responder.generate(messages, temperature=0.6)
        return response
