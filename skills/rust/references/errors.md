# Errors

## Which crate where

| Code | Error type | Crate |
|---|---|---|
| Domain, services, ports | enum per module/concern | `thiserror` |
| Adapters (DB, HTTP clients, files) | enum per adapter, wraps the driver error as `#[source]` | `thiserror` |
| Library crates (published or internal) | enum (or struct) per module, never `anyhow` in the public API | `thiserror` |
| HTTP layer | `ApiError` that implements `IntoResponse` / `ResponseError` | `thiserror` |
| Binary: `main`, composition root, CLI command handlers | `anyhow::Result` with `.context(…)` | `anyhow` |
| Tests, test helpers, build scripts | `anyhow::Result` or `Box<dyn Error>` | `anyhow` |

`anyhow` never appears in a library crate's dependencies (dev-dependencies are fine).
No crate-wide "everything" enum — it couples unrelated modules and forces callers to
match on variants that can't happen.

## Designing an error enum

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum PlaceOrderError {
    #[error("customer {0} not found")]
    UnknownCustomer(CustomerId),

    #[error("item {sku} is out of stock (requested {requested}, available {available})")]
    OutOfStock { sku: Sku, requested: u32, available: u32 },

    #[error("order store unavailable")]
    Store(#[source] StoreError),
}
```

- **Variants carry the data the caller needs** to react (ids, limits) — not a
  preformatted string.
- **Messages**: lowercase, no trailing period, one line, no secrets or personal data.
- **Don't print the source twice**: either `#[error("…: {0}")]` *or* `#[source]`, not both
  — reporters walk the chain and would repeat it.
- **`#[from]` only when the conversion is unambiguous** (one variant per source type) and
  you want `?` to convert automatically. Otherwise `#[source]` plus an explicit
  `map_err` that adds context.
- **Never stringify a source** (`e.to_string()` into a variant) — the chain and the type
  are lost.
- A module with exactly one failure mode gets a struct error instead of an enum.
- Errors are `Send + Sync + 'static` (no `Rc`, no borrowed `&'a str` fields), so they can
  cross tasks and threads.
- A crate may export `pub type Result<T, E = Error> = std::result::Result<T, E>;`.
- Errors that several frontends or machines react to get **stable codes**
  (`fn code(&self) -> &'static str`, plus `is_user_error()` where useful) — callers branch
  on codes, never on message strings (`applications.md`). No stringly-typed errors across
  crate boundaries.

## Translate at layer boundaries — once

Each layer converts the lower layer's error into its own vocabulary in **one** place
(a `From` impl or one mapping function), not ad hoc in every call site:

```rust
impl From<sqlx::Error> for StoreError {
    fn from(err: sqlx::Error) -> Self {
        match err {
            sqlx::Error::RowNotFound => Self::NotFound,
            sqlx::Error::Database(db) if db.is_unique_violation() => Self::Conflict,
            other => Self::Backend(other),
        }
    }
}
```

Internal errors and wire errors are different types. The HTTP error (`ApiError`) is
built from domain errors explicitly — a status code and a public message per variant —
never by forwarding `Display` of an internal error to the client. Examples:
`web-backend.md`.

## Retryable vs permanent

When callers retry, make it a decision of the error type, not of string matching:

```rust
impl FetchError {
    pub fn is_retryable(&self) -> bool {
        match self {
            Self::Timeout | Self::Unavailable { .. } => true,
            Self::NotFound | Self::Unauthorized | Self::InvalidResponse(_) => false,
        }
    }
}
```

The `match` is exhaustive on purpose: a new variant forces a decision. A server-provided
delay (`Retry-After`) travels inside the variant (`Unavailable { retry_after: Option<Duration> }`).

## anyhow in the binary

```rust
use anyhow::Context;

let raw = std::fs::read_to_string(&path)
    .with_context(|| format!("reading config file {}", path.display()))?;
let config: Config = toml::from_str(&raw).context("parsing config file")?;
```

- `.context("static text")`, `.with_context(|| format!(…))` when the text is built.
  Context describes **what was being done**, not what went wrong (the source says that).
- Print the full chain once: `eprintln!("error: {err:#}")` (single line) or `{err:?}`
  (multi-line with causes and, if enabled, backtrace).
- `anyhow::bail!`/`ensure!` for early exits in command handlers.
- To branch on a specific cause: `err.downcast_ref::<StoreError>()` — if you do that often,
  the code wants a typed error instead.

## Panics

- `panic!`, `unwrap`, `expect`, `unreachable!`, `todo!`, `unimplemented!` and indexing that
  can fail are for **bugs**, never for input, I/O, configuration or network states.
- Library code never panics on caller input; return an error.
- Clippy enforces this (`unwrap_used`, `expect_used` = deny; `panic`, `todo`,
  `indexing_slicing` optional) — see `tooling.md`. Tests are exempt via `clippy.toml`.
- A true invariant may use `expect` with a local, reasoned suppression:

  ```rust
  #[expect(
      clippy::expect_used,
      reason = "regex literal is validated by a unit test"
  )]
  static SKU: LazyLock<Regex> =
      LazyLock::new(|| Regex::new(r"^[A-Z]{3}-\d{4}$").expect("valid regex"));
  ```

- "Impossible" branches at runtime: `debug_assert!` plus a safe fallback (return an error
  or a neutral value) instead of crashing production.
- Document panics a public function can still raise under `# Panics`.
- Servers keep `panic = "unwind"` (default): tokio isolates a panicking task, and the
  HTTP layer can turn it into a 500 (`tower_http::catch_panic`).

## Logging errors

- Log where the error is **handled** (the HTTP error mapper, the CLI `main`, a worker
  loop), once, with the full chain: typed errors as
  `tracing::error!(error = &err as &dyn std::error::Error, "…")` (the subscriber records
  the source chain), `anyhow::Error` as `tracing::error!(error = ?err, "…")`.
- Code that only propagates with `?` doesn't log.
- Never log secrets, tokens, passwords or request bodies in error messages.

## Documentation

Public fallible functions document their failure modes under `# Errors` (clippy pedantic
`missing_errors_doc`).
