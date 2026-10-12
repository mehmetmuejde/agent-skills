# Database — PostgreSQL with SQLAlchemy 2.0 or SQLModel

## One ORM per project

The project uses **either** SQLAlchemy 2.0 **or** SQLModel. Detect it before writing code:

- `from sqlmodel import SQLModel, Field` with `table=True` models → SQLModel
- `DeclarativeBase`, `Mapped[...]`, `mapped_column` → SQLAlchemy 2.0

Never introduce the other one. Migrations run through Alembic in both cases.

## SQLAlchemy 2.0 style

- Models with `Mapped[...]` + `mapped_column()`; queries with `select()` +
  `session.scalars()` / `session.scalar()` / `session.execute()`.
- ❌ Legacy 1.x API: `session.query(...)`, `Column(...)` without `Mapped`.
- ORM models (`models.py`) and Pydantic schemas (`schemas.py`) are separate classes.
  Endpoints return a schema type, never the ORM object as declared type.

```python
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    total_cents: Mapped[int]
```

## SQLModel style

- One base model with the shared fields, a `table=True` model for the table, and
  separate data models per action:
  `HeroBase` → `Hero(HeroBase, table=True)`, `HeroCreate`, `HeroUpdate`, `HeroPublic`.
- **Never return the table model** — return `HeroPublic`. Table models often hold
  fields (hashed password, internal flags) that must not leak.
- Input models set `model_config = ConfigDict(extra="forbid")` like any Pydantic input.
- Partial updates: `data = hero_in.model_dump(exclude_unset=True)` then
  `hero.sqlmodel_update(data)` — the input model defines which fields may change.

## Sessions

- One session per request via a `yield` dependency (`SessionDep`).
- Engine and session factory are created once in a module/lifespan, not per request.
- Commit at one clear place per use case; on exception the session rolls back.

## Sync or async data access

Follows the async rule in `SKILL.md`:

- **Sync engine + `def` endpoints** is the safe default.
- **Async engine** (`create_async_engine` with `asyncpg` or psycopg async) only when the
  whole data path is async. Then:
  - `async_sessionmaker(engine, expire_on_commit=False)`,
  - no lazy loading — use `selectinload()` / `joinedload()`; implicit lazy loads fail
    (`MissingGreenlet`),
  - never call the sync session from async code.

## Ownership and tenant scoping (BOLA, API1 / ASVS 8.2.2)

Every query for user-owned data filters by owner (and tenant in multi-tenant systems)
**in the query itself**:

```python
# ✅ scoped
order = session.scalar(
    select(Order).where(Order.id == order_id, Order.owner_id == user.id)
)

# ❌ load by id, check later (or never)
order = session.get(Order, order_id)
```

- Service/repository functions for user-owned data take the user or tenant as a
  **required parameter** — then forgetting the scope doesn't compile.
- Return 404 for "not found" and "not owned" alike.
- Multi-tenant: `tenant_id` on every tenant-owned table, indexed, filtered in every
  query — **and** PostgreSQL row-level security as second line of defense (below).
- Prefer non-guessable ids (UUID) for externally visible identifiers; it does not replace
  the ownership check.

## PostgreSQL row-level security (RLS)

RLS makes the database enforce tenant/owner isolation even when a query forgets the
filter. Use it for every tenant- or user-owned table in multi-tenant systems.

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;  -- applies to the table owner too

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

- Set the tenant **per transaction**, from the authenticated user — never from the
  request:

  ```python
  session.execute(
      text("SELECT set_config('app.tenant_id', :tenant_id, true)"),  # true = SET LOCAL
      {"tenant_id": str(user.tenant_id)},
  )
  ```

  `SET LOCAL` / `set_config(..., true)` ends with the transaction, so a pooled connection
  never carries another request's tenant. A plain `SET` leaks across requests.
- Do it in the session dependency right after authentication, so no query runs without
  it. Without the setting `current_setting` raises — the query fails closed.
- **Roles**: the app connects with a role that is neither superuser nor `BYPASSRLS` and
  doesn't own the tables. Migrations run with a separate owner role.
- Policies live in Alembic migrations (`op.execute(...)`) and are reviewed like code.
- Test isolation explicitly: a test that queries as tenant A must not see tenant B's rows
  (`testing.md`).
- RLS complements the `WHERE` filters in the code; it doesn't replace them (indexes,
  clear intent, 404 handling).

## Queries

- Parameterized only. `text()` gets bind parameters, never f-strings or `%`/`.format()`
  with user input:
  `session.execute(text("... WHERE id = :id"), {"id": item_id})`.
- Dynamic sorting/filtering: map user input to an allowlist of columns
  (`Literal["created_at", "name"]`), never pass column names through.
- N+1: load relationships explicitly with `selectinload()` / `joinedload()`.
- Lists are always paginated with an upper bound on `limit`.

## Integrity and races

- Enforce invariants in the database: `UNIQUE`, `CHECK`, `NOT NULL`, foreign keys.
- Check-then-act on shared state (stock, balances, "only one active X") needs
  `SELECT … FOR UPDATE` (`.with_for_update()`), a unique constraint or an atomic
  `UPDATE … WHERE` — otherwise two requests can pass the check (ASVS 15.4).

## Migrations (Alembic)

- Review every autogenerated migration before committing it — autogenerate misses
  renames and some constraint changes.
- Never edit a migration that has already run in a shared environment; add a new one.
- Destructive or renaming changes break running clients: expand first (add new column),
  migrate data, contract later (drop old column) in a separate release.

## Exports

CSV/XLSX exports escape cells starting with `=`, `+`, `-`, `@`, tab or carriage return
to prevent formula injection (ASVS 1.2.10).
