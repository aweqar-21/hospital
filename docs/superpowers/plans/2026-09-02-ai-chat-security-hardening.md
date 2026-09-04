# AI Chat Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining AI chat ownership, resource-bound, proxy-trust, logging, concurrency, startup, and empty-response findings without changing the buffered `/chat/stream` contract.

**Architecture:** `ConversationManager` will own lifecycle policy and per-session fair async locks. Routes will execute ownership claim/migration, history read, model work, validation, and atomic turn commit inside one session transaction, rolling back newly-created empty sessions on failure. Spring will authenticate its internal requests with a shared proxy secret; FastAPI will trust identity-bearing headers only when that secret matches in constant time.

**Tech Stack:** Python 3.14, FastAPI, asyncio, pytest/httpx, Java 8 source target, Spring Boot/RestTemplate, JUnit 4, Docker Compose.

---

### Task 1: Bounded, expiring conversation state

**Files:**
- Modify: `chatbot-service/config/settings.py`
- Modify: `chatbot-service/core/conversation_manager.py`
- Test: `chatbot-service/tests/test_conversation/test_conversation.py`

- [ ] Write focused tests proving production get/create/delete paths evict expired sessions and their lock entries, history is trimmed to `MAX_HISTORY_TURNS * 2`, capacity rejects instead of evicting live sessions, and failed reservations can be removed safely.
- [ ] Run the focused tests and confirm failures specifically show missing automatic cleanup, bounds, and capacity behavior.
- [ ] Add validated `MAX_ACTIVE_SESSIONS`; centralize cleanup, capacity checks, history trimming, and lock lifecycle in `ConversationManager`.
- [ ] Re-run focused tests and the conversation suite until green.

### Task 2: Atomic ownership upgrade and serialized turns

**Files:**
- Modify: `chatbot-service/api/routes.py`
- Modify: `chatbot-service/core/conversation_manager.py`
- Test: `chatbot-service/tests/test_api.py`

- [ ] Write API tests proving anonymous-to-authenticated migration revokes anonymous/other-user access, racing authenticated claimers yield one owner, same-session turns serialize and see prior committed history, different sessions remain concurrent, and failed first calls leave no empty session.
- [ ] Run those tests and observe the expected ownership/concurrency/rollback failures.
- [ ] Implement an async session transaction using a FIFO waiter queue; run ownership claim/migration, model/RAG work, output validation, and commit while holding it; remove only the failed request's new empty session.
- [ ] Re-run focused tests and all Python tests.

### Task 3: Trusted proxy boundary

**Files:**
- Modify: `chatbot-service/config/settings.py`
- Modify: `chatbot-service/api/dependencies.py`
- Modify: `chatbot-service/api/routes.py`
- Modify: `src/main/java/cn/yujian95/hospital/config/AiChatProperties.java`
- Modify: `src/main/java/cn/yujian95/hospital/service/impl/AiChatServiceImpl.java`
- Modify: `src/main/resources/application.yml`
- Test: `chatbot-service/tests/test_api.py`
- Test: `src/test/java/cn/yujian95/hospital/service/AiChatServiceImplTest.java`

- [ ] Write failing tests proving identity headers are ignored without a correct proxy secret, accepted with it, comparisons use the intended authentication path, and Spring attaches the secret to every identity-bearing upstream call without sending browser bearer tokens.
- [ ] Run focused Python and Java tests to confirm RED.
- [ ] Add `AI_PROXY_SECRET`, validate it with `hmac.compare_digest`, reject untrusted identity-bearing requests with a generic response, and make Spring send `X-AI-Proxy-Secret` while no longer forwarding `Authorization`.
- [ ] Re-run focused Python and Java tests.

### Task 4: Deployment and logging contract

**Files:**
- Modify: `docker-compose.yml`
- Modify: `chatbot-service/docker-compose.yml`
- Modify: `.env.example`
- Modify: `chatbot-service/.env.example`
- Modify: `chatbot-service/Dockerfile`
- Modify: `chatbot-service/main.py`
- Modify: `chatbot-service/scripts/bootstrap.py`
- Modify: `README.md`
- Modify: `chatbot-service/README.md`
- Test: `src/test/java/cn/yujian95/hospital/DeploymentConfigTest.java`
- Test: `src/test/java/cn/yujian95/hospital/ReadmeDocumentationTest.java`
- Test: `chatbot-service/tests/test_settings.py`

- [ ] Write deployment contract tests requiring a non-empty Compose proxy secret injected into both services, empty examples, loopback-only child ports, restricted CORS, `--no-access-log`, port 8000, and no production reload.
- [ ] Run the focused tests and confirm RED against current Compose/start commands.
- [ ] Update configuration, deployment files, launchers, and documentation; explicitly document buffered stream semantics and session resource limits.
- [ ] Re-run focused tests.

### Task 5: Verification, self-review, and commit

**Files:**
- Review all modified files.

- [ ] Run Ruff and the complete Python suite with `chatbot-service/.venv/Scripts/python.exe`.
- [ ] Run the complete Maven suite and package using `C:/Users/12259/.jdks/ms-21.0.8` and the specified Maven binary.
- [ ] Inspect `git diff --check`, secret-pattern scans, deployment contracts, and the full diff against every finding.
- [ ] Commit all reviewed changes and report the commit SHA plus exact RED/GREEN evidence and test totals.
