"""动作映射器 —— 将意图映射到具体动作（API 调用、数据库查询等）。"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class ActionType(str, Enum):
    GREET = "greet"
    SEARCH_KNOWLEDGE = "search_knowledge"
    QUERY_DATABASE = "query_database"
    CALL_API = "call_api"
    NONE = "none"


@dataclass
class Action:
    """一个具体动作。"""

    type: ActionType
    params: dict = None  # type: ignore

    def __post_init__(self) -> None:
        if self.params is None:
            self.params = {}


ActionHandler = Callable[[Action], Awaitable[Any]]


class ActionMapper:
    """管理意图 → 动作的映射与执行。"""

    def __init__(self) -> None:
        self._intent_actions: dict[str, Action] = {
            "greet": Action(type=ActionType.GREET),
            "knowledge_qa": Action(type=ActionType.SEARCH_KNOWLEDGE),
            "task_query": Action(type=ActionType.CALL_API),
        }
        self._handlers: dict[ActionType, ActionHandler] = {}

    def register_handler(self, action_type: ActionType, handler: ActionHandler) -> None:
        """注册动作处理器。"""
        self._handlers[action_type] = handler

    def map_intent(self, intent_name: str) -> Optional[Action]:
        """将意图名映射为动作。"""
        return self._intent_actions.get(intent_name)

    async def execute(self, action: Action) -> Any:
        """执行动作并返回结果。"""
        handler = self._handlers.get(action.type)
        if handler is None:
            return None
        return await handler(action)
