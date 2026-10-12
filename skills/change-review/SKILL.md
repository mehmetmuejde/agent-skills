---
name: change-review
description: Code review of a merge request, pull request or branch for FastAPI/Python and React/TypeScript projects (plus Docker/Helm/CI changes). Use when the user asks for a review — "review MR 142", "review PR 87", "review this branch", "mach ein Review", "schau dir den Branch an" — or calls /change-review. Not the built-in /code-review. Works with GitHub (gh), GitLab (glab), Gitea (MCP) or a local branch. Asks for the scope (everything, frontend, backend, infrastructure), reviews in a separate worktree next to the repo, checks change size, then runs one subagent per dimension — correctness, design and reuse (reuse before building new, duplicates, consistency, typos and translations, signs of unreviewed generated code), breaking changes, tests, security, FastAPI/React/UI conventions, infrastructure. Verifies and merges all findings into one numbered report (file:line, severity, confidence), each with a short hand-typed comment ready to post. Posts to the platform only after explicit approval.
---

# Code review (MR / PR / branch)

An orchestrator: it prepares the review, fans out one subagent per dimension, verifies
and merges what they find and writes one report.

## Rules — always

- **Read-only.** The review never edits, commits, pushes, approves or merges anything.
- **Separate worktree.** Never review in the user's working directory — they keep
  working there.
- **Nothing goes to the platform without approval.** No comments, no labels, no review
  status ("approve", "request changes") unless the user explicitly approves it for
  *this* review, after seeing the report.
- **Report every verified finding** — no cap, no "top 10". Unverified suspicions go to
  "Open questions", not into the findings.
- **Don't invent findings to fill the list.** A review without blockers — or without
  findings — is a valid result.
- **Comments sound human.** Every finding comes with a one-line comment, short and plain
  like a colleague would type it — rules in `references/comment-style.md`.
- **Context over diff.** A review that only reads the diff misses the context the change
  lands in: read the surrounding code, callers and existing equivalents.
- **Ask, don't guess.** When something the review depends on is unclear (branch, target
  branch, scope), ask the user.

## Languages

- **Report**: in the language of the conversation.
- **Review comments**: in the team's language — default: the conversation language. On
  request, add the same comment in a second language (e.g. German and English) so the
  user can pick one when posting.

## Step 1 — target and scope

1. Identify the target: MR/PR number or URL, branch name, or "current branch".
2. Detect the platform from the remote URL or the link and load
   `references/platforms.md` for the matching commands (GitHub → `gh`, GitLab → `glab`,
   Gitea → MCP tools). No remote/platform → local branch review.
3. Get title, description, linked ticket, source and target branch. For an MR/PR URL,
   look up the source branch first; if it can't be determined, ask — don't guess. The
   description says what the change is *supposed* to do — the review checks whether it
   does.
4. If the scope isn't stated, ask with `AskUserQuestion`:
   - **Everything** — the complete diff
   - **Frontend** — UI, component and client code
   - **Backend** — API, services, database
   - **Infrastructure** — Docker, Compose, Helm/Kubernetes, CI, deployment configs

   Only the chosen part is reviewed. Out-of-scope issues get one sentence at the end,
   not a finding.

## Step 2 — worktree

```sh
git fetch origin <source-branch> <target-branch>   # or the MR/PR ref, see platforms.md
git worktree add ../<repo>-review-<id> <source-ref>
```

`<id>` = `MR142`, `PR87` or the ticket key as it is. The worktree is created **next to**
the repo and checks out the branch under review. Don't use an agent's built-in worktree
tool if it creates the worktree inside the repo or branches off the default branch
instead of the branch under review.

The worktree stays after the review; it is removed only when the user says so
(`git worktree remove <path>`).

## Step 3 — understand the change

```sh
git -C <worktree> diff --stat $(git -C <worktree> merge-base origin/<target> HEAD)
git -C <worktree> diff $(git -C <worktree> merge-base origin/<target> HEAD)
```

Always diff against the **merge base**, not the target branch tip.

- Overview first: which features, layers and files changed; new dependencies;
  migrations; config/env changes; Docker/Helm changes. Then go into the files.
- **Change size** (`references/dimensions/change-size.md`): the orchestrator checks it
  itself. Too large → a finding with a concrete split proposal; the review still runs.
- Decide which dimensions apply (table below), limited to the chosen scope.

## Step 4 — one subagent per dimension

Start the applicable dimensions **in parallel**, one subagent each. Give every subagent:

- the **full path** of its dimension file in `references/dimensions/`,
- the worktree path, the merge base and the target branch,
- the MR/PR title and description,
- the scope chosen in step 1 — the subagent reviews only files in scope,
- for skill-backed dimensions the **full path** of that skill's `SKILL.md`,
- for the frontend dimension, when UI code changed (markup, styling, forms, animation,
  copy), also the full path of `references/web-interface-guidelines.md`.

Each subagent reads its dimension file first and follows it, reads all relevant code
(not only the hunks), does **not** stop after the first finding, and returns findings in
the schema from `references/output-format.md`.

| Dimension | File | Runs when |
|---|---|---|
| Correctness | `dimensions/correctness.md` | always |
| Design and reuse — incl. duplicates, consistency, language, generated-code signs | `dimensions/design-and-reuse.md` | always |
| Breaking changes | `dimensions/breaking-changes.md` | always |
| Tests | `dimensions/tests.md` | always |
| Security | `dimensions/security.md` → `appsec-review` skill | always |
| Backend conventions | `dimensions/backend.md` → `fastapi-backend` skill | Python/FastAPI files changed and in scope |
| Frontend conventions | `dimensions/frontend.md` → `react-frontend` skill, `web-interface-guidelines.md` for UI code | React/TS files changed and in scope |
| Infrastructure | `dimensions/infrastructure.md` → `docker-kubernetes` skill | Dockerfile, `.dockerignore`, Compose, Helm, CI changed and in scope |

New dimensions are added as a file in `references/dimensions/` plus a row here — the
orchestrator doesn't change.

## Step 5 — verify and merge

1. Collect all findings. Merge duplicates (same location, same cause) and keep the
   most precise one; note when several dimensions found it.
2. **Verify** every Blocker and Major yourself by reading the code at `file:line` and the
   path that leads there. Not reproducible → downgrade or move to "Open questions".
3. Assign the final severity and confidence per `references/output-format.md`.
   Security severities map: Critical/High → Blocker, Medium → Major, Low → Minor,
   Info → Nit.
4. Sort: Blocker → Major → Minor → Nit, then by file.

## Step 6 — report

In the chat, in the conversation language, format from `references/output-format.md`:
summary and verdict, numbered findings — each with its ready-to-post one-liner
(`references/comment-style.md`) — "Positive", "Open questions", "Out of scope / not
checked".

## Step 7 — post to the platform (only on request)

Only if the user explicitly asks — and only the findings they choose:

1. Ask which findings to post — and, if the comments exist in two languages, which
   language.
2. Show exactly what will be posted: the one-liners per `file:line`, plus the short
   summary comment.
3. Wait for approval of that list.
4. Post with the commands in `references/platforms.md` — the one-liner is the whole
   comment, no headings, no severity labels, no generated-looking structure.

Never set a review status, labels or assignees without separate approval.

## Sources

Orchestrator/dimension pattern and change-size, breaking-change and testing dimensions
adapted from the OpenAI Codex repository's code-review skills (`.codex/skills/code-review*`);
security dimension based on the `appsec-review` skill (OWASP Secure Agent Playbook,
CC BY 4.0; ASVS 5.0); stack dimensions based on the official FastAPI skill and Vercel's
React best practices via the `fastapi-backend` and `react-frontend` skills. UI checks in
`references/web-interface-guidelines.md` are a snapshot of Vercel's Web Interface
Guidelines (vercel-labs/web-interface-guidelines, MIT, © 2025 Vercel Labs).
