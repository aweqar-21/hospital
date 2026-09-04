"""REST API 路由定义。"""
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from api.dependencies import (
    get_context_builder,
    get_conversation_manager,
    get_intent_classifier,
    get_knowledge_retriever,
    get_post_processor,
    get_responder,
    get_router,
    get_user_id,
)
from api.schemas import ChatRequest, ChatResponse, HealthResponse, ServiceUnavailableResponse
from config.settings import get_settings
from core.conversation_manager import Session, SessionCapacityError
from core.medical_safety import emergency_reply, is_emergency
from core.post_processor import PostProcessor
from core.responder import LLMError
from policies.router import FlowType

app = FastAPI(
    title="Chatbot API",
    description="模块化智能对话机器人 API",
    version="0.1.0",
)

# 静态文件目录
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _require_session_owner(session: Session | None, user_id: str | None) -> Session:
    """Return a session only when its trusted owner matches the caller.

    Anonymous sessions deliberately remain capability-based: their random session id is
    the capability, and a body-supplied user_id can never claim or change ownership.
    """
    if session is None or (session.user_id is not None and session.user_id != user_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


def _persist_turn(conv_mgr, session: Session, message: str, reply: str):
    """Persist a complete turn without changing the previously claimed owner."""
    conv_mgr.commit_turn(session, message, reply)


@app.exception_handler(SessionCapacityError)
async def session_capacity_error_handler(_request, _exception):
    return JSONResponse(
        status_code=429,
        content={"detail": "会话容量已满，请稍后重试"},
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    """聊天页面。"""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Chatbot API 已就绪</h1><p>访问 <a href='/docs'>/docs</a> 查看 API 文档</p>")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查。"""
    return HealthResponse()


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        429: {"model": ServiceUnavailableResponse, "description": "活动会话容量已满"},
        503: {"model": ServiceUnavailableResponse, "description": "AI 服务暂时不可用"},
    },
)
async def chat(
    req: ChatRequest,
    user_id: str | None = Depends(get_user_id),
):
    """非流式对话接口。"""
    conv_mgr = get_conversation_manager()
    session_id = req.session_id or uuid.uuid4().hex
    async with conv_mgr.session_scope(session_id, user_id, create=True) as lease:
        session = _require_session_owner(lease.session, user_id)

        # 紧急情况必须在任何 AI 服务之前直接分流。
        if is_emergency(req.message):
            reply = emergency_reply()
            _persist_turn(conv_mgr, session, req.message, reply)
            return ChatResponse(
                session_id=session_id,
                reply=reply,
                intent="medical_emergency",
                confidence=1.0,
            )

        # The lock deliberately covers history read, all awaited AI work, and commit.
        context_builder = get_context_builder()
        intent_classifier = get_intent_classifier()
        router = get_router()
        responder = get_responder()
        post_processor = get_post_processor()
        intent_result = await intent_classifier.classify(req.message)
        route = router.route(intent_result)

        try:
            if route.flow == FlowType.KNOWLEDGE_QA and get_settings().ENABLE_RAG:
                knowledge_retriever = get_knowledge_retriever()
                extra_context = await knowledge_retriever.retrieve_context(req.message)
                messages = context_builder.build_messages(
                    session, req.message, extra_context=extra_context
                )
            else:
                messages = context_builder.build_messages(session, req.message)
            reply = await responder.generate(messages)
        except LLMError:
            raise HTTPException(
                status_code=503,
                detail="AI 问诊服务暂时不可用，请稍后重试",
            ) from None

        reply = post_processor.process(reply)
        if not PostProcessor.validate(reply):
            raise HTTPException(
                status_code=503,
                detail="AI 问诊服务暂时不可用，请稍后重试",
            )
        _persist_turn(conv_mgr, session, req.message, reply)

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )


@app.post(
    "/chat/stream",
    response_class=Response,
    responses={
        200: {
            "description": "Plain-text AI response",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        },
        429: {
            "model": ServiceUnavailableResponse,
            "description": "活动会话容量已满",
        },
        503: {
            "model": ServiceUnavailableResponse,
            "description": "AI 服务暂时不可用",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ServiceUnavailableResponse"}
                }
            },
        }
    },
)
async def chat_stream(
    req: ChatRequest,
    user_id: str | None = Depends(get_user_id),
):
    """流式对话接口。"""
    conv_mgr = get_conversation_manager()
    session_id = req.session_id or uuid.uuid4().hex
    async with conv_mgr.session_scope(session_id, user_id, create=True) as lease:
        session = _require_session_owner(lease.session, user_id)
        context_builder = get_context_builder()
        responder = get_responder()
        post_processor = get_post_processor()

        if is_emergency(req.message):
            final = post_processor.process(emergency_reply())
        else:
            messages = context_builder.build_messages(session, req.message)
            try:
                # Intentionally buffer the bounded response so failures remain an
                # atomic 503 and never commit a partial conversation turn.
                tokens = [token async for token in responder.generate_stream(messages)]
            except LLMError:
                raise HTTPException(
                    status_code=503,
                    detail="AI 问诊服务暂时不可用，请稍后重试",
                ) from None
            final = post_processor.process("".join(tokens))

        if not PostProcessor.validate(final):
            raise HTTPException(
                status_code=503,
                detail="AI 问诊服务暂时不可用，请稍后重试",
            )
        _persist_turn(conv_mgr, session, req.message, final)

    async def generate():
        yield final

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.delete("/session/{session_id}")
async def delete_session(session_id: str, user_id: str | None = Depends(get_user_id)):
    """删除会话。"""
    conv_mgr = get_conversation_manager()
    async with conv_mgr.session_scope(session_id, user_id, create=False) as lease:
        _require_session_owner(lease.session, user_id)
        if conv_mgr.delete_session(session_id):
            return {"status": "deleted", "session_id": session_id}
        raise HTTPException(status_code=404, detail="会话不存在")


@app.get("/session/{session_id}/history")
async def get_history(session_id: str, user_id: str | None = Depends(get_user_id)):
    """获取会话历史。"""
    conv_mgr = get_conversation_manager()
    async with conv_mgr.session_scope(session_id, user_id, create=False) as lease:
        session = _require_session_owner(lease.session, user_id)
        return {
            "session_id": session_id,
            "turn_count": session.turn_count,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in session.messages
            ],
        }
