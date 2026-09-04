"""对话管理单元测试。"""
import asyncio
import time

import pytest

from core.conversation_manager import ConversationManager, Session


class TestSession:
    def test_add_message(self):
        session = Session(session_id="test-1")
        session.add_message("user", "你好")
        session.add_message("assistant", "你好！")
        assert session.turn_count == 1
        assert len(session.messages) == 2

    def test_recent_messages(self):
        session = Session(session_id="test-2")
        for i in range(10):
            session.add_message("user", f"msg-{i}")
            session.add_message("assistant", f"reply-{i}")
        recent = session.recent_messages(4)
        assert len(recent) == 4
        assert recent[-1].content == "reply-9"


class TestConversationManager:
    def setup_method(self):
        self.manager = ConversationManager()

    def test_create_session(self):
        session = self.manager.create_session(user_id="user-1")
        assert session.session_id
        assert session.user_id == "user-1"

    def test_get_session(self):
        session = self.manager.create_session()
        found = self.manager.get_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_delete_session(self):
        session = self.manager.create_session()
        assert self.manager.delete_session(session.session_id)
        assert self.manager.get_session(session.session_id) is None

    def test_duplicate_session_id(self):
        """同一 session_id 多次 get_or_create 返回同一对象。"""
        sid = "shared-session"
        s1 = self.manager.get_or_create_session(sid)
        s2 = self.manager.get_or_create_session(sid)
        assert s1 is s2

    def test_add_messages(self):
        session = self.manager.add_user_message("s1", "hello")
        assert session.turn_count == 1
        session = self.manager.add_assistant_message("s1", "hi!")
        assert session.turn_count == 1  # assistant 不计入 turn
        assert len(session.messages) == 2

    def test_production_access_evicts_expired_sessions(self):
        self.manager.settings.SESSION_TTL_SECONDS = 10
        expired = self.manager.get_or_create_session("expired")
        expired.updated_at = time.time() - 11

        assert self.manager.get_session("expired") is None
        assert "expired" not in self.manager._sessions

    def test_history_is_trimmed_to_configured_complete_turns(self):
        self.manager.settings.MAX_HISTORY_TURNS = 2

        for index in range(3):
            self.manager.add_user_message("bounded", f"question-{index}")
            self.manager.add_assistant_message("bounded", f"answer-{index}")

        session = self.manager.get_session("bounded")
        assert [(message.role, message.content) for message in session.messages] == [
            ("user", "question-1"),
            ("assistant", "answer-1"),
            ("user", "question-2"),
            ("assistant", "answer-2"),
        ]

    def test_capacity_rejects_new_live_session_without_evicting_existing_sessions(self):
        self.manager.settings.MAX_ACTIVE_SESSIONS = 1
        first = self.manager.claim_or_get_session("first", "alice")

        with pytest.raises(Exception) as raised:
            self.manager.claim_or_get_session("second", "bob")

        assert raised.value.__class__.__name__ == "SessionCapacityError"
        assert self.manager.get_session("first") is first
        assert self.manager.get_session("second") is None


@pytest.mark.asyncio
async def test_cancelled_lock_waiter_does_not_leak_session_lock():
    manager = ConversationManager()

    async def wait_for_same_session():
        async with manager.session_scope("cancelled-waiter", None, create=False):
            raise AssertionError("cancelled waiter must never acquire the lock")

    async with manager.session_scope("cancelled-waiter", None, create=True) as lease:
        lease.session.add_message("user", "keep reservation alive")
        waiter = asyncio.create_task(wait_for_same_session())
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert manager.delete_session("cancelled-waiter")

    assert "cancelled-waiter" not in manager._session_locks
