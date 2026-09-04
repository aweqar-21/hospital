"""gRPC 服务定义与实现（可选）。"""
# 使用前需安装: pip install grpcio grpcio-tools
# 编译 proto: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. chatbot.proto

from typing import Optional


class ChatbotServicer:
    """gRPC 服务实现 —— 与 REST 接口逻辑一致。

    proto 定义参考:
    ```
    service Chatbot {
        rpc Chat (ChatRequest) returns (ChatResponse);
        rpc ChatStream (ChatRequest) returns (stream ChatChunk);
    }
    ```
    """

    def __init__(self) -> None:
        from api.dependencies import (
            get_context_builder,
            get_conversation_manager,
            get_intent_classifier,
            get_responder,
        )

        self.conv_mgr = get_conversation_manager()
        self.context_builder = get_context_builder()
        self.intent_classifier = get_intent_classifier()
        self.responder = get_responder()

    async def Chat(self, request: object, context: object) -> object:
        """一元对话调用。"""
        # 实际项目中根据 proto 生成的类型实现
        raise NotImplementedError("gRPC 服务待实现 —— 请先编译 .proto 文件")

    async def ChatStream(self, request: object, context: object) -> object:
        """流式对话调用。"""
        raise NotImplementedError("gRPC 服务待实现 —— 请先编译 .proto 文件")
