"""上下文构建器 —— 拼接历史消息、系统提示、用户画像等信息，生成模型输入。"""
from typing import Optional

from config.settings import get_settings
from core.conversation_manager import Session


SYSTEM_PROMPT = """你是医疗咨询助手，使用中文提供谨慎、清晰且有帮助的信息。
遵循以下原则：
1. 你的回答不能替代医生的面对面诊断、检查或治疗；不得作出确定性诊断或开具处方。
2. 回答应简洁概括用户描述的情况，说明可能的原因（使用不确定性表达），并给出建议科室。
3. 明确说明就医紧急程度，并提供可执行的下一步建议，例如观察重点、预约就诊或携带既往资料。
4. 如出现胸痛、呼吸困难、意识不清、大出血、抽搐、服毒、自杀或自伤等紧急信号，立即建议联系当地急救服务或前往急诊；提醒不要等待症状缓解、不要自行驾车，并请身边的人协助。
5. 如信息不足，先询问必要的症状、持续时间、严重程度和既往病史；对知识盲区诚实说明。"""


class ContextBuilder:
    """将对话状态构建为模型可用的上下文。"""

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self.settings = get_settings()
        self.system_prompt = system_prompt or SYSTEM_PROMPT

    def build_messages(
        self,
        session: Session,
        user_input: str,
        *,
        extra_context: Optional[str] = None,
        user_profile: Optional[dict] = None,
    ) -> list[dict]:
        """构建发送给 LLM 的消息列表。"""
        messages: list[dict] = []

        # 1. 系统消息
        system_content = self.system_prompt
        if user_profile:
            profile_text = self._format_profile(user_profile)
            system_content += f"\n\n## 当前用户信息\n{profile_text}"
        if extra_context:
            system_content += f"\n\n## 参考知识\n{extra_context}"
        messages.append({"role": "system", "content": system_content})

        # 2. 历史消息（截取最近 N 轮）
        max_history = self.settings.MAX_HISTORY_TURNS * 2  # user + assistant
        recent = session.recent_messages(max_history)
        for msg in recent:
            messages.append({"role": msg.role, "content": msg.content})

        # 3. 当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def build_prompt_text(self, messages: list[dict]) -> str:
        """将消息列表转成纯文本 prompt（兼容不支持 chat 格式的模型）。"""
        parts: list[str] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"<|system|>\n{content}\n")
            elif role == "user":
                parts.append(f"<|user|>\n{content}\n")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{content}\n")
        parts.append("<|assistant|>\n")
        return "\n".join(parts)

    @staticmethod
    def _format_profile(profile: dict) -> str:
        lines = [f"- {k}: {v}" for k, v in profile.items()]
        return "\n".join(lines)
