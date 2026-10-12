# Output format — findings and review layout

The review goes **into the chat**, in the **conversation language**. It is never posted to
GitHub, GitLab or Gitea by this skill — posting review comments is done by
`change-review`, and only after explicit approval for that review.

The templates below define the labels in English. Translate labels, headings and prose
into the conversation language; keep severities, confidence levels, ids (CWE, ASVS, OWASP),
principle tags, code, paths and identifiers unchanged.

## Severity

Rate the impact **in this application's context**, after verification — not the
theoretical worst case of the weakness class.

| Severity | Criteria | Typical examples |
|---|---|---|
| **Critical** | Remotely exploitable without or with trivial preconditions; leads to code execution, full authentication bypass, takeover of arbitrary accounts, or cross-tenant/mass data exposure | RCE via `pickle`/`eval`/shell on request or model data; JWT signature not verified; live production secret with broad rights in the repo; provider API key in the browser bundle; SQL injection on a public endpoint |
| **High** | Exploitable by an ordinary authenticated user or with modest preconditions; significant data exposure, privilege escalation, or integrity loss | IDOR/BOLA on personal data; missing function-level authorization on admin actions; mass assignment of `role`/`owner_id`; stored XSS; missing CSRF protection on sensitive state changes with cookie auth; SSRF reaching internal services; agent tool acting with service-account rights |
| **Medium** | Exploitable only under specific conditions (user interaction, particular configuration, chained with another weakness) or with limited impact | Reflected XSS needing a click; open redirect; missing rate limit on login; tokens in `localStorage`; missing `max_tokens`/timeouts enabling cost abuse; overly broad CORS without credentials; verbose errors leaking internals |
| **Low** | Hardening gap with minor direct impact; defence in depth missing where other controls exist | Missing security header with an otherwise strict setup; version disclosure; unpinned non-critical dependency; `passlib` still in use |
| **Info** | No exploitable weakness; best practice, requirement above the target ASVS level, or observation worth knowing | ASVS L3 gap in an L2 project; documentation gap; unused dependency |

Rules:

- Reachability and exposure lower or raise the rating (internal admin tool vs public
  internet; dev dependency vs runtime).
- A weakness that is only exploitable through another finding is rated by the chain, and
  the chain is named in both findings.
- Don't inflate: a missing control on a route that has nothing to protect is not High.

## Confidence

| Confidence | Meaning |
|---|---|
| **High** | Code path read end to end (source → sink, or route → missing check); exploit conditions confirmed in the code or by tool output |
| **Medium** | Strong indicators, but a part is outside the reviewed code (proxy config, IdP settings, another service) — name exactly what is unconfirmed |
| **Low** | Pattern match with a plausible but unverified path |

- **Low-confidence items are not findings.** Either verify them (read more code) or list
  them as "Open questions" under "Out of scope / not checked", with what would confirm
  them.
- Critical and High require Confidence High or Medium.

## Mapping to `change-review` severities

| appsec-review | change-review |
|---|---|
| Critical, High | Blocker |
| Medium | Major |
| Low | Minor |
| Info | Nit |

When findings are handed to `change-review`, keep the original severity in the text
("Blocker (Security: High)").

## Finding schema

One finding per root cause. The same pattern in several places is **one** finding with
all locations listed. Numbering is continuous, sorted by severity, then confidence.

````markdown
#### 1. [High] <Short title: what is broken, where>

- **Severity:** High · **Confidence:** High
- **Location:** `app/orders/router.py:42` (also: `app/orders/router.py:88`)
- **Classification:** CWE-639 · ASVS 8.2.2 · API1:2023 · A01:2025
- **Principle:** Derived Integrity
- **Impact:** <1–2 sentences: what an attacker concretely achieves, under which
  preconditions>
- **Evidence:**
  ```python
  order = session.get(Order, order_id)   # no owner_id filter
  return order
  ```
- **Fix:** <concrete: which change at which place; short code only if it makes the
  change unambiguous; reference to the rule in the fastapi-backend or react-frontend
  skill, if there is one>
````

Field rules:

- **Title** — names the weakness and the place, not the category ("Other users' orders
  retrievable by id", not "Broken Access Control").
- **Location** — `path:line` relative to the repo root; for a diff, the line in the new
  version.
- **Classification** — always one CWE (the most specific). ASVS 5.0 requirement id when
  one matches; for LLM/agent findings without an ASVS match write `ASVS —`. Add
  `APIx:2023`, `LLMxx:2025`, `ASIxx` and the OWASP Top 10:2025 id (`A01:2025` …) where
  applicable.
- **Principle** — one tag from `principles.md`.
- **Impact** — attacker, precondition, result.
- **Evidence** — the shortest excerpt that proves the finding (≤ 10 lines); secrets
  redacted (`sk-ant-****`).
- **Fix** — concrete and minimal; never just "validate input properly".
- Optional **Assumption:** — if the rating depends on something outside the code (e.g.
  "API is publicly reachable").

## Review layout

```markdown
## Security review: <target — branch/MR/files/codebase>

**Mode:** Review · Diff `origin/main...HEAD` (<n> files) · **Stack:** FastAPI/SQLAlchemy,
React/Vite · **Auth:** Cookie session + CSRF · **ASVS target:** L2
**Checked:** Backend, Frontend, Secrets, LLM · **Tools:** gitleaks 8.x, pattern search

**Result:** 0 Critical · 2 High · 1 Medium · 1 Low · 0 Info

### Findings
<findings per schema, most severe first>

### Confirmed controls
- <existing controls, concrete with location — e.g. "Owner scoping in all order
  queries (`app/orders/service.py`)">

### Out of scope / not checked
- <areas, files, configuration outside the repo (reverse proxy, IdP, cloud)>
- <reasons: not in the diff, no scanner available, …>
- Open questions: <unverified suspicions and what would resolve them>

### Recommendations (optional)
- <cross-cutting improvements without a concrete finding, prioritized>
```

Optional sections, only when the step ran:

- **Dependency audit** — see `secrets-and-dependencies.md` B4.
- **Tool risk matrix** — MCP reviews, see `mcp.md` §2.
- **Data flow / injection surface** — LLM/agent reviews, see `llm-agents.md` §1 (short).

No findings: say so explicitly ("No findings."), and still fill "Confirmed controls"
and "Out of scope / not checked" — a result without a scope statement is not a result.

Requirements mode has its own layout: `requirements.md` §6.
