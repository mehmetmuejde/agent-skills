# New FastAPI project — setup

Sets up the current directory as a FastAPI project with a production-ready
configuration. Talk to the user in the conversation language; code, comments and docs
in the repository are English.

Binding rules: `SKILL.md`, `structure.md`, `tooling.md`, `testing.md`.

## Versions — always current, then locked

Don't copy version numbers from this skill. At setup time:

- **Python**: the newest **stable** release:

  ```bash
  curl -s https://endoflife.date/api/python.json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['latest'])"
  ```

  Check that the core dependencies (pydantic-core, SQLAlchemy, the PostgreSQL driver)
  already ship wheels for it. If not, take the previous minor and tell the user why.
  Pin it with `uv python pin <major>.<minor>`, set `requires-python` to match and derive
  Ruff's `target-version` from it (`tooling.md`).
- **Packages**: `uv add <pkg>` without a version — uv resolves the latest stable release,
  `uv.lock` pins it.
- **uv itself**: whatever is installed locally; it is not pinned in the project.
- **Never** pre-releases (`a`, `b`, `rc`, `dev`).
- If a new **major** of FastAPI, Pydantic or SQLAlchemy/SQLModel breaks something this
  skill assumes, say so before writing files.

Report the resolved versions in the plan (step 2).

## Step 1: assess

```bash
pwd
ls -la
test -f pyproject.toml && head -30 pyproject.toml || echo "no pyproject.toml"
command -v uv && uv --version || echo "uv not installed"
python3 --version
test -d .git && echo "git repo present" || echo "NO git repo"
```

- uv missing → tell the user and stop; **don't install it yourself** (installation:
  docs.astral.sh/uv, e.g. `brew install uv` on macOS).
- Needed Python version missing locally → point it out (`uv python install <version>`
  is the user's call); don't install it yourself.

## Step 2: propose a plan — wait for the user's approval

Include the resolved versions and the open decisions: ORM (SQLAlchemy 2.0 or SQLModel),
sync or async data path, whether features must be fully independent (import-linter
`independence` contract). Ask the user; record the answers as ADRs in `docs/adr/`.

### Project structure

```
app/
├── __init__.py
├── main.py                 # create app, lifespan, middleware, include routers
├── core/                   # config, security, logging, middleware, exceptions
├── db/                     # base, session + SessionDep, migrations/ (Alembic)
├── features/
│   └── health/             # example feature and template for new ones
│       ├── __init__.py  router.py  schemas.py  service.py
└── shared/                 # domain-free helpers (pagination, …)

tests/
├── conftest.py             # engine, session (rollback), client fixtures
└── features/health/test_router.py

docs/adr/                   # binding decisions, 0001-…
```

Real features add `models.py`, `dependencies.py` and `exceptions.py` as needed
(`structure.md`). The `health` feature provides liveness `/healthz/live` (process only) and readiness
`/healthz/ready` (DB reachable), outside any `/api` prefix — the Dockerfile healthcheck
and Kubernetes probes use them (`docker.md`).

### Tooling

| Tool | Purpose |
|---|---|
| uv | package manager and Python version manager — the only one |
| Ruff | linter + formatter |
| ty | type checker |
| import-linter | layers and the public API of features |
| pre-commit + gitleaks | git hooks, secret detection on commit and push |
| `uv audit` | dependency vulnerability scan (pre-push + CI) |
| pytest, pytest-cov, pytest-mock, respx | tests, coverage, mocking |

### Files to be written

- `.python-version`, `pyproject.toml` (PEP 621 `[project]`, `[dependency-groups]`,
  `[tool.fastapi]`, Ruff, pytest, coverage, import-linter contracts)
- `.pre-commit-config.yaml` (hook revisions: the current release tags)
- `.env.example` (placeholders, committed) — `.env` stays untracked
- `app/main.py`, `app/core/config.py`, `app/db/session.py`, `app/features/health/*`
- `tests/conftest.py`, `tests/features/health/test_router.py`
- `docs/adr/0001-…` for the decisions above

## Step 3: write the files — one step at a time

After approval, one step at a time; **get the user's approval again after each step**:

1. Directory structure with `__init__.py` in every package
2. `.python-version` + `pyproject.toml`
3. `.pre-commit-config.yaml`
4. `.env.example`
5. `app/core/config.py` (pydantic-settings)
6. `app/db/session.py` (engine, session factory, `SessionDep`)
7. `app/features/health/` (router + schema + service)
8. `app/main.py`
9. `tests/conftest.py` + the first test
10. ADRs

## Step 4: install — separate approval

Installing changes the environment; ask right before running:

```bash
uv add "fastapi[standard]" pydantic-settings alembic sqlalchemy "psycopg[binary]"
# SQLModel projects: uv add sqlmodel instead of sqlalchemy
uv add --dev ruff ty import-linter pre-commit pytest pytest-cov pytest-mock respx
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Step 5: smoke tests

```bash
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
uv run ty check
uv run lint-imports
uv audit --locked
uv run pytest
uv run fastapi dev
```

Report whether everything is green. On failures: **don't fix on your own** — report them
to the user and propose the fix.

## Related

- Dockerizing the project: `docker.md`
- Rules: `SKILL.md`, `structure.md`, `tooling.md`, `testing.md`
