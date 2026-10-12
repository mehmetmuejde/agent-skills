# Dockerizing a FastAPI project

The Dockerfile, `.dockerignore`, build rules and hardening live in the
`docker-kubernetes` skill — use its backend template, don't write a second one:

- Dockerfile (FastAPI + uv, multi-stage): [`../../docker-kubernetes/references/dockerfile.md`](../../docker-kubernetes/references/dockerfile.md)
- `.dockerignore` (backend allowlist/denylist): [`../../docker-kubernetes/references/dockerignore.md`](../../docker-kubernetes/references/dockerignore.md)
- Compose with PostgreSQL: [`../../docker-kubernetes/references/compose.md`](../../docker-kubernetes/references/compose.md)
- Safety rules for builds and destructive commands: [`../../docker-kubernetes/SKILL.md`](../../docker-kubernetes/SKILL.md)

This file is the workflow and the FastAPI-specific points. Talk to the user in the
conversation language; code and comments in English.

## Versions — resolved, then pinned

- **Python image**: the version from the project's `.python-version`. No
  `.python-version` → resolve the newest stable Python first (`setup.md`).
- **uv in the builder**: the official `ghcr.io/astral-sh/uv` image at the current uv
  release, pinned exactly:

  ```bash
  curl -s https://pypi.org/pypi/uv/json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
  ```

- Pin every resolved tag exactly (digest for production) — never `latest`.
- Report the resolved versions in the plan.

## Step 1: assess

```bash
pwd
ls -la
test -f pyproject.toml && head -20 pyproject.toml
test -f uv.lock && echo "uv.lock present" || echo "WARNING: no uv.lock — run 'uv lock' first"
test -f Dockerfile && echo "Dockerfile exists (overwrite?)" || echo "no Dockerfile"
test -f .dockerignore && echo ".dockerignore exists" || echo "no .dockerignore"
grep -n "tool.fastapi" pyproject.toml || echo "no [tool.fastapi] entrypoint"
```

- No `uv.lock` → the image can't be built reproducibly; lock first.
- Existing `Dockerfile` → ask before overwriting.
- No `[tool.fastapi]` entrypoint → add it (`SKILL.md`, "Running"), `fastapi run`
  reads it.

## Step 2: propose a plan — wait for the user's approval

Files: `Dockerfile` and `.dockerignore` (**always** both). The plan names the resolved
versions and confirms the image properties:

- multi-stage; only the virtualenv and the app code reach the runtime stage — no uv, no
  pip, no compilers (smaller image, smaller attack surface),
- numeric non-root user,
- `PYTHONUNBUFFERED=1` so logs appear immediately,
- `HEALTHCHECK` through the Python standard library on the liveness endpoint (no
  `curl`/`wget` in the image),
- `CMD ["fastapi", "run", …, "--proxy-headers"]` in exec form,
- `.env` never in the image; configuration comes from the environment at runtime
  (Compose, Kubernetes Secrets/ConfigMaps).

Packages with C extensions (psycopg without binary wheel, Pillow, lxml, numpy …):
build dependencies only in the builder stage, runtime stage gets only the shared
libraries; prefer binary wheels.

## Step 3: write the files (after approval)

Adapt the `docker-kubernetes` backend template; check the FastAPI-specific points:

- The `health` feature exists (`/healthz/live`, `/healthz/ready`) — the healthcheck and
  the probes depend on it (`setup.md`).
- Migrations (`alembic.ini`, `app/db/migrations/` or `migrations/`) are in the image —
  the same image runs the migration job; never in app startup.
- API docs are off in production (`SKILL.md`), so `/docs` is not part of the image's
  contract.

## Step 4: build and smoke test — separate approval

`docker build` pulls images — ask right before running:

```bash
docker build -t backend:dev .
docker image ls backend:dev        # report the image size
docker run --rm -p 127.0.0.1:8000:8000 backend:dev
```

In a second terminal:

```bash
curl -f http://127.0.0.1:8000/healthz/live
curl -f http://127.0.0.1:8000/healthz/ready   # needs a reachable database
```

Report the results and the image size. On failures: report them and propose the fix —
no silent changes.

## Workers

One process per container: in Kubernetes one worker per pod, scaled with replicas
(HPA). `fastapi run --workers <n>` only for single-host deployments
([`dockerfile.md`](../../docker-kubernetes/references/dockerfile.md), "Process, signals,
health").
