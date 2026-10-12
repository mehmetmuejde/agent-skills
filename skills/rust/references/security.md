# Security

Memory safety removes a class of bugs; it doesn't give you authentication,
authorization, input limits or safe secret handling. This file holds the Rust-specific
implementation rules. For a full security review (threat model, OWASP/ASVS mapping,
severity report) use the `appsec-review` skill: `../../appsec-review/SKILL.md`.

## Input validation

- Validate at the edge, once, into **typed values**: request DTO → `TryFrom` → domain
  newtype (`Email`, `Sku`, `Quantity`). Inner code trusts the types (`idioms.md`).
- Every string has a maximum length, every number a range, every list a maximum size,
  every enum a closed set (`#[serde(rename_all = "snake_case")] enum`, unknown values
  rejected).
- `#[serde(deny_unknown_fields)]` on request DTOs — protects against mass assignment
  (`role`, `owner_id`, `tenant_id` sneaking in).
- Derived integrity: owner, tenant, role, price and status come from the authenticated
  principal or the database, never from the request.
- For many field rules on DTOs, `garde` (or `validator`) is fine — one per project; the
  conversion into domain types still happens.
- Types deserialized straight from input (commands, config, messages) validate in serde
  through the same constructor: `#[serde(try_from = "String")]` on the newtype, whose
  `TryFrom<String>` calls `parse` — no second, weaker path into the domain.
- Bound **everything** that comes from outside: string lengths, list sizes, recursion
  depth, file sizes, message sizes.
- Stored data is untrusted on read too: invalid values map to a `Corrupt` error, never a
  panic (`database.md`).
- Paths from input: never join user input onto a base path without canonicalizing and
  checking the result stays inside the base (path traversal); better, map ids to paths.
- `get()` instead of indexing with externally supplied indexes.

## Secrets

- Held in `secrecy::SecretString` / `SecretBox<T>` (secrecy 0.10): no `Display`, a
  redacting `Debug`, zeroized on drop; read with `.expose_secret()` only at the point of
  use.
- Loaded from the environment or a mounted secret file at startup (desktop apps: the OS
  keychain); never in code, config files in the repo, Docker images, `ARG`/`ENV` lines or
  CLI flags.
- `.env.example` with placeholders only — and only when a host actually reads
  configuration from the environment.
- Types that contain secrets implement `Debug` by hand and redact
  (`finish_non_exhaustive()`); never `#[derive(Debug)]` on them.
- Logging: `#[instrument(skip_all, fields(…))]` and explicit fields only; tower-http
  `SetSensitiveRequestHeadersLayer` for `Authorization`/`Cookie`; never log bodies, tokens
  or full URLs with query strings that may carry tokens. Full command payloads that can
  contain personal data are not logged at `info` (log the command name and ids).
- No secrets in logs, URLs or error messages returned to clients.
- gitleaks runs on commit and push (`tooling.md`); a leaked secret is rotated
  immediately — rewriting history is not enough.

## TLS

- **rustls** everywhere: `reqwest` with its rustls feature (`default-features = false`),
  sqlx `tls-rustls-ring-webpki`, `tokio-rustls` for raw sockets. No OpenSSL in the
  dependency tree (`cargo deny` bans it, `tooling.md`).
- Certificate verification is never disabled (`danger_accept_invalid_certs` only in a
  test against a local test server, never behind a config flag).
- Database connections to non-local servers use `sslmode=verify-full`.
- TLS usually terminates at the gateway; the app still validates `X-Forwarded-*` only from
  the trusted proxy.

## SQL injection

- Queries are parameterized: sqlx macros, `.bind()`, `QueryBuilder::push_bind`, SeaORM
  query builder or `Statement::from_sql_and_values`.
- sqlx 0.9 accepts only `&'static str` or `AssertSqlSafe(…)` as query text — treat every
  `AssertSqlSafe` and `format!` near SQL as a review finding until proven safe.
- Identifiers (columns, sort direction) come from enums, never from input
  (`database.md`).

## Authentication

- **Bearer JWT** (APIs): `jsonwebtoken` with a fixed algorithm allowlist
  (`Validation::new(Algorithm::RS256)` or `EdDSA`), required `exp`, validated `iss` and
  `aud`; keys from the IdP's JWKS, cached and refreshed by `kid`. Never accept `none` or
  switch algorithms based on the token header.
- **External IdP (OIDC)**: authorization code flow with PKCE (`openidconnect` crate);
  validate `state` and `nonce`.
- **Cookie sessions** (browser apps): `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict`),
  narrow `Path`, no `Domain` unless required; rotate the session id after login and
  privilege changes; server-side invalidation on logout. CSRF protection for
  state-changing requests: tower-http 0.7 `CsrfLayer` (Fetch-Metadata/Origin check) or a
  synchronizer token.
- **Passwords**: `argon2` (Argon2id, RustCrypto) with a per-password salt; hash and verify
  inside `spawn_blocking` — it is deliberately slow. Never a fast hash (SHA-256) for
  passwords.
- **API keys**: random (≥ 32 bytes from the OS CSPRNG, e.g. `getrandom::fill`), shown once,
  stored as a hash; compare hashes in constant time.
- One identity boundary: middleware produces a minimal `CurrentUser`; a failure is 401,
  never an anonymous fallback (`web-backend.md`).

## Authorization

- Default deny: routers are protected unless explicitly public.
- Check per request: principal × action × resource × tenant. 401 when not
  authenticated, 403 when authenticated but not allowed, 404 for objects outside the
  user's scope.
- Scope queries by owner/tenant in SQL (`database.md`); PostgreSQL RLS as the second line
  in multi-tenant systems.
- `is_admin` is not a skeleton key — admin actions have their own explicit permissions
  and are audited.

## Destructive commands and automation clients

For applications with a command core (`applications.md`, `agent-interfaces.md`):

- Every command has an `Effect` (`Read`, `Write`, `Destructive`); an unknown or
  unclassified command is treated as **destructive**.
- Destructive commands need **explicit confirmation in every frontend that acts for
  someone else**: a confirm dialog in the UI, `--allow-destructive` in the CLI,
  `confirm: true` plus a user-side allow-list in MCP.
- Agents and scripts **never pass confirmation flags on their own**; a human approves the
  specific action.

## Network-facing hosts (server, MCP over HTTP, control channels)

- Bind to **`127.0.0.1` by default**; listening on other interfaces is an explicit,
  documented configuration.
- Require a **token on every request** (compared in constant time, below); reject
  non-JSON early.
- **Cap request size and connection count** (e.g. 4 MiB per line or body, 16 concurrent
  connections).
- **Authorize per `Effect`**: read-only tokens can run `Read` commands only; write tokens
  `Write`; destructive commands additionally need the confirmation rules above.

## Timing-safe comparison

Compare secrets (API key hashes, HMAC signatures, webhook signatures, CSRF tokens) in
constant time:

```rust
use subtle::ConstantTimeEq;

fn signature_matches(expected: &[u8], received: &[u8]) -> bool {
    expected.ct_eq(received).into()
}
```

For HMACs prefer the library's own check (`hmac::Mac::verify_slice`), which is constant
time. Never `==` on secrets.

## DoS limits

- **Body size**: `DefaultBodyLimit` + `RequestBodyLimitLayer` (axum) /
  `JsonConfig::limit` (actix). Uploads stream with a size cap.
- **Timeouts**: request timeout layer, body read timeout/deadline, outbound client
  timeouts, DB statement timeout (`web-backend.md`, `async.md`).
- **Bounded everything**: channels, queues, caches (with eviction), concurrency
  (`Semaphore`, `ConcurrencyLimitLayer`), pagination `limit`, result set sizes.
- **Parsing**: limits on nesting depth and sizes for untrusted formats; `serde_json`
  limits recursion by default — keep it on.
- **Hashing**: default `HashMap` hasher (SipHash) for attacker-controlled keys.
- **Regex**: the `regex` crate is linear-time; still cap input length. No
  backtracking engines (`fancy-regex`) on untrusted input.
- **Rate limiting** at the reverse proxy/gateway first; in-app (`tower_governor`) only
  without one. Login, reset and expensive endpoints always.
- Expensive work (password hashing, image processing) behind limits and off the async
  workers.

## SSRF (server-side requests to user-supplied URLs)

- Allowlist schemes (`https`) and, where possible, hosts.
- Resolve the host yourself, reject private, loopback, link-local, multicast and
  cloud-metadata ranges (IPv4 **and** IPv6, including IPv4-mapped IPv6), then connect to
  the **checked IP** (prevents DNS rebinding).
- Disable automatic redirects or re-check every hop; cap response size and time.

## Panics and error output

- Production errors return generic messages; details go to the log (`errors.md`).
- `CatchPanicLayer` turns handler panics into 500 without leaking the panic message.

## Dependencies and supply chain

- Fewer dependencies: add a crate only when std or an existing dependency can't do it;
  check maintenance, downloads, owners, license, the size of the transitive tree and
  `unsafe` usage before adding. Prefer `default-features = false` and enable only what is
  used.
- `Cargo.lock` committed; CI builds with `--locked`.
- `cargo deny check` (advisories, licenses, bans, sources) and `cargo audit` on every MR
  and on a schedule; findings fail the pipeline; accepted risks are ignored per advisory
  id **with a reason** in `deny.toml`.
- Dependency updates through Renovate/Dependabot with a waiting period for new releases;
  review lockfile diffs — new transitive crates and owner changes deserve a look (recent
  crates.io incidents involved typosquats and compromised maintainer accounts).
- `build.rs` and proc macros run arbitrary code at build time — another reason to keep the
  dependency list short.
- CI jobs that write to a shared/public build cache never receive secrets.
- Toolchain pinned (`rust-toolchain.toml`), GitHub Actions pinned by commit SHA
  (`tooling.md`).
- `unsafe` stays forbidden; if ever needed, it is isolated in one crate with `// SAFETY:`
  comments and tests (`unsafe-ffi-wasm.md`).
