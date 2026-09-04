"""API 集成测试。"""
import asyncio
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from api import dependencies, routes
from api.routes import app
from core.context_builder import SYSTEM_PROMPT
from core.conversation_manager import ConversationManager
from core.responder import LLMError
from nlu.intent_classifier import IntentResult
from policies.router import FlowType, RouteDecision

PROXY_SECRET = "test-proxy-secret"


def trusted_headers(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id, "X-AI-Proxy-Secret": PROXY_SECRET}


@pytest.fixture
async def client():
    """创建异步测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class FakeResponder:
    """无网络的响应生成器，并记录路由是否调用了 LLM。"""

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []
        self.error: LLMError | None = None
        self.reply = "离线测试回复"
        self.stream_tokens = ["离线", "测试回复"]
        self.stream_error_after_tokens: LLMError | None = None

    async def generate(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        if self.error:
            raise self.error
        return self.reply

    async def generate_stream(self, messages: list[dict]):
        self.calls.append(messages)
        if self.error:
            raise self.error
        for token in self.stream_tokens:
            yield token
        if self.stream_error_after_tokens:
            raise self.stream_error_after_tokens


class YieldingResponder(FakeResponder):
    """Forces concurrent requests to interleave after ownership must be claimed."""

    async def generate(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        await asyncio.sleep(0)
        return "离线测试回复"


class OrderedResponder(FakeResponder):
    """Hold the first call so a second request can contend for the same session."""

    def __init__(self) -> None:
        super().__init__()
        self.first_started = asyncio.Event()
        self.release_first = asyncio.Event()

    async def generate(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        call_number = len(self.calls)
        if call_number == 1:
            self.first_started.set()
            await self.release_first.wait()
        return f"reply-{call_number}"


class ParallelResponder(FakeResponder):
    """Release only after two different sessions reach model work concurrently."""

    def __init__(self) -> None:
        super().__init__()
        self.both_started = asyncio.Event()

    async def generate(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        if len(self.calls) == 2:
            self.both_started.set()
        await asyncio.wait_for(self.both_started.wait(), timeout=1)
        return "parallel"


class FakeIntentClassifier:
    def __init__(self) -> None:
        self.result = IntentResult(intent="chitchat", confidence=0.9)
        self.calls: list[str] = []

    async def classify(self, message: str) -> IntentResult:
        self.calls.append(message)
        return self.result


class FakeRouter:
    def route(self, intent_result: IntentResult) -> RouteDecision:
        if intent_result.confidence < 0.5:
            flow = FlowType.FALLBACK
        elif intent_result.intent == "knowledge_qa":
            flow = FlowType.KNOWLEDGE_QA
        else:
            flow = FlowType.CHITCHAT
        return RouteDecision(flow=flow, intent=intent_result)


class FakePostProcessor:
    def process(self, reply: str) -> str:
        return reply


class FakeKnowledgeRetriever:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def retrieve_context(self, message: str) -> str:
        self.calls.append(message)
        return "离线知识上下文"


class FallbackHandlerMustNotRun:
    async def handle(self, *args, **kwargs) -> str:
        raise AssertionError("fallback handler must not replace the medical responder path")


@pytest.fixture
def api_fakes(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """隔离所有外部 AI/向量服务，同时保留真实会话行为。"""
    conversation_manager = ConversationManager()
    responder = FakeResponder()
    classifier = FakeIntentClassifier()
    knowledge_retriever = FakeKnowledgeRetriever()
    settings = SimpleNamespace(ENABLE_RAG=False)
    security_settings = SimpleNamespace(AI_PROXY_SECRET=PROXY_SECRET)

    monkeypatch.setattr(routes, "get_conversation_manager", lambda: conversation_manager)
    monkeypatch.setattr(routes, "get_context_builder", routes.get_context_builder)
    monkeypatch.setattr(routes, "get_intent_classifier", lambda: classifier)
    monkeypatch.setattr(routes, "get_knowledge_retriever", lambda: knowledge_retriever)
    monkeypatch.setattr(routes, "get_router", lambda: FakeRouter())
    monkeypatch.setattr(
        routes, "get_fallback_handler", FallbackHandlerMustNotRun, raising=False
    )
    monkeypatch.setattr(routes, "get_responder", lambda: responder)
    monkeypatch.setattr(routes, "get_post_processor", lambda: FakePostProcessor())
    monkeypatch.setattr(routes, "get_settings", lambda: settings, raising=False)
    monkeypatch.setattr(dependencies, "get_settings", lambda: security_settings)

    return SimpleNamespace(
        conversation_manager=conversation_manager,
        responder=responder,
        classifier=classifier,
        knowledge_retriever=knowledge_retriever,
        settings=settings,
    )


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """测试健康检查接口。"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"X-User-Id": "mallory"},
        {"X-User-Id": "mallory", "X-AI-Proxy-Secret": "wrong-secret"},
        {"Authorization": "Bearer forged"},
    ],
)
async def test_identity_headers_require_the_trusted_proxy_secret(
    client: AsyncClient, api_fakes: SimpleNamespace, headers: dict[str, str]
):
    response = await client.post("/chat", headers=headers, json={"message": "hello"})

    assert response.status_code == 401
    assert response.json() == {"detail": "未授权的代理请求"}
    assert "wrong-secret" not in response.text
    assert "forged" not in response.text
    assert api_fakes.responder.calls == []


@pytest.mark.asyncio
async def test_trusted_proxy_secret_allows_identity_headers(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post(
        "/chat", headers=trusted_headers("alice"), json={"message": "hello"}
    )

    assert response.status_code == 200
    session = api_fakes.conversation_manager.get_session(response.json()["session_id"])
    assert session.user_id == "alice"


@pytest.mark.asyncio
async def test_session_capacity_returns_stable_429_and_preserves_live_sessions(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.conversation_manager.settings.MAX_ACTIVE_SESSIONS = 1
    existing = api_fakes.conversation_manager.claim_or_get_session("existing", None)
    existing.add_message("user", "live")

    response = await client.post(
        "/chat", json={"session_id": "over-capacity", "message": "hello"}
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "会话容量已满，请稍后重试"}
    assert api_fakes.conversation_manager.get_session("existing") is existing
    assert api_fakes.conversation_manager.get_session("over-capacity") is None


@pytest.mark.asyncio
async def test_chat_basic(client: AsyncClient, api_fakes: SimpleNamespace):
    """测试基本聊天接口。"""
    response = await client.post(
        "/chat",
        json={"message": "你好", "stream": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "reply" in data
    assert len(data["reply"]) > 0
    messages = api_fakes.responder.calls[-1]
    assert [message["content"] for message in messages].count("你好") == 1


@pytest.mark.asyncio
async def test_chat_with_session(client: AsyncClient, api_fakes: SimpleNamespace):
    """测试带会话 ID 的聊天。"""
    session_id = "test-session-001"
    # 第一轮
    r1 = await client.post(
        "/chat",
        json={"session_id": session_id, "message": "你好"},
    )
    assert r1.status_code == 200

    # 第二轮（同一会话）
    r2 = await client.post(
        "/chat",
        json={"session_id": session_id, "message": "我刚才说了什么？"},
    )
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id

    history = await client.get(f"/session/{session_id}/history")
    assert history.json()["turn_count"] == 2
    assert [message["role"] for message in history.json()["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_get_history(client: AsyncClient, api_fakes: SimpleNamespace):
    """测试获取会话历史。"""
    session_id = "test-session-002"
    await client.post("/chat", json={"session_id": session_id, "message": "Hello"})
    await client.post("/chat", json={"session_id": session_id, "message": "World"})

    response = await client.get(f"/session/{session_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert data["turn_count"] == 2
    assert len(data["messages"]) == 4  # 2 user + 2 assistant


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient, api_fakes: SimpleNamespace):
    """测试删除会话。"""
    session_id = "test-session-003"
    await client.post("/chat", json={"session_id": session_id, "message": "Hi"})

    response = await client.delete(f"/session/{session_id}")
    assert response.status_code == 200

    # 确认已删除
    r2 = await client.get(f"/session/{session_id}/history")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_authenticated_sessions_are_private_and_ignore_body_user_id(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    session_id = "alice-private-session"
    alice_headers = trusted_headers("alice")
    response = await client.post(
        "/chat",
        headers=alice_headers,
        json={"session_id": session_id, "user_id": "bob", "message": "Alice first turn"},
    )
    assert response.status_code == 200
    assert api_fakes.conversation_manager.get_session(session_id).user_id == "alice"

    continued = await client.post(
        "/chat", headers=alice_headers, json={"session_id": session_id, "message": "Alice second turn"}
    )
    assert continued.status_code == 200
    calls_before_denial = len(api_fakes.responder.calls)
    turns_before_denial = api_fakes.conversation_manager.get_session(session_id).turn_count

    bob_headers = trusted_headers("bob")
    assert (await client.post("/chat", headers=bob_headers, json={"session_id": session_id, "message": "steal"})).status_code == 404
    assert (await client.get(f"/session/{session_id}/history", headers=bob_headers)).status_code == 404
    assert (await client.delete(f"/session/{session_id}", headers=bob_headers)).status_code == 404
    assert len(api_fakes.responder.calls) == calls_before_denial
    assert api_fakes.conversation_manager.get_session(session_id).turn_count == turns_before_denial

    assert (await client.get(f"/session/{session_id}/history", headers=alice_headers)).status_code == 200
    assert (await client.delete(f"/session/{session_id}", headers=alice_headers)).status_code == 200


@pytest.mark.asyncio
async def test_anonymous_sessions_are_capability_based_and_body_user_id_does_not_claim_them(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post("/chat", json={"user_id": "alice", "message": "anonymous turn"})
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    session = api_fakes.conversation_manager.get_session(session_id)
    assert session.user_id is None

    # Anonymous session IDs are random capabilities: possession of the returned ID is required for access.
    assert (await client.get(f"/session/{session_id}/history")).status_code == 200
    assert (await client.get("/session/not-held-by-caller/history")).status_code == 404


@pytest.mark.asyncio
async def test_authenticated_request_atomically_upgrades_anonymous_session_owner(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    created = await client.post("/chat", json={"message": "anonymous turn"})
    session_id = created.json()["session_id"]

    upgraded = await client.post(
        "/chat",
        headers=trusted_headers("alice"),
        json={"session_id": session_id, "message": "authenticated turn"},
    )

    assert upgraded.status_code == 200
    assert api_fakes.conversation_manager.get_session(session_id).user_id == "alice"
    assert (await client.get(f"/session/{session_id}/history")).status_code == 404
    assert (
        await client.get(
            f"/session/{session_id}/history", headers=trusted_headers("bob")
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/session/{session_id}/history", headers=trusted_headers("alice")
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_same_session_requests_are_fifo_and_second_sees_first_committed_turn(
    client: AsyncClient, api_fakes: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    responder = OrderedResponder()
    monkeypatch.setattr(routes, "get_responder", lambda: responder)
    session_id = "serialized-session"

    first = asyncio.create_task(
        client.post("/chat", json={"session_id": session_id, "message": "first"})
    )
    await responder.first_started.wait()
    second = asyncio.create_task(
        client.post("/chat", json={"session_id": session_id, "message": "second"})
    )
    await asyncio.sleep(0)
    assert len(responder.calls) == 1

    responder.release_first.set()
    first_response, second_response = await asyncio.gather(first, second)

    assert [first_response.status_code, second_response.status_code] == [200, 200]
    assert [message["content"] for message in responder.calls[1]] == [
        SYSTEM_PROMPT,
        "first",
        "reply-1",
        "second",
    ]
    history = await client.get(f"/session/{session_id}/history")
    assert [message["content"] for message in history.json()["messages"]] == [
        "first",
        "reply-1",
        "second",
        "reply-2",
    ]


@pytest.mark.asyncio
async def test_different_sessions_can_reach_model_work_in_parallel(
    client: AsyncClient, api_fakes: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    responder = ParallelResponder()
    monkeypatch.setattr(routes, "get_responder", lambda: responder)

    responses = await asyncio.gather(
        client.post("/chat", json={"session_id": "parallel-a", "message": "a"}),
        client.post("/chat", json={"session_id": "parallel-b", "message": "b"}),
    )

    assert [response.status_code for response in responses] == [200, 200]


@pytest.mark.asyncio
async def test_stream_rejects_other_authenticated_owner_before_model_invocation(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    session_id = "alice-stream-session"
    await client.post(
        "/chat", headers=trusted_headers("alice"), json={"session_id": session_id, "message": "Alice turn"}
    )
    calls_before_denial = len(api_fakes.responder.calls)

    response = await client.post(
        "/chat/stream", headers=trusted_headers("bob"), json={"session_id": session_id, "message": "steal"}
    )
    assert response.status_code == 404
    assert len(api_fakes.responder.calls) == calls_before_denial


@pytest.mark.asyncio
async def test_concurrent_first_authenticated_claim_allows_only_one_owner(
    client: AsyncClient, api_fakes: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    session_id = "concurrent-first-claim"
    responder = YieldingResponder()
    monkeypatch.setattr(routes, "get_responder", lambda: responder)

    alice, bob = await asyncio.gather(
        client.post("/chat", headers=trusted_headers("alice"), json={"session_id": session_id, "message": "alice only"}),
        client.post("/chat", headers=trusted_headers("bob"), json={"session_id": session_id, "message": "bob only"}),
    )

    winners = [("alice", alice), ("bob", bob)]
    assert sorted(response.status_code for _, response in winners) == [200, 404]
    winner, _ = next((name, response) for name, response in winners if response.status_code == 200)
    loser, _ = next((name, response) for name, response in winners if response.status_code == 404)
    assert len(responder.calls) == 1

    history = await client.get(f"/session/{session_id}/history", headers=trusted_headers(winner))
    assert history.status_code == 200
    assert [message["content"] for message in history.json()["messages"] if message["role"] == "user"] == [f"{winner} only"]
    assert (await client.get(f"/session/{session_id}/history", headers=trusted_headers(loser))).status_code == 404
    assert (await client.delete(f"/session/{session_id}", headers=trusted_headers(loser))).status_code == 404


@pytest.mark.asyncio
async def test_stream_claims_new_session_before_model_work(client: AsyncClient, api_fakes: SimpleNamespace):
    session_id = "stream-first-claim"
    assert (await client.post("/chat/stream", headers=trusted_headers("alice"), json={"session_id": session_id, "message": "alice only"})).status_code == 200
    calls_before_denial = len(api_fakes.responder.calls)

    denied = await client.post("/chat/stream", headers=trusted_headers("bob"), json={"session_id": session_id, "message": "bob only"})

    assert denied.status_code == 404
    assert len(api_fakes.responder.calls) == calls_before_denial


@pytest.mark.asyncio
async def test_chat_rejects_whitespace_only_message(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post("/chat", json={"message": " \t\n "})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_keeps_4096_character_message_limit(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post("/chat", json={"message": "a" * 4097})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_short_circuits_emergency_before_ai_services(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post("/chat", json={"message": "我现在胸痛呼吸困难"})

    assert response.status_code == 200
    data = response.json()
    assert "立即" in data["reply"]
    assert data["intent"] == "medical_emergency"
    assert data["confidence"] == 1.0
    assert api_fakes.classifier.calls == []
    assert api_fakes.responder.calls == []

    history = await client.get(f"/session/{data['session_id']}/history")
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_chat_maps_llm_error_to_sanitized_service_unavailable(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.responder.error = LLMError("upstream secret diagnostic")

    response = await client.post(
        "/chat", json={"session_id": "llm-failure", "message": "你好"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI 问诊服务暂时不可用，请稍后重试"
    assert "upstream secret diagnostic" not in response.text

    history = await client.get("/session/llm-failure/history")
    assert history.status_code == 404


@pytest.mark.asyncio
async def test_chat_rejects_empty_model_output_and_rolls_back_new_session(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.responder.reply = " \n\t "

    response = await client.post(
        "/chat", json={"session_id": "empty-output", "message": "你好"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI 问诊服务暂时不可用，请稍后重试"
    assert (await client.get("/session/empty-output/history")).status_code == 404


@pytest.mark.asyncio
async def test_chat_does_not_construct_retriever_when_rag_is_disabled(
    client: AsyncClient, api_fakes: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    api_fakes.classifier.result = IntentResult(intent="knowledge_qa", confidence=1.0)

    def retriever_must_not_be_constructed():
        raise AssertionError("RAG disabled must not construct a knowledge retriever")

    monkeypatch.setattr(routes, "get_knowledge_retriever", retriever_must_not_be_constructed)

    response = await client.post("/chat", json={"message": "高血压是什么"})

    assert response.status_code == 200
    assert api_fakes.responder.calls


@pytest.mark.asyncio
async def test_chat_uses_retriever_context_when_rag_is_enabled(
    client: AsyncClient, api_fakes: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    api_fakes.settings.ENABLE_RAG = True
    api_fakes.classifier.result = IntentResult(intent="knowledge_qa", confidence=1.0)
    constructed: list[FakeKnowledgeRetriever] = []

    def construct_retriever() -> FakeKnowledgeRetriever:
        constructed.append(api_fakes.knowledge_retriever)
        return api_fakes.knowledge_retriever

    monkeypatch.setattr(routes, "get_knowledge_retriever", construct_retriever)

    response = await client.post("/chat", json={"message": "高血压是什么"})

    assert response.status_code == 200
    assert constructed == [api_fakes.knowledge_retriever]
    assert api_fakes.knowledge_retriever.calls == ["高血压是什么"]
    assert "离线知识上下文" in api_fakes.responder.calls[-1][0]["content"]


@pytest.mark.asyncio
async def test_chat_fallback_uses_medical_context_and_responder(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.classifier.result = IntentResult(intent="unknown", confidence=0.1)

    response = await client.post("/chat", json={"message": "我不太确定怎么描述"})

    assert response.status_code == 200
    assert response.json()["reply"] == "离线测试回复"
    assert api_fakes.responder.calls[-1][0]["content"] == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_chat_openapi_documents_actual_validation_and_service_errors(client: AsyncClient):
    schema = (await client.get("/openapi.json")).json()
    responses = schema["paths"]["/chat"]["post"]["responses"]

    assert "400" not in responses
    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }
    assert responses["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ServiceUnavailableResponse"
    }
    assert responses["429"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ServiceUnavailableResponse"
    }
    service_error = schema["components"]["schemas"]["ServiceUnavailableResponse"]
    assert service_error["properties"] == {"detail": {"type": "string", "title": "Detail"}}
    assert service_error["required"] == ["detail"]


@pytest.mark.asyncio
async def test_chat_stream_openapi_documents_plain_text_success(client: AsyncClient):
    schema = (await client.get("/openapi.json")).json()
    responses = schema["paths"]["/chat/stream"]["post"]["responses"]

    assert responses["200"]["content"] == {"text/plain": {"schema": {"type": "string"}}}
    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }
    assert responses["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ServiceUnavailableResponse"
    }
    assert responses["429"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ServiceUnavailableResponse"
    }
    assert list(responses["503"]["content"]) == ["application/json"]


@pytest.mark.asyncio
async def test_chat_stream_rejects_whitespace_only_message(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post("/chat/stream", json={"message": "  \n\t "})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_hides_llm_error_details(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.responder.error = LLMError("stream upstream secret diagnostic")

    response = await client.post(
        "/chat/stream", json={"session_id": "stream-failure", "message": "你好"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI 问诊服务暂时不可用，请稍后重试"
    assert "stream upstream secret diagnostic" not in response.text
    history = await client.get("/session/stream-failure/history")
    assert history.status_code == 404


@pytest.mark.asyncio
async def test_chat_stream_rejects_empty_model_output_and_rolls_back_new_session(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.responder.stream_tokens = [" \n\t "]

    response = await client.post(
        "/chat/stream", json={"session_id": "empty-stream-output", "message": "你好"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI 问诊服务暂时不可用，请稍后重试"
    assert (await client.get("/session/empty-stream-output/history")).status_code == 404


@pytest.mark.asyncio
async def test_chat_stream_discards_partial_output_and_history_on_llm_error(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    api_fakes.responder.stream_tokens = ["partial token"]
    api_fakes.responder.stream_error_after_tokens = LLMError("partial stream secret")

    response = await client.post(
        "/chat/stream", json={"session_id": "partial-stream-failure", "message": "你好"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI 问诊服务暂时不可用，请稍后重试"
    assert "partial token" not in response.text
    history = await client.get("/session/partial-stream-failure/history")
    assert history.status_code == 404


@pytest.mark.asyncio
async def test_chat_stream_short_circuits_emergency(
    client: AsyncClient, api_fakes: SimpleNamespace
):
    response = await client.post("/chat/stream", json={"message": "我现在胸痛呼吸困难"})

    assert response.status_code == 200
    assert "立即" in response.text
    assert api_fakes.responder.calls == []
