# Docker Compose for local development

Compose is for **local development only** — never a production deployment format here.
Production runs on Kubernetes (`references/kubernetes.md`).

## Rules

- File name `compose.yaml` at the project root (or the backend repo root); no
  `version:` key (obsolete).
- **PostgreSQL** locally, same major version as production, with `healthcheck`
  (`pg_isready`) and a **named volume**. PostgreSQL ≥ 18 images mount the volume at
  `/var/lib/postgresql` (not `/var/lib/postgresql/data` any more).
- Backend waits for the DB: `depends_on: db: condition: service_healthy`.
- **Migrations are a one-shot service** (`alembic upgrade head`); the backend depends on
  it with `condition: service_completed_successfully`. The app never migrates on
  startup.
- Hot reload via **Compose Watch** (`develop.watch`) + `fastapi dev` / Vite dev server
  — the standard; source bind mounts only as a documented exception. Dev setup only; the
  production image is never started with Watch or a bind mount.
- Ports are published on **`127.0.0.1`** only — a bare `"5432:5432"` exposes the DB to
  the whole network (and Docker bypasses host firewalls like `ufw`).
- `.env` holds local values, is **git-ignored and never committed**; `.env.example` with
  placeholders is committed. Required values use `${VAR:?message}` so Compose fails
  early instead of starting with empty passwords.
- Local credentials are throwaway values, never copies of staging/production secrets.
- Containers run as non-root also locally (the `dev` targets set `USER 10001` /
  `USER 1000`).
- On Apple silicon the dev images run natively as `arm64` — no `platform:` setting;
  cluster images are built for `linux/amd64` in CI (`references/build-and-supply-chain.md`).
- Validate with `docker compose config --quiet` — plain `docker compose config` prints
  the interpolated model including passwords from `.env`; never paste that into logs.
- `init: true` only for images whose PID 1 doesn't handle `SIGTERM` or that spawn child
  processes — not needed for `fastapi`, `react-router-serve` or nginx.
- Destructive commands (`down -v`, `volume rm`, `volume prune`, `system prune`) delete the
  local database: approval first, see `references/guardrails.md`.

## `compose.yaml`

```yaml
name: myapp

services:
  db:
    image: postgres:18.6-trixie
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
    volumes:
      - pgdata:/var/lib/postgresql
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \"$${POSTGRES_USER}\" -d \"$${POSTGRES_DB}\""]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  migrate:
    build:
      context: ./backend
      target: dev                # contains the current migrations (rebuilt by --build)
    command: ["alembic", "upgrade", "head"]
    environment:
      DATABASE_URL: postgresql+psycopg://app:${POSTGRES_PASSWORD}@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  backend:
    build:
      context: ./backend
      target: dev
    environment:
      DATABASE_URL: postgresql+psycopg://app:${POSTGRES_PASSWORD}@db:5432/app
      ENVIRONMENT: local
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy
        restart: true            # restart the backend when Compose restarts/recreates db
      migrate:
        condition: service_completed_successfully
    develop:
      watch:
        - action: sync           # fastapi dev (uvicorn reload) picks the change up
          path: ./backend/app
          target: /app/app
          ignore:
            - "**/__pycache__"
        - action: rebuild        # new dependencies → rebuild the image
          path: ./backend/uv.lock
        - action: rebuild
          path: ./backend/pyproject.toml

  # Optional: Vite inside Docker. Default is running Vite on the host (faster HMR).
  frontend:
    profiles: ["frontend"]
    build:
      context: ./frontend
      target: dev
    environment:
      DEV_API_PROXY_TARGET: http://backend:8000
    ports:
      - "127.0.0.1:5173:5173"
    depends_on:
      - backend
    develop:
      watch:
        - action: sync           # Vite HMR sees the synced files
          path: ./frontend/src
          target: /app/src
        - action: sync
          path: ./frontend/public
          target: /app/public
        - action: sync+restart   # read only at dev-server start
          path: ./frontend/vite.config.ts
          target: /app/vite.config.ts
        - action: rebuild
          path: ./frontend/package-lock.json

volumes:
  pgdata:
```

- **Compose Watch (`develop.watch`) is the standard** for source sync: no host/container
  ownership issues, no host `.venv`/`node_modules` (macOS binaries) leaking into the
  container, dependency changes rebuild automatically. Requirements: the image contains
  the source and the container user can write to the targets (the `dev` stages copy the
  source with `--chown`, `references/dockerfile.md`), and `stat`, `mkdir`, `rmdir` exist
  in the image (true for the slim images).
- `sync` for code with hot reload, `sync+restart` for config read only at startup,
  `rebuild` for lockfiles and manifests. Only listed paths are synced —
  tests, docs and local files never enter the container.
- React Router framework mode: sync `./frontend/app` instead of `src`.
- `$$` escapes `$` so the variable is expanded inside the container, not by Compose.
- The driver in `DATABASE_URL` matches the backend (`psycopg` 3 shown).
- The Vite dev server proxies `/api` to `DEV_API_PROXY_TARGET` (read in
  `vite.config.ts`, default `http://localhost:8000` when Vite runs on the host), so the
  browser talks to one origin like in production.
- Start (short confirmation first — builds and pulls images): `docker compose up --build --watch`;
  with the frontend container: `docker compose --profile frontend up --build --watch`.
- New migration: generate it on the host against the local DB —
  `DATABASE_URL=postgresql+psycopg://app:…@127.0.0.1:5432/app uv run alembic revision --autogenerate -m "…"`
  (watch syncs one way only, files written inside the container never reach the host).
  Apply it with `docker compose up --build migrate` (rebuilds the dev image with the new
  migration, short confirmation first).
- Reset the local DB: `docker compose down -v` deletes the `pgdata` volume — destructive,
  ask first (`references/guardrails.md`).
- Validate after every change: `docker compose config --quiet` (add
  `--profile frontend` to include profiled services).

## Exception: bind mount

Only when Watch doesn't fit — e.g. a tool inside the container must write files back to
the host (code generators, snapshot updates) — and documented in the project README.
Bind mount and Watch are never combined for one service.

```yaml
# compose.bind.yaml — used with: docker compose -f compose.yaml -f compose.bind.yaml up --build   (no --watch)
services:
  backend:
    volumes:
      - ./backend:/app           # the venv lives in /opt/venv, the mount doesn't hide it
```

For a Node service the container's `node_modules` needs its own named volume
(`- frontend_node_modules:/app/node_modules`) so the host's macOS binaries don't shadow it.

## Build secrets in Compose (private package index)

The Dockerfile's `--mount=type=secret,id=uv_index_password` receives the value from the
caller's environment; Compose passes it through `build.secrets`:

```yaml
services:
  backend:
    build:
      context: ./backend
      target: dev
      secrets:
        - uv_index_password
secrets:
  uv_index_password:
    environment: UV_INDEX_INTERNAL_PASSWORD     # read from the host environment, never from compose.yaml
```

Build-time only — the secret is not available in the running container.

## Several repositories

When frontend and backend live in separate repos, the frontend repo can start the
backend stack with `include` instead of copying its services:

```yaml
# frontend/compose.yaml
include:
  - path: ../backend/compose.yaml
services:
  frontend: …
```

Name conflicts between included and local resources are reported as warnings, not merged
— keep service names unique.

## `.env.example` (committed)

```dotenv
# Copy to .env and adjust. Local development values only — never real credentials.
POSTGRES_PASSWORD=change-me-local-only
```

`.gitignore` contains `.env` and `.env.*` with `!.env.example`.

## Production-like smoke test (optional)

Run the **runtime** image locally with the same restrictions as in Kubernetes before
opening a merge request — catches writes to the root filesystem and root assumptions:

```yaml
# compose.prodlike.yaml — used with: docker compose -f compose.yaml -f compose.prodlike.yaml up --build   (no --watch)
services:
  backend:
    build:
      context: ./backend
      target: runtime
    read_only: true
    tmpfs:
      - /tmp
    cap_drop: ["ALL"]
    security_opt: ["no-new-privileges:true"]
```

## Review checklist

- [ ] DB has a healthcheck and a named volume; backend uses `condition: service_healthy`.
- [ ] Migrations run in a one-shot service, not in the backend's startup command.
- [ ] All ports bound to `127.0.0.1`.
- [ ] No secrets in `compose.yaml`; `.env` ignored, `.env.example` present.
- [ ] Source sync via `develop.watch`; a bind mount only as a documented exception, never
      both for one service; dev servers only in the dev setup.
- [ ] `docker compose config --quiet` passes; no rendered config with secrets in logs.
- [ ] Build credentials via `build.secrets`, never `build.args`.
