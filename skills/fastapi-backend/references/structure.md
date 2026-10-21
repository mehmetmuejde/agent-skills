# Project structure — vertical feature slices

The backend is organized by **feature** (domain), not by technical layer. A feature is a
vertical slice with everything it needs: router, schemas, models, business logic,
dependencies, exceptions and tests.

```
app/
├── main.py                 # create app, lifespan, middleware, include routers
├── core/                   # cross-cutting: settings, security helpers, logging, errors
│   ├── config.py           # pydantic-settings
│   ├── security.py         # hashing, token verification
│   ├── logging.py
│   ├── middleware.py
│   └── exceptions.py       # last-resort handler, error base classes
├── db/
│   ├── base.py             # DeclarativeBase / SQLModel metadata
│   ├── session.py          # engine, session factory, SessionDep (+ RLS tenant setting)
│   └── migrations/         # Alembic
├── features/
│   ├── orders/
│   │   ├── __init__.py     # public API of the feature
│   │   ├── router.py       # APIRouter — HTTP only
│   │   ├── schemas.py      # Pydantic input/output models
│   │   ├── models.py       # ORM / SQLModel table models
│   │   ├── service.py      # business logic — no FastAPI imports
│   │   ├── repository.py   # data access — queries only, no commits
│   │   ├── dependencies.py # wiring session → repository → service, feature `Depends`
│   │   └── exceptions.py   # domain exceptions
│   └── users/
└── shared/                 # domain-free helpers (pagination, time, ids)

tests/
├── conftest.py
├── features/
│   └── orders/             # mirrors app/features
└── e2e/                    # optional API flow tests
```

**One feature = one domain** (auth, users, orders, payments), self-contained.

What does **not** go into `features/`:

- Database engine, session, base, migrations → `db/`
- Auth helpers (hashing, token verification) → `core/security.py`
- Configuration → `core/config.py`
- Cross-cutting, domain-free utilities → `shared/`

❌ Layer-based layout (`routers/`, `schemas/`, `models/`, `services/` for all features) —
every change touches four folders, boundaries between domains disappear, and with
dozens of features every folder becomes unwieldy.

## Responsibilities

| File | Does | Doesn't |
|---|---|---|
| `router.py` | HTTP: parameters, dependencies, status codes, return types; calls the service | business rules, SQL, touch the session or a repository |
| `service.py` | business rules, transactions (`commit`), calls other features via their public API | import FastAPI, read `Request`, write SQL |
| `repository.py` | queries and writes through the injected session | business rules, `commit`, import FastAPI |
| `schemas.py` | input/output contracts per action | ORM logic |
| `models.py` | tables, relationships, constraints | HTTP concerns |
| `dependencies.py` | wiring session → repository → service, auth/ownership lookups, feature-specific `Depends` | business workflows |

Services raise domain exceptions; the router (or an exception handler) maps them to HTTP
status codes. That keeps services testable without HTTP.

## Layers: router → service → repository

Every feature with data access uses three layers, each talking only to the one below:

```
router (HTTP)  →  service (business rules, transaction)  →  repository (queries)  →  DB
```

- Services and repositories are **classes that receive their collaborators in
  `__init__`** (constructor injection) — they never create a session or another service
  themselves. `dependencies.py` wires them together (`references/dependencies.md`).
- **The service owns the transaction**: it calls `commit`; repositories only `add`,
  `execute` and `flush`. All layers share the request's session, so one request is one
  transaction.
- **The router only takes the service dependency** (`service: OrderServiceDep`) — never
  the session or a repository.
- Keep the layers thin: no pass-through methods without a reason. A feature without data
  access (health, a pure proxy) needs no repository.

## Public API per feature

- A feature's `__init__.py` exports what other features may use — the service and its
  dependency alias, public schemas. Repositories and models stay internal.
- Other features import **only** the public API:
  `from app.features.users import get_user` — never
  `from app.features.users.models import User`.
- No direct access to another feature's tables; go through its service.
- Cross-feature calls stay rare. Logic that several features need moves to `shared/`
  (no domain rules) or into its own feature.

### Enforce it with import-linter

Rules that are only documented rot. import-linter checks the import direction in
pre-commit and CI:

```bash
uv add --dev import-linter
uv run lint-imports
```

```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Layers: main → features → core/db/shared"
type = "layers"
layers = [
    "app.main",
    "app.features",
    "app.core | app.db | app.shared",
]
```

The pre-commit hook is in `tooling.md`; CI runs `uv run lint-imports` again. For fully
decoupled features add an `independence` contract with `modules = ["app.features.*"]` —
features may then not import each other at all, and shared logic must move to
`shared/`. That is a per-project decision: ask the user and record it as an ADR.

## Imports and naming

- Absolute imports from the package root (`from app.core.config import settings`), no
  relative imports.
- Router objects are named `router`; the app includes them in `main.py`.
- One feature = one domain noun in plural (`orders`, `users`, `invoices`).
