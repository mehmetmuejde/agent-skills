# Requirements mode — harden a feature before implementation

Turns a ticket, user story, spec or feature list into explicit, testable security
requirements before code is written. Works on text only — it neither reviews nor writes
code.

## Inputs

Ask for what is missing (one question round, not piecemeal):

- The ticket/spec/feature list.
- Context: user types, exposure (internet, internal), auth model (cookie session, bearer
  JWT, external OIDC), single- or multi-tenant.
- Data sensitivity: PII, credentials, payment, health; regulatory context (GDPR, sector
  rules).
- Target ASVS level, if already decided.

## Procedure

### 1. Normalize the features

One record per independently testable capability (split bullets that hide several):

- Id (`F-01` …) and title
- Actor (role, anonymous user, system, external service)
- Data touched and sensitivity
- Trust boundaries crossed (browser → API, API → DB, API → third party, webhook in,
  LLM/tool calls, background job)
- Existing acceptance criteria, verbatim

### 2. Choose the ASVS level first

| Level | Use when |
|---|---|
| **L1** | Internal tools, prototypes, low-sensitivity data, small blast radius |
| **L2** | Production web/API systems with authenticated users, customer data, business-critical behaviour — **the default** |
| **L3** | Payments, health records, identity providers, government; compromise causes severe harm or attackers are well-resourced |

State the level with a 2–4 sentence rationale and any feature that escalates above the
baseline (e.g. the payment step inside an L2 product gets L3 treatment).

### 3. Map features to ASVS 5.0

Use `asvs/README.md` (lookup table) and the gap-pattern table below; read the section
files for exact requirement text and level. Include requirements up to the chosen level.
Classify each:

- **Covered** — the spec already states it testably
- **Partial** — mentioned, but vague or untestable
- **Missing** — absent
- **N/A** — not applicable, with a one-line reason when not obvious

When a feature matches a gap pattern, prefill those requirements as **Missing** unless
the spec explicitly covers them.

### 4. Securability notes

Per feature, a short paragraph with only the principles from `principles.md` that shape
the implementation (usually Derived Integrity, Request Surface Minimization, Boundary
Control, Transparency). Don't enumerate all of them.

### 5. Acceptance criteria

Every Missing/Partial requirement gets at least one criterion that is:

- **Observable** — a test, response code, log event or UI state confirms pass/fail
- **Specific about failure** — unauthorized actor, malformed input, limit exceeded
- **Traceable** — cites the ASVS id (or LLM/API Top 10 id)

"Secure", "robust", "properly validated" are not acceptance criteria.

### 6. Output

Chat output in the conversation language — translate the English labels of the template
below. Criteria that go into a repository file (spec, ADR, test plan) are written in
English; criteria for a ticket follow the ticket's language.

```markdown
## Security requirements: <feature/ticket>

### ASVS level
Level 2 — <rationale, 2–4 sentences>. Escalations: <F-03 payment → L3 | none>

### Coverage
<only Partial/Missing as a list: F-01 · 6.3.1 · L1 · Missing — no brute-force protection>
Covered: <count>, N/A: <count, reasons if not obvious>

### F-01: <title>
- Actor · Data · Trust boundaries
- ASVS: 6.3.1, 6.3.8, 16.3.1 …
- Requirements: <existing, sharpened + new>
- Acceptance criteria:
  1. <observable, with id>
- Securability: <short, only relevant principles>

### Cross-cutting requirements
<logging, secrets, headers, dependency policy … each with ASVS id>

### Open points / assumptions
<what could not be resolved from the input>
```

## Gap-pattern table (ASVS 5.0)

Phrases that reliably come with missing requirements. Level in brackets where above L1.

| Spec says | Usually missing | ASVS 5.0 |
|---|---|---|
| "User logs in with email and password" | Brute-force/credential-stuffing limits per account and IP; breached/common password check; new session on login; auth events logged; password hashing; MFA requirement (L2); same response for unknown user (L3) | 6.3.1, 2.4.1 (L2), 6.2.4, 6.2.12 (L2), 7.2.4, 16.3.1 (L2), 11.4.2 (L2), 6.3.3 (L2), 6.3.8 (L3) |
| "User can register / sign up" | Anti-automation; password policy without composition rules; activation code random with expiry; enumeration-safe responses | 2.4.1 (L2), 6.2.1, 6.2.5, 6.2.9 (L2), 6.4.1, 6.3.8 (L3) |
| "User resets a forgotten password" | Enumeration-safe response; token from CSPRNG, single use, short-lived, stored hashed; MFA not bypassed; rate limit per email and IP; offer to end other sessions; event logged; `Referrer-Policy` on the reset page | 6.4.3 (L2), 6.3.8 (L3), 11.5.1 (L2), 2.4.1 (L2), 7.4.3 (L2), 16.3.1 (L2), 3.4.5 (L2) |
| "User logs in via SSO / external IdP" | PKCE + `state`; `nonce`; user keyed by `iss`+`sub`; `aud` checked; tokens kept in the backend (BFF); no identity spoofing across IdPs | 10.2.1, 10.5.1, 10.5.2, 10.5.4, 10.3.1, 10.3.3, 10.1.1, 6.8.1 (all L2) |
| "User logs out" / session handling | Server-side invalidation; all sessions end when account disabled; idle + absolute timeout; client storage cleared | 7.4.1, 7.4.2, 7.3.1 (L2), 7.3.2 (L2), 14.3.1 |
| "User edits profile / settings" | Allowlisted mutable fields (no role/owner/email-verified from the body); ownership check; re-authentication for email/password/MFA changes; change logged; user notified (L3) | 15.3.3 (L2), 8.2.2, 8.2.3 (L2), 7.5.1 (L2), 16.2.1 (L2), 6.3.7 (L3) |
| "Admin can …" / roles | Documented permission model; function-level checks server-side; deny by default; denied attempts logged; admin can end user sessions; changes effective immediately (L3) | 8.1.1, 8.2.1, 8.3.1, 16.3.2 (L2), 7.4.5 (L2), 8.3.2 (L3), 8.4.2 (L3) |
| "Customers / organizations / workspaces" (multi-tenant) | Tenant derived from the authenticated user; every query tenant-scoped; cross-tenant attempts logged; PostgreSQL RLS as safety net (project decision) | 8.4.1 (L2), 8.2.2, 16.3.2 (L2) |
| "User uploads a file" | Allowed types and max size documented; size, extension and content checked; archives limited; stored under generated name outside web root; never executed; safe download headers; SVG sanitized; AV scan (L2) | 5.1.1 (L2), 5.2.1, 5.2.2, 5.2.3 (L2), 5.3.1, 5.3.2, 5.4.1 (L2), 1.3.4 (L2), 5.4.3 (L2) |
| "Search / filter / sort / list" | Parameterized queries; sort/filter fields allowlisted; page size capped; owner/tenant scope; minimal fields; regex input safe (L3) | 1.2.4, 2.2.1, 8.2.2, 15.2.2 (L2), 15.3.1, 1.3.12 (L3) |
| "Export / download report" | Authorization re-checked for the export itself; rate limit; formula injection escaped (L3); audit event with row count; minimal data (L3) | 8.2.2, 2.4.1 (L2), 15.2.2 (L2), 1.2.10 (L3), 16.3.3 (L2), 14.2.6 (L3) |
| "Public API / partner integration" | Token validation (signature, algorithm, `aud`, `exp`); per-client rate limits; field allowlist in responses; docs exposure decided; request ids in logs | 9.1.1, 9.1.2, 9.2.1, 9.2.3 (L2), 2.4.1 (L2), 15.3.1, 13.4.5 (L2), 16.2.1 (L2) |
| "Webhook receiver" / "callback from provider" | Authenticated source (signature over raw body or mTLS); timestamp window + replay protection (API10:2023); idempotent processing; rate limit; events logged | 13.2.1 (L2), 4.1.5 (L3), 2.3.3 (L2), 2.4.1 (L2), 16.3.3 (L2) |
| "Server fetches a URL the user provides" (import, preview, webhook target) | Scheme/host/port allowlist; internal ranges blocked on the resolved IP; no redirect following; timeout and size limit | 1.3.6 (L2), 13.2.4 (L2), 13.2.5 (L2), 15.3.2 (L2) |
| "Send email / SMS / notification" | No user-controlled headers; per-recipient and per-actor limits; codes bound to the request, single use, short-lived | 1.3.11 (L2), 2.4.1 (L2), 6.6.2 (L2), 6.6.3 (L2), 6.5.1 (L2), 6.5.5 (L2) |
| "User writes comments / notes / rich text" | Owner never client-supplied; length limits; HTML sanitized, Markdown restricted; changes logged | 8.2.2, 2.2.1, 1.3.1, 1.3.5 (L2), 16.2.1 (L2) |
| "Checkout / payment / booking / stock / vouchers" | Prices and totals computed server-side; steps in order; transactions; locking against double booking; atomic check-then-act (L3); multi-user approval for high value (L3) | 2.3.1, 2.3.2 (L2), 2.3.3 (L2), 2.3.4 (L2), 15.4.2 (L3), 2.3.5 (L3) |
| "Background job processes user data" | Same validation and scoping as the request path; acts with the originating user's permissions (L3); fails closed; errors logged | 2.2.2, 8.3.3 (L3), 16.5.3 (L2), 16.3.4 (L2) |
| "Admin setting / feature flag / configuration" | Only privileged roles; changes audited; secrets never echoed back; no debug/dev functionality in production | 8.2.1, 16.2.1 (L2), 13.3.1 (L2), 13.4.2 (L2), 15.2.3 (L2) |
| "Stores personal / health / financial data" | Data classified with protection rules; not in URLs; retention and deletion (GDPR export/erasure); not in browser storage; logged only masked; encryption in transit and at rest | 14.1.1 (L2), 14.1.2 (L2), 14.2.1, 14.2.4 (L2), 14.2.7 (L3), 14.3.3 (L2), 16.2.5 (L2), 12.2.1, 11.3.2 |
| "Real-time / WebSocket / streaming" | WSS only; Origin check on handshake; auth not via URL; per-connection limits; closed on logout | 4.4.1, 4.4.2 (L2), 4.4.3 (L2), 4.4.4 (L2), 2.4.1 (L2), 7.4.1 |
| "AI / LLM feature, assistant, agent" | Context only with the requesting user's data; tools act with the user's permissions; confirmation for consequential actions; output validated before any sink; Markdown rendering sanitized; `max_tokens`, timeouts, per-user cost limit; prompts logged only redacted | LLM01, LLM02, LLM05, LLM06, LLM10; ASVS 8.2.2, 8.3.3 (L3), 1.3.5 (L2), 2.4.1 (L2), 16.2.5 (L2) — details in `llm-agents.md` |

## Mini example

Input: *"F-03: Users can reset their password via 'Forgot password'; the system emails a
reset link."* → pattern "resets a forgotten password".

Acceptance criteria (excerpt):

1. Requesting a reset for an unknown email returns the same status and body as for a
   known one (ASVS 6.3.8).
2. A reset token is 128+ bits from a CSPRNG, stored only as a hash, expires after
   15 minutes and works once; reuse or expiry returns a generic error and logs
   `password_reset.token_invalid` (ASVS 11.5.1, 6.4.3, 16.3.1).
3. More than 5 requests per email or 20 per IP within 10 minutes return 429 and are
   logged (ASVS 2.4.1).
4. After a successful reset the user is offered to end all other sessions
   (ASVS 7.4.3).
5. The reset page sends `Referrer-Policy: no-referrer` (ASVS 3.4.5).

## Source

Based on the `prd-securability-enhancement` skill of the OWASP Secure Agent Playbook
(CC BY 4.0); requirement ids corrected to ASVS 5.0 (the original table used ASVS 4.0
chapter numbering) and the table extended.
