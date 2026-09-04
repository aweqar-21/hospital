"""对话路由器 —— 根据意图/场景选择处理流程。"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from nlu.intent_classifier import IntentResult


class FlowType(str, Enum):
    CHITCHAT = "chitchat"          # 闲聊
    KNOWLEDGE_QA = "knowledge_qa"  # 知识问答（走 RAG）
    TASK = "task"                   # 任务型（调 API / 查 DB）
    FALLBACK = "fallback"          # 兜底


@dataclass
class RouteDecision:
    flow: FlowType
    intent: IntentResult
    extra: dict = field(default_factory=dict)


# 意图 → 流程 映射表
INTENT_FLOW_MAP: dict[str, FlowType] = {
    "greet": FlowType.CHITCHAT,
    "farewell": FlowType.CHITCHAT,
    "ask_capability": FlowType.CHITCHAT,
    "chitchat": FlowType.CHITCHAT,
    "knowledge_qa": FlowType.KNOWLEDGE_QA,
    "task_query": FlowType.TASK,
}


class Router:
    """根据意图分类结果决定处理流程。"""

    def __init__(self) -> None:
        self._flow_map = dict(INTENT_FLOW_MAP)

    def route(self, intent_result: IntentResult) -> RouteDecision:
        """根据意图结果做出路由决策。"""
        flow = self._flow_map.get(intent_result.intent, FlowType.FALLBACK)

        # 低置信度时降级为兜底流程
        if intent_result.confidence < 0.5:
            flow = FlowType.FALLBACK

        return RouteDecision(flow=flow, intent=intent_result)

    def register_intent_flow(self, intent_name: str, flow: FlowType) -> None:
        """动态注册意图 → 流程映射。"""
        self._flow_map[intent_name] = flow
