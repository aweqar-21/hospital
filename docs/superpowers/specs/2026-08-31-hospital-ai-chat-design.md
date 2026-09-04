# 医院 AI 问诊整合设计

## 目标

将现有 Spring Boot 医院预约系统与 Python FastAPI chatbot 合并为一个可独立部署的 `hospital` 仓库，为患者提供可直接访问的 AI 健康咨询网页和统一的医院后端 API。模型继续使用现有 DeepSeek 配置，敏感配置仅从环境变量读取。

## 范围

本次交付包括：

- 将现有 Python chatbot 作为 `chatbot-service/` 纳入医院仓库。
- 在 Spring Boot 中增加 AI 问诊代理接口，由医院后端调用 chatbot 服务。
- 在医院项目中增加响应式聊天网页，支持匿名使用，并兼容现有 JWT。
- 支持多轮会话、会话历史查询和会话清理。
- 增加医疗安全提示、急症提示、输入校验、超时和服务不可用降级。
- 增加统一配置示例、Docker Compose、测试和中文 README。
- 将最终项目推送到 GitHub 和 Gitee 的 `hospital` 仓库。

本次不包括在线医生接管、处方开具、正式诊断、患者病历自动写入、支付功能和模型微调。

## 架构

项目采用单仓库、双服务结构：

```text
患者浏览器
    |
    v
Spring Boot 医院服务（统一入口、页面、JWT、AI 代理）
    |
    v
FastAPI chatbot-service（会话、意图、问诊提示词、DeepSeek）
    |
    v
DeepSeek OpenAI 兼容 API
```

浏览器不直接访问 Python 服务，也不接触 DeepSeek 密钥。Spring Boot 对外提供统一路径并通过可配置的内部地址调用 chatbot。两个服务可分别本地启动，也可通过根目录 Docker Compose 一起启动。

## 仓库结构

```text
hospital/
├── src/                         # 现有 Spring Boot 医院服务
├── chatbot-service/             # 合并后的 FastAPI chatbot
├── docs/                        # 部署、演示与设计文档
├── docker-compose.yml           # 双服务编排
├── .env.example                 # 无密钥的配置模板
├── pom.xml
└── README.md                    # 统一项目说明
```

Python 的缓存、虚拟环境、SQLite/Chroma 数据、日志和 `.env` 不进入 Git。Java 的 `target/`、IDE 配置和本地敏感配置同样排除。

## Spring Boot AI 接口

新增独立的 AI 模块，包含配置、请求响应 DTO、chatbot HTTP 客户端、服务和控制器。外部接口使用医院现有 `CommonResult` 响应风格：

- `POST /ai/chat`：发送消息并返回回答、会话 ID、意图和置信度。
- `GET /ai/session/{sessionId}/history`：查询会话历史。
- `DELETE /ai/session/{sessionId}`：清理会话。
- `GET /ai/health`：检查 Python chatbot 可用性。

聊天请求最多 4096 个字符。匿名患者可使用；若请求携带有效 JWT，Spring 服务将当前账户标识传给 chatbot。Spring 调用 Python 服务时设置连接和读取超时，不记录消息正文、JWT 或 API Key。

## Python 问诊服务

保留现有 FastAPI、多轮会话、DeepSeek 调用和基础意图能力，并进行医院场景收敛：

- 使用系统提示词声明其为健康咨询和分诊助手，不能替代医生诊断。
- 回答优先给出可能原因、建议科室、就医紧迫程度和下一步行动。
- 对胸痛、呼吸困难、意识障碍、大出血、自伤等高风险描述返回明确的急诊提示。
- DeepSeek 请求失败、超时或未配置时返回结构化错误，由 Spring 转换为友好提示。
- API Key、模型名和 Base URL 仅通过 `.env`/环境变量配置。

现有配置把 `text-embedding-3-small` 指向 DeepSeek 地址，而 DeepSeek 对话接口不保证提供该嵌入模型。基础问诊流程不依赖 Embedding；知识库检索仅在单独配置兼容 Embedding 服务时启用，否则自动降级为纯 DeepSeek 问诊，不影响聊天可用性。

## 聊天网页

聊天页作为 Spring Boot 静态资源交付，通过相对路径调用 `/hospital/ai/*`：

- 展示医疗免责声明和紧急情况提示。
- 提供消息列表、输入框、发送按钮、加载状态和错误提示。
- 在浏览器本地保存当前会话 ID，支持“新建会话”。
- 支持手机和桌面尺寸，使用原生 HTML/CSS/JavaScript，不引入额外前端构建链。
- 不在浏览器保存 DeepSeek Key；JWT 仅从现有登录存储中读取并作为 Authorization 请求头发送。

## 数据流

1. 患者打开医院服务提供的聊天页面并提交症状描述。
2. 页面向 Spring Boot `POST /ai/chat` 发送消息和可选会话 ID。
3. Spring 校验输入、读取可选登录身份并转发至 FastAPI。
4. FastAPI 执行安全分流、构建多轮上下文并调用 DeepSeek。
5. FastAPI 返回结构化结果，Spring 包装成医院统一响应格式。
6. 页面展示回复并保存会话 ID，后续消息复用该会话。

## 错误与安全处理

- 空消息或超长消息返回 400，不调用模型。
- chatbot 不可达或超时返回 503，并提示患者稍后重试或联系人工医生。
- DeepSeek 限流或异常不暴露上游响应、堆栈和密钥。
- 高风险症状优先提示拨打当地急救电话或立即前往急诊，不继续给出可能延误治疗的居家建议。
- 页面和 README 明确说明 AI 输出仅供参考。
- `.env`、数据库密码、JWT 密钥和第三方凭据不得提交到远程仓库。

## 测试与验收

按照测试先行方式完成：

- Python：测试问诊提示词、急症分流、输入校验、会话延续、DeepSeek 错误映射和无 Embedding 降级。
- Java：测试请求校验、身份透传、chatbot 成功响应、超时/不可用映射及控制器响应。
- 页面：验证发送消息、复用/新建会话、错误展示和移动端布局。
- 集成：构建 Java 服务、运行 Python 全量测试、验证 Docker Compose 配置，并对健康检查和聊天链路进行冒烟测试。

验收标准是：在仅配置 DeepSeek API Key 的情况下，按 README 启动两个服务后，患者可从医院页面完成多轮健康咨询；异常时获得明确提示；仓库中不存在真实密钥或构建产物。

## 发布策略

完成验证后创建一次清晰的功能提交。检查本机 GitHub CLI、Gitee 凭据和目标仓库状态：若名为 `hospital` 的仓库不存在则新建；若已存在则在不覆盖远程历史的前提下连接和推送。GitHub 与 Gitee 分别配置独立 remote，最终报告两个仓库地址和推送分支。
