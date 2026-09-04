# Chatbot — 模块化智能对话机器人

一个基于 Python 的模块化智能对话机器人框架，支持意图识别、知识检索增强（RAG）、多轮对话管理、多通道接入。

## 项目结构

```
chatbot-service/
├── config/          # 配置层（环境变量、模型参数、意图规则）
├── core/            # 核心对话引擎（对话管理、上下文构建、响应生成）
├── nlu/             # 自然语言理解（意图分类、实体抽取、情感分析）
├── knowledge/       # 知识库与 RAG（向量存储、嵌入、检索）
├── memory/          # 长期记忆（用户画像、情景记忆）
├── policies/        # 对话策略与路由
├── api/             # 对外服务接口（REST / gRPC）
├── connectors/      # 外部系统适配器（企业微信、Slack、Webhook）
├── models/          # 本地模型管理
├── utils/           # 工具模块（日志、缓存、文本处理）
├── tests/           # 测试
└── scripts/         # 运维脚本
```

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv venv && source venv/bin/activate  # Linux/Mac
# python -m venv venv && venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -e .

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key 等配置

# 4. 初始化（下载模型、构建向量库）
python scripts/bootstrap.py

# 5. 启动服务
uvicorn api.routes:app --host 127.0.0.1 --port 8000 --no-access-log
```

## Docker 部署

```bash
docker-compose up -d
```

## 核心特性

- **意图识别**：支持规则匹配 + 小模型 + 大模型三级策略
- **RAG 检索增强**：基于向量数据库的知识问答
- **多轮对话**：会话状态管理与上下文构建
- **多通道接入**：企业微信 / Slack / Webhook / REST API
- **本地模型支持**：可接入 ChatGLM、Qwen 等开源模型

## 安全部署契约

浏览器应只调用 Spring API。Spring 与 FastAPI 必须配置相同的强随机 `AI_PROXY_SECRET`；FastAPI 仅在代理密钥通过常量时间比较后接受 `X-User-Id` 或 `Authorization`。独立 Compose 仅绑定 `127.0.0.1`，默认空代理密钥不授予任何身份伪造能力。

Uvicorn 必须使用 `--no-access-log`，防止 capability 型 `session_id` 出现在访问日志。会话由 `SESSION_TTL_SECONDS`、`MAX_HISTORY_TURNS` 和 `MAX_ACTIVE_SESSIONS` 限制；失败的新空会话会自动回滚。`/chat/stream` 有意完整缓冲输出，以保证 503 状态和历史提交原子性。
