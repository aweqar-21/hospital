"""对话状态管理 —— 会话创建、历史记录存取、状态流转。"""
import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from config.settings import get_settings


class SessionCapacityError(RuntimeError):
    """The configured live-session capacity has been reached."""


@dataclass
class _SessionLock:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


@dataclass
class SessionLease:
    session: "Session | None"
    created: bool = False


@dataclass
class Message:
    """单条消息。"""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    """会话对象。"""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    messages: list[Message] = field(default_factory=list)
    user_id: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        self.updated_at = time.time()

    @property
    def turn_count(self) -> int:
        """用户-助手 交互轮数。"""
        return sum(1 for m in self.messages if m.role == "user")

    def recent_messages(self, n: int) -> list[Message]:
        """取最近 n 条消息。"""
        return self.messages[-n:]


class ConversationManager:
    """管理所有活跃会话。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._sessions: dict[str, Session] = {}
        self._session_locks: dict[str, _SessionLock] = {}

    def create_session(self, user_id: str | None = None) -> Session:
        self._evict_expired()
        self._require_capacity()
        session = Session(user_id=user_id)
        while session.session_id in self._sessions:
            session.session_id = uuid.uuid4().hex
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        self._evict_expired()
        session = self._sessions.get(session_id)
        return session

    def delete_session(self, session_id: str) -> bool:
        self._evict_expired()
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def add_user_message(self, session_id: str, content: str) -> Session:
        session = self.get_or_create_session(session_id)
        session.add_message("user", content)
        self._trim_history(session)
        return session

    def add_assistant_message(self, session_id: str, content: str) -> Session:
        session = self.get_or_create_session(session_id)
        session.add_message("assistant", content)
        self._trim_history(session)
        return session

    def get_or_create_session(self, session_id: str) -> Session:
        session = self.get_session(session_id)
        if session is None:
            self._require_capacity()
            session = Session(session_id=session_id)
            self._sessions[session_id] = session
        return session

    def claim_or_get_session(self, session_id: str, user_id: str | None) -> Session:
        """Create or atomically bind an anonymous session to a trusted user.

        Production callers must invoke this while holding ``session_scope``.
        """
        session = self.get_session(session_id)
        if session is None:
            self._require_capacity()
            session = Session(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = session
        elif session.user_id is None and user_id is not None:
            session.user_id = user_id
            session.updated_at = time.time()
        return session

    @asynccontextmanager
    async def session_scope(
        self, session_id: str, user_id: str | None, *, create: bool
    ) -> AsyncIterator[SessionLease]:
        """Serialize all work for one session and manage reservation rollback.

        ``asyncio.Lock`` grants acquisition in waiter order. The reference count keeps
        the lock entry alive while a holder or waiter exists, so TTL cleanup cannot
        create a second lock for the same session.
        """
        self._evict_expired()
        state = self._session_locks.setdefault(session_id, _SessionLock())
        state.users += 1
        lease = SessionLease(session=None)
        acquired = False
        try:
            await state.lock.acquire()
            acquired = True
            self._evict_expired_session(session_id)
            session = self._sessions.get(session_id)
            if session is None and create:
                self._require_capacity()
                session = Session(session_id=session_id, user_id=user_id)
                self._sessions[session_id] = session
                lease.created = True
            elif session is not None and session.user_id is None and user_id is not None:
                session.user_id = user_id
                session.updated_at = time.time()
            lease.session = session
            yield lease
        finally:
            if (
                acquired
                and lease.created
                and lease.session is not None
                and not lease.session.messages
                and self._sessions.get(session_id) is lease.session
            ):
                del self._sessions[session_id]
            if acquired:
                state.lock.release()
            state.users -= 1
            if state.users == 0 and session_id not in self._sessions:
                self._session_locks.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量。"""
        return self._evict_expired()

    def _evict_expired(self) -> int:
        now = time.time()
        ttl = self.settings.SESSION_TTL_SECONDS
        expired_ids = [
            sid
            for sid, s in self._sessions.items()
            if now - s.updated_at > ttl
            and not self._lock_in_use(sid)
        ]
        for sid in expired_ids:
            del self._sessions[sid]
            self._session_locks.pop(sid, None)
        return len(expired_ids)

    def _evict_expired_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if time.time() - session.updated_at <= self.settings.SESSION_TTL_SECONDS:
            return False
        del self._sessions[session_id]
        return True

    def _lock_in_use(self, session_id: str) -> bool:
        state = self._session_locks.get(session_id)
        return state is not None and state.users > 0

    def _require_capacity(self) -> None:
        if len(self._sessions) >= self.settings.MAX_ACTIVE_SESSIONS:
            raise SessionCapacityError("active session capacity reached")

    def _trim_history(self, session: Session) -> None:
        max_messages = self.settings.MAX_HISTORY_TURNS * 2
        if len(session.messages) > max_messages:
            del session.messages[:-max_messages]

    def commit_turn(self, session: Session, user_message: str, assistant_message: str) -> None:
        session.add_message("user", user_message)
        session.add_message("assistant", assistant_message)
        self._trim_history(session)
