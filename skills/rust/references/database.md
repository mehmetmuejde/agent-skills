# Database — PostgreSQL with sqlx or SeaORM, SQLite for local apps

## One data layer per project

Servers use PostgreSQL through **either** sqlx 0.9 (SQL first, compile-time checked)
**or** SeaORM 2 (entities + query builder, built on sqlx). Detect it from `Cargo.toml` and
never add the other one. Both live **only in adapters** (`orders/postgres.rs`); the domain
never sees `sqlx` or `sea_orm` types (`architecture.md`).

Local applications (desktop, browser) store data on the device: SQLite via `rusqlite`
natively and an IndexedDB snapshot in the browser, behind synchronous ports — see
"Ports for application cores" below.

## Shared rules

- **One pool per process**, created in the composition root, stored in the adapter (or
  app state). Never a connection or pool per request.
- Pool limits are explicit: `max_connections` (sum over all replicas below the server's
  `max_connections`), `acquire_timeout` of a few seconds, statement timeout on the role or
  per transaction (`SET LOCAL statement_timeout = '5s'`).
- **Rows are not domain types.** Query into a row struct, convert with `TryFrom` into the
  domain type — that's where invalid data from the database is caught.
- **Parameterized only.** User input never becomes SQL text (see below for dynamic
  ordering/filtering).
- **Migrations run as a one-shot job** (a `migrate` subcommand of the binary, executed by
  the Kubernetes migration Job / Compose service) — never implicitly at server startup
  with several replicas racing. Same image, separate command.
- Every list query is paginated with an upper bound on `limit`.
- Integrity in the database: `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys. Check-then-act
  on shared state (stock, balances, "only one active X") uses `SELECT … FOR UPDATE`, a
  unique constraint, or an atomic `UPDATE … WHERE … RETURNING`.
- Map driver errors once (`errors.md`): `RowNotFound` → not found, unique violation →
  conflict, everything else → internal.

## Ownership and tenant scoping (BOLA)

Every query for user-owned data filters by owner/tenant **in the query itself** — never
"load by id, then check":

```rust
// ✅ the scope is part of the query; the port method requires it
async fn find(&self, owner: UserId, id: OrderId) -> Result<Option<Order>, StoreError> {
    let row = sqlx::query_as!(
        OrderRow,
        r#"SELECT id, owner_id, status AS "status: OrderStatusDb", total_cents, created_at
           FROM orders WHERE id = $1 AND owner_id = $2"#,
        id.as_uuid(),
        owner.as_uuid(),
    )
    .fetch_optional(&self.pool)
    .await?;
    row.map(Order::try_from).transpose().map_err(StoreError::Corrupt)
}
```

Port methods for user-owned data take the owner/tenant as a **required parameter**, so a
forgotten scope doesn't compile. "Not found" and "not yours" are the same result.

## sqlx 0.9

```toml
[dependencies]
sqlx = { version = "0.9", default-features = false, features = [
    "runtime-tokio", "tls-rustls-ring-webpki", "postgres",
    "macros", "migrate", "uuid", "time", "json",
] }
```

### Pool

```rust
pub async fn connect(cfg: &DbConfig) -> Result<PgPool, sqlx::Error> {
    PgPoolOptions::new()
        .max_connections(cfg.max_connections)
        .acquire_timeout(Duration::from_secs(3))
        .connect(cfg.url.expose_secret())
        .await
}
```

`PgPool` is a cheap `Arc` handle — clone it into adapters.

### Compile-time checked queries and offline mode

- Prefer the macros `query!`, `query_as!`, `query_scalar!`: SQL and types are checked
  against the real schema at build time. Annotate types where inference needs help
  (`"status: OrderStatusDb"`, `"total!"` for non-null, `"note?"` for nullable).
- Offline data for builds without a database: `cargo sqlx prepare --workspace` writes
  `.sqlx/` — **commit it**. CI and Docker builds set `SQLX_OFFLINE=true`.
- CI verifies the offline data is current: start PostgreSQL, run migrations, then
  `cargo sqlx prepare --workspace --check`.
- `sqlx-cli` comes in the same minor version as the `sqlx` crate
  (`cargo install sqlx-cli --version ~0.9 --no-default-features --features postgres,rustls`
  — a tool install, ask first).

### Runtime queries and dynamic SQL

- Non-macro functions (`sqlx::query`, `query_as::<_, Row>`) are fine where the macros
  can't be used; they still bind parameters with `.bind(value)`.
- Since 0.9 the query functions accept only `&'static str` or an explicit
  `AssertSqlSafe(…)` wrapper. `AssertSqlSafe` is a review flag: only allowlisted
  fragments, never input.
- Dynamic filters and sorting: `QueryBuilder` with `push_bind` for values; column names
  and directions come from an enum, never from the request.

```rust
#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderSort { CreatedAt, Total }

impl OrderSort {
    fn column(self) -> &'static str {
        match self {
            Self::CreatedAt => "created_at",
            Self::Total => "total_cents",
        }
    }
}

let mut qb = QueryBuilder::<Postgres>::new("SELECT id, total_cents FROM orders WHERE owner_id = ");
qb.push_bind(owner.as_uuid());
if let Some(status) = filter.status {
    qb.push(" AND status = ").push_bind(OrderStatusDb::from(status));
}
qb.push(" ORDER BY ").push(sort.column()).push(" LIMIT ").push_bind(i64::from(limit));
let rows = qb.build_query_as::<OrderSummaryRow>().fetch_all(&pool).await?;
```

### Transactions

```rust
let mut tx = self.pool.begin().await?;
sqlx::query!("UPDATE stock SET quantity = quantity - $1 WHERE sku = $2 AND quantity >= $1",
    i32::from(qty), sku.as_str())
    .execute(&mut *tx)
    .await?;
sqlx::query!("INSERT INTO orders (id, owner_id, total_cents) VALUES ($1, $2, $3)",
    order.id().as_uuid(), order.owner().as_uuid(), order.total().cents())
    .execute(&mut *tx)
    .await?;
tx.commit().await?;          // dropping `tx` without commit rolls back
```

- A use case that writes several tables gets **one adapter method** that runs the whole
  write in one transaction (`place_order`), so the domain never handles transactions.
- Keep transactions short; no external HTTP calls inside one.

### Migrations

- `sqlx migrate add -r <name>` creates `migrations/<timestamp>_<name>.up.sql` / `.down.sql`.
- Embedded with `sqlx::migrate!()` (path `./migrations`) and run by the `migrate`
  subcommand: `sqlx::migrate!().run(&pool).await?`.
- Never edit a migration that already ran in a shared environment; add a new one.
- Destructive changes in expand → migrate → contract steps across releases.

## SeaORM 2

```toml
[dependencies]
sea-orm = { version = "2", default-features = false, features = [
    "sqlx-postgres", "runtime-tokio-rustls", "macros", "with-uuid", "with-time",
] }
```

SeaORM 2 requires Rust ≥ 1.94 (same as sqlx 0.9); `default-features = false` drops
chrono, rust_decimal and JSON support you may not need.

- **Entities are adapter code**: generate them with `sea-orm-cli generate entity` into
  the adapter module (e.g. `orders/entity/`), convert `Model` → domain type with
  `TryFrom`. Never expose `Model`/`ActiveModel` in domain or HTTP code.
- **Writes set fields explicitly** from the validated domain value
  (`ActiveModel { status: Set(…), ..Default::default() }`). Never build an `ActiveModel`
  from client JSON (`from_json`) — that's mass assignment.
- **Scoping**: every `find()` for owned data adds the owner/tenant filter
  (`.filter(order::Column::OwnerId.eq(owner))`); `find_by_id` alone is the IDOR pattern.
- **Connection**: `ConnectOptions::new(url).max_connections(n).acquire_timeout(…)`;
  `record_stmt_in_spans(false)` when statements could contain sensitive literals.
- **Transactions**: `let txn = db.begin().await?; … txn.commit().await?;` or the
  closure helper `db.transaction_async(async |txn| { … }).await`.
- **Raw SQL**: `execute_raw` / `query_one_raw` / `query_all_raw` with
  `Statement::from_sql_and_values(DbBackend::Postgres, "… $1 …", [value.into()])` — values
  always as parameters. (In 2.0 `execute`/`query_*` take SeaQuery statements; the `_raw`
  variants take SQL.)
- **Migrations**: a `migration` crate with `sea-orm-migration`, run by the binary's
  `migrate` subcommand or `sea-orm-cli migrate up` in the migration job.

## PostgreSQL row-level security (RLS)

For multi-tenant systems RLS is the second line of defense behind the `WHERE` filters.

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

Set the tenant **per transaction**, from the authenticated principal, with the
transaction-local form (`is_local = true`):

```rust
pub async fn begin_for_tenant(
    pool: &PgPool,
    tenant: TenantId,
) -> Result<Transaction<'static, Postgres>, sqlx::Error> {
    let mut tx = pool.begin().await?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant.to_string())
        .execute(&mut *tx)
        .await?;
    Ok(tx)
}
```

- The setting ends with the transaction, so a pooled connection never carries another
  request's tenant; a plain `SET` would leak.
- Every tenant-scoped adapter method goes through `begin_for_tenant`; without the setting
  `current_setting` raises and the query fails closed.
- SeaORM: same statement via `txn.execute_raw(Statement::from_sql_and_values(…))` right
  after `begin()`.
- Roles: the app role is not superuser, not `BYPASSRLS` and doesn't own the tables;
  migrations run with a separate owner role.
- Policies live in migrations and are reviewed like code; a test proves tenant A can't
  read tenant B's rows even without the `WHERE` filter (`testing.md`).

## Ports for application cores

Multi-frontend applications (`applications.md`) have a synchronous core, so their storage
ports are synchronous too:

```rust
pub trait ItemRepository {
    fn insert(&mut self, item: &Item) -> Result<(), StorageError>; // Duplicate if the id exists
    fn update(&mut self, item: &Item) -> Result<(), StorageError>; // Missing if the id is unknown
    fn delete(&mut self, id: ItemId) -> Result<bool, StorageError>;
    fn get(&self, id: ItemId) -> Result<Option<Item>, StorageError>;
    fn list(&self) -> Result<Vec<Item>, StorageError>;             // defined order
    fn describe(&self) -> String;                                  // location, for diagnostics
}

#[derive(Debug, thiserror::Error)]
pub enum StorageError {
    #[error("an entry with this id already exists")]
    Duplicate,
    #[error("no entry with this id")]
    Missing,
    #[error("stored data is invalid: {0}")]
    Corrupt(String),
    #[error("storage written by a newer version (schema {found}, supported {supported})")]
    NewerSchema { found: i64, supported: i64 },
    #[error("storage backend failed: {0}")]
    Backend(String),
}
```

- **One method = one unit of work = one transaction.** Multi-step operations get their own
  port method (`move_items`), implemented atomically per backend. Transactions never leak
  into the application layer.
- **Typed errors** (`Duplicate`, `Missing`, `Corrupt`, `Backend`, `NewerSchema`), never
  strings only. (`Corrupt`/`Backend` carry a message here because the driver error type
  must not cross into the core.)
- **Stored data is untrusted on read**: domain types are rebuilt through their validated
  constructors; invalid stored data → `Corrupt`, never a panic.
- **Defined list order** (by creation time, then id) — every backend returns the same
  order, or tests and UIs flicker.
- Synchronous by design: asynchronous backends use an in-memory mirror (browser, below) or
  live behind a server.

### Contract tests — one suite for all adapters

A shared suite defines the behavior every adapter must have:
`contract::run_all(&mut || Box::new(MyRepo::new()))`. It lives in the application crate
behind a `contract-tests` feature that other crates enable only as a dev-dependency
(`tooling.md`). A new adapter is done when it passes the suite **plus** its own specifics:
reopen/persistence, migration, newer schema refused, corrupt data, rollback.

### SQLite with rusqlite (native)

- `rusqlite` 0.40 with the `bundled` feature (no system SQLite); `journal_mode = WAL`,
  `busy_timeout` (e.g. 5 s), `foreign_keys = ON` on every connection, `STRICT` tables.
- **Migrations**: numbered SQL files embedded with `include_str!`, the schema version in
  `PRAGMA user_version`, each migration in its own transaction together with the version
  update.
- **Refuse a database with a newer version** (`StorageError::NewerSchema`) — never
  "repair" or downgrade it.
- **Never edit a released migration**; add a new one.
- Parameterized SQL only (`params![…]`).
- Tests: `Connection::open_in_memory()` for speed, `tempfile` directories for reopen and
  migration tests. SQLite is the real backend here, not a stand-in for PostgreSQL.

### Browser persistence

- In-memory repository + a **versioned JSON snapshot in IndexedDB**, written after each
  change (in order), loaded **before** the UI starts. Refuse newer or corrupt snapshots.
- Request `navigator.storage.persist()` so the browser doesn't evict the data.
- Grow path when snapshots get too big: per-record IndexedDB writes, or SQLite in wasm
  (`rusqlite` with `sqlite-wasm-rs`; OPFS storage only inside a Web Worker).

### PostgreSQL / shared data

- Only **behind a server process**. Desktop and browser frontends talk to an API, never
  to the database.
- The server adapter follows the rules of this file (pool, migrations in the adapter
  crate, sqlx or SeaORM — the starter template's alternative `deadpool-postgres` is not
  part of this stack) and passes the same contract suite against a containerized test
  database in CI.

### Schema evolution checklist

1. New migration file — and a snapshot version bump with backward-compatible reading in
   the browser adapter.
2. Adapter mapping for the new columns/fields.
3. Contract and regression tests for old data: open a database (and a snapshot) created
   by the previous version.
4. Document the change (ADR if the storage format changes).

## Tests

PostgreSQL adapters are tested against real PostgreSQL only — never SQLite as a
stand-in. `#[sqlx::test]` creates a fresh database per test and applies migrations; or
testcontainers. See `testing.md`.
