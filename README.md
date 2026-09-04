# Hospital 医院预约与 AI 问诊系统

## 项目简介

本项目将医院预约挂号后端与面向患者的 AI 健康咨询能力放在同一仓库中。Spring Boot 负责医院业务、身份认证、静态聊天页面和公共 API；FastAPI 负责多轮会话、医疗安全分流和模型调用；DeepSeek 是 FastAPI 通过 OpenAI 兼容接口访问的外部大模型。浏览器只访问 Spring Boot，不应直接持有或调用 DeepSeek 密钥。

AI 问诊适合提供一般健康信息、就医科室建议和就医紧迫度提示，不替代医生诊断、处方或急救服务。

## 系统架构

```text
浏览器
  └─ http://localhost:8080/hospital/ai-chat.html
       └─ Spring Boot :8080（/hospital，医院业务、认证、/ai/* 代理）
            ├─ MySQL（医院业务数据）
            ├─ Redis（验证码等缓存）
            └─ FastAPI :8000（会话、医疗安全、提示词与模型适配）
                 └─ DeepSeek API（仅 FastAPI 持有 LLM_API_KEY）
```

Spring Boot 将四个公开的 `/hospital/ai/*` 请求转发到 FastAPI。FastAPI 会先识别明显的紧急症状，再决定是否调用 DeepSeek；默认关闭 RAG（`ENABLE_RAG=false`）。Docker Compose 中 FastAPI 仅在内部网络暴露，宿主机只绑定 `127.0.0.1:8080`。

## 项目结构

```text
.
├─ chatbot-service/                  # FastAPI/DeepSeek 服务
│  ├─ api/                           # 路由、请求与响应模型
│  ├─ core/                          # 会话上下文、回复与医疗安全规则
│  ├─ config/                        # Python 配置
│  ├─ tests/                         # pytest 测试
│  ├─ pyproject.toml                 # Python 依赖与工具配置
│  └─ Dockerfile
├─ src/main/java/...                 # Spring Boot 医院后端与 AI 代理
├─ src/main/resources/
│  ├─ application.yml               # MySQL、Redis、JWT、AI 代理配置
│  ├─ hospital.sql                   # MySQL 初始化脚本
│  └─ static/ai-chat.html            # 患者聊天页面
├─ src/test/                         # Java、页面及部署契约测试
├─ .env.example                      # Compose 环境变量模板
├─ docker-compose.yml
├─ Dockerfile                        # Spring Boot 镜像
└─ pom.xml
```

Python 项目元数据的实际路径为 `chatbot-service/pyproject.toml`，数据库初始化文件为 `src/main/resources/hospital.sql`。

## 环境要求

- Python 3.11。`pyproject.toml` 声明支持 Python 3.10 及以上，容器和本文命令以 3.11 为基准。
- Java/JDK 8 与 Maven。项目源码和字节码目标均为 Java 8（Spring Boot 2.1.6）；建议使用 JDK 8 运行以保持兼容。Docker 构建使用 Maven 3.9.9 和 Java 8 镜像。
- MySQL 8；本地运行需创建 `hospital` 数据库并导入 SQL。
- Redis 7 或兼容版本；本地默认地址为 `localhost:6379`，若启用密码需同步设置 `REDIS_PASSWORD`。
- Node.js；仅用于 `AiChatPageBehaviorTest` 的离线页面行为测试，不需要 npm 安装依赖。
- Docker CLI 及 Compose v2；仅 Docker Compose 启动和配置验证需要。

可先检查工具：

```powershell
# Windows PowerShell
py -3.11 --version
java -version
mvn -version
node --version
docker version
docker compose version
```

```bash
# Linux/macOS
python3.11 --version
java -version
mvn -version
node --version
docker version
docker compose version
```

## DeepSeek 配置

先从仓库根目录复制根 `.env.example`，不要修改并提交模板本身：

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux/macOS
cp .env.example .env
```

编辑未纳入版本控制的 `.env`，至少填写：

```dotenv
LLM_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
JWT_SECRET=
```

`LLM_API_KEY` 只交给 FastAPI；`JWT_SECRET` 用于 Spring Security JWT 签名。不要使用示例值、短口令或在两个环境间复用密钥。Compose 会把 `DEEPSEEK_MODEL`/`DEEPSEEK_BASE_URL` 映射为 FastAPI 使用的 `LLM_MODEL`/`LLM_BASE_URL`。

本地直接启动时，当前终端还需设置 FastAPI 实际读取的变量：

```powershell
$env:LLM_API_KEY = Read-Host 'DeepSeek API Key'
$env:LLM_MODEL = 'deepseek-v4-flash'
$env:LLM_BASE_URL = 'https://api.deepseek.com/v1'
$env:JWT_SECRET = Read-Host '强随机 JWT 密钥'
```

```bash
read -rsp 'DeepSeek API Key: ' LLM_API_KEY; export LLM_API_KEY; printf '\n'
export LLM_MODEL='deepseek-v4-flash'
export LLM_BASE_URL='https://api.deepseek.com/v1'
read -rsp '强随机 JWT 密钥: ' JWT_SECRET; export JWT_SECRET; printf '\n'
```

## 本地启动

以下命令均从仓库根目录执行。

### 1. 初始化 MySQL 与 Redis

> **数据破坏警告：** `src/main/resources/hospital.sql` 包含删表语句，会执行 `DROP TABLE` 并重建表。它仅用于全新或确认可清空的一次性开发数据库。已有数据库先备份并确认可以丢弃其中数据，再执行下面的导入命令；不要对生产库或需要保留数据的数据库执行。

确认满足上述条件后，创建数据库并导入 `src/main/resources/hospital.sql`。命令会提示输入 MySQL 密码：

```powershell
# Windows PowerShell（重定向由 cmd.exe 处理）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS hospital CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
cmd /c "mysql -u root -p hospital < src\main\resources\hospital.sql"
```

```bash
# Linux/macOS
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS hospital CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p hospital < src/main/resources/hospital.sql
```

`hospital.sql` 只负责表结构和初始数据，不创建数据库账号。Windows 与 Linux/macOS 均可执行 `mysql -u root -p` 进入 MySQL 8 客户端，再把下列 `<HOSPITAL_DB_PASSWORD>` 替换为一个强随机本地密码并执行 SQL：

```sql
CREATE USER 'hospital_app'@'localhost' IDENTIFIED BY '<HOSPITAL_DB_PASSWORD>';
GRANT SELECT, INSERT, UPDATE, DELETE ON hospital.* TO 'hospital_app'@'localhost';
```

稍后启动 Spring 时，`MYSQL_USERNAME` 使用 `hospital_app`，`MYSQL_PASSWORD` 必须使用与 `<HOSPITAL_DB_PASSWORD>` 相同的实际密码。创建命令在同名账号已存在时会明确失败，避免修改或接管已有账号；发生冲突时应选择另一个专用新账号，并同步修改 `CREATE USER`、`GRANT` 和 `MYSQL_USERNAME`。上述账号仅允许从本机连接，并只获得应用运行所需的 DML 权限；不要把真实密码写入 README 或提交到仓库。

Redis 也必须先启动并确认连通。本地无密码配置与项目默认的 `localhost:6379` 一致。

Redis 官方不维护 Windows 原生版本。Windows 推荐安装 Docker Desktop，确认已切换到 **Linux containers**，并先确认本机 `6379 端口` 未被其他进程或容器占用。若端口已占用，应先停用冲突服务或为本项目选择其他宿主端口并同步 `REDIS_PORT`。

先检查是否已有同名容器：

```powershell
docker ps -a --filter "name=^/hospital-redis$"
```

- 首次创建：仅当列表中没有 `hospital-redis` 且 6379 端口空闲时运行：

```powershell
docker run --name hospital-redis --restart unless-stopped -p 127.0.0.1:6379:6379 -d redis:7.4.2-alpine
```

- 容器已在运行：不要重复 `docker run`，直接探活：

```powershell
docker exec hospital-redis redis-cli ping
```

- 容器已创建但已停止：启动后探活：

```powershell
docker start hospital-redis
docker exec hospital-redis redis-cli ping
```

探活命令应输出 `PONG`。

也可以在 WSL 的 Debian/Ubuntu 中安装 Redis：

```powershell
wsl -l -q
# 将 <DistroName> 替换为上一步列出的实际发行版名称
wsl -d "<DistroName>" -- bash -lc "sudo apt-get update && sudo apt-get install -y redis-server redis-tools"
```

若该 WSL 发行版已启用 systemd，可运行：

```powershell
wsl -d "<DistroName>" -- bash -lc "sudo systemctl enable --now redis-server && redis-cli ping"
```

未启用 systemd 时不应调用 `systemctl`，改用不依赖 systemd 的启动方式：

```powershell
wsl -d "<DistroName>" -- bash -lc "sudo redis-server --daemonize yes && redis-cli ping"
```

两种 WSL 探活均应输出 `PONG`。还需确认 Windows 可通过 `localhost:6379` 访问 WSL 服务；若发行版未提供 localhost 转发，请优先使用上面的 Docker Desktop 方案。

Debian/Ubuntu：

```bash
sudo apt-get update
sudo apt-get install -y redis-server redis-tools
sudo systemctl enable --now redis-server
redis-cli ping
```

macOS（使用 Homebrew）：

```bash
brew install redis
brew services start redis
redis-cli ping
```

`redis-cli ping` 应输出 `PONG`。若 Redis 启用了密码，验证时使用 `redis-cli -a '<本机 Redis 密码>' ping`，并在 FastAPI 与 Spring 启动终端中设置相同的 `REDIS_PASSWORD`。

### 2. 安装并启动 FastAPI（端口 8000）

```powershell
# Windows PowerShell
py -3.11 -m venv chatbot-service\.venv
.\chatbot-service\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\chatbot-service[dev]"
$env:LLM_API_KEY = Read-Host 'DeepSeek API Key'
$env:LLM_MODEL = 'deepseek-v4-flash'
$env:LLM_BASE_URL = 'https://api.deepseek.com/v1'
$env:REDIS_HOST = 'localhost'
$env:REDIS_PORT = '6379'
$env:AI_PROXY_SECRET = Read-Host 'Spring/FastAPI 共享代理密钥'
python -m uvicorn api.routes:app --app-dir chatbot-service --host 127.0.0.1 --port 8000 --no-access-log
```

```bash
# Linux/macOS
python3.11 -m venv chatbot-service/.venv
source chatbot-service/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e './chatbot-service[dev]'
read -rsp 'DeepSeek API Key: ' LLM_API_KEY; export LLM_API_KEY; printf '\n'
export LLM_MODEL='deepseek-v4-flash'
export LLM_BASE_URL='https://api.deepseek.com/v1'
export REDIS_HOST='localhost'
export REDIS_PORT='6379'
read -rsp 'Spring/FastAPI 共享代理密钥: ' AI_PROXY_SECRET; export AI_PROXY_SECRET; printf '\n'
python -m uvicorn api.routes:app --app-dir chatbot-service --host 127.0.0.1 --port 8000 --no-access-log
```

访问 `http://localhost:8000/health` 应得到 `{"status":"ok","version":"0.1.0"}`。

### 3. 启动 Spring Boot（端口 8080）

另开终端，在仓库根目录设置本机数据库、Redis 和强随机 JWT 配置，然后启动：

```powershell
# Windows PowerShell
$env:MYSQL_USERNAME = 'hospital_app'
$env:MYSQL_PASSWORD = '<HOSPITAL_DB_PASSWORD>'
$env:REDIS_HOST = 'localhost'
$env:REDIS_PORT = '6379'
$env:JWT_SECRET = Read-Host '强随机 JWT 密钥'
$env:CHATBOT_BASE_URL = 'http://localhost:8000'
$env:AI_PROXY_SECRET = Read-Host '与 FastAPI 相同的共享代理密钥'
mvn spring-boot:run
```

```bash
# Linux/macOS
export MYSQL_USERNAME='hospital_app'
export MYSQL_PASSWORD='<HOSPITAL_DB_PASSWORD>'
export REDIS_HOST='localhost'
export REDIS_PORT='6379'
read -rsp '强随机 JWT 密钥: ' JWT_SECRET; export JWT_SECRET; printf '\n'
export CHATBOT_BASE_URL='http://localhost:8000'
read -rsp '与 FastAPI 相同的共享代理密钥: ' AI_PROXY_SECRET; export AI_PROXY_SECRET; printf '\n'
mvn spring-boot:run
```

Spring Boot 的 context path 是 `/hospital`，因此应用入口以 `http://localhost:8080/hospital` 开头。

## Docker Compose 启动

确保根 `.env` 已填写 `LLM_API_KEY`、强随机 `JWT_SECRET` 和独立的强随机 `AI_PROXY_SECRET`，再执行：

```powershell
# Windows PowerShell
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f hospital chatbot
```

```bash
# Linux/macOS
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f hospital chatbot
```

Compose 会启动 MySQL、Redis、FastAPI `chatbot` 和 Spring Boot `hospital`；MySQL 首次创建数据卷时会自动导入 `src/main/resources/hospital.sql`。停止服务使用 `docker compose down`；该命令保留数据卷，只有明确需要清空本地数据时才使用 `docker compose down -v`。

> 当前文档不声称 Docker 镜像已在任意特定开发机成功构建；请以本机 `docker compose config --quiet`、构建日志和健康检查结果为准。

## AI 问诊接口

公共接口均经过 Spring Boot，完整前缀为 `http://localhost:8080/hospital`：

| 方法与路径 | 用途 |
| --- | --- |
| `POST /hospital/ai/chat` | 发送消息；`session_id` 可省略以创建会话 |
| `GET /hospital/ai/session/{sessionId}/history` | 获取当前调用者可访问的会话历史 |
| `DELETE /hospital/ai/session/{sessionId}` | 删除当前调用者可访问的会话 |
| `GET /hospital/ai/health` | 检查 Spring 到 FastAPI 的健康链路 |

Windows PowerShell 示例（显式使用 `curl.exe`，避免与 PowerShell 别名混淆）：

```powershell
curl.exe -X POST "http://localhost:8080/hospital/ai/chat" `
  -H "Content-Type: application/json" `
  -d '{"message":"我头疼两天了，应该挂什么科？"}'
```

Linux/macOS 示例：

```bash
curl -X POST 'http://localhost:8080/hospital/ai/chat' \
  -H 'Content-Type: application/json' \
  -d '{"message":"我头疼两天了，应该挂什么科？"}'
```

成功响应由医院统一格式包装，例如：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "session_id": "8b68fcb52cf84f98aa7b428b84ced7da",
    "reply": "根据你描述的情况……",
    "intent": "medical_consultation",
    "confidence": 0.92
  }
}
```

后续请求可带回 `session_id` 延续对话。请求体中的 `user_id` 不会被信任；已认证用户身份由 Spring Security 的认证主体确定。

### 常见 503 排查

HTTP 503 表示 Spring 无法完成上游 AI 调用，按顺序检查：

1. `http://localhost:8000/health` 是否正常；Compose 环境用 `docker compose ps` 和 `docker compose logs chatbot hospital` 检查健康状态。
2. 本地 Spring 的 `CHATBOT_BASE_URL` 是否为 `http://localhost:8000`；Compose 中必须为 `http://chatbot:8000`。
3. `LLM_API_KEY` 是否已设置且有效，DeepSeek 账户是否可用；检查 `LLM_BASE_URL`/`DEEPSEEK_BASE_URL` 与模型名。
4. 防火墙、代理、DNS 或网络是否阻止 FastAPI 访问 `https://api.deepseek.com/v1`。
5. 超时场景可按需要调整 `CHATBOT_CONNECT_TIMEOUT_MS` 和 `CHATBOT_READ_TIMEOUT_MS`，不要通过无限增大超时掩盖上游故障。

## 患者聊天页面

两项服务启动后访问：

<http://localhost:8080/hospital/ai-chat.html>

页面只向同源的 `/hospital/ai/chat` 发送请求，并在浏览器本地保存随机会话 ID。点击“新建会话”会清除当前本地会话引用；需要彻底删除服务端会话时调用对应的 `DELETE` 接口。

## 测试

Python 测试（Windows 与 Linux/macOS 均可在激活虚拟环境后执行）：

```powershell
Push-Location chatbot-service
python -m pytest -q
Pop-Location
```

```bash
(cd chatbot-service && python -m pytest -q)
```

Java、代理、静态页面和部署契约测试：

```bash
mvn test
mvn package -DskipTests
```

完整 `mvn test` 会调用 Node.js 运行 `src/test/resources/ai-chat-page-behavior.test.js`。有 Docker CLI 时，可额外验证 Compose 配置：

```bash
docker compose config --quiet
```

## 医疗免责声明

本系统的 AI 输出仅供一般健康信息与就医导航参考，不构成医疗诊断、处方、检查结论或治疗方案，也不能替代执业医生面诊。模型可能产生不完整或错误内容，请由专业医务人员复核。

若出现胸痛、呼吸困难、意识不清、大出血、抽搐、服毒、自伤风险等紧急症状，请立即拨打当地急救电话或前往最近的急诊，并尽快寻求线下专业救治；不要等待 AI 回复，也不要仅依赖本系统处理紧急情况。

## 安全说明

- 不提交根目录或 `chatbot-service/` 下的 `.env`、API Key、JWT 密钥、真实密码、患者数据或运行日志；仓库只保留空值模板 `.env.example`。
- 匿名会话采用 capability 模式：高熵随机 `session_id` 本身就是访问能力。不要分享、记录到公开日志或使用可猜测的会话 ID。
- 匿名会话在用户登录后首次继续使用时，会在单会话锁内原子绑定到该认证用户；此后匿名调用和其他用户的读、写、删除都返回 404。
- 已认证会话按可信认证用户隔离。Spring 从认证主体生成可信用户标识并用 `AI_PROXY_SECRET` 认证内部请求；FastAPI 不信任缺少正确代理密钥的身份头，且不会在错误中泄露密钥。
- 会话默认 1 小时无活动过期、每个会话保留最近 20 个完整回合、最多保留 10000 个活动会话；可用 `SESSION_TTL_SECONDS`、`MAX_HISTORY_TURNS`、`MAX_ACTIVE_SESSIONS` 调整，容量满时拒绝创建新会话。
- Uvicorn 启动命令禁用 access log，避免 bearer `session_id` 出现在路径日志中；反向代理也必须关闭或脱敏 `/session/{session_id}` 的访问日志。
- `/chat/stream` 为保证模型失败返回 503 且历史按完整回合原子提交，会先完整缓冲有界模型输出再返回，并非逐 token 流式传输。
- AI 控制器启用敏感日志抑制，禁止记录问诊请求/响应正文、Authorization、密钥和患者隐私。新增日志与监控也必须遵守同一规则。
- 生产部署应启用 HTTPS、使用密钥管理服务定期轮换凭据、限制 FastAPI/数据库/Redis 的网络暴露，并根据合规要求设置数据保留和删除策略。
