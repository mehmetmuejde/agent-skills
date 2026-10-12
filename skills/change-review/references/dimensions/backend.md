# Dimension: backend conventions

Runs when Python/FastAPI files changed and are in scope. The subagent gets the full path
of the `fastapi-backend` skill's `SKILL.md`, reads it and the references that match the
changed code, and checks the diff against those rules.

## Focus

- **Parameters and dependencies**: `Annotated` for parameters and dependencies,
  dependency type aliases; no Ellipsis, no `RootModel`, no class dependencies.
  `Depends()` in the router, not in the service; DB session via a dependency, not opened
  by hand and forgotten; authentication and authorization as a dependency, not as a line
  of code inside the handler.
- **Path operations**: return types; `response_model` only where needed; router
  configuration on the `APIRouter`; protected by default; one HTTP operation per
  function; no state change via `GET`; status codes that fit (no 200 on errors, no 500
  where a 4xx belongs).
- **Schemas**: separate input and output schemas; `extra="forbid"` on input schemas;
  constrained fields; no types that let everything through (`dict`, `Any`, missing
  annotations).
- **Async rule**: `async def` only with non-blocking code — blocking calls (`requests`,
  `time.sleep`, sync drivers, file I/O) block the event loop; Asyncer used for mixing;
  sync endpoints in an async project (or the reverse) only on purpose; background tasks
  whose errors nobody sees.
- **Derived integrity**: owner/tenant/role/price never from the client; queries scoped by
  owner/tenant; RLS tenant setting via `SET LOCAL`.
- **Database**: the project's ORM only (SQLAlchemy 2.0 **or** SQLModel), 2.0 query style;
  N+1 — relations accessed in a loop without `selectinload()`/`joinedload()`; queries
  without a limit on growing tables, pagination bounds; missing indexes on columns newly
  filtered or sorted by; parameterized `text()`; constraints/locks for races;
  migration present for every model change, reversible, quality.
- **Structure**: feature slices (`app/features/<domain>/`), public API per feature,
  absolute imports. Routers accept, call a service, return — no business logic and no
  database access in the router. Services are plain functions without FastAPI imports
  (no `Request`, no `HTTPException` deep inside a service). An import of another
  feature's `models` or `service` module instead of its public API is a finding.
- **Errors and logging**: specific exceptions, no swallowed exceptions (`except: pass`,
  a log line without consequence), generic client messages — no stack traces, SQL or
  file paths in responses; audit events; no secrets/PII in logs.
- **Tooling**: dependencies via uv (lockfile updated; not pip or Poetry) — and does the
  new package really belong; new settings have an entry in the example env file.
  Run only if the environment exists: `uv run --no-sync ruff check`,
  `uv run --no-sync ty check`, `uv run --no-sync lint-imports` (import-linter
  contracts).

Always a **Blocker**, whichever dimension finds it:

- a new endpoint without an authorization check, unless it is explicitly meant to be
  public;
- sensitive fields in a response schema — `password_hash`, tokens, internal ids, raw
  data from third-party systems.

Other security topics belong to the security dimension — report them here only if the
security dimension doesn't run.

## Report

Cite the rule (file + section of the backend skill) in `refs`. Severity: rule violation
with functional or security impact = Major; convention only = Minor/Nit. Schema:
`../output-format.md`.
