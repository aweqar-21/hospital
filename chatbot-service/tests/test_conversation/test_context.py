"""上下文构建器单元测试。"""
from core.context_builder import ContextBuilder
from core.conversation_manager import Session


class TestContextBuilder:
    def setup_method(self):
        self.builder = ContextBuilder()
        self.session = Session(session_id="ctx-test")

    def test_build_basic_messages(self):
        messages = self.builder.build_messages(self.session, "你好")
        assert len(messages) >= 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "你好"

    def test_build_with_history(self):
        self.session.add_message("user", "我叫小明")
        self.session.add_message("assistant", "你好小明！")
        messages = self.builder.build_messages(self.session, "你还记得我叫什么吗？")
        # 应包含 system + 2 历史 + 1 当前用户消息
        assert len(messages) == 4

    def test_build_with_extra_context(self):
        messages = self.builder.build_messages(
            self.session, "介绍一下产品", extra_context="产品A：价格100元\n产品B：价格200元"
        )
        system = messages[0]["content"]
        assert "产品A" in system

    def test_build_prompt_text(self):
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"},
        ]
        prompt = self.builder.build_prompt_text(messages)
        assert "<|system|>" in prompt
        assert "<|user|>" in prompt
        assert "<|assistant|>" in prompt
