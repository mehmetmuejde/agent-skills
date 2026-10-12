---
name: fastapi-backend
description: Apply for any work on a FastAPI/Python backend — path operations, routers, Pydantic schemas, dependencies, feature modules, database access with SQLAlchemy 2.0 or SQLModel on PostgreSQL, authentication (cookie session + CSRF, bearer JWT, external OIDC provider), streaming/SSE, serving a built frontend, tests, observability and tooling (uv, Ruff, ty, import-linter, fastapi CLI); also when setting up a new FastAPI project or dockerizing a backend. Holds the rules that always apply — uv as the only package manager, vertical feature slices with a public API per feature checked by import-linter, Annotated everywhere, type hints and return types, async only when non-blocking, derived integrity, secure-by-default app setup, repository hygiene (ADRs, scratch notes, .dockerignore) — and points to references per topic.
---

# FastAPI backend

Rules for every FastAPI backend. This file holds what always applies; read the matching
reference **before** working on that topic.

| Task | Read |
|---|---|
| Project layout, new feature, imports between features | `references/structure.md` |
| Writing or changing tests, coverage | `references/testing.md` |
| Dependencies, `yield`, scopes, authorization dependencies | `references/dependencies.md` |
| Database access, models, sessions, migrations | `references/database.md` |
| Login, tokens, cookies, CSRF, OIDC, passwords | `references/auth.md` |
| New or changed endpoint — API security checklist | `references/api-security.md` |
| Streaming: JSON Lines, Server-Sent Events, bytes | `references/streaming.md` |
| Logging, audit trail, OpenTelemetry, error handling | `references/observability.md` |
| uv, Python version, Ruff, ty, pre-commit + gitleaks, `uv audit`, fastapi CLI, Asyncer, HTTPX | `references/tooling.md` |
| Setting up a new FastAPI project | `references/setup.md` |
| Dockerizing the backend (FastAPI-specific workflow) | `references/docker.md` |

## Stack

- **Python**: current stable release, resolved at setup (`references/setup.md`); FastAPI
  requires ≥ 3.10
- **Package manager**: **uv only** — never pip directly, Poetry, pipenv or
  `requirements.txt`; see `references/tooling.md`
- **Structure**: vertical feature slices with a public API per feature, enforced by
  import-linter — see `references/structure.md`
- **Lint/format**: Ruff · **Type check**: ty
- **Database**: PostgreSQL with **either** SQLAlchemy 2.0 + Alembic **or** SQLModel (+
  Alembic). The ORM is fixed per project — detect it from the existing code, never mix.
- **HTTP client**: HTTPX · **Sync/async bridging**: Asyncer

## Use `Annotated` everywhere

Parameters (`Path`, `Query`, `Header`, `Cookie`, `Body`) and dependencies are declared with
`Annotated`. Every reusable dependency gets a type alias:

```python
from typing import Annotated

from fastapi import Depends, Path, Query

CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/{item_id}")
def read_item(
    item_id: Annotated[int, Path(ge=1)],
    current_user: CurrentUserDep,
    q: Annotated[str | None, Query(max_length=50)] = None,
) -> ItemPublic: ...
```

❌ `db: Session = Depends(get_db)` (old default-value style) · ❌ `Query(...)` / `Field(...)`
— never use the Ellipsis `...` as a default; a parameter without default is required.

## Imports and type hints

- **Absolute imports** from the package root (`from app.core.config import settings`) —
  never relative (`from .service import …`).
- **Type hints on every function** — arguments and return. Modern syntax: `list[str]`,
  `int | None` (not `List`, `Optional`).
- No `Any` without a comment giving the reason.

## Schemas and responses

- **Declare a return type** on every path operation. It validates, filters, documents and
  serializes the response (serialization runs in Pydantic's Rust core).
- Use `response_model=` only when the returned object differs from the public schema
  (e.g. returning an ORM object, but exposing `UserPublic`).
- **Separate input and output schemas** per action (`ItemCreate`, `ItemUpdate`,
  `ItemPublic`). Output schemas list only the fields the consumer may see — never
  password hashes, tokens, internal flags or other users' data.
- **Input schemas forbid unknown fields**: `model_config = ConfigDict(extra="forbid")`.
  An action only accepts the fields it is meant to change (mass assignment protection).
- No Pydantic `RootModel` — use `Annotated[list[int], Field(min_length=1), Body()]`.
- Constrain every input: `max_length` on strings, `ge`/`le` on numbers, enums/`Literal`
  instead of free text, `UUID`/`EmailStr`/`HttpUrl` instead of `str`.
- Don't use `ORJSONResponse` / `UJSONResponse` — they are deprecated; the return type is
  faster.

## Derived integrity — the server owns its state

Never take security-relevant values from the client: owner, user id, tenant, role,
price, status, permissions. Derive them from the authenticated user or the database.

- The owner comes from `current_user`, never from the body, a path parameter or a header
  like `X-Tenant-ID`.
- Every query for user-owned data is **scoped by owner/tenant** — "load by id, then
  check" is how IDOR bugs happen. Return **404** for "not found" and "not yours" alike.
- Prices, totals and discounts are computed on the server.

Details and examples: `references/database.md` and `references/api-security.md`.

## Routers

- Put `prefix`, `tags` and shared `dependencies` on the `APIRouter`, not on
  `include_router()`.
- **Protected by default**: authenticated routers carry the auth dependency at router
  level; public endpoints live on an explicitly public router.
- **One HTTP operation per function** — no `@app.api_route(methods=["GET", "POST"])`.
- State-changing operations never use `GET`.

## Async vs. sync

- `async def` **only** when everything inside is awaitable and non-blocking.
- **In doubt, use `def`** — FastAPI runs it in a threadpool, so it doesn't block the event
  loop. The same applies to dependencies.
- Never call blocking code (sync DB driver, `requests`, `time.sleep`, file I/O, CPU-heavy
  work) inside `async def` — it works, but stalls every request on that worker.
- Mixing is done with Asyncer: `await asyncify(blocking_fn)(...)` inside async code,
  `syncify(async_fn)(...)` inside sync code. Prefer it over `run_in_threadpool`.

## Secure-by-default app setup

- **API docs off in production**: `FastAPI(docs_url=None, redoc_url=None,
  openapi_url=None)` unless public docs are intended (ASVS 13.4.5). Toggle via settings.
- **CORS**: explicit origin allowlist from settings; never `"*"` together with
  `allow_credentials=True`.
- **Host header**: `TrustedHostMiddleware` with the real hostnames.
- **Behind a proxy**: trust `X-Forwarded-*` only from the proxy (`fastapi run
  --proxy-headers --forwarded-allow-ips <proxy-ip>`), otherwise client IPs used for rate
  limiting and logs are spoofable (ASVS 4.1.3, 15.3.4).
- **Limits**: request body size (reverse proxy), pagination `limit` with an upper bound,
  upload size, timeouts on every outbound call.
- **Rate limiting**: at the reverse proxy / gateway whenever possible (best practice);
  only if that's not available, with a limiter library inside the app. Login, reset, OTP
  and expensive endpoints always need a limit.
- **Errors**: consumers get generic messages; details go to the log. A last-resort
  exception handler logs and returns a generic 500 (ASVS 16.5). See
  `references/observability.md`.
- **Settings**: `pydantic-settings`; secrets only from the environment/secret store,
  never in code or the repo.

## Repository hygiene — always

- **Python version pinned** in `.python-version` (`uv python pin`), matching
  `requires-python`, Ruff `target-version` and the Docker base image.
- **pre-commit** installed for commit **and** push: gitleaks on staged changes and on
  all unpushed commits, Ruff, `uv lock --check`, import-linter; ty and `uv audit` on
  push. Never bypass with `--no-verify`.
- **`uv audit --locked`** in CI on every MR and on a schedule.
- **`uv.lock` committed**; `.env.example` with placeholders committed, `.env` never.
- **`.dockerignore`** always present next to every Dockerfile (see `docker-kubernetes`).
- **`docs/adr/`** at the project root for decisions that bind the whole project, and in
  every sub-project for decisions that only concern it (Nygard format, sequential
  `0001-…`). A decision lives at the narrowest level it applies to.
- **`.scratch/`** for temporary notes (plans, drafts, findings) — ignored through the
  global git ignore file; never add it to the project `.gitignore`.
- **TODOs** use the project's TODO marker (e.g. `TODO(name): <description>`) so they can
  be found with grep.

Details: `references/tooling.md`.

## Tests are part of the change

Every feature and bug fix ships with pytest tests; CI enforces **80 % line and branch
coverage**. See `references/testing.md`.

## Serving a built frontend

Use `app.frontend("/", directory="dist")` (or `router.frontend()` under a prefix) for a
built SPA instead of mounting `StaticFiles` by hand. Frontend routes have low priority:
API routes match first, then static files and the client-side routing fallback.

## Running

`fastapi dev` locally, `fastapi run` in production. Declare the entrypoint once in
`pyproject.toml`:

```toml
[tool.fastapi]
entrypoint = "app.main:app"
```

## Docker and Kubernetes

Dockerfiles, `.dockerignore`, Compose with a local PostgreSQL, Helm and Kubernetes are
covered by the `docker-kubernetes` skill. Backend-specific points: `fastapi run` with
proxy headers, migrations as a one-shot job (never in app startup), config only via
environment. The dockerizing workflow (assess, plan, approvals, build and smoke test) is
in `references/docker.md`.

## Approvals

Ask the user before binding decisions — new dependency, ORM choice, async vs. sync data
path, decoupling features completely — and record approved ones as an ADR. Never install
tools (uv, Python versions, scanners) yourself; say what is missing. Project setup and
dockerizing run step by step with the user's approval (`references/setup.md`,
`references/docker.md`).

## After writing

Suggest a security review of the result (the `appsec-review` skill) after changes to
auth, endpoints, queries, file handling, outbound calls or dependencies.

## Sources

Combined from the official FastAPI agent skill (fastapi/fastapi, `.agents/skills/fastapi`)
and the OWASP Secure Agent Playbook (CC BY 4.0; ASVS 5.0, OWASP API Security Top 10 2023,
FIASSE v1.0.4).
