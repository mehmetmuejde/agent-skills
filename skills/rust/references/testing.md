# Testing

Tests are written with the change, not afterwards. CI enforces **80 % line coverage**;
below that the pipeline fails. Coverage is a floor — a test without a meaningful
assertion is worse than none.

## Tools

| Purpose | Tool |
|---|---|
| Test runner | `cargo nextest run` (cargo-nextest) |
| Doctests | `cargo test --doc` — **nextest doesn't run doctests**, so CI runs both |
| Snapshots | `insta` + `cargo-insta` |
| Property tests | `proptest` |
| Parameterized tests (optional) | `rstest` (`#[case]`, fixtures) |
| Mocks (only when needed) | `mockall` |
| HTTP fakes for outbound calls | `wiremock` |
| PostgreSQL | `#[sqlx::test]` or `testcontainers` (+ `testcontainers-modules`) |
| CLI binaries | `assert_cmd` + `predicates`, or `trycmd` |
| Coverage | `cargo-llvm-cov` |
| Benchmarks | `criterion` (`performance.md`) |

```bash
cargo nextest run --workspace --all-features
cargo test --doc --workspace --all-features
```

## Layout

- **Unit tests** next to the code in `#[cfg(test)] mod tests { use super::*; … }` — they
  may test private items. Large test modules move to a sibling file
  (`orders/service.rs` + `orders/service/tests.rs`, declared as `#[cfg(test)] mod tests;`).
- **Integration tests** in `tests/` use only the public API, one file per area
  (`tests/orders_api.rs`). Shared helpers in `tests/common/mod.rs` (the `mod.rs` form keeps
  Cargo from compiling it as a test of its own).
- Fakes and fixtures shared by several crates: a `*-testing` workspace crate used as a
  dev-dependency.
- `unwrap`/`expect`/`panic!` are allowed in tests (`clippy.toml`, `tooling.md`).
  Helpers outside `#[test]` functions or `#[cfg(test)]` modules are still linted —
  return `Result` there.

## Writing tests

- **Names describe behavior** in sentence form:
  `place_order_fails_when_item_is_out_of_stock`, not `test_place_order_2`.
- One behavior per test; arrange / act / assert.
- Tests return `Result` and use `?` for setup steps:

  ```rust
  #[tokio::test]
  async fn get_returns_not_found_for_order_of_other_user() -> anyhow::Result<()> {
      let repo = InMemoryOrders::default();
      repo.insert(&order_owned_by(OTHER_USER)).await?;
      let service = OrderService::new(repo, FixedClock::at(NOON));

      let result = service.get(USER, ORDER_ID).await;

      assert_matches!(result, Err(GetOrderError::NotFound(id)) if id == ORDER_ID);
      Ok(())
  }
  ```

- Assert the **specific error variant** (`assert_matches!`, stable since 1.96 —
  `use std::assert_matches;`), not just `is_err()`.
- No sleeps, no real time, no real randomness: inject `Clock`/RNG ports; async timing via
  `#[tokio::test(start_paused = true)]` (tokio feature `test-util`) and
  `tokio::time::advance`.
- `#[tokio::test]` uses a current-thread runtime; add `flavor = "multi_thread"` only when
  the test needs real parallelism.
- A bug fix starts with a failing regression test that reproduces it — then the fix.
- Tests are independent of order and of each other — nextest runs each test in its own
  process.

## Fakes over mocks

Ports (`architecture.md`) get an in-memory implementation — that is the default test
double:

```rust
#[derive(Default)]
pub struct InMemoryOrders {
    orders: Mutex<HashMap<OrderId, Order>>,
}

impl OrderRepository for InMemoryOrders {
    async fn find(&self, owner: UserId, id: OrderId) -> Result<Option<Order>, StoreError> {
        let orders = self.orders.lock().unwrap_or_else(PoisonError::into_inner);
        Ok(orders.get(&id).filter(|o| o.owner() == owner).cloned())
    }

    async fn insert(&self, order: &Order) -> Result<(), StoreError> {
        let mut orders = self.orders.lock().unwrap_or_else(PoisonError::into_inner);
        orders.insert(order.id(), order.clone());
        Ok(())
    }
}
```

- A fake behaves like the real thing (scoping, conflicts), so service tests exercise real
  rules. Add failure switches (`fail_next_insert`) when error paths need testing.
- `mockall` only when the test is about the **interaction** itself (called exactly once,
  with these arguments) and a fake can't express it.
- **Don't mock what you own**: your own ports are tested through their in-memory
  implementations, not through generated mocks.
- Never mock types you don't own (`reqwest::Client`, `PgPool`): put them behind your own
  port, or use the real thing (wiremock server, real PostgreSQL).
- Outbound HTTP: `wiremock::MockServer` and point the client's base URL at it.

## HTTP handler tests (axum)

```rust
use tower::ServiceExt; // for `oneshot`

#[tokio::test]
async fn get_order_returns_404_for_order_of_other_user() -> anyhow::Result<()> {
    let app = test_app(InMemoryOrders::with([order_owned_by(OTHER_USER)]));

    let response = app
        .oneshot(
            Request::get(format!("/api/v1/orders/{ORDER_ID}"))
                .header(AUTHORIZATION, bearer_for(USER))
                .body(Body::empty())?,
        )
        .await?;

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    Ok(())
}
```

`test_app` builds the real router with fakes and a test token verifier — the same
`router()` functions as production. actix-web: `test::init_service` + `test::call_service`.

### Security tests are mandatory

For every endpoint that touches user-owned data:

- unauthenticated → 401,
- other user's object → 404 (BOLA),
- missing permission → 403,
- unknown fields in the body → 400/422 (mass assignment),
- response contains no internal fields,
- RLS tables: tenant A sees none of tenant B's rows even without the `WHERE` filter.

Plus negative validation tests: oversized strings and bodies, out-of-range numbers,
wrong enum values, tampered and expired tokens.

## Database tests

Real PostgreSQL only — never SQLite as a stand-in.

```rust
#[sqlx::test(migrations = "./migrations")]
async fn insert_then_find_returns_order(pool: PgPool) -> anyhow::Result<()> {
    let repo = PgOrderRepository::new(pool);
    repo.insert(&sample_order()).await?;
    assert!(repo.find(USER, ORDER_ID).await?.is_some());
    Ok(())
}
```

- `#[sqlx::test]` creates a fresh database per test from `DATABASE_URL` (the local
  Compose PostgreSQL or a CI service), applies the migrations and drops it afterwards.
- Without sqlx (SeaORM) or for full-stack tests: `testcontainers-modules` PostgreSQL
  started once per test binary, a fresh schema or transaction per test. Starting
  containers locally is a Docker action — ask first.
- Migrations run in tests, so they are tested too.

## Snapshots — insta

- For larger outputs: rendered JSON responses, CLI help/output, error reports, generated
  code. Not for single values — `assert_eq!` is clearer.
- `insta::assert_json_snapshot!(value, { ".id" => "[id]", ".created_at" => "[ts]" })` —
  redact ids and timestamps.
- Snapshots (`snapshots/*.snap`) are committed and reviewed like code;
  `cargo insta review` locally.
- CI: `cargo insta test --check --test-runner nextest` (or plain tests — insta detects CI
  and never writes snapshots there). Pending `.snap.new` files fail the check.

## Property tests — proptest

```rust
proptest! {
    #[test]
    fn sku_roundtrips_through_display_and_parse(raw in "[A-Z]{3}-[0-9]{4}") {
        let sku: Sku = raw.parse()?;
        prop_assert_eq!(sku.to_string(), raw);
    }
}
```

Good targets: parse/serialize roundtrips, invariants of domain operations (totals never
negative), sequences of operations against a simple model. Commit the
`proptest-regressions/` files.

## Test levels for application workspaces

Multi-frontend applications (`applications.md`) test at eight levels — each piece of logic
at the lowest level where it lives:

1. **Domain unit tests** — every rule of every value object: boundaries, unicode, invalid
   input.
2. **Command tests** — `App` with the in-memory repository, the inline job runner and a
   manual clock; assert outputs, error codes and emitted events.
3. **Contract tests** — one suite that every repository adapter passes (`database.md`).
4. **Adapter tests** — reopen/persistence, migrations, newer schema refused, corrupt data,
   rollback.
5. **Concurrency tests** — the job runner with real threads: completion, cancellation,
   shutdown time — with deadlines, never open-ended waits.
6. **UI tests** — `egui_kittest` (or the framework's harness) drives the real UI headless:
   `Harness::new_ui_state(…)`, `get_by_label("Name:").focus()`, `.type_text(…)`,
   `get_by_label("Create").click()`, `harness.run()`. Screenshots need the `wgpu` +
   `snapshot` features.
7. **Binary smoke tests** — `assert_cmd` runs the CLI against a temp data dir; check the
   JSON envelope and exit codes (`agent-interfaces.md`).
8. **Architecture tests** — layer check, wasm build of shared crates, lints
   (`tooling.md`).

Determinism: inject clocks and job runners; no sleeps in core tests; real-thread tests use
deadlines.

## Concurrency and unsafe

loom for own lock-free code, Miri for own `unsafe` — `unsafe-ffi-wasm.md`.

## Verify, then claim

Run the commands and report the real result. Never say a build or test passed without
having run it, and say explicitly what was not checked ("rendered output checked
manually", "not checked in a browser", "desktop app not started").

## Coverage — 80 % lines

```bash
cargo llvm-cov nextest --workspace --all-features --fail-under-lines 80 --lcov --output-path lcov.info
```

- Gate on **lines**: branch coverage in cargo-llvm-cov still needs nightly.
- Doctests aren't included (needs nightly `--doctests`) — they still run in their own CI
  step.
- Exclude generated code and the thin `main.rs` only with a stated reason
  (`--ignore-filename-regex`), never to reach the number.

## nextest configuration

```toml
# .config/nextest.toml
[profile.default]
slow-timeout = { period = "30s", terminate-after = 4 }

[profile.ci]
fail-fast = false
retries = 0

[profile.ci.junit]
path = "junit.xml"
```

CI uses `cargo nextest run --profile ci --locked`. Flaky tests are fixed, not retried.
