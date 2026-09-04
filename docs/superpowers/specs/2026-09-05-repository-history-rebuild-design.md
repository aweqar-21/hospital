# Repository History Rebuild Design

## Goal

Publish the current working hospital application to newly created `hospital`
repositories on GitHub and Gitee, make the current snapshot commit use
`AWEQAR_21 <aweqar1225918785@gmail.com>`, and leave only `hospital` and
`GYM_lifu` in both hosting accounts.

## Current state

- The Java source comments already use `AWEQAR_21` and the Gmail address.
- IntelliJ still shows `Yujian95` in line annotations because those lines were
  last changed by commits in the imported Git history.
- The hospital working tree contains local runtime changes that must be
  reviewed and included deliberately.
- Secret `.env` files, runtime database data, vector data, logs, and the
  personal Word document must not be published.
- The Java package `cn.yujian95.hospital` is an application identifier, not a
  Git author field. It remains unchanged to avoid a broad compatibility
  migration.
- The local gym repository is
  `C:\Users\12259\Desktop\AWEQAR\Dev\GYM_lifu\gym-management-system`.

## Selected approach

Create a clean snapshot repository for `hospital` with one root commit instead
of rewriting every imported commit. The root commit author and committer will
both be `AWEQAR_21 <aweqar1225918785@gmail.com>`. This makes current-branch
line annotations consistently show `AWEQAR_21` without fabricating a rewritten
sequence of historical commits.

The project remains licensed under its existing license. Required license and
third-party notices are retained; current maintenance and snapshot ownership
are described separately from upstream authorship.

## Local workflow

1. Inventory tracked, untracked, and ignored files.
2. Include the tested application source, chatbot service, web chat page,
   documentation, `application.yml` health allowlist, and
   `HealthController.java`.
3. Exclude secrets and machine-local artifacts, especially `.env` files,
   runtime MySQL files, vector databases, logs, generated build output, and the
   personal Word document.
4. Run Java and Python tests and perform the local health/chat smoke checks.
5. Build a clean Git snapshot in an isolated staging directory and create one
   root commit using the requested identity.
6. Replace the current local `hospital` branch with the verified clean history
   while keeping a recoverable local backup until both remotes are verified.

## Remote workflow

1. Read the complete authenticated repository lists on GitHub and Gitee.
2. Preserve or normalize the gym repository as `GYM_lifu` on both platforms.
3. Remove the old remote `hospital` repositories and recreate them with the
   exact name `hospital`.
4. Push the verified clean hospital snapshot to both new repositories.
5. Clone or query both new repositories to confirm their default branch, root
   commit, author email, and essential files.
6. Delete every remaining repository other than `hospital` and `GYM_lifu` only
   after the two retained repositories are verified.

## Safety and rollback

- Exact remote repository names are recorded before deletion.
- Remote deletion happens only in the authenticated accounts
  `aweqar-21` (GitHub) and `AWEQAR33` (Gitee).
- The clean snapshot is verified before old repositories are removed.
- A local backup of the previous Git metadata is retained until remote
  verification succeeds.
- No credentials or personal documents are staged or pushed.

## Acceptance criteria

- `git log -1 --format='%an <%ae>'` prints
  `AWEQAR_21 <aweqar1225918785@gmail.com>` in the clean hospital repository.
- `git blame` for `HospitalApplication.java` reports `AWEQAR_21` on every
  current line.
- Java and Python test suites pass from the clean snapshot.
- GitHub contains exactly `hospital` and `GYM_lifu` for the authenticated user.
- Gitee contains exactly `hospital` and `GYM_lifu` for the authenticated user.
- Both `hospital` remotes can be cloned and contain the README and chat page.
