# Dockerfiles

Rules first, then complete examples for the backend, the static SPA and the React Router
framework server.

## Rules

### Base images and pinning

- Slim Debian images: `python:<x.y.z>-slim-trixie`, `node:<LTS x.y.z>-trixie-slim`,
  `nginxinc/nginx-unprivileged:<x.y.z>-alpine-slim` (or the Debian variant if the
  platform requires it).
- Pin the **full version tag**; in production also the **digest**:
  `FROM python:3.14.8-slim-trixie@sha256:<digest>`. Read the digest with
  `docker buildx imagetools inspect python:3.14.8-slim-trixie` (talks to the registry —
  short confirmation first).
- Let Renovate/Dependabot bump tag and digest together; rebuild regularly — a pinned
  image doesn't get OS security fixes by itself.
- Builder and runtime stage of the backend use the **same Python image**, so the venv's
  interpreter path matches.
- uv comes from the official image at a pinned version:
  `COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/` (digest form:
  `ghcr.io/astral-sh/uv@sha256:<digest>`). Never `uv:latest`.
- Start every Dockerfile with `# syntax=docker/dockerfile:1` (BuildKit features:
  cache/secret/bind mounts, `COPY --chmod`, `COPY --link`, build checks).
- Build checks (`docker build --check`), mount details, target platform (`linux/amd64`), SBOM,
  provenance, Trivy and opt-in signing: `references/build-and-supply-chain.md`.

### Layers and cache

1. Lockfile and manifest (`uv.lock` + `pyproject.toml`, `package.json` + lockfile).
2. Dependency install with a cache mount (`--mount=type=cache`) — not stored in the
   image, reused across builds.
3. Source code.
4. Build / project install.

Source changes then only rebuild steps 3–4. Bind-mount the manifests into the install
step (`--mount=type=bind`) when the command only reads them (`uv sync --locked`, `npm ci`).
apt only in build stages, with cache mounts (`sharing=locked`, see
`references/build-and-supply-chain.md`) and `--no-install-recommends`; avoid apt in the
runtime stage entirely if possible. Copy build output into the runtime stage with
`COPY --link --from=<stage>` — the layer survives base image updates.

### Users and filesystem

- Create a system user with a **fixed numeric UID/GID** (`10001`) and switch with
  `USER 10001:10001`. Kubernetes can only verify `runAsNonRoot` for numeric users.
- `COPY` creates root-owned files — keep it that way for application code. The runtime
  user reads, never writes its own code. No `--chown` to the app user unless a path
  must be writable.
- Must work with a **read-only root filesystem**: no writes outside `/tmp` (mounted as
  `emptyDir` in Kubernetes, `tmpfs` in Compose). Set `PYTHONDONTWRITEBYTECODE=1`; uv
  pre-compiles dependencies with `UV_COMPILE_BYTECODE=1`.
- No `sudo`, no SUID tools added, no shell tricks to drop privileges at runtime.

### Secrets during the build

- Never in `ARG`, `ENV`, a copied file or a `RUN` command line — all of them persist in
  layers or `docker history`.
- Use BuildKit secret mounts; the secret exists only for that `RUN`:

```dockerfile
# Private package index for uv (index named "internal" in pyproject.toml)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=uv_index_password,env=UV_INDEX_INTERNAL_PASSWORD,required=true \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    UV_INDEX_INTERNAL_USERNAME=ci uv sync --locked --no-install-project --no-dev
```

```dockerfile
# Private npm registry token: .npmrc contains //registry.example.com/:_authToken=${NPM_TOKEN}
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=secret,id=npm_token,env=NPM_TOKEN,required=true \
    npm ci --no-audit --no-fund
```

Build: `docker build --secret id=npm_token,env=NPM_TOKEN .` (the value comes from the
caller's environment, never from the repo). `required=true` fails fast when the secret
is missing; private Git dependencies use `--mount=type=ssh`
(`references/build-and-supply-chain.md`).

### Process, signals, health

- Exec form only: `CMD ["fastapi", "run", …]`. Shell form wraps the process in `sh -c`,
  which doesn't forward `SIGTERM` → hard kill after the grace period.
- The app runs as **PID 1**. The kernel doesn't apply default signal actions to PID 1, so
  the process must install its own `SIGTERM` handler — otherwise `docker stop` / pod
  termination waits for the grace period and ends with `SIGKILL` (exit 137).
- No wrapper scripts as PID 1. If an entrypoint script is unavoidable, it ends with
  `exec "$@"` so the app replaces the shell.
- One process per container. In Kubernetes run **one worker** and scale with replicas
  (HPA); `--workers` only for single-host deployments.

| Runtime | Stop signal | Graceful shutdown | Init process needed? |
|---|---|---|---|
| `fastapi run` (Uvicorn) | `SIGTERM` | Uvicorn handles `SIGTERM`/`SIGINT`: stops accepting, finishes in-flight requests | No |
| `react-router-serve` | `SIGTERM` | Handles `SIGTERM`/`SIGINT` and closes the HTTP server — start it directly, not via `npm start` | No |
| nginx-unprivileged | `SIGQUIT` (`STOPSIGNAL` in the base image) | Graceful: finishes open requests | No (nginx master reaps its workers) |
| Anything spawning child processes or without own signal handling | — | — | Yes: `tini` as `ENTRYPOINT ["tini", "--"]`, or `init: true` in Compose / `docker run --init` |

Kubernetes has no `--init`; an image that needs an init process ships `tini` (Debian
package `tini`, installed in the image) itself. The stack above doesn't need one.
Graceful shutdown in Kubernetes additionally needs `preStop` + a matching
`terminationGracePeriodSeconds` (`references/kubernetes.md`).
- `HEALTHCHECK` for Docker/Compose. `python:*-slim` has no `curl` — use Python's
  `urllib`; Kubernetes ignores `HEALTHCHECK` and uses probes (`references/kubernetes.md`).
- Backend health endpoints: liveness `/healthz/live` (process only) and readiness
  `/healthz/ready` (DB reachable), **outside** the `/api` prefix so the Gateway never
  routes them publicly.

### Proxy headers

`fastapi run --proxy-headers` makes Uvicorn use `X-Forwarded-For`/`-Proto` — but only from
trusted proxies. Set them with `--forwarded-allow-ips <ip-or-cidr>` or the
`FORWARDED_ALLOW_IPS` environment variable (Uvicorn reads it when the flag is absent; CIDRs
are supported). The image defaults to `127.0.0.1`; the Helm values set the gateway's
pod CIDR per environment. Never `*` — client IPs for rate limiting and logs become
spoofable.

### Labels

```dockerfile
ARG VERSION=0.0.0-dev
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="backend" \
      org.opencontainers.image.source="https://git.example.com/myapp/backend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}"
```

CI passes `--build-arg VERSION=… REVISION=$(git rev-parse HEAD) CREATED=<RFC 3339>`.
These args are not secret — that's why they are allowed as `ARG`.

## Backend (FastAPI + uv)

Follows the uv Docker guide and `uv-docker-example` (multistage). The venv lives in
`/opt/venv` (`UV_PROJECT_ENVIRONMENT`) so neither Compose Watch syncing into `/app` nor the
bind-mount exception on `/app` touches it.

```dockerfile
# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=python:3.14.8-slim-trixie

FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

# ---------------------------------------------------------------- base
FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid 10001 --no-create-home \
      --home-dir /nonexistent --shell /usr/sbin/nologin app
WORKDIR /app

# ---------------------------------------------------------------- builder
FROM base AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Dependencies only: cached until uv.lock or pyproject.toml change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Project source, then the project itself
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---------------------------------------------------------------- dev (Compose only)
FROM base AS dev
COPY --from=uv /uv /uvx /bin/
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
# Dev only: source owned by the app user so Compose Watch (the standard) can sync
# into it. With the bind-mount exception the mount hides this copy.
COPY --chown=10001:10001 . /app
USER 10001:10001
EXPOSE 8000
CMD ["fastapi", "dev", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------- runtime (default target)
FROM base AS runtime
ARG VERSION=0.0.0-dev
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="backend" \
      org.opencontainers.image.source="https://git.example.com/myapp/backend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}"

# Root-owned, read-only for the app user; no uv, no build tools
COPY --link --from=builder /opt/venv /opt/venv
COPY --link --from=builder /app /app

ENV FORWARDED_ALLOW_IPS=127.0.0.1
USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/live', timeout=2)"]

CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

Notes:

- `fastapi run` reads the entrypoint from `[tool.fastapi]` in `/app/pyproject.toml`
  (working directory `/app`).
- The runtime image contains `alembic.ini` and `migrations/`, so the **same image** runs
  the migration Job (`command: ["alembic", "upgrade", "head"]`).
- Packages needing system libraries at build time (`gcc`, `libpq-dev`): install them in
  `builder` only; the runtime stage gets just the shared libraries (`libpq5`) if a wheel
  doesn't bundle them. Prefer binary wheels (`psycopg[binary]`).
- Build: `docker build -t backend:dev .` (runtime is the last stage, so the default);
  dev image: `docker build --target dev -t backend:devserver .`.

## Frontend — Vite SPA on nginx-unprivileged

```dockerfile
# syntax=docker/dockerfile:1

# ---------------------------------------------------------------- build
# Static output is platform-independent: build on the builder's native platform
FROM --platform=$BUILDPLATFORM node:24.21.0-trixie-slim AS build
WORKDIR /app

RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

COPY . .
# No environment-specific VITE_* here: one image for all environments
RUN npm run build

# ---------------------------------------------------------------- dev (Compose only)
FROM node:24.21.0-trixie-slim AS dev
WORKDIR /app
RUN chown 1000:1000 /app
USER 1000:1000
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/home/node/.npm,uid=1000,gid=1000 \
    npm ci --no-audit --no-fund
# Owned by the node user: Compose Watch syncs into it, Vite writes node_modules/.vite
COPY --chown=1000:1000 . .
EXPOSE 5173
CMD ["node_modules/.bin/vite", "--host", "0.0.0.0", "--port", "5173"]

# ---------------------------------------------------------------- runtime (default target)
FROM nginxinc/nginx-unprivileged:1.30.5-alpine-slim AS runtime
ARG VERSION=0.0.0-dev
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="frontend" \
      org.opencontainers.image.source="https://git.example.com/myapp/frontend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}"

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --chmod=0755 nginx/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
COPY --link --from=build /app/dist /usr/share/nginx/html

# The base image already runs as UID 101 and listens on 8080
USER 101
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
```

- `docker build .` builds the runtime image (last stage); Compose uses `target: dev`
  (`references/compose.md`). React Router framework mode gets the same dev stage with
  `CMD ["node_modules/.bin/react-router", "dev", "--host", "0.0.0.0", "--port", "5173"]`.

pnpm variant of the build stage (pnpm version = `packageManager` in `package.json`;
Node ≥ 25 no longer ships Corepack):

```dockerfile
FROM --platform=$BUILDPLATFORM node:24.21.0-trixie-slim AS build
WORKDIR /app
RUN npm install --global pnpm@12.10.1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile --store-dir /pnpm/store
COPY . .
RUN pnpm run build
```

### `nginx/default.conf`

```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    server_tokens off;
    client_max_body_size 1k;

    gzip on;
    gzip_types text/css text/javascript application/javascript application/json image/svg+xml;

    # Hashed build assets: cache forever; a missing asset is a 404, never index.html
    location /assets/ {
        include /etc/nginx/snippets/security-headers.conf;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    # Runtime config written at container start (see 40-runtime-config.sh)
    location = /config.json {
        include /etc/nginx/snippets/security-headers.conf;
        add_header Cache-Control "no-store" always;
        default_type application/json;
        alias /tmp/runtime-config/config.json;
    }

    location = /healthz {
        access_log off;
        default_type text/plain;
        return 200 "ok\n";
    }

    # SPA fallback: client-side routes get index.html, which is never cached
    location / {
        include /etc/nginx/snippets/security-headers.conf;
        add_header Cache-Control "no-cache" always;
        try_files $uri /index.html;
    }
}
```

**nginx pitfall**: an `add_header` inside a `location` drops *all* `add_header`
directives inherited from `server`. That's why every location that sets a header
includes the security-headers snippet again.

### `nginx/security-headers.conf`

CSP as an **HTTP header** (a `<meta>` CSP can't set `frame-ancestors`). Baseline from the
frontend skill's security reference; adjust origins, no inline scripts.

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; report-to csp-endpoint" always;
add_header Reporting-Endpoints 'csp-endpoint="/api/csp-reports"' always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

`connect-src 'self'` works because the Gateway serves `/api` on the same origin. The CSP
report endpoint must exist in the backend (or point to the error-tracking service).

### Runtime config — `nginx/40-runtime-config.sh`

`VITE_*` values are inlined at build time. Environment-specific **public** values
(API base URL, environment name, error-tracking DSN) are written at container start and
fetched by the app before rendering (validated with Zod, see the frontend skill). The
base image's entrypoint runs executable `*.sh` files in `/docker-entrypoint.d/` before
nginx starts.

```sh
#!/bin/sh
# Writes the public runtime config from APP_PUBLIC_* variables.
# Every value here is visible to every visitor: never put secrets in it.
set -eu

out_dir=/tmp/runtime-config
mkdir -p "$out_dir"

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

cat > "$out_dir/config.json" <<EOF
{
  "apiBaseUrl": "$(json_escape "${APP_PUBLIC_API_BASE_URL:-/api}")",
  "environment": "$(json_escape "${APP_PUBLIC_ENVIRONMENT:-production}")",
  "errorTrackingDsn": "$(json_escape "${APP_PUBLIC_ERROR_TRACKING_DSN:-}")"
}
EOF
```

- Explicit allowlist of keys — never dump the whole environment.
- Writes to `/tmp` only, so it works with `readOnlyRootFilesystem` (`/tmp` is an
  `emptyDir`; nginx-unprivileged keeps its pid and temp files there too).
- Single-line values only.
- Alternative in Kubernetes: render `config.json` from Helm values into a ConfigMap and
  mount it at `/tmp/runtime-config/config.json`; the script is then not needed.

## Frontend — React Router framework mode (Node server)

SSR needs a Node process at runtime; it is not a static deployment.

```dockerfile
# syntax=docker/dockerfile:1

ARG NODE_IMAGE=node:24.21.0-trixie-slim

FROM ${NODE_IMAGE} AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

FROM deps AS build
COPY . .
RUN npm run build

FROM ${NODE_IMAGE} AS prod-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev --no-audit --no-fund

FROM ${NODE_IMAGE} AS runtime
ARG VERSION=0.0.0-dev
ARG REVISION=unknown
LABEL org.opencontainers.image.title="frontend-ssr" \
      org.opencontainers.image.source="https://git.example.com/myapp/frontend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"
ENV NODE_ENV=production \
    PORT=3000
WORKDIR /app
COPY package.json ./
COPY --link --from=prod-deps /app/node_modules ./node_modules
COPY --link --from=build /app/build ./build

# "node" user of the official image, numeric for runAsNonRoot
USER 1000:1000
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

CMD ["node_modules/.bin/react-router-serve", "./build/server/index.js"]
```

- Start the server directly, not via `npm run start` — npm doesn't forward signals
  reliably and adds a process.
- Runtime config: the server reads `process.env` at runtime; pass public values to the
  client through loader data, never secrets.
- Security headers and the per-request CSP nonce are set by the server
  (`entry.server.tsx`), see the frontend skill.
- `/healthz` is a resource route in the app.
- Set `NODE_OPTIONS=--max-old-space-size=<~75 % of the memory limit in MiB>` via the
  Deployment if the default heap doesn't match the limit.

## Lint and scan

Trivy is the scanner (image, config, secrets); CI runs all three
(`references/build-and-supply-chain.md`). Locally only if installed:

```bash
command -v hadolint && hadolint Dockerfile
command -v trivy && trivy config --severity HIGH,CRITICAL .
command -v trivy && trivy fs --scanners secret .
command -v trivy && trivy image --scanners vuln,secret --severity HIGH,CRITICAL --ignore-unfixed backend:dev
```

```bash
docker build --check .     # BuildKit build checks; non-zero exit on violations
```

`docker build --check` needs no extra tool (Buildx ≥ 0.15) but resolves base images from
the registry — locally only after a short confirmation. hadolint/trivy not installed →
say so and skip. Never install, never run them via `docker run`.

## Review checklist

- [ ] `# syntax=docker/dockerfile:1`, multi-stage, runtime stage without toolchain;
      `docker build --check` clean.
- [ ] Base images and uv pinned by full tag (digest for production), no `latest`.
- [ ] Lockfile copied/bound before source; dependency step uses a cache mount;
      `uv sync --locked`, `npm ci`, `pnpm install --frozen-lockfile`.
- [ ] Numeric non-root `USER`; app files root-owned; works with a read-only root fs.
- [ ] No secrets in `ARG`/`ENV`/files; build credentials via `--mount=type=secret`.
- [ ] Exec-form `CMD`; PID 1 handles `SIGTERM` (no `npm start`, no shell wrapper
      without `exec`); no `fastapi dev`/`--reload`; `--proxy-headers` with a narrow
      trusted proxy list.
- [ ] Runtime `COPY --from` with `--link`; platform-independent build stages on
      `$BUILDPLATFORM`, Python venv and native `node_modules` on the target platform.
- [ ] `HEALTHCHECK` present; health paths outside `/api`.
- [ ] OCI labels set.
- [ ] SPA: fallback to `index.html`, long cache only for hashed assets, `no-cache` for
      `index.html`, security headers incl. CSP in every location, runtime config without
      secrets.
