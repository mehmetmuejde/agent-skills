# Principles — finding tags (FIASSE / SSEM)

Every finding names the engineering principle it violates. The tag tells the developer
*why* the code is weak, not only *what* is wrong, and groups findings with the same root
cause. Use exactly one primary tag per finding (add a second only if both are load-bearing).

Based on FIASSE v1.0.4 (Framework for Integrating Application Security into Software
Engineering) and its SSEM model (Securable Software Engineering Model). Section numbers
in brackets refer to FIASSE.

## The eight principles

| Tag | Principle | In this stack |
|---|---|---|
| **Derived Integrity** [S4.4.1.2] | Security-relevant server state (owner, tenant, role, price, status, permissions, token algorithm) is derived on the server, never accepted from the client. | Owner from `current_user`, never from body/path/`X-Tenant-ID`; prices computed server-side; JWT algorithm from config, not from the token header; React never decides permissions on its own. |
| **Request Surface Minimization** [S4.4.1.1] | Process only the named values you expect; everything else is rejected (and ideally logged). | Pydantic input schema per action with `extra="forbid"`; no `**payload` into ORM models; output schemas list only allowed fields; Zod `.strict()` at frontend boundaries. |
| **Boundary Control** [S4.3] | Hard shell at every trust boundary, flexible interior. Validation, authentication, authorization and encoding happen at the boundary, once and centrally. | Auth dependency at router level; validation in schemas, not deep in services; LLM output, webhook bodies, upstream API responses and tool results are boundaries too. |
| **Canonical Input Handling** [S4.4.1] | Canonicalize → sanitize → validate, in that order, once. Specific types instead of strings. | `UUID`, `EmailStr`, `HttpUrl`, `Literal`/enums, `Path.resolve()` before the containment check, Unicode normalization before comparisons, decode once. |
| **Resilient Coding** [S4.4] | Specific exceptions, fail closed, bounded resources, timeouts, deterministic cleanup, least privilege in code. | No bare `except`, no fail-open on errors, timeouts on every outbound call, size limits, `with` for resources, DB role without superuser/`BYPASSRLS`. |
| **Transparency** [S2.5] | Security-relevant behaviour is observable: structured logs with who/what/where/when/outcome at boundaries; failures produce signals. | Structured audit events for login, logout, denied access, admin actions; no `print`; no silent `except: pass`; secrets and PII redacted. |
| **Least Astonishment** [S2.6] | Behaviour and side effects match name and signature. No hidden mutation, network or file effects. | `GET` never changes state; a `get_*` function doesn't create records; a "read-only" tool doesn't write; a confirmation dialog shows the real action. |
| **Dependency Stewardship** [S4.5, S4.6] | Every dependency is an ongoing relationship: chosen deliberately, pinned, monitored, updated, removed when unused. | Locked versions (`uv.lock`, `pnpm-lock.yaml`), no unmaintained auth/crypto libs (e.g. `python-jose`), no `curl \| sh` installs, lifecycle scripts reviewed. |

SSEM groups the qualities into three pillars — *Maintainability* (Analyzability,
Modifiability, Testability, Observability), *Trustworthiness* (Confidentiality,
Accountability, Authenticity) and *Reliability* (Availability, Integrity, Resilience).
Mention an attribute only when it explains the impact (e.g. "Accountability: no audit
trail for admin role changes"). Do not score attributes — this skill does not produce an
SSEM scorecard.

## Anti-pattern → tag

| Pattern in code | Tag | Correct shape |
|---|---|---|
| f-string / `%` / `.format()` / `+` building SQL, shell commands, LDAP or template source with input | Canonical Input Handling | `select()` / `text()` with bind params; `subprocess.run([...])` without `shell=True`; fixed templates |
| Owner, tenant, role, price or status read from body, path, query or header | Derived Integrity | Derive from `current_user` / DB; scope the query |
| `Model(**payload.model_dump())`, `setattr` loop, `sqlmodel_update(request_json)` with an unrestricted schema, `{...req.body}` spread | Request Surface Minimization | Action-specific schema with `extra="forbid"`, explicit field mapping |
| ORM object or table model returned without a public schema | Request Surface Minimization | Return type / `response_model` = public schema |
| `os.path.join(base, user_input)`, `Path(base) / name` without `resolve()` + `is_relative_to(base)` | Canonical Input Handling | Generated names; resolve, then check containment |
| `jwt.decode` without `algorithms=`, `audience=`, `issuer=`, or with `verify_signature: False` | Derived Integrity | Pinned algorithm allowlist, `aud`, `iss`, required claims |
| Auth/authz check inside some endpoints only, or only in the frontend | Boundary Control | Router-level dependency; server-side enforcement |
| `try: ... except Exception: pass` / `catch {}` / errors swallowed | Transparency | Specific exception, log with context, fail closed |
| Exception text, stack trace or SQL returned to the client | Resilient Coding | Generic message to client, detail to log |
| Error path that lets the operation continue ("if the check fails, allow") | Resilient Coding | Fail closed |
| `print()` / `console.log()` as audit trail; no actor/outcome fields | Transparency | Structured event `{event, actor, target, outcome, request_id}` |
| Request body, token, password, prompt or full LLM response logged | Transparency (Confidentiality) | Log ids and outcome, redact credentials and PII |
| `httpx`/`requests` call without timeout, unbounded read of body/stream, no pagination cap | Resilient Coding | Explicit timeout, size limit, `le=` on `limit` |
| `==` comparison of secrets, tokens, HMACs | Derived Integrity (Authenticity) | `hmac.compare_digest` / `secrets.compare_digest` |
| `random` / `Math.random()` for tokens, ids, codes | Resilient Coding (Authenticity) | `secrets.token_urlsafe()` / `crypto.getRandomValues()` / `crypto.randomUUID()` |
| Secret, key or connection string in code, config file or `VITE_*` variable | Boundary Control (Confidentiality) | Environment / secret store, server side only |
| `any` / `dict[str, Any]` / unvalidated `response.json()` at a boundary | Canonical Input Handling | Pydantic model / Zod schema at the boundary |
| `time.sleep` / `setTimeout` used as throttling | Resilient Coding | Real rate limiter keyed by actor/IP |
| State-changing `GET`, function with hidden side effects, misleading tool description | Least Astonishment | Correct method; honest names and descriptions |
| New dependency for a trivial task, unpinned range, unmaintained or typo-similar package | Dependency Stewardship | Standard library / maintained package, locked version |

## Source

FIASSE v1.0.4 by Alton Crossley, OWASP — <https://github.com/OWASP/FIASSE>, licensed
under CC BY-SA 4.0. Condensed and adapted for Python/TypeScript; the anti-pattern table is
based on the tag reference in the OWASP Secure Agent Playbook (CC BY 4.0).
