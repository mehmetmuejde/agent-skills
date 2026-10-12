# API security checklist — OWASP API Security Top 10 (2023)

Walk through this list for every new or changed endpoint. Each item names the FastAPI
way to get it right. ASVS 5.0 ids in brackets.

## API1 — Broken Object Level Authorization (BOLA / IDOR)

- [ ] Every object access is scoped by owner/tenant **in the query** (`database.md`).
- [ ] Batch/list endpoints apply the same scope to every element.
- [ ] Nested resources check the parent too (`/projects/{pid}/tasks/{tid}`: the task
      belongs to the project **and** the project to the user).
- [ ] "Not yours" returns 404 like "not found". [8.2.2]

## API2 — Broken Authentication

- [ ] Auth dependency at router level; public endpoints explicit.
- [ ] Token validation complete: algorithm allowlist, `exp`/`nbf`, `aud`, `iss`, token
      type (`auth.md`). [9.1, 9.2]
- [ ] Rate limits on login/reset/OTP; generic error messages. [2.4.1]

## API3 — Broken Object Property Level Authorization (BOPLA)

- [ ] Input schema per action with `extra="forbid"` — no `role`, `owner_id`, `is_admin`,
      `price`, `status` unless the action is meant to change them. [15.3.3]
- [ ] Never `Model(**request.json())` or `setattr` loops over client data.
- [ ] Output schema contains only the fields this consumer may see; role-specific
      output schemas where needed. [15.3.1, 8.2.3]

## API4 — Unrestricted Resource Consumption

- [ ] Pagination with an upper bound (`Query(le=100)`).
- [ ] String/list lengths constrained in schemas (`max_length`, `min_length`).
- [ ] Request body size limited at the reverse proxy; upload size checked. [5.2.1]
- [ ] Timeouts on every outbound call (`httpx.Client(timeout=...)`), DB statement timeout.
- [ ] Rate limits at the reverse proxy / gateway; in-app limiter library only where the
      proxy can't (per-account limits). [2.4.1]
- [ ] Expensive operations (exports, LLM calls, emails, SMS) rate-limited per user and
      ideally run as background jobs. [2.4.1]

## API5 — Broken Function Level Authorization (BFLA)

- [ ] Every operation has an explicit permission requirement; admin operations live on a
      separate router with a role dependency. [8.2.1]
- [ ] Changing the HTTP method (`GET` → `DELETE`) or path doesn't bypass the check.

## API6 — Unrestricted Access to Sensitive Business Flows

- [ ] Prices, discounts, totals and stock are computed server-side (derived integrity).
- [ ] Flows that can be abused by automation (sign-up, voucher redemption, booking,
      sending messages) have per-account limits and, if needed, anti-automation.
- [ ] State machines are enforced server-side: an order can't jump from `draft` to
      `paid` because the client says so.

## API7 — Server-Side Request Forgery (SSRF)

When the server fetches a URL that the client influences (webhooks, imports, previews,
avatars by URL):

- [ ] Allowlist of target hosts/schemes where possible. [13.2.4]
- [ ] Otherwise resolve the host and reject private, loopback, link-local and metadata
      addresses (`127.0.0.0/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254.0.0/16`,
      `::1`, `fc00::/7`) — and connect to the **resolved** IP, otherwise DNS rebinding
      bypasses the check.
- [ ] `follow_redirects=False` (HTTPX default) or re-check every redirect target. [15.3.2]
- [ ] Timeout and response size limit; don't return raw upstream responses or errors.

## API8 — Security Misconfiguration

- [ ] `/docs`, `/redoc`, `/openapi.json` off in production unless intended. [13.4.5]
- [ ] CORS: explicit origins; no `"*"` with credentials.
- [ ] `TrustedHostMiddleware`; proxy headers only from the proxy. [4.1.3]
- [ ] Generic error responses; no stack traces, SQL or library versions. [16.5.1]
- [ ] Security headers on API responses (usually set at the reverse proxy):
      `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
      `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` for pure JSON
      APIs.
- [ ] `Cache-Control: no-store` on responses with personal or sensitive data. [14.3.2]
- [ ] Debug mode and auto-reload never in production (`fastapi run`, not `fastapi dev`).

## API9 — Improper Inventory Management

- [ ] No forgotten endpoints: removed features remove their routes; old API versions
      have an end date.
- [ ] Debug/test/internal endpoints are not mounted in production.
- [ ] The OpenAPI schema (even if not public) matches what is deployed — use it to
      review the attack surface.

## API10 — Unsafe Consumption of APIs

Data from third-party APIs and webhooks is untrusted input:

- [ ] Validate upstream responses with Pydantic models before using them.
- [ ] Webhooks: verify the signature (HMAC with `hmac.compare_digest`) over the raw
      body, check the timestamp against a short window and reject replays (store event
      ids).
- [ ] TLS verification stays on (`verify=True`); timeouts set.
- [ ] No `pickle`, `yaml.load` (use `yaml.safe_load`), or XML parsing with external
      entities on untrusted data (`defusedxml`).

## Files

- [ ] Size limit; extension **and** content (magic bytes) checked against an allowlist.
      [5.2.1, 5.2.2]
- [ ] Stored under an internally generated name outside any executable/public path;
      user-supplied filenames never become paths. [5.3.1, 5.3.2]
- [ ] Archives: max uncompressed size and file count before extracting; ignore paths in
      entries (zip slip). [5.2.3, 5.3.3]
- [ ] Downloads: `Content-Disposition: attachment` and the stored content type.

## WebSockets

- [ ] Check the `Origin` header in the handshake against the allowlist; authenticate the
      connection (cookie session or token in the first message, not in the URL).
      [4.4.2]
