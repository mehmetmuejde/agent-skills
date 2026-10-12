# Backend review checklist — FastAPI / Python / PostgreSQL

Review side of the `fastapi-backend` skill. The preventive rules live there
(`references/auth.md`, `references/api-security.md`, `references/database.md`); this file
is self-contained so a review works without them.

How to use:

1. Run the **recon** greps to map entry points, auth model and trust boundaries.
2. For each domain the scope touches, run its greps — they find **candidates**, not
   findings.
3. Open every candidate and follow the data from the request to the sink (and the
   control from the router to the query). Only a confirmed path is a finding.
4. Cite ASVS 5.0 ids in brackets and the CWE in parentheses as given here.

Grep patterns are ripgrep regexes (`rg -n --type py '<pattern>'` or the Grep tool).

---

## 0. Recon

```bash
rg -n --type py 'FastAPI\(|APIRouter\(|include_router\(|\.mount\('          # apps, routers, mounted sub-apps
rg -n --type py '@(app|router|\w+_router)\.(get|post|put|patch|delete|api_route|websocket)\(' # endpoints
rg -n --type py 'add_middleware\(|@app\.middleware|BaseHTTPMiddleware'       # middleware stack
rg -n --type py 'Depends\(|Security\(|dependencies=\['                     # dependency wiring
rg -n --type py 'OAuth2PasswordBearer|HTTPBearer|APIKeyHeader|APIKeyCookie|SessionMiddleware|set_cookie\(' # auth model
rg -n --type py 'BaseSettings|os\.environ|os\.getenv'                       # configuration
rg -n --type py 'httpx\.|requests\.|aiohttp|urllib'                         # outbound calls
rg -n --type py 'openai|anthropic|litellm|langchain|llama_index|pydantic_ai|mcp' # LLM/agent/MCP code → llm-agents.md / mcp.md
```

Write down before checking anything:

- **Auth model**: cookie session + CSRF · bearer JWT (own issuer) · external OIDC
  (resource server, maybe BFF) — or a combination.
- **Public endpoints** (no auth dependency) and why they are public.
- **Trust boundaries**: client → API, API → DB, API → external services, webhooks in,
  LLM/tool calls, background jobs.
- **Data sensitivity**: PII, credentials, payment, health; multi-tenant or not.
- **ORM**: SQLAlchemy 2.0 or SQLModel; RLS in use or not.

---

## 1. Authentication — API2:2023 · A07:2025

### All models

- [ ] Auth dependency at **router level**; every route without it is intentionally
      public. Check routers added in the diff and routes added to existing routers
      [8.2.1] (CWE-306).
- [ ] Mounted sub-apps (`app.mount(...)`) don't inherit the main app's router/app
      dependencies — each one needs its own auth (CWE-306).
- [ ] `include_in_schema=False` hides a route from the docs only — not an access control.
- [ ] `OAuth2PasswordBearer(auto_error=False)` / `HTTPBearer(auto_error=False)` return
      `None` — the code must reject `None` explicitly (CWE-287).
- [ ] `SecurityScopes` declared → the scopes are actually compared (CWE-863).
- [ ] Users identified by a stable id (OIDC: `iss` + `sub`), never by email or display
      name [10.3.3] (CWE-287).
- [ ] Login, registration, reset, OTP and token endpoints are rate-limited per account
      **and** per client IP [6.3.1, 2.4.1] (CWE-307) — see §5 for where.
- [ ] Generic auth errors; same status, body and comparable timing for "unknown user" and
      "wrong password" [6.3.8] (CWE-204).
- [ ] No default/demo accounts or seeded admin credentials outside fixtures [6.3.2]
      (CWE-1392).
- [ ] Authentication events are logged (success, failure, logout) without secrets
      [16.3.1] (CWE-778).

### Bearer JWT (own issuer)

- [ ] `jwt.decode` with `algorithms=[...]` allowlist, `audience=`, `issuer=` and required
      claims (`exp`, `iat`, `iss`, `aud`, `sub`) [9.1.1, 9.1.2, 9.2.1, 9.2.3] (CWE-347).
- [ ] No `options={"verify_signature": False}`, no `"none"` algorithm, no HS/RS confusion
      (an RSA public key passed as HMAC secret) (CWE-347).
- [ ] Key material from configuration; `jku`/`x5u`/`jwk` headers ignored [9.1.3]
      (CWE-347).
- [ ] Token type checked — a refresh token or ID token is not accepted as access token
      [9.2.2] (CWE-287).
- [ ] Short access-token lifetime; refresh tokens rotated and revocable server-side;
      logout/"log out everywhere" actually revokes (`jti` denylist or token version)
      [7.4.1, 7.4.3] (CWE-613).
- [ ] No secrets or unnecessary personal data in the payload (base64, not encrypted)
      [9.2.x] (CWE-312).
- [ ] Signing secret has ≥ 256 bits and comes from the secret store, not a default like
      `"secret"` / `"changeme"` [11.2.3, 13.3.1] (CWE-798).
- [ ] Library: PyJWT or Authlib. `python-jose` is unmaintained (alg-confusion CVEs) →
      Dependency Stewardship finding. With Authlib, `claims.validate()` must be called —
      `jwt.decode()` alone doesn't check `exp` (CWE-613).

### External IdP (OIDC) — API as resource server

- [ ] Access token validated against the IdP's JWKS (from config/discovery, cached), with
      algorithm allowlist, exact `iss`, `aud` = this API [9.1.x, 10.3.1] (CWE-347).
- [ ] ID tokens are not accepted as API credentials [9.2.2] (CWE-287).
- [ ] Authorization from `scope`/role claims goes through an explicit mapping; no
      "any authenticated user is admin" [10.3.2] (CWE-863).
- [ ] Required authentication strength/recentness (`acr`, `amr`, `auth_time`) checked for
      sensitive operations when the IdP provides it [10.3.4, 6.8.4].
- [ ] Multiple IdPs: users from IdP A can't impersonate users from IdP B (key on
      `iss` + `sub`) [6.8.1] (CWE-287).
- [ ] BFF login in the backend: Authorization Code + PKCE, `state` and `nonce` checked,
      exact `redirect_uri`, tokens stay in the backend [10.1.1, 10.2.1, 10.5.1]
      (CWE-352).

### Cookie session + CSRF

- [ ] Cookie flags: `Secure`, `HttpOnly`, `SameSite` (`Lax`/`Strict`), `__Host-` prefix
      with `Path=/` and no `Domain` [3.3.1–3.3.4] (CWE-614, CWE-1004).
- [ ] Session id from `secrets.token_urlsafe(32)` or equivalent [7.2.3, 11.5.1]
      (CWE-330); a new id on login and re-authentication [7.2.4] (CWE-384).
- [ ] Logout deletes the server-side session, not only the cookie [7.4.1] (CWE-613);
      disabling a user kills all sessions [7.4.2].
- [ ] Idle and absolute timeouts exist [7.3.1, 7.3.2] (CWE-613).
- [ ] Starlette `SessionMiddleware` is a **signed client-side** cookie: readable,
      not revocable — no secrets in it; `https_only=True`; key from settings (CWE-315).
- [ ] **CSRF** on every state-changing route (`POST/PUT/PATCH/DELETE`), as a router-level
      dependency [3.5.1–3.5.3] (CWE-352):
      `Origin` (fallback `Referer`) checked against an allowlist, missing → reject;
      **plus** a non-safelisted header (`X-CSRF-Token` double submit /
      `X-Requested-With`) or a synchronizer token compared with `compare_digest`;
      JSON endpoints reject form content types; no state change on `GET`.
- [ ] Sensitive account changes (email, password, MFA) need re-authentication
      [7.5.1] (CWE-620).

### Passwords (only if stored locally)

- [ ] Argon2id / bcrypt / scrypt via a maintained library (`pwdlib`, `argon2-cffi`,
      `bcrypt`) — never MD5/SHA*, never unsalted [11.4.2] (CWE-916). `passlib` is
      unmaintained → Dependency Stewardship (Low/Info).
- [ ] Policy: min 8 (15 recommended), ≥ 64 allowed, no composition rules, no truncation,
      breached/common password check, no forced rotation
      [6.2.1, 6.2.4, 6.2.5, 6.2.8, 6.2.9, 6.2.10, 6.2.12] (CWE-521).
- [ ] Password change requires the current password [6.2.3] (CWE-620).
- [ ] Reset tokens: CSPRNG, single use, short lifetime, stored hashed, same response for
      unknown emails, MFA not bypassed [6.4.3, 6.3.8, 11.5.1] (CWE-640).

```bash
rg -n --type py 'jwt\.decode\(|jwt\.encode\(|jose|authlib|PyJWKClient'
rg -n --type py 'verify_signature|algorithms\s*=|audience\s*=|issuer\s*='
rg -n --type py 'auto_error\s*=\s*False'
rg -n --type py 'set_cookie\(|delete_cookie\(|SessionMiddleware|samesite|httponly|secure\s*='
rg -n --type py -i 'csrf|x-requested-with|origin|sec-fetch'
rg -n --type py 'hashlib\.(md5|sha1|sha256)\(|passlib|bcrypt|argon2|pwdlib'
rg -n --type py "(SECRET|JWT|TOKEN)_?KEY\s*=\s*['\"]"
```

---

## 2. Authorization — API1/API3/API5:2023 · A01:2025

- [ ] **BOLA/IDOR**: every query for user-owned data filters by owner/tenant **in the
      query**; "load by id, check later" (`session.get(Model, id)`) is a candidate
      [8.2.2] (CWE-639).
- [ ] Service/repository functions for owned data take the user/tenant as a required
      parameter.
- [ ] List, search, export, batch and count endpoints apply the same scope to every
      element [8.2.2] (CWE-639).
- [ ] Nested resources check the whole chain (`/projects/{pid}/tasks/{tid}`) (CWE-639).
- [ ] "Not yours" and "not found" both return 404 (CWE-204).
- [ ] **BFLA**: admin/privileged routes on a separate router with a role/permission
      dependency; changing the method or path doesn't skip the check [8.2.1]
      (CWE-285).
- [ ] **BOPLA (read)**: output schemas contain only fields this consumer may see; no ORM
      or SQLModel table object returned directly; role-specific schemas where needed
      [15.3.1, 8.2.3] (CWE-213).
- [ ] **BOPLA (write)**: see §4 mass assignment [15.3.3] (CWE-915).
- [ ] **Derived Integrity**: owner, tenant, role from `current_user`, never from body,
      path, query or headers like `X-Tenant-ID` / `X-User-ID` [8.3.1, 4.1.3]
      (CWE-602, CWE-639).
- [ ] Authorization enforced in the backend, not only hidden in the UI [8.3.1]
      (CWE-602).
- [ ] Role/permission changes take effect immediately (or within token lifetime, which
      is short) [8.3.2].
- [ ] Multi-tenant: `tenant_id` on every tenant-owned table, filtered in every query,
      including joins and subqueries [8.4.1] (CWE-639).
- [ ] Denied authorization decisions are logged [16.3.2] (CWE-778).

### PostgreSQL row-level security (if used)

- [ ] Every tenant-owned table: `ENABLE ROW LEVEL SECURITY` **and** `FORCE ROW LEVEL
      SECURITY` (otherwise the table owner bypasses the policies) [8.4.1] (CWE-284).
- [ ] The application connects with a role that is **not** the table owner, not
      superuser and has no `BYPASSRLS` (CWE-250).
- [ ] Policies cover reads (`USING`) **and** writes (`WITH CHECK`) — otherwise rows can
      be inserted/moved into another tenant (CWE-639).
- [ ] Tenant context is set **per transaction**: `SET LOCAL app.tenant_id = …` or
      `set_config('app.tenant_id', :tid, true)`. A session-level `SET` survives in
      pooled connections and leaks to the next request (CWE-668).
- [ ] The value comes from the authenticated user, never from a request header
      (Derived Integrity).
- [ ] Missing context fails closed: `current_setting('app.tenant_id', true)` → `NULL` →
      no rows, never "all rows".
- [ ] New tables in Alembic migrations get RLS + policies in the same migration; check
      migrations in the diff.
- [ ] Jobs/admin tasks that need cross-tenant access use a separate, documented role.
- [ ] RLS is a safety net — application-level scoping (above) is still required.

```bash
rg -n --type py 'session\.get\(|\.get\(\w+,\s*\w+_id\)|get_by_id\('          # load-by-id candidates
rg -n --type py 'select\(\w+\)\.where\(\w+\.id\s*=='                          # filter by id only
rg -n --type py -i 'x-tenant|x-user-id|tenant_id\s*[:=]\s*(body|payload|request|data)\.'
rg -n --type py 'owner_id|user_id|tenant_id' -g '*schemas*'                   # client-settable ownership fields
rg -n 'ROW LEVEL SECURITY|CREATE POLICY|BYPASSRLS|set_config\(|SET LOCAL|SET app\.' -g '*.py' -g '*.sql'
rg -n --type py 'is_admin|role\s*==|has_permission|require_role'
```

---

## 3. Injection and unsafe processing — A05:2025

- [ ] **SQL**: no f-strings, `%`, `.format()` or `+` in `text()`, `execute()`,
      `exec_driver_sql()`, raw `cursor.execute()`; `order_by`/column names from input
      only via an allowlist (`Literal[...]`) [1.2.4] (CWE-89).
- [ ] **OS commands**: no `shell=True`, `os.system`, `os.popen` with input; argument lists
      only; no user-controlled program names or option injection (`--`-prefixed values)
      [1.2.5] (CWE-78).
- [ ] **Code execution**: no `eval`, `exec`, `compile`, `__import__`, `importlib` with
      input [1.3.2] (CWE-94).
- [ ] **Templates**: no `Template(user_input)` / `env.from_string(user_input)`; Jinja2
      autoescape on; `|safe` / `Markup()` only on sanitized content [1.3.7, 1.2.1]
      (CWE-1336, CWE-79).
- [ ] **HTML responses**: `HTMLResponse` with interpolated input is XSS [1.2.1]
      (CWE-79); user rich text sanitized with a maintained sanitizer (`nh3`) [1.3.1].
- [ ] **Deserialization**: no `pickle`/`dill`/`shelve`/`marshal` on untrusted data,
      `yaml.safe_load` only, `jsonpickle` avoided [1.5.2] (CWE-502).
- [ ] **XML**: `defusedxml` or `lxml` with `resolve_entities=False`, `no_network=True`
      [1.5.1] (CWE-611).
- [ ] **Path traversal**: user input never becomes a path; otherwise
      `resolve()` + `is_relative_to(base)` [5.3.2] (CWE-22). `FileResponse(path)` and
      `StaticFiles(directory=...)` pointing at a directory with secrets are candidates.
- [ ] **Regex**: no user-supplied patterns (or `re.escape`); no nested quantifiers on
      user input [1.2.9, 1.3.12] (CWE-1333).
- [ ] **Email**: no CR/LF from input in headers (subject, to, from) [1.3.11] (CWE-93).
- [ ] **Headers / redirects**: no CR/LF in header values;
      `RedirectResponse(url=<input>)` only with a relative path or allowlisted host
      [3.7.2] (CWE-601, CWE-113).
- [ ] **CSV/XLSX export**: cells starting with `=`, `+`, `-`, `@`, tab, CR escaped
      [1.2.10] (CWE-1236).
- [ ] **NoSQL/LDAP/XPath** if present: parameterized/escaped [1.2.4, 1.2.6, 1.2.7].
- [ ] **Validation** happens in Pydantic schemas at the boundary: `max_length`,
      `ge`/`le`, `Literal`/enums, `UUID`, `EmailStr`, `HttpUrl`; `model_construct()`
      skips validation and must not touch request data [2.2.1, 2.2.2] (CWE-20).

```bash
rg -n --type py 'text\(f["'\'']|execute\(f["'\'']|execute\([^)]*%|\.format\([^)]*\)\s*\)|exec_driver_sql'
rg -n --type py 'order_by\(\s*(text\(|getattr|\w+\[)'
rg -n --type py 'shell\s*=\s*True|os\.system\(|os\.popen\(|subprocess\.(call|run|Popen|check_output)\('
rg -n --type py '\beval\(|\bexec\(|compile\(|__import__\(|importlib\.import_module\('
rg -n --type py 'Template\(|from_string\(|autoescape\s*=\s*False|\|\s*safe|Markup\('
rg -n --type py 'HTMLResponse\(|RedirectResponse\(|FileResponse\(|StaticFiles\('
rg -n --type py 'pickle\.loads?|yaml\.load\(|yaml\.unsafe_load|jsonpickle|dill\.|marshal\.loads'
rg -n --type py 'xml\.etree|xml\.dom|xml\.sax|lxml\.etree|XMLParser\('
rg -n --type py 're\.(compile|match|search|fullmatch|sub)\(\s*(request|payload|body|query|q\b|pattern)'
rg -n --type py 'open\(|Path\(|os\.path\.join\(|send_file|shutil\.'
rg -n --type py 'model_construct\(|csv\.writer|openpyxl|xlsxwriter'
```

---

## 4. Mass assignment and response filtering — API3:2023

- [ ] Input schema per action (`ItemCreate`, `ItemUpdate`) with
      `model_config = ConfigDict(extra="forbid")`; no `role`, `owner_id`, `is_admin`,
      `status`, `price`, `tenant_id`, `email_verified` unless the action is meant to set
      them [15.3.3] (CWE-915).
- [ ] No `Model(**payload.model_dump())` with a schema broader than intended, no
      `setattr` loops, no `sqlmodel_update(dict_from_request)`, no `request.json()` into
      the ORM. Partial updates: `model_dump(exclude_unset=True)` of the restricted update
      schema [15.3.3] (CWE-915).
- [ ] Every path operation has a return type / `response_model` that is a public schema;
      no table model, no `dict` with internal fields, no password hash, tokens, internal
      flags [15.3.1] (CWE-213).
- [ ] `response_model_exclude` is fragile as the only filter — a dedicated public schema
      is expected.
- [ ] Error bodies don't echo internal objects.

```bash
rg -n --type py '\*\*\w+\.(model_dump|dict)\(\)|\*\*await request\.json|\*\*payload|\*\*data\b'
rg -n --type py 'setattr\(\w+,\s*(k|key|field)|sqlmodel_update\(|\.update\(\*\*'
rg -n --type py 'extra\s*=\s*["'\'']forbid'                                      # present?
rg -n --type py 'class \w+\((SQLModel|Base)\b.*table\s*=\s*True'                # table models — returned anywhere?
rg -n --type py 'def \w+\(.*\)\s*:\s*$' -g '*routers*'                            # path operations without return type
```

---

## 5. Resource consumption and rate limiting — API4/API6:2023

Rate limiting is preferably configured at the **reverse proxy** (nginx `limit_req`,
Traefik `RateLimit`, Caddy, API gateway), otherwise with a library in the app (`slowapi`,
`limits`, `fastapi-limiter` with Redis). If the proxy config is not in the reviewed
repository, list it under "Out of scope / not checked" — don't report it as missing.

- [ ] Login, registration, reset, OTP, invite, contact/message sending, exports, LLM
      calls and other costly operations are limited per account and per IP [2.4.1,
      6.3.1, 6.6.3] (CWE-770, CWE-307).
- [ ] In-app limiter keyed on the **trusted** client IP (see §10 proxy headers) — keyed on
      a spoofable `X-Forwarded-For` it is bypassable [15.3.4] (CWE-348); in-memory
      storage doesn't work with several workers/instances.
- [ ] Pagination with an upper bound (`Query(le=100)`); no unbounded `.all()` on
      user-controlled filters [15.2.2] (CWE-770).
- [ ] String/list/dict lengths constrained in schemas; nested JSON depth bounded where
      needed (CWE-400).
- [ ] Request body size limited (proxy `client_max_body_size` or ASGI middleware);
      uploads streamed with a size cap [5.2.1] (CWE-400).
- [ ] Timeouts: outbound calls (`httpx` default 5 s — `timeout=None` disables it;
      `requests` has **no** default), DB `statement_timeout`, LLM calls [13.2.6, 15.2.2]
      (CWE-400).
- [ ] Expensive work runs as background jobs with per-user quotas [15.2.2].
- [ ] **Sensitive business flows** (sign-up, voucher redemption, booking, purchase,
      invitations) have per-account limits and, where needed, anti-automation
      [2.4.1, 2.3.2] (CWE-799).

```bash
rg -n --type py 'slowapi|limits|Limiter\(|RateLimit|fastapi_limiter'
rg -n 'limit_req|limit_conn|client_max_body_size|ratelimit' -g '*.conf' -g '*.yml' -g '*.yaml' -g '*.toml' -g 'Caddyfile'
rg -n --type py 'Query\([^)]*\)' -g '*router*'                                   # limit params without le=
rg -n --type py 'timeout\s*=\s*None|requests\.(get|post|put|delete|request)\('
rg -n --type py '\.all\(\)|scalars\([^)]*\)\.all\(\)'
```

---

## 6. Business logic and concurrency — A06:2025

- [ ] State machines enforced server-side: no jump from `draft` to `paid` because the
      client says so; steps in order [2.3.1] (CWE-841).
- [ ] Prices, totals, discounts, quantities computed on the server (Derived Integrity)
      [2.3.2] (CWE-602).
- [ ] Check-then-act on shared state (stock, balance, "only one active X", voucher use)
      is atomic: `with_for_update()`, unique constraint or conditional
      `UPDATE … WHERE` [2.3.4, 15.4.2] (CWE-362, CWE-367).
- [ ] Multi-step writes in one transaction; failure rolls back [2.3.3].
- [ ] Idempotency for retried operations (payments, webhooks) (CWE-841).
- [ ] Negative numbers, zero, huge values, duplicates in lists rejected where they make
      no business sense [2.2.3] (CWE-20).

---

## 7. SSRF and outbound requests — API7:2023 · A01:2025

Any server-side request to a URL or host the client influences (webhook targets,
imports, link previews, avatars by URL, OIDC discovery from input, PDF renderers):

- [ ] Allowlist of schemes/hosts/ports where possible [1.3.6, 13.2.4] (CWE-918).
- [ ] Otherwise the resolved IP is checked against private, loopback, link-local,
      metadata ranges (`127/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `::1`,
      `fc00::/7`, `fe80::/10`, IPv4-mapped IPv6) **and** the connection goes to that
      resolved IP — otherwise DNS rebinding bypasses the check (CWE-918, CWE-367).
- [ ] Redirects not followed (`httpx` default) or re-validated per hop
      [15.3.2] (CWE-918).
- [ ] Timeout and response size limit; raw upstream bodies/errors not returned to the
      client (CWE-918, CWE-209).
- [ ] TLS verification on (`verify=True`, no `verify=False`, no custom `ssl` context with
      `CERT_NONE`) [12.3.2] (CWE-295).
- [ ] Outbound credentials are scoped to the target; the user's token isn't forwarded to
      third parties [10.1.1] (CWE-201).

```bash
rg -n --type py '(httpx|requests|aiohttp)\.\w+\(\s*(url|target|link|callback|webhook|f["'\''])'
rg -n --type py 'follow_redirects\s*=\s*True|allow_redirects\s*=\s*True|max_redirects'
rg -n --type py 'verify\s*=\s*False|CERT_NONE|check_hostname\s*=\s*False|InsecureRequestWarning'
rg -n --type py 'ipaddress\.|is_private|getaddrinfo|gethostbyname'
```

---

## 8. Webhooks and third-party APIs — API10:2023 · A08:2025

- [ ] Incoming webhooks: signature (HMAC) verified over the **raw body**
      (`await request.body()`, not re-serialized JSON) with `hmac.compare_digest`
      [13.2.1] (CWE-345, CWE-208).
- [ ] Timestamp checked against a short window and event ids stored to reject replays
      (CWE-294).
- [ ] Processing is idempotent; unknown event types ignored safely.
- [ ] Webhook secret per provider from the secret store [13.3.1] (CWE-798).
- [ ] Data from upstream APIs validated with Pydantic before use; never trusted for
      authorization decisions (CWE-20).
- [ ] Upstream failures fail closed and don't leak details [16.5.2, 16.5.3] (CWE-636).

```bash
rg -n --type py -i 'webhook|signature|x-hub-signature|stripe-signature|hmac\.(new|compare_digest)'
rg -n --type py '==\s*(signature|expected|digest|token|api_key)|(signature|digest|token)\s*==' # timing-unsafe compare
```

---

## 9. Files — uploads and downloads

- [ ] Size limit enforced while streaming, not after reading everything [5.2.1]
      (CWE-400).
- [ ] Extension **and** content (magic bytes) checked against an allowlist; client
      `content_type` not trusted [5.2.2] (CWE-434).
- [ ] Stored under a generated name outside any public/executable path; user filenames
      never become paths [5.3.1, 5.3.2] (CWE-22, CWE-434).
- [ ] Archives: uncompressed size and file count checked before extraction; paths in
      entries ignored; `tarfile.extractall()` only with `filter="data"`; no symlinks
      [5.2.3, 5.2.5, 5.3.3] (CWE-409, CWE-22).
- [ ] Images: pixel dimensions limited (Pillow `MAX_IMAGE_PIXELS` not disabled) [5.2.6]
      (CWE-400).
- [ ] SVG and HTML uploads sanitized or served as attachment / from a separate origin
      [1.3.4, 3.2.1] (CWE-79).
- [ ] Downloads: owner check, `Content-Disposition: attachment` with a safe filename,
      stored content type, `X-Content-Type-Options: nosniff` [5.4.1, 5.4.2, 3.4.4]
      (CWE-79, CWE-639).
- [ ] Signed URLs (S3/MinIO) are short-lived and per object.

```bash
rg -n --type py 'UploadFile|File\(|\.filename|content_type|python-multipart'
rg -n --type py 'extractall\(|ZipFile\(|tarfile\.open|shutil\.unpack_archive|MAX_IMAGE_PIXELS'
rg -n --type py 'Content-Disposition|generate_presigned_url|presigned'
```

---

## 10. Application configuration — API8/API9:2023 · A02:2025

- [ ] `/docs`, `/redoc`, `/openapi.json` disabled in production unless intended:
      `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` driven by settings
      [13.4.5] (CWE-200).
- [ ] `FastAPI(debug=True)`, `uvicorn --reload`, `fastapi dev` never in production
      (Dockerfile `CMD`, compose, systemd) [13.4.2] (CWE-489).
- [ ] `TrustedHostMiddleware` with the real hostnames (or host check at the proxy)
      (CWE-20).
- [ ] Proxy headers trusted only from the proxy: `fastapi run --proxy-headers
      --forwarded-allow-ips <proxy-ip>` / uvicorn `forwarded_allow_ips`; `"*"` is only
      acceptable if the app is unreachable except via the proxy [4.1.3, 15.3.4]
      (CWE-348).
- [ ] CORS: explicit origin list from settings; never `allow_origins=["*"]` together with
      `allow_credentials=True` — Starlette then reflects the caller's origin for
      credentialed requests, i.e. any site can read responses. `allow_origin_regex` must
      be anchored and tight [3.4.2] (CWE-942).
- [ ] Security headers (app or proxy): HSTS, `X-Content-Type-Options: nosniff`,
      `Referrer-Policy`, CSP (`default-src 'none'; frame-ancestors 'none'` for pure JSON
      APIs), `Cache-Control: no-store` on responses with personal data
      [3.4.1, 3.4.4, 3.4.5, 3.4.6, 14.3.2]. If set at a proxy outside the repo → Out of
      Scope.
- [ ] No server/framework version disclosure in headers or error bodies [13.4.6].
- [ ] Debug, test, metrics, admin and health-detail endpoints not exposed publicly;
      removed features remove their routes; old API versions have an end date
      [13.4.5, 15.2.3] (CWE-489).
- [ ] `app.dependency_overrides` only in tests, never in application code (CWE-489).
- [ ] Settings via `pydantic-settings`; secrets as `SecretStr`; no secrets in defaults,
      `.env` committed, Dockerfiles or compose files [13.3.1] (CWE-798).
- [ ] DB connection with least privilege (no superuser), TLS to DB where it crosses a
      network [13.2.2, 12.3.1] (CWE-250, CWE-319).
- [ ] HTTP methods: one operation per function; no `api_route(methods=[...])` mixing
      safe and unsafe methods [4.1.4, 3.5.3].
- [ ] GraphQL (if present): introspection off in production, depth/cost limits
      [4.3.1, 4.3.2] (CWE-770).

```bash
rg -n --type py 'docs_url|redoc_url|openapi_url|debug\s*=\s*True|reload\s*=\s*True'
rg -n 'fastapi dev|--reload|uvicorn .*--reload|forwarded.allow.ips|proxy-headers|proxy_headers' -g 'Dockerfile*' -g '*.yml' -g '*.yaml' -g '*.toml' -g '*.sh' -g '*.py'
rg -n --type py 'TrustedHostMiddleware|CORSMiddleware|allow_origins|allow_origin_regex|allow_credentials'
rg -n --type py -i 'strict-transport|content-security-policy|x-content-type-options|referrer-policy|cache-control'
rg -n --type py 'dependency_overrides'
rg -n --type py 'strawberry|graphene|ariadne|introspection'
```

---

## 11. Cryptography and randomness — A04:2025

- [ ] Tokens, ids, codes, CSRF tokens, reset links from `secrets` (or `uuid4` for
      non-secret ids), never `random` [11.5.1] (CWE-338).
- [ ] Secret comparisons with `hmac.compare_digest` / `secrets.compare_digest`
      [11.2.4] (CWE-208).
- [ ] Encryption via `cryptography` (AES-GCM / Fernet), no ECB, no static IV/nonce, no
      home-made crypto [11.2.1, 11.3.1, 11.3.2, 11.3.4] (CWE-327, CWE-329).
- [ ] MD5/SHA-1 only for non-security checksums [11.4.1] (CWE-328).
- [ ] Keys ≥ 128-bit security (RSA ≥ 3072 for new keys, or EC) [11.2.3] (CWE-326).
- [ ] TLS for every external and cross-network connection; certificate validation on
      [12.2.1, 12.3.2] (CWE-319, CWE-295).

```bash
rg -n --type py '\brandom\.(random|randint|choice|choices|getrandbits|sample)\('
rg -n --type py 'AES\.MODE_ECB|MODE_ECB|DES|RC4|Blowfish|hashlib\.(md5|sha1)\('
rg -n --type py 'iv\s*=\s*b["'\'']|nonce\s*=\s*b["'\'']'
```

---

## 12. Error handling and logging — A10:2025 · A09:2025

- [ ] Clients get generic messages; no stack traces, SQL, file paths or library versions
      [16.5.1, 13.4.2] (CWE-209).
- [ ] `HTTPException(detail=str(e))` / returning `repr(exc)` is a leak candidate
      (CWE-209).
- [ ] Last-resort exception handler logs and returns a generic 500 [16.5.4] (CWE-755).
- [ ] **Fail closed**: an exception in an auth, payment, validation or permission path
      denies; no `except: pass` that continues with the operation [16.5.3] (CWE-636).
- [ ] External dependency failures degrade safely (timeouts, circuit breaker) [16.5.2]
      (CWE-703).
- [ ] No bare `except:`; broad `except Exception` only at boundaries and with logging
      (CWE-396, CWE-390).
- [ ] Background tasks: exceptions are logged (they don't reach the client) (CWE-778).
- [ ] Security events logged with who/what/where/when/outcome, UTC timestamps: login,
      logout, failures, denied access, admin actions, permission changes, password/MFA
      changes [16.2.1, 16.2.2, 16.3.1–16.3.3] (CWE-778).
- [ ] No passwords, tokens, `Authorization`/`Cookie` headers, full request bodies, PII or
      prompts in logs; ids/hashes instead [16.2.5] (CWE-532).
- [ ] Structured (JSON) logging or encoding so user input can't forge log lines
      [16.4.1] (CWE-117).

```bash
rg -n --type py 'except\s*:|except\s+Exception\s*:\s*$|except\s+BaseException'
rg -n --type py -A2 'except' | rg -n 'pass$|continue$|return (True|None)$'
rg -n --type py 'detail\s*=\s*(str|repr)\(|traceback\.format_exc|exc_info.*detail'
rg -n --type py 'exception_handler\(|add_exception_handler'
rg -n --type py 'log(ger)?\.\w+\(.*(password|token|secret|authorization|cookie|api_key|request\.body|\.json\(\))'
rg -n --type py '\bprint\('
```

---

## 13. WebSockets, SSE and streaming

- [ ] WebSocket handshake checks `Origin` against the allowlist [4.4.2] (CWE-1385).
- [ ] Authentication via cookie session or a token in the first message — not in the URL
      query (logged by proxies) [4.4.3, 14.2.1] (CWE-598).
- [ ] Per-connection authorization for every subscribed channel/room (CWE-639).
- [ ] Message size, rate and connection count limited; idle timeout (CWE-770).
- [ ] Connection closed on logout/session expiry [7.4.1] (CWE-613).
- [ ] SSE/streaming endpoints carry the same auth dependency as their JSON siblings.

```bash
rg -n --type py '@\w+\.websocket\(|WebSocket\b|websocket\.accept|EventSourceResponse|StreamingResponse'
```

---

## 14. Background jobs and internal services

- [ ] Jobs re-validate their input and scope by the user/tenant that triggered them
      — same boundary discipline as the request path [2.2.2, 8.3.3] (CWE-639).
- [ ] Service-to-service calls are authenticated with short-lived credentials, not shared
      static keys [13.2.1] (CWE-798).
- [ ] Poison messages don't crash the worker loop or retry forever (CWE-400).

---

## Mapping: OWASP Top 10:2025 → sections

| Id | Name | Sections |
|---|---|---|
| A01:2025 | Broken Access Control (incl. SSRF) | §2, §7, CSRF in §1 |
| A02:2025 | Security Misconfiguration | §10 |
| A03:2025 | Software Supply Chain Failures | `secrets-and-dependencies.md` |
| A04:2025 | Cryptographic Failures | §11, cookies/JWT in §1 |
| A05:2025 | Injection | §3 |
| A06:2025 | Insecure Design | §6, §5 business flows |
| A07:2025 | Authentication Failures | §1 |
| A08:2025 | Software or Data Integrity Failures | §8, deserialization in §3 |
| A09:2025 | Security Logging and Alerting Failures | §12 |
| A10:2025 | Mishandling of Exceptional Conditions | §12 |

## Mapping: OWASP API Security Top 10 2023 → sections

| Id | Name | Sections |
|---|---|---|
| API1:2023 | Broken Object Level Authorization | §2 |
| API2:2023 | Broken Authentication | §1 |
| API3:2023 | Broken Object Property Level Authorization | §2, §4 |
| API4:2023 | Unrestricted Resource Consumption | §5, §9 |
| API5:2023 | Broken Function Level Authorization | §2 |
| API6:2023 | Unrestricted Access to Sensitive Business Flows | §5, §6 |
| API7:2023 | Server Side Request Forgery | §7 |
| API8:2023 | Security Misconfiguration | §10 |
| API9:2023 | Improper Inventory Management | §10 |
| API10:2023 | Unsafe Consumption of APIs | §8 |
