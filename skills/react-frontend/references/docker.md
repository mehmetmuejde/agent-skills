# Container image for the frontend

Dockerfiles, nginx config, `.dockerignore`, Compose and Kubernetes are covered by the
[`docker-kubernetes`](../../docker-kubernetes/SKILL.md) skill — follow it for the
image itself:

- Vite SPA on nginx-unprivileged, nginx `default.conf`, security headers, runtime
  config: [`dockerfile.md`](../../docker-kubernetes/references/dockerfile.md)
  ("Frontend — Vite SPA on nginx-unprivileged")
- React Router framework mode on a Node server: same file, "Frontend — React Router
  framework mode"
- `.dockerignore` (allowlist preferred):
  [`dockerignore.md`](../../docker-kubernetes/references/dockerignore.md)
- Image builds in CI, scans, SBOM:
  [`build-and-supply-chain.md`](../../docker-kubernetes/references/build-and-supply-chain.md)
- Local development with Compose Watch:
  [`compose.md`](../../docker-kubernetes/references/compose.md)

This file adds the React-specific facts and the workflow.

## Workflow

1. **Assess** — read-only:

```bash
test -f package.json && head -20 package.json
ls pnpm-lock.yaml package-lock.json 2>/dev/null || echo "WARNING: no lockfile — install first"
test -f Dockerfile && echo "Dockerfile exists" || echo "no Dockerfile"
test -f .dockerignore && echo ".dockerignore exists" || echo "no .dockerignore"
ls nginx/ 2>/dev/null || echo "no nginx/ config folder"
```

2. **Plan** — list the files (`Dockerfile`, `.dockerignore`, `nginx/default.conf`,
   `nginx/security-headers.conf`, runtime-config script) with the resolved image tags.
   Existing files are only overwritten after the user confirmed it. Wait for approval.
3. **Write** the files after approval.
4. **Build test** — a separate approval (it pulls images):

```bash
docker build -t frontend:dev .
docker image ls frontend:dev
docker run --rm -p 8080:8080 frontend:dev   # then open http://localhost:8080
```

## Versions — resolve, then pin

- **Node** (build stage): the major of the current LTS, the same as `.nvmrc`
  (resolution command in `setup.md`), pinned to the full version tag.
- **nginx** (serve stage): the current **stable** release — nginx stable lines have an
  even minor version, mainline an odd one. Check the tags of the image the
  `docker-kubernetes` skill uses (`nginxinc/nginx-unprivileged`) and pick the newest
  `<x.even.z>-alpine-slim`.
- **Package manager**: the version from `packageManager` in `package.json`.
- Never `latest`; pin the full tag (and the digest in production).

## React-specific rules

- **`.dockerignore` always exists** — no image without one. `.env*` stays out of the
  build context; only `.env.example` may be re-included.
- **`VITE_*` values are baked into the bundle at build time** and are public. One image
  for all environments: environment-specific public values come from the runtime
  `config.json` (written at container start, fetched and Zod-validated at app startup).
  Never secrets.
- **SPA fallback is mandatory** for client-side routing (`try_files $uri /index.html`):
  without it, reloading a sub-route returns 404. Hashed assets: missing → 404, never
  `index.html`.
- **Caching**: hashed assets `public, max-age=31536000, immutable`; `index.html`
  `no-cache`; runtime `config.json` `no-store`.
- **Non-root, port 8080** — unprivileged nginx cannot bind below 1024.
- **Security headers** as HTTP headers from nginx, values from `security.md` (CSP,
  HSTS, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP).
- **Healthcheck** against a cheap endpoint (`/healthz`); Kubernetes uses probes instead.
- **Image size**: a static SPA image should stay well **under 50 MB**. If it doesn't,
  something besides `dist/` got in (check the `.dockerignore`) or the bundle is bloated
  (bundle analysis, `performance.md`).
- **React Router framework mode** (SSR) is not static: it needs a Node runtime image
  (`react-router-serve` or a custom server).
