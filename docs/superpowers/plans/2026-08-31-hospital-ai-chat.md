# Hospital AI Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the existing FastAPI DeepSeek chatbot into the hospital repository and expose a safe, patient-facing AI consultation page through the Spring Boot service.

**Architecture:** Keep Spring Boot as the public entry point and place the Python application in `chatbot-service/` as an internal sidecar. Spring validates and proxies `/ai/*` requests to FastAPI, while a static browser client calls only the hospital origin. FastAPI owns medical prompting, emergency triage, conversation state, and DeepSeek access.

**Tech Stack:** Java 8, Spring Boot 2.1.6, RestTemplate, JUnit/MockMvc, Python 3.10+, FastAPI, Pydantic 2, pytest, OpenAI-compatible DeepSeek API, Docker Compose, native HTML/CSS/JavaScript.

---

## File map

- `chatbot-service/`: copied Python service, with hospital-specific safety and configuration changes.
- `chatbot-service/core/medical_safety.py`: deterministic emergency phrase detection.
- `chatbot-service/core/context_builder.py`: medical consultation system prompt.
- `chatbot-service/api/routes.py`: validated API flow and structured upstream failures.
- `src/main/java/cn/yujian95/hospital/config/AiChatProperties.java`: chatbot URL and timeout configuration.
- `src/main/java/cn/yujian95/hospital/config/AiChatConfig.java`: configured `RestTemplate` bean.
- `src/main/java/cn/yujian95/hospital/dto/ai/`: external request/response DTOs.
- `src/main/java/cn/yujian95/hospital/service/AiChatService.java`: proxy boundary.
- `src/main/java/cn/yujian95/hospital/service/impl/AiChatServiceImpl.java`: internal HTTP calls and error mapping.
- `src/main/java/cn/yujian95/hospital/controller/AiChatController.java`: public `/ai/*` API.
- `src/main/resources/static/ai-chat.html`: patient chat client.
- `docker-compose.yml`, `.env.example`: local two-service deployment.
- `README.md`: complete combined-project documentation.

### Task 1: Import the chatbot without local artifacts or secrets

**Files:**
- Create: `chatbot-service/**`
- Modify: `.gitignore`

- [ ] **Step 1: Copy only source-controlled chatbot content**

Run from the hospital repository in PowerShell:

```powershell
$source = 'C:\Users\12259\Desktop\AWEQAR\Dev\Python\chatbot'
$destination = Join-Path (Get-Location) 'chatbot-service'
New-Item -ItemType Directory -Force $destination | Out-Null
robocopy $source $destination /E /XD .git .venv venv __pycache__ .pytest_cache data logs chatbot.egg-info /XF .env *.pyc *.log
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }
```

Expected: Python source, tests, static assets, `pyproject.toml`, and Dockerfile exist under `chatbot-service/`; `.env` and generated data do not.

- [ ] **Step 2: Extend root ignore rules**

Add these exact rules to `.gitignore`:

```gitignore
/target/
**/__pycache__/
**/*.py[cod]
**/*.egg-info/
**/.pytest_cache/
**/.env
!**/.env.example
/chatbot-service/.venv/
/chatbot-service/venv/
/chatbot-service/data/
/chatbot-service/logs/
```

- [ ] **Step 3: Verify excluded files**

Run:

```powershell
git status --short
git check-ignore chatbot-service/.env chatbot-service/data/vector_store/chroma.sqlite3 target
```

Expected: imported source is untracked; all three sensitive/generated paths are reported as ignored.

- [ ] **Step 4: Commit the import**

```powershell
git add .gitignore chatbot-service
git commit -m "chore: merge chatbot service into hospital"
```

### Task 2: Add deterministic medical safety behavior

**Files:**
- Create: `chatbot-service/tests/test_medical_safety.py`
- Create: `chatbot-service/core/medical_safety.py`
- Modify: `chatbot-service/core/context_builder.py`

- [ ] **Step 1: Write failing emergency and prompt tests**

```python
from core.context_builder import SYSTEM_PROMPT
from core.medical_safety import emergency_reply, is_emergency


def test_detects_emergency_symptom():
    assert is_emergency("突然胸痛而且呼吸困难") is True


def test_does_not_flag_routine_question():
    assert is_emergency("轻微感冒应该挂什么科") is False


def test_emergency_reply_directs_patient_to_urgent_help():
    reply = emergency_reply()
    assert "立即" in reply
    assert "急诊" in reply or "急救" in reply


def test_system_prompt_sets_medical_limits():
    assert "不能替代医生" in SYSTEM_PROMPT
    assert "建议科室" in SYSTEM_PROMPT
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_medical_safety.py -q` from `chatbot-service/`.

Expected: collection fails because `core.medical_safety` does not exist.

- [ ] **Step 3: Implement the minimal safety module**

```python
EMERGENCY_TERMS = (
    "胸痛", "呼吸困难", "喘不上气", "意识不清", "昏迷",
    "大出血", "抽搐", "服毒", "自杀", "自伤",
)


def is_emergency(message: str) -> bool:
    normalized = message.strip().lower()
    return any(term in normalized for term in EMERGENCY_TERMS)


def emergency_reply() -> str:
    return (
        "你描述的情况可能属于医疗急症。请立即拨打当地急救电话或前往最近的急诊，"
        "不要等待 AI 回复，也不要自行驾车。若身边有人，请让对方陪同并告知医护人员当前症状。"
    )
```

Replace `SYSTEM_PROMPT` with a Chinese medical assistant prompt that explicitly requires: no definitive diagnosis or prescription; concise symptom summary; likely causes expressed as possibilities; suggested department; urgency; next steps; and immediate escalation for emergencies.

- [ ] **Step 4: Run safety tests and full Python tests**

Run:

```powershell
python -m pytest tests/test_medical_safety.py -q
python -m pytest -q
```

Expected: all tests pass without warnings caused by the new behavior.

- [ ] **Step 5: Commit**

```powershell
git add chatbot-service/core chatbot-service/tests/test_medical_safety.py
git commit -m "feat: add medical consultation safety rules"
```

### Task 3: Make the FastAPI consultation flow reliable

**Files:**
- Modify: `chatbot-service/api/schemas.py`
- Modify: `chatbot-service/api/routes.py`
- Modify: `chatbot-service/config/settings.py`
- Modify: `chatbot-service/knowledge/knowledge_retriever.py`
- Modify: `chatbot-service/tests/test_api.py`
- Create: `chatbot-service/.env.example`

- [ ] **Step 1: Write failing API behavior tests**

Add dependency overrides so tests do not call DeepSeek, then add:

```python
@pytest.mark.asyncio
async def test_chat_rejects_blank_message(client):
    response = await client.post("/chat", json={"message": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_emergency_chat_does_not_call_llm(client, fake_responder):
    response = await client.post("/chat", json={"message": "我现在胸痛呼吸困难"})
    assert response.status_code == 200
    assert "立即" in response.json()["reply"]
    assert fake_responder.calls == 0


@pytest.mark.asyncio
async def test_chat_returns_503_when_llm_fails(client, failing_responder):
    response = await client.post("/chat", json={"message": "头疼怎么办"})
    assert response.status_code == 503
    assert response.json()["detail"] == "AI 问诊服务暂时不可用，请稍后重试"
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest tests/test_api.py -q`.

Expected: blank whitespace is accepted, emergency routing calls the responder, or LLM failures return HTTP 200.

- [ ] **Step 3: Implement validation, emergency short-circuit, and error mapping**

Use a Pydantic validator to reject whitespace-only messages. In `/chat`, call `is_emergency(req.message)` before intent/RAG work and return `ChatResponse` with `intent="medical_emergency"`, `confidence=1.0`. Convert `LLMError` to:

```python
raise HTTPException(
    status_code=503,
    detail="AI 问诊服务暂时不可用，请稍后重试",
) from exc
```

Add `ENABLE_RAG: bool = False` to settings. Only instantiate and call the knowledge retriever when `ENABLE_RAG` is true; otherwise continue through DeepSeek without embeddings.

Create `.env.example` containing non-secret defaults:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=
ENABLE_RAG=false
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
API_HOST=0.0.0.0
API_PORT=8000
```

- [ ] **Step 4: Run API and full tests**

Run:

```powershell
python -m pytest tests/test_api.py -q
python -m pytest -q
```

Expected: all tests pass without making a real external API request.

- [ ] **Step 5: Commit**

```powershell
git add chatbot-service
git commit -m "feat: harden DeepSeek consultation API"
```

### Task 4: Add the Spring chatbot client and proxy API

**Files:**
- Modify: `pom.xml`
- Modify: `src/main/resources/application.yml`
- Create: `src/main/java/cn/yujian95/hospital/config/AiChatProperties.java`
- Create: `src/main/java/cn/yujian95/hospital/config/AiChatConfig.java`
- Create: `src/main/java/cn/yujian95/hospital/dto/ai/AiChatRequest.java`
- Create: `src/main/java/cn/yujian95/hospital/dto/ai/AiChatResponse.java`
- Create: `src/main/java/cn/yujian95/hospital/service/AiChatService.java`
- Create: `src/main/java/cn/yujian95/hospital/service/impl/AiChatServiceImpl.java`
- Create: `src/main/java/cn/yujian95/hospital/controller/AiChatController.java`
- Create: `src/test/java/cn/yujian95/hospital/controller/AiChatControllerTest.java`
- Create: `src/test/java/cn/yujian95/hospital/service/AiChatServiceImplTest.java`

- [ ] **Step 1: Add test dependencies and write failing controller tests**

Use Spring Boot's existing test starter and remove obsolete `mockito-all`, which conflicts with modern Mockito. Test the controller directly with MockMvc standalone setup:

```java
@RunWith(MockitoJUnitRunner.class)
public class AiChatControllerTest {
    @Mock private AiChatService aiChatService;
    private MockMvc mvc;

    @Before
    public void setUp() {
        mvc = MockMvcBuilders.standaloneSetup(new AiChatController(aiChatService)).build();
    }

    @Test
    public void rejectsBlankMessage() throws Exception {
        mvc.perform(post("/ai/chat").contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"   \"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    public void returnsChatbotResponse() throws Exception {
        when(aiChatService.chat(any(AiChatRequest.class), anyString()))
                .thenReturn(new AiChatResponse("session-1", "建议前往内科就诊", "medical", 0.9));
        mvc.perform(post("/ai/chat").contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"我头疼\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.session_id").value("session-1"));
    }
}
```

- [ ] **Step 2: Run controller tests and confirm RED**

Run: `mvn -Dtest=AiChatControllerTest test`.

Expected: compilation fails because the AI controller, DTO, and service do not exist.

- [ ] **Step 3: Implement DTOs, configuration, service boundary, and controller**

`AiChatRequest` contains `session_id`, `user_id`, and a `@NotBlank @Size(max=4096) message`. `AiChatResponse` contains `session_id`, `reply`, `intent`, and `confidence`, with Jackson-compatible constructors and accessors.

The service interface is:

```java
public interface AiChatService {
    AiChatResponse chat(AiChatRequest request, String authorization);
    Object history(String sessionId, String authorization);
    Object deleteSession(String sessionId, String authorization);
    Object health();
}
```

`AiChatProperties` binds `hospital.ai.base-url`, `connect-timeout-ms`, and `read-timeout-ms`. `AiChatConfig` creates a `RestTemplate` using `SimpleClientHttpRequestFactory` with those timeouts. The implementation forwards `Authorization` and derives an `X-User-Id` only when a trusted authenticated principal is available; it maps connection, timeout, and upstream 5xx errors to an `AiChatUnavailableException` handled as HTTP 503.

The controller uses `@Valid`, returns `CommonResult.success(...)`, and exposes POST chat, GET history, DELETE session, and GET health under `/ai`.

Add non-secret configuration:

```yaml
hospital:
  ai:
    base-url: ${CHATBOT_BASE_URL:http://localhost:8000}
    connect-timeout-ms: ${CHATBOT_CONNECT_TIMEOUT_MS:3000}
    read-timeout-ms: ${CHATBOT_READ_TIMEOUT_MS:60000}
```

- [ ] **Step 4: Write and run service error-mapping tests**

Use `MockRestServiceServer` to assert the exact `/chat` request and simulate 503:

```java
server.expect(requestTo("http://localhost:8000/chat"))
      .andExpect(method(HttpMethod.POST))
      .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));

assertThrows(AiChatUnavailableException.class,
        () -> service.chat(new AiChatRequest(null, null, "头疼"), null));
```

Run: `mvn -Dtest=AiChatControllerTest,AiChatServiceImplTest test`.

Expected: all AI Java tests pass.

- [ ] **Step 5: Run the full Java test suite and commit**

```powershell
mvn test
git add pom.xml src/main/java src/main/resources/application.yml src/test
git commit -m "feat: expose AI consultation through hospital API"
```

Expected: Maven exits 0; only intended Java/config files enter the commit.

### Task 5: Add the patient chat page and anonymous access

**Files:**
- Create: `src/main/resources/static/ai-chat.html`
- Modify: `src/main/resources/application.yml`
- Create: `src/test/java/cn/yujian95/hospital/AiChatPageTest.java`

- [ ] **Step 1: Write a failing static-page contract test**

```java
public class AiChatPageTest {
    @Test
    public void pageContainsSafetyAndApiContract() throws Exception {
        String html = new String(Files.readAllBytes(
                Paths.get("src/main/resources/static/ai-chat.html")), StandardCharsets.UTF_8);
        assertTrue(html.contains("AI 健康咨询"));
        assertTrue(html.contains("不能替代医生"));
        assertTrue(html.contains("/ai/chat"));
        assertTrue(html.contains("新建会话"));
    }
}
```

- [ ] **Step 2: Run the page test and confirm RED**

Run: `mvn -Dtest=AiChatPageTest test`.

Expected: failure because `ai-chat.html` does not exist.

- [ ] **Step 3: Implement the page**

Create one self-contained semantic HTML document with embedded CSS and JavaScript. It must:

- Render a header, medical disclaimer, scrollable message region, textarea, send button, and new-session button.
- Store only `hospitalAiSessionId` in `localStorage`.
- POST `{session_id, message}` to a context-path-safe `ai/chat` URL.
- Reuse an existing `Authorization` value if the hospital client already stores one, without displaying it.
- Disable sending while waiting, submit with Enter, allow Shift+Enter for a newline, escape all reply text with `textContent`, and show a retryable error bubble.
- Use a mobile breakpoint and no external CDN assets.

Add `/ai/**`, `/ai-chat.html`, and `/` static resources needed by this page to the existing anonymous allow-list.

- [ ] **Step 4: Run tests and inspect the page locally**

Run:

```powershell
mvn -Dtest=AiChatPageTest,AiChatControllerTest test
mvn package -DskipTests
```

Expected: tests and packaging exit 0. Start the service and open `http://localhost:8080/hospital/ai-chat.html`; verify desktop and narrow-window layouts, message submission, loading state, and new session.

- [ ] **Step 5: Commit**

```powershell
git add src/main/resources/static/ai-chat.html src/main/resources/application.yml src/test/java/cn/yujian95/hospital/AiChatPageTest.java
git commit -m "feat: add patient AI consultation page"
```

### Task 6: Add unified local deployment

**Files:**
- Modify: `chatbot-service/Dockerfile`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Write the deployment contract before configuration**

The root Compose contract is exactly two application services plus optional infrastructure already required by the hospital project:

```text
hospital -> http://chatbot:8000
chatbot  -> https://api.deepseek.com/v1
browser  -> http://localhost:8080/hospital/ai-chat.html
```

No API key appears in an image layer or committed file.

- [ ] **Step 2: Implement Dockerfiles and Compose**

The Java Dockerfile uses a Maven build stage and a JRE 8 runtime stage. Compose builds the root hospital service and `./chatbot-service`, injects `CHATBOT_BASE_URL=http://chatbot:8000`, loads root `.env`, exposes hospital port 8080, exposes chatbot only to the internal Compose network, and defines HTTP health checks for both services.

Root `.env.example` contains:

```dotenv
LLM_API_KEY=
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com/v1
ENABLE_RAG=false
CHATBOT_BASE_URL=http://chatbot:8000
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_DATABASE=hospital
MYSQL_USERNAME=root
MYSQL_PASSWORD=
REDIS_HOST=host.docker.internal
REDIS_PORT=6379
```

- [ ] **Step 3: Validate deployment configuration**

Run:

```powershell
docker compose config --quiet
docker build -t hospital-local .
docker build -t hospital-chatbot-local .\chatbot-service
```

Expected: all commands exit 0 and no secret is printed or embedded.

- [ ] **Step 4: Commit**

```powershell
git add Dockerfile docker-compose.yml .env.example chatbot-service/Dockerfile
git commit -m "build: add unified hospital deployment"
```

### Task 7: Replace README with combined project documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the README acceptance checklist**

The README must contain these literal section headings:

```text
项目简介
系统架构
项目结构
环境要求
DeepSeek 配置
本地启动
Docker Compose 启动
AI 问诊接口
患者聊天页面
测试
医疗免责声明
安全说明
```

- [ ] **Step 2: Rewrite README**

Document exact Windows and Unix commands, MySQL import using `src/main/resources/hospital.sql`, Redis expectations, `.env.example` copying, DeepSeek variables, separate Java/Python startup, Compose startup, the four `/ai/*` endpoints, a curl example, page URL, test commands, common 503 troubleshooting, and the rule that AI output is not diagnosis or emergency care.

- [ ] **Step 3: Verify all commands and paths named in README exist**

Run:

```powershell
$required = '项目简介','系统架构','项目结构','环境要求','DeepSeek 配置','本地启动','Docker Compose 启动','AI 问诊接口','患者聊天页面','测试','医疗免责声明','安全说明'
$readme = Get-Content -Raw README.md
$missing = $required | Where-Object { $readme -notmatch [regex]::Escape($_) }
if ($missing) { throw "README missing: $($missing -join ', ')" }
Test-Path chatbot-service\.env.example
Test-Path src\main\resources\static\ai-chat.html
```

Expected: no missing section and both path checks return `True`.

- [ ] **Step 4: Commit**

```powershell
git add README.md
git commit -m "docs: document hospital AI consultation setup"
```

### Task 8: Final verification and dual-remote publication

**Files:**
- Inspect: all tracked files
- Modify only if verification exposes a defect.

- [ ] **Step 1: Run fresh full verification**

```powershell
Push-Location chatbot-service
python -m pytest -q
Pop-Location
mvn clean test
mvn package -DskipTests
docker compose config --quiet
git diff --check HEAD~1 HEAD
```

Expected: every command exits 0, with zero failed tests.

- [ ] **Step 2: Audit repository contents for secrets and artifacts**

```powershell
git ls-files | rg '(^|/)(\.env|target|data|logs|__pycache__|.*\.sqlite3)(/|$)'
git grep -n -E 'sk-[A-Za-z0-9_-]{16,}|LLM_API_KEY=.+|password:[[:space:]]*[^$<{[:space:]]+'
git status --short
```

Expected: no real key, password, generated data, or build artifact is tracked. Only known pre-existing user changes may remain outside the completed commits.

- [ ] **Step 3: Resolve GitHub and Gitee targets without overwriting history**

```powershell
gh auth status
gh repo view hospital
git remote -v
```

Use the authenticated GitHub account. If `hospital` does not exist, run `gh repo create hospital --public --source . --remote github`; otherwise add its exact URL as `github`. For Gitee, use an installed/authenticated CLI or the user's configured HTTPS/SSH identity to query first; create `hospital` only when absent, then add its exact URL as `gitee`. Never force-push.

- [ ] **Step 4: Push and verify both remotes**

```powershell
git push -u github master
git push -u gitee master
git ls-remote --heads github master
git ls-remote --heads gitee master
```

Expected: both pushes succeed and both remote `master` hashes equal local `git rev-parse HEAD`.

- [ ] **Step 5: Report delivery**

Provide the local repository path, page URL, startup commands, exact test counts, final commit hash, GitHub URL, Gitee URL, and any preserved pre-existing local changes.
