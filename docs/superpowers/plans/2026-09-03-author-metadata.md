# Author Metadata Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace current-file legacy author metadata with `AWEQAR_21 <aweqar1225918785@gmail.com>` without rewriting Git history or changing Java package names.

**Architecture:** A repository contract test scans current source and project metadata for legacy attribution and verifies the new maintainer identity. A mechanical replacement updates comments and metadata only; build identifiers and historical commits remain untouched for compatibility and truthful attribution.

**Tech Stack:** Java 8, JUnit 4, Maven, Python `pyproject.toml`, Git, PowerShell

---

### Task 1: Add the author metadata contract

**Files:**
- Create: `src/test/java/cn/yujian95/hospital/AuthorMetadataTest.java`

- [ ] **Step 1: Write the failing contract test**

Create a JUnit 4 test that recursively reads `src/main/java`, plus `pom.xml` and `chatbot-service/pyproject.toml`. It must assert:

```java
private static final String AUTHOR = "AWEQAR_21";
private static final String EMAIL = "aweqar1225918785@gmail.com";

assertFalse(content.contains("clj9509@163.com"));
assertFalse(content.contains("yujian95_cn@163.com"));
assertFalse(content.contains("blog.yujian95.cn"));
assertFalse(content.matches("(?s).*@author\\s+(?:YuJian95|yujian|chenlijian).*"));
assertTrue(javaSources.contains("@author " + AUTHOR + " " + EMAIL));
assertTrue(pyproject.contains("{name = \"AWEQAR_21\", email = \"aweqar1225918785@gmail.com\"}"));
assertTrue(pom.contains("<url>https://github.com/aweqar-21/hospital</url>"));
```

The recursive scan must include the working-tree `HealthController.java` if it exists, while the commit step must not stage that pre-existing untracked file.

- [ ] **Step 2: Run the test and verify RED**

Run with repository-local Git identity already set to the new maintainer:

```powershell
$env:JAVA_HOME='C:\Users\12259\.jdks\ms-21.0.8'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
& 'C:\Users\12259\.m2\wrapper\dists\apache-maven-3.9.15-bin\4rlcemksed9vjmkvgss0jpc4po\apache-maven-3.9.15\bin\mvn.cmd' -Dtest=AuthorMetadataTest test
```

Expected: FAIL because current Java comments, Maven URL, and Python author metadata still contain legacy values.

- [ ] **Step 3: Commit the RED test separately**

```powershell
git add src/test/java/cn/yujian95/hospital/AuthorMetadataTest.java
git commit -m "test: define author metadata contract"
```

### Task 2: Replace current metadata and publish

**Files:**
- Modify: `src/main/java/**/*.java`
- Modify: `src/main/java/cn/yujian95/hospital/controller/HealthController.java` only in the working tree; do not stage it
- Modify: `chatbot-service/pyproject.toml`
- Modify: `pom.xml`

- [ ] **Step 1: Apply the minimal metadata replacement**

Mechanically rewrite every Java source `@author` line to:

```java
 * @author AWEQAR_21 aweqar1225918785@gmail.com
```

Set Python project metadata to:

```toml
authors = [
    {name = "AWEQAR_21", email = "aweqar1225918785@gmail.com"}
]
```

Set Maven project URL to:

```xml
<url>https://github.com/aweqar-21/hospital</url>
```

Do not rename `cn.yujian95.hospital`, Maven `groupId`, directories, imports, database objects, or Git history.

- [ ] **Step 2: Run the focused test and verify GREEN**

Run:

```powershell
& 'C:\Users\12259\.m2\wrapper\dists\apache-maven-3.9.15-bin\4rlcemksed9vjmkvgss0jpc4po\apache-maven-3.9.15\bin\mvn.cmd' -Dtest=AuthorMetadataTest test
```

Expected: the author contract passes.

- [ ] **Step 3: Run full verification**

Run:

```powershell
& 'C:\Users\12259\.m2\wrapper\dists\apache-maven-3.9.15-bin\4rlcemksed9vjmkvgss0jpc4po\apache-maven-3.9.15\bin\mvn.cmd' clean test
& 'C:\Users\12259\.m2\wrapper\dists\apache-maven-3.9.15-bin\4rlcemksed9vjmkvgss0jpc4po\apache-maven-3.9.15\bin\mvn.cmd' package -DskipTests
rg -n -i '@author\\s+(YuJian95|yujian|chenlijian)|clj9509@163\\.com|yujian95_cn@163\\.com|blog\\.yujian95\\.cn' src/main/java pom.xml chatbot-service/pyproject.toml
git diff --check
```

Expected: all tests and packaging pass; `rg` returns no legacy author match; diff check is clean.

- [ ] **Step 4: Commit only intended tracked metadata**

```powershell
git add pom.xml chatbot-service/pyproject.toml
git add --update src/main/java
git commit -m "chore: update project author metadata"
```

Before committing, verify `application.yml` and `HealthController.java` remain outside the index.

- [ ] **Step 5: Push without rewriting history**

```powershell
git push origin master
```

Update Gitee through its authenticated repository synchronization flow or a normal `git push gitee master` when credentials are available. Never use `--force`. Verify both public branch APIs point to local `git rev-parse HEAD`.
