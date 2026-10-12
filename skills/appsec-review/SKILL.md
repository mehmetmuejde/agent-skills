---
name: appsec-review
description: Security review for FastAPI/Python backends and React/TypeScript frontends, including code that calls LLMs, runs agents or tools, does RAG, or implements MCP servers/clients. Use when asked for a security review or audit of a diff, branch, merge request, files or a whole codebase ("security review", "is this secure?", "OWASP check", "check the MR for security", German "ist das sicher?", "Security-Review", "prüf den MR auf Sicherheit"), for a dependency/vulnerability audit or secrets scan, when manifests or lockfiles change, or to turn a feature, ticket or spec into security requirements and testable acceptance criteria before implementation. Read-only — never changes code; reports in the conversation language with severity, confidence, CWE and ASVS 5.0 ids.
---

# Application security review

The review side of the `fastapi-backend` and `react-frontend` skills: they hold the
preventive coding rules, this skill finds and reports what slipped through — and hardens
requirements before code exists.

## Modes

| Mode | When | Procedure |
|---|---|---|
| **Review** (default) | Security review of a diff, branch/MR, files or a whole codebase | Workflow below |
| **Requirements** | Feature, ticket, user story or spec before implementation | `references/requirements.md` |
| **Dependency audit** | On request, or when the scope changes `pyproject.toml`, `uv.lock`, `requirements*.txt`, `package.json`, a lockfile or a Docker base image | `references/secrets-and-dependencies.md` Part B |

## Rules — always

- **Read-only.** Never edit, format, commit or "quickly fix" code during a review. Fixes
  go into the report; implementing them is a separate task that needs approval.
- **No installs.** Scanners run only if already installed. Never install a tool, never
  fetch one via `uvx`/`npx`/`pipx run`, never use `uv run` without `--no-sync`, never run
  `--fix`/`audit fix`. Nothing available → say so and ask the user.
- **Read-only commands only**: `git diff`, `git log`, `git show`, `rg`, reading files,
  installed scanners. No requests against running environments, no active testing
  (prompt injection, fuzzing) unless the user explicitly asks and agrees on the scope.
- **Verify before reporting.** A grep hit is a candidate. Every finding is confirmed by
  reading the actual code path — source to sink, route to (missing) check. No speculative
  findings; every finding states its Confidence; unverified suspicions go to "Open
  questions".
- **Redact secrets** everywhere — report, tool calls, commands (`sk-ant-****`). Never send
  a found secret to an external service.
- **Configuration outside the repo** (reverse proxy, IdP, cloud, CDN) is "Out of scope /
  not checked", not a finding.
- **Chat only.** The report goes to the chat, in the conversation language. Never post
  comments to GitHub, GitLab or Gitea — that is `change-review`'s job, after explicit
  approval.

## Review workflow

### 1. Scope and context

Determine the target and read it:

- Diff/branch: `git diff --merge-base origin/<base>` (or `origin/<base>...HEAD`) plus the
  surrounding code of every changed hunk; files: as named; codebase: start at the trust
  boundaries (routers, auth, file handling, outbound calls, LLM/tool code, frontend API
  client and rendering) and list what wasn't sampled under "Out of scope / not checked".
- Record: **stack** (FastAPI + SQLAlchemy 2.0 or SQLModel, PostgreSQL/RLS; React SPA or
  React Router framework mode), **trust boundaries**, **data sensitivity**, **exposure**
  (internet, internal), **auth model** — cookie session + CSRF, bearer JWT (own issuer),
  external OIDC (resource server / BFF) — and the **ASVS target level** (L2 unless stated).
- Use the recon greps at the top of `backend-checklist.md` / `frontend-checklist.md`.

### 2. Secrets scan

Always, on the reviewed scope (whole history for a codebase review):
`references/secrets-and-dependencies.md` Part A.

### 3. Targeted checklists

Load only the references for the domains the scope touches:

| Scope touches | Load |
|---|---|
| FastAPI routes, dependencies, auth, DB access, uploads, outbound HTTP, settings, middleware | `references/backend-checklist.md` |
| React components, routing, API client, auth/token handling, rendering, build config | `references/frontend-checklist.md` |
| LLM calls, prompts, tools/function calling, agent loops, RAG/vector store, memory, rendering of model output | `references/llm-agents.md` |
| MCP server or client code, MCP client config files | `references/mcp.md` (+ `llm-agents.md`) |
| Manifests, lockfiles, new dependencies | `references/secrets-and-dependencies.md` Part B |
| Exact requirement text and level | `references/asvs/README.md` → section file |
| Principle tag for a finding | `references/principles.md` |
| Writing the report | `references/output-format.md` |

The checklists are self-contained; the backend skill's `references/auth.md`,
`api-security.md` and `database.md` show the intended implementation when a fix needs
more detail.

### 4. Diff-specific analysis

For diffs, look at what was **removed or weakened**, not only at what was added:

- Deleted or loosened auth: `Depends(...)`/`Security(...)` removed from a route or router
  `dependencies=[...]`, permission/role checks, owner filters in queries, `auto_error`
  flipped to `False`.
- Validation removed: `extra="forbid"`, `max_length`, `le=`/`ge=`, `Literal`/enum
  replaced by `str`, schema widened by new writable fields.
- CSRF/Origin checks, `TrustedHostMiddleware`, CORS origins widened, security headers or
  CSP relaxed, rate limits removed, `docs_url` re-enabled.
- Sanitization dropped (`DOMPurify`, `rehype-sanitize`), `dangerouslySetInnerHTML` added.
- Response schema replaced by the ORM object; error handler now returns `str(exc)`.
- RLS policies dropped/changed in migrations; constraints removed.
- Security tests deleted or skipped.
- New endpoints: do they follow the auth pattern of their neighbours? New dependencies:
  run the dependency audit.

```bash
git diff --merge-base origin/<base> | rg -n '^-.*(Depends\(|Security\(|dependencies=|require_|permission|owner_id|tenant_id|csrf|extra=|max_length|le=|sanitize|DOMPurify|TrustedHost|CORSMiddleware|allow_origins|limiter|Content-Security|POLICY|ROW LEVEL)'
```

### 5. Verify every candidate

For each candidate: trace the data from the entry point to the sink (or the request from
the router to the data access); check controls upstream (middleware, router dependencies,
schema validation) and downstream (encoding, DB constraints, RLS); look for tests that
pin the behaviour. Then rate Severity and Confidence (`references/output-format.md`).
Merge duplicates into one finding per root cause.

### 6. Report

In the conversation language (labels translated from the English templates), numbered
findings, most severe first. Per finding: Title, Severity (Critical/High/Medium/Low/Info),
Confidence (High/Medium/Low), Location `path:line`, CWE, ASVS 5.0 id (plus
API/LLM/Agentic Top 10 and OWASP Top 10:2025 id where they apply), principle tag, Impact,
Evidence (short excerpt), Fix (concrete). Then "Confirmed controls", "Out of scope / not
checked", optionally "Recommendations".
Full schema, severity criteria and the `change-review` mapping (Critical/High → Blocker,
Medium → Major, Low → Minor, Info → Nit): `references/output-format.md`.

## Requirements mode — short

Normalize features → choose the ASVS level first (default L2) → map to ASVS 5.0 with the
gap-pattern table → only the principles that matter → testable acceptance criteria with
ids → summary in the conversation language. Details: `references/requirements.md`.

## Dependency audit — short

Detect ecosystems → run an installed scanner (osv-scanner, `uv run --no-sync pip-audit`,
`pnpm audit`, `npm audit`) or ask → reachability, context, fix availability → health flags
(unmaintained, typosquatting, dependency confusion, install scripts, license, pinning) →
findings plus upgrade commands as text, never executed. Details:
`references/secrets-and-dependencies.md` Part B.

## Standards and versions

- OWASP Top 10:**2025** (A01 Broken Access Control incl. SSRF … A10 Mishandling of
  Exceptional Conditions) — the current edition on owasp.org/Top10.
- OWASP API Security Top 10 **2023**.
- OWASP Top 10 for LLM Applications **2025**; OWASP Top 10 for Agentic Applications
  **2026** (ASI01–ASI10).
- OWASP ASVS **5.0** — ids without `V` prefix for requirements (`8.2.2`), with prefix for
  sections (`V8.2`). ASVS 4.0 numbering is different; don't mix.
- CWE for every finding.

## Sources

- OWASP Secure Agent Playbook (OWASP, Chris Maenner et al.), CC BY 4.0 — plays and skills
  `code-review-security`, `owasp-top10-web-review`, `api-security-review`, `secrets-scan`,
  `sca-audit`, `prd-securability-enhancement`, `securability-engineering`,
  `agent-security-audit`, `mcp-server-review`, `llm-risk-assess`,
  `agentic-ai-risk-assess`, `prompt-injection-testing`, templates `finding`/`report`.
  Condensed, corrected (ASVS 5.0 ids, OWASP Top 10:2025) and adapted to FastAPI/React.
- OWASP Application Security Verification Standard 5.0, CC BY-SA 4.0 — section files in
  `references/asvs/` via the OWASP Agent Skills Project (Erlend Oftedal); see
  `references/asvs/README.md`.
- FIASSE v1.0.4 / SSEM (OWASP, Alton Crossley), CC BY-SA 4.0 — `references/principles.md`.
- OWASP Top 10:2025 — <https://owasp.org/Top10/>
- OWASP API Security Top 10 2023 — <https://owasp.org/API-Security/>
- OWASP Top 10 for LLM Applications 2025 and Top 10 for Agentic Applications 2026 —
  <https://genai.owasp.org/>
- Arcanum Prompt Injection Taxonomy (Jason Haddix, Arcanum Information Security),
  CC BY 4.0 — input surfaces and test intents in `references/llm-agents.md`.
- Model Context Protocol specification, security best practices —
  <https://modelcontextprotocol.io/specification>
- MITRE CWE — <https://cwe.mitre.org>
