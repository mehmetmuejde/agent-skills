# Tooling and libraries

## uv

Dependencies are managed with uv only.

```bash
uv add fastapi[standard]          # runtime dependency ([project] dependencies)
uv add --dev ruff ty pytest       # dev dependency ([dependency-groups] dev)
uv sync                           # install from uv.lock
uv lock --upgrade-package <pkg>   # update one package
uv run <cmd>                      # run inside the project environment
uv python pin <version>           # writes .python-version
```

- `pyproject.toml` follows the standards: runtime dependencies in `[project]` (PEP 621),
  dev tools in `[dependency-groups]` (PEP 735), `requires-python` set.
- `uv.lock` is committed.
- ❌ `pip install <pkg>` — bypasses the lock file.
- ❌ Poetry, pipenv or `requirements.txt` as the dependency source.
- ❌ Mixing package managers in one project.
- uv itself is not pinned in the project — the locally installed uv is used; the
  Docker builder pins its uv image (`docker.md`).

## Python version — pinned

```bash
uv python pin 3.14        # writes .python-version (committed)
```

- `.python-version` is committed; uv, CI and the Dockerfile use the same version.
- `pyproject.toml` declares `requires-python = ">=3.14"` (match the pinned minor).
- Ruff's `target-version` matches it (`"py314"`).
- Upgrading Python is one change touching all three places plus the Docker base image.
- Which version to pin for a new project (newest stable with wheels for the core
  dependencies): `setup.md`.

## fastapi CLI

- `fastapi dev` — development server with reload, localhost only.
- `fastapi run` — production server. Behind a reverse proxy add
  `--proxy-headers --forwarded-allow-ips <proxy-ip>`.
- Entrypoint in `pyproject.toml` (`[tool.fastapi] entrypoint = "app.main:app"`); pass a
  file path only if that's not possible.

## Ruff

Linter and formatter — one tool for both. Enable the FastAPI rules (`FAST`) and the
security rules (`S`, flake8-bandit) in addition to the usual sets:

```toml
[tool.ruff]
line-length = 100
target-version = "py314"  # matches .python-version

[tool.ruff.lint]
select = [
    "E", "F", "W", "I", "B", "UP", "S", "FAST", "ASYNC",
    "C4", "ARG", "SIM", "PT", "N",
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ARG"]  # assert and unused fixture arguments are fine in tests
```

`ASYNC` catches blocking calls inside `async def`; `PT` enforces pytest style; `ARG`
flags unused arguments; `N` checks naming.

## ty

Type checker: `uv run ty check`. Type hints on all functions (arguments and return);
modern syntax (`list[str]`, `int | None`).

## Asyncer

Bridges sync and async code. Prefer it over AnyIO/asyncio primitives and over
`run_in_threadpool`:

```python
from asyncer import asyncify, syncify

result = await asyncify(do_blocking_work)(name="World")  # blocking call from async code
result = syncify(do_async_work)(name="World")            # async call from sync code
```

## HTTPX

HTTP client for other APIs — sync and async. Prefer it over Requests.

- One client per app (created in the lifespan), not per request.
- Always set a timeout: `httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))`.
- Keep `follow_redirects=False` (default) unless redirects are intended.
- Validate responses with Pydantic before use.

## Dependencies — stewardship and audit

- Add a library only if the standard library or FastAPI/Pydantic can't do it.
- Prefer maintained packages with an active release history; pin via `uv.lock`.
- **`uv audit`** checks the locked dependencies against the OSV vulnerability database:

  ```bash
  uv audit --locked                      # local, before a push / after dependency changes
  uv audit --locked --output-format sarif > uv-audit.sarif   # CI artifact
  ```

  Runs in CI on every MR and on a schedule (new CVEs appear without code changes).
  A finding fails the pipeline; accepted risks use `--ignore-until-fixed <id>` with a
  comment and a ticket, never a blanket `--ignore`.

## Git hooks — pre-commit

Secrets must never reach the repository. `pre-commit` runs the checks on commit **and**
on push:

```bash
uv add --dev pre-commit
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

```yaml
# .pre-commit-config.yaml
default_install_hook_types: [pre-commit, pre-push]
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1                       # pin; update with `pre-commit autoupdate`
    hooks:
      - id: gitleaks                   # staged changes, on commit
        stages: [pre-commit]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.0
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: gitleaks-push              # all commits not yet on any remote, on push
        name: gitleaks (unpushed commits)
        entry: gitleaks git --redact --verbose --log-opts="--branches --not --remotes"
        language: system
        pass_filenames: false
        stages: [pre-push]
      - id: uv-lock
        name: uv.lock up to date
        entry: uv lock --check
        language: system
        pass_filenames: false
        files: ^(pyproject\.toml|uv\.lock)$
      - id: import-linter
        name: import-linter
        entry: uv run lint-imports
        language: system
        pass_filenames: false
        types: [python]
      - id: ty
        name: ty
        entry: uv run ty check
        language: system
        pass_filenames: false
        types: [python]
        stages: [pre-push]
      - id: uv-audit
        name: uv audit
        entry: uv audit --locked
        language: system
        pass_filenames: false
        stages: [pre-push]
```

- The `gitleaks-push` hook uses the local `gitleaks` binary; the commit hook builds it
  through pre-commit. A false positive goes into `.gitleaks.toml` (allowlist with a
  reason) or a `gitleaks:allow` comment — never `--no-verify`.
- Hooks are a convenience, CI is the gate: CI runs gitleaks over the MR's commits, Ruff,
  ty, import-linter, pytest with coverage and `uv audit` again.
- A leaked secret is rotated immediately — deleting the commit is not enough.
