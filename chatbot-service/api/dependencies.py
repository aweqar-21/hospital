"""FastAPI 依赖注入 —— 获取当前用户/会话/核心组件。"""
import hmac
from functools import lru_cache

from fastapi import Header, HTTPException

from config.settings import get_settings
from core.context_builder import ContextBuilder
from core.conversation_manager import ConversationManager
from core.post_processor import PostProcessor
from core.responder import Responder
from knowledge.knowledge_retriever import KnowledgeRetriever
from nlu.entity_extractor import EntityExtractor
from nlu.intent_classifier import IntentClassifier
from policies.fallback_handler import FallbackHandler
from policies.router import Router


# ---- 单例 ----
@lru_cache
def get_conversation_manager() -> ConversationManager:
    return ConversationManager()


@lru_cache
def get_context_builder() -> ContextBuilder:
    return ContextBuilder()


@lru_cache
def get_responder() -> Responder:
    return Responder()


@lru_cache
def get_post_processor() -> PostProcessor:
    return PostProcessor()


@lru_cache
def get_intent_classifier() -> IntentClassifier:
    return IntentClassifier()


@lru_cache
def get_entity_extractor() -> EntityExtractor:
    return EntityExtractor()


@lru_cache
def get_knowledge_retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever()


@lru_cache
def get_router() -> Router:
    return Router()


@lru_cache
def get_fallback_handler() -> FallbackHandler:
    return FallbackHandler()


# ---- 请求级 ----
async def get_user_id(
    x_user_id: str | None = Header(None),
    authorization: str | None = Header(None),
    x_ai_proxy_secret: str | None = Header(None),
) -> str | None:
    """Only accept identity-bearing headers across the authenticated proxy boundary."""
    if x_user_id is None and authorization is None:
        return None

    expected = get_settings().AI_PROXY_SECRET
    supplied = x_ai_proxy_secret or ""
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="未授权的代理请求")
    return x_user_id


async def get_session_id(x_session_id: str | None = Header(None)) -> str | None:
    """从 Header 中提取会话 ID。"""
    return x_session_id
