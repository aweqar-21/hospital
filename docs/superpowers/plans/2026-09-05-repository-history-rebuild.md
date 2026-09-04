# Repository History Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the hospital repository as a verified clean snapshot authored by AWEQAR_21, publish it to newly created GitHub and Gitee repositories, and leave only `hospital` and `GYM_lifu` on both platforms.

**Architecture:** The existing working repository remains the source of truth while a separate staging directory receives only publishable files. The staging directory is initialized as a new Git repository with one root commit, tested, pushed to newly created remotes, and then used to replace the local current-history view. Remote cleanup occurs last, after both retained projects are verified.

**Tech Stack:** Git, PowerShell, Maven/Spring Boot, Python/pytest, browser-use, GitHub, Gitee

---

### Task 1: Freeze and audit the publishable source

**Files:**
- Inspect: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/.gitignore`
- Inspect: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/src/main/resources/application.yml`
- Inspect: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/src/main/java/cn/yujian95/hospital/controller/HealthController.java`
- Exclude: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/doc/Chatbot-计科2304班-22450150619-马振楠.docx`

- [ ] **Step 1: Record the working-tree inventory**

Run:

```powershell
git status --short --ignored
git ls-files
```

Expected: the application changes are visible; `.env`, runtime data, build output, and the personal Word document are identifiable and will not be included in the snapshot.

- [ ] **Step 2: Scan candidate files for secrets**

Run:

```powershell
$patterns = 'sk-[A-Za-z0-9_-]{16,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|password\s*[:=]|api[_-]?key\s*[:=]|access[_-]?token\s*[:=]'
git grep -Il -E $patterns
rg -l -i $patterns src/main/resources/application.yml src/main/java/cn/yujian95/hospital/controller/HealthController.java
```

Expected: no DeepSeek API key, password, token, private key, runtime database file, or personal Word document is selected for publication.

- [ ] **Step 3: Verify author-facing source metadata**

Run:

```powershell
rg -n -i '@author\s+(YuJian95|yujian|chenlijian)|clj9509@163\.com|yujian95_cn@163\.com|blog\.yujian95\.cn' src/main/java pom.xml chatbot-service/pyproject.toml
```

Expected: no legacy author annotation, legacy email, or legacy author blog remains in the maintained metadata.

### Task 2: Verify the current application before snapshotting

**Files:**
- Test: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/src/test/java/cn/yujian95/hospital/AuthorMetadataTest.java`
- Test: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/src/test/java/cn/yujian95/hospital/AiChatPageTest.java`
- Test: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/chatbot-service/tests/`

- [ ] **Step 1: Run the Java suite**

Run:

```powershell
mvn test
```

Expected: all Maven tests pass with zero failures and zero errors.

- [ ] **Step 2: Run the chatbot suite**

Run:

```powershell
Push-Location chatbot-service
& .\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

Expected: all pytest tests pass.

- [ ] **Step 3: Run local smoke checks**

Start the isolated MySQL service on port `3307`, FastAPI chatbot service on port `8001`, and Spring application on port `8080` using the local `.env` values without printing them. Run:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8080/hospital/ai/health'
$body = @{ message = '你好，请简要说明感冒患者何时应及时就医'; sessionId = 'repository-rebuild-smoke' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8080/hospital/ai/chat' -ContentType 'application/json' -Body $body
```

Expected: health returns success and chat returns a non-empty model response without exposing credentials in logs.

### Task 3: Build and validate the clean hospital snapshot

**Files:**
- Create: `%TEMP%/hospital-clean-<generated-guid>/`
- Preserve: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/`

- [ ] **Step 1: Export publishable files**

Run:

```powershell
$source = 'C:\Users\12259\Desktop\AWEQAR\Dev\hospital_fd\hospital'
$stage = Join-Path $env:TEMP ('hospital-clean-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
git -C $source ls-files | ForEach-Object {
    $destination = Join-Path $stage $_
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $source $_) -Destination $destination
}
$health = 'src\main\java\cn\yujian95\hospital\controller\HealthController.java'
$healthDestination = Join-Path $stage $health
New-Item -ItemType Directory -Path (Split-Path $healthDestination) -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source $health) -Destination $healthDestination
```

Expected: a file-list comparison shows every intended source file and none of the excluded artifacts.

- [ ] **Step 2: Initialize the new history**

Run in the staging directory:

```powershell
git init -b master
git config user.name AWEQAR_21
git config user.email aweqar1225918785@gmail.com
git add --all
git commit -m "feat: publish hospital AI consultation system"
```

Expected: exactly one root commit exists and both author and committer use the requested identity.

- [ ] **Step 3: Verify blame and tests in staging**

Run:

```powershell
git rev-list --count HEAD
git log -1 --format='%an <%ae>|%cn <%ce>'
git blame --line-porcelain src/main/java/cn/yujian95/hospital/HospitalApplication.java | Select-String '^author '
mvn test
```

Then run:

```powershell
Push-Location (Join-Path $stage 'chatbot-service')
& 'C:\Users\12259\Desktop\AWEQAR\Dev\hospital_fd\hospital\chatbot-service\.venv\Scripts\python.exe' -m pytest -q
Pop-Location
```

Expected: commit count is `1`, every blame author is `AWEQAR_21`, the Gmail address is correct, and all tests pass.

### Task 4: Recreate and publish retained repositories

**Files:**
- Inspect: `C:/Users/12259/Desktop/AWEQAR/Dev/GYM_lifu/gym-management-system/.git/config`
- Update: clean hospital staging repository remote configuration

- [ ] **Step 1: Inventory authenticated repositories**

Use the headed `AWEQAR` browser profile to list every repository owned by `aweqar-21` on GitHub and `AWEQAR33` on Gitee. Record visibility and exact repository names.

Expected: the final preserve/delete list is exact, including private repositories.

- [ ] **Step 2: Normalize the gym repository**

Confirm the local gym repository matches the retained remote. On Gitee, rename `力夫健身房` / `lifu-gym` to the exact repository name and path `GYM_lifu`. On GitHub, retain the existing `GYM_lifu` repository if it verifies against the local project.

Expected: both platforms expose a working `GYM_lifu` repository before any unrelated deletion.

- [ ] **Step 3: Recreate hospital repositories**

Delete the old `hospital` repository on each platform, immediately create a new empty public repository named `hospital`, and do not initialize it with generated files.

Expected: both new repository pages exist and contain no old commit history.

- [ ] **Step 4: Push the clean snapshot**

Configure the new GitHub and Gitee URLs as separate remotes and push `master` to both.

Expected: both platforms show the single root commit authored by `AWEQAR_21` and contain the README, Java service, chatbot service, and direct-use chat page.

- [ ] **Step 5: Delete all non-retained repositories**

Delete only repositories whose exact names are not `hospital` or `GYM_lifu` from each authenticated owner account.

Expected: each platform's authenticated repository list contains exactly those two names.

### Task 5: Replace local history and perform final verification

**Files:**
- Replace Git metadata for: `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/hospital/`
- Create: a recoverable local Git metadata backup outside the project directory until verification completes

- [ ] **Step 1: Back up and replace local Git metadata**

Stop application processes using the project only if they lock files. Back up the current `.git` directory to a uniquely named directory under `C:/Users/12259/Desktop/AWEQAR/Dev/hospital_fd/`, copy the verified staging `.git` into the hospital project, and confirm the working tree is clean except for the excluded personal Word document.

Expected: IntelliJ reads the clean root history from the original hospital project path and the previous Git metadata remains locally recoverable.

- [ ] **Step 2: Verify both remote heads**

Run:

```powershell
git ls-remote origin refs/heads/master
git ls-remote gitee refs/heads/master
git log -1 --format='%H|%an|%ae|%s'
git blame src/main/java/cn/yujian95/hospital/HospitalApplication.java
```

Expected: both remote hashes equal local `HEAD`, and all current lines blame to `AWEQAR_21`.

- [ ] **Step 3: Re-run clean-project verification**

Run Maven tests, chatbot pytest tests, health check, and one AI chat smoke test from the final local path.

Expected: the clean local repository remains fully functional.

- [ ] **Step 4: Document the self-service author procedure in the handoff**

Explain the difference between source `@author`, Git identity for future commits, amending the most recent commit, and rebuilding/re-writing older history. Include commands for setting `user.name`, setting `user.email`, checking `git log`, and checking `git blame`, with a warning that changing published history requires a coordinated force push.

Expected: the final handoff gives the user repeatable commands without exposing credentials or encouraging accidental history loss.
