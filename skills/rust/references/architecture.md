# Architecture — feature slices and ports

The code is organized by **feature** (domain), not by technical layer — the same idea as
the FastAPI and React skills. Inside a feature, a small hexagon: domain in the middle,
ports as traits, adapters at the edge, wiring in `main`.

This is the default for web backends, CLIs and services. **Applications with several
frontends** (desktop + browser + CLI + agents) use a layered command core on top of it —
crates L0–L4, one `App::execute(Command)` entry point — see `applications.md`; feature
slices still organize the modules inside its domain and application crates.

## One crate first

Start with **one package** (library + binary). Most services and CLIs never need more.
The module tree gives the structure; crate visibility (`pub(crate)`, private modules)
gives the boundaries.

### Web backend

```
shop/
├── Cargo.toml
├── migrations/                      # sqlx or SeaORM migrations
├── src/
│   ├── main.rs                      # composition root: config, tracing, pool, wiring, serve
│   ├── lib.rs                       # pub mod declarations + build_router(); no logic
│   ├── config.rs                    # typed settings from the environment
│   ├── telemetry.rs                 # tracing subscriber setup (called from main only)
│   ├── db.rs                        # pool construction, migrations runner
│   ├── http.rs                      # router assembly, middleware, ApiError, health
│   ├── http/
│   │   └── error.rs
│   ├── orders.rs                    # feature facade: pub use of what other features may use
│   ├── orders/
│   │   ├── domain.rs                # Order, OrderId, Status, invariants — no I/O, no frameworks
│   │   ├── service.rs               # use cases: place_order, cancel_order (generic over ports)
│   │   ├── ports.rs                 # trait OrderRepository, trait PaymentGateway
│   │   ├── error.rs                 # PlaceOrderError, … (thiserror)
│   │   ├── http.rs                  # axum handlers + DTOs (request/response structs)
│   │   └── postgres.rs              # PgOrderRepository: impl OrderRepository
│   ├── users.rs
│   ├── users/ …
│   ├── shared.rs                    # domain-free helpers: pagination, clock, ids
│   └── shared/
└── tests/
    ├── common/mod.rs                # helpers shared by integration tests
    └── orders_api.rs
```

### CLI

```
imgtool/
├── src/
│   ├── main.rs                      # parse args, init tracing, run, map error → exit code
│   ├── lib.rs
│   ├── cli.rs                       # clap structs only
│   ├── resize.rs                    # feature: domain + service
│   ├── resize/
│   │   ├── ops.rs                   # pure transformation logic
│   │   └── command.rs               # glue: clap args → service call → output
│   ├── convert.rs
│   └── fs.rs                        # adapter: file system access behind a small trait if tests need it
└── tests/cli.rs                     # assert_cmd / trycmd
```

❌ Layer folders for the whole app (`src/models/`, `src/handlers/`, `src/services/`,
`src/repositories/`) — every change touches four folders and domain boundaries vanish.
❌ `utils.rs`/`common.rs`/`misc.rs` dumping grounds — name modules after what they do.

## Responsibilities

| Module | Does | Doesn't |
|---|---|---|
| `domain.rs` | types, invariants, pure rules, domain errors | I/O, async, framework or DB types |
| `ports.rs` | traits for what the feature needs from the outside world | implementations |
| `service.rs` | use cases: orchestrates domain + ports, transactions boundaries | parse HTTP, know SQL |
| `http.rs` | extract, validate into domain types, call service, map errors to status codes | business rules |
| `postgres.rs` (adapter) | implements the port with sqlx/SeaORM, maps rows ↔ domain | business rules |
| `main.rs` | build adapters, inject into services, start the server | anything testable |

The domain never imports `axum`, `actix_web`, `sqlx`, `sea_orm`, `clap`, `reqwest` or
`tokio` (except `tokio` in rare pure-async utilities). If a domain type needs `serde`,
derive it behind the DTO instead: DTOs live in `http.rs` and convert into domain types.

## Ports — traits at real I/O boundaries

Ports exist for the database, external services, the clock and randomness — places where
tests need a fake. Not for pure logic.

```rust
// orders/ports.rs
use std::future::Future;

pub trait OrderRepository: Send + Sync + 'static {
    fn find(
        &self,
        owner: UserId,
        id: OrderId,
    ) -> impl Future<Output = Result<Option<Order>, StoreError>> + Send;

    fn insert(&self, order: &Order) -> impl Future<Output = Result<(), StoreError>> + Send;
}

pub trait Clock: Send + Sync + 'static {
    fn now(&self) -> jiff::Timestamp;
}
```

- **Native async in traits.** Writing the method as `fn … -> impl Future<Output = …> + Send`
  in the trait guarantees the future is `Send` (needed for `tokio::spawn` and axum
  handlers). Implementations may still write plain `async fn`.
  A bare `async fn` in a public trait gives no `Send` guarantee (rustc warns:
  `async_fn_in_trait`).
- **Generic by default**: the service is generic over its ports — static dispatch, no
  boxing, fakes plug in at compile time.

  ```rust
  // orders/service.rs
  pub struct OrderService<R, C> {
      repo: R,
      clock: C,
  }

  impl<R: OrderRepository, C: Clock> OrderService<R, C> {
      pub fn new(repo: R, clock: C) -> Self {
          Self { repo, clock }
      }

      pub async fn get(&self, owner: UserId, id: OrderId) -> Result<Order, GetOrderError> {
          self.repo
              .find(owner, id)
              .await?
              .ok_or(GetOrderError::NotFound(id))
      }
  }
  ```

- **`dyn` via constructor injection where needed**: the implementation is chosen at
  runtime or per target (config-selected backend, storage backend per platform — SQLite
  on desktop, IndexedDB in the browser), you hold a heterogeneous list (plugins),
  generic parameters spread through too many types, or it is the `App` service of a
  multi-frontend application (`applications.md`). The constructor takes
  `Box<dyn Port>`/`Arc<dyn Port>`; generics there only where a measured hot path needs
  monomorphization. Traits with `async fn`/`impl Future` aren't dyn compatible; for those
  ports use `#[async_trait]` on that trait only (boxes the future, `Send` by default) or
  `dynosaur`. Keep the rest generic.
- **Ports only with real implementations**: a trait needs a second implementation you
  actually use — another backend, or the in-memory test double your tests run against.
  No speculative interfaces "in case we switch databases".
- Name ports after the capability (`OrderRepository`, `PaymentGateway`, `Mailer`), not
  after the technology (`PostgresThing`).
- The fake for tests implements the same trait (in-memory `HashMap` behind a `Mutex`) —
  that's the second implementation that justifies the trait (`testing.md`).
- **No generic `Repository<T>`** before there is a second entity with the same needs —
  one port per aggregate, with the methods the use cases need.

## Adapters at the edge

- One adapter per technology, inside the feature (`orders/postgres.rs`) or — once shared
  by several features — in its own module/crate.
- Adapters translate both ways: rows → domain types (validated with `TryFrom`), driver
  errors → port errors (`errors.md`).
- Adapters own their config types (`PgConfig`), built in `main`.

## Composition root in `main`

```rust
// main.rs (web backend)
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = shop::config::Config::from_env().context("loading configuration")?;
    shop::telemetry::init(&config.log)?;

    let pool = shop::db::connect(&config.database)
        .await
        .context("connecting to database")?;
    let orders = OrderService::new(PgOrderRepository::new(pool.clone()), SystemClock);
    let users = UserService::new(PgUserRepository::new(pool.clone()));

    let api = Router::new()
        .merge(shop::orders::router(Arc::new(orders)))
        .merge(shop::users::router(Arc::new(users)));
    let health = shop::http::health_router(pool);
    let auth = shop::http::AuthState::from_config(&config.auth).await?;
    let app = shop::http::app(api, health, auth, &config.http);

    shop::http::serve(app, config.listen_addr)
        .await
        .context("HTTP server failed")
}
```

- `main` returns `anyhow::Result<()>` (or `ExitCode` for CLIs); it is the only place that
  knows every concrete type.
- No globals for state (`static POOL: OnceLock<…>`); pass dependencies explicitly.
- Only the binary may call `std::process::exit`.

## Features talk through their facade

- `orders.rs` declares its submodules privately (`mod domain; mod postgres; …`) and
  re-exports only what others may use: `pub use domain::{Order, OrderId}; pub use
  service::OrderService;`.
- Other features use `crate::orders::OrderService`, never `crate::orders::postgres::…`.
- Visibility enforces it: submodules are private, items needed across the crate but not
  outside are `pub(crate)`. The compiler then rejects reaching into another feature.
- Cross-feature calls stay rare; shared, domain-free code goes to `shared/`; shared domain
  concepts become their own feature.

## When to split into workspace crates

Split only on a concrete trigger — otherwise add a module:

- the domain must be **compiler-enforced free of I/O** (a `*-domain` crate without
  tokio/sqlx/axum dependencies),
- a **second implementation of a port** that must not pull its driver into the others
  (SQLite adapter vs. browser adapter),
- a part is **published or reused** by other projects,
- a part has different **targets/features** (`no_std`, WASM, FFI, a proc macro),
- a **heavy optional dependency** that most binaries shouldn't compile,
- **build time** or binary size: a measured problem, e.g. a slow-changing core recompiles
  too often,
- several binaries share most of the code.

**No god-crates** (`common`, `utils`, `shared-everything`): code goes to the crate that
uses it; truly shared domain concepts get a named crate or module of their own.

Layout once split — virtual manifest, flat `crates/`, prefixed names:

```
shop/
├── Cargo.toml                 # [workspace] only: members, package defaults, deps, lints, profiles
├── Cargo.lock
├── rust-toolchain.toml
├── docs/adr/
└── crates/
    ├── shop-domain/           # types + rules + port traits; deps: thiserror, serde?, jiff
    ├── shop-postgres/         # adapters; deps: shop-domain, sqlx
    ├── shop-http/             # axum router + handlers; deps: shop-domain, axum
    ├── shop-testing/          # fakes and fixtures, used as dev-dependency only
    └── shop-server/           # binary: composition root; deps: everything above, anyhow
```

- Dependencies point **inward only**: `server → http/postgres → domain`. Check with
  `cargo tree -i shop-domain` — nothing in `domain` may depend on an adapter.
- Feature slices stay **inside** each crate (`shop-domain/src/orders.rs`, …) — crates are
  layers here, features remain modules.
- Each crate with its own decisions gets its own `docs/adr/`.
- Workspace configuration (`[workspace.package]`, `[workspace.dependencies]`,
  `[workspace.lints]`, profiles): `tooling.md`.
- Test helpers shared across crates live in a `*-testing` crate, not behind `#[path]`
  hacks.
