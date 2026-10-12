# Builds and supply chain

How images are built in CI and locally beyond the Dockerfile itself: BuildKit mounts,
build checks, target platform, SBOM and provenance attestations, Trivy scans, and opt-in
signing. Dockerfile rules and complete examples: `references/dockerfile.md`.

Requirements: Docker Engine with BuildKit (default since 23.0), Buildx ≥ 0.15 and
Dockerfile frontend ≥ 1.8 for build checks, Dockerfile ≥ 1.10 for
`--mount=type=secret,env=…`. `# syntax=docker/dockerfile:1` always pulls the newest 1.x
frontend.

## Build checks — `docker build --check`

BuildKit ships a linter for Dockerfiles (stage name casing, shell-form `CMD`, secrets in
`ARG`/`ENV`, undefined variables, …).

```bash
docker build --check .                        # runs the checks only, no build steps
docker build --check -f Dockerfile.ssr .      # per Dockerfile
```

- `--check` exits non-zero on any violation → use it as a CI gate before the real build.
  It still resolves the base images (registry metadata) — run locally only after a short
  confirmation.
- In the Dockerfile, the parser directive `# check=error=true` (next to
  `# syntax=docker/dockerfile:1`) makes every normal build fail on violations.
  `# check=skip=<CheckName>,<CheckName>` disables single checks — only with a comment
  explaining why.
- `hadolint` adds shell-level checks (`RUN` scripts); run it too if installed.

## BuildKit mounts

| Mount | Use | Never |
|---|---|---|
| `--mount=type=cache,target=<dir>` | Package manager caches (`/root/.cache/uv`, `/root/.npm`, `/pnpm/store`, apt) — reused across builds, never in a layer | For build output that must end up in the image |
| `--mount=type=bind,source=<f>,target=<f>` | Lockfile/manifest for the dependency step (`uv.lock`, `pyproject.toml`, `package.json`, lockfile) — read-only, not in a layer | When the command must write the file back |
| `--mount=type=secret,id=<id>[,env=<VAR>\|,target=<path>][,required=true]` | Registry tokens, `.npmrc`, `pip.conf` — exists only during that `RUN` | `ARG`, `ENV`, `COPY` of credentials |
| `--mount=type=ssh` | Private Git dependencies over SSH | `StrictHostKeyChecking=no`, copied private keys |

### apt in a build stage

Debian images delete downloaded packages via `/etc/apt/apt.conf.d/docker-clean`, which
makes an apt cache mount useless. Docker's reference pattern (build stage only — the
runtime stage installs no packages if at all possible):

```dockerfile
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev
```

`sharing=locked` because apt needs exclusive access; no `rm -rf /var/lib/apt/lists/*`
needed — the lists live in the cache mount, not in the layer.

### Secrets

```dockerfile
# Token as an environment variable for one RUN (Dockerfile >= 1.10)
RUN --mount=type=secret,id=npm_token,env=NPM_TOKEN,required=true \
    --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

# Whole config file mounted at the path the tool reads
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,required=true \
    npm ci --no-audit --no-fund
```

- `required=true` when the build can't succeed without it (private registry) — fails
  fast instead of a confusing 401 later. `required=false` (default) only for optional
  credentials.
- Never echo, `cat` or interpolate the value into a logged command. `--progress=plain`
  shows every command line; a leaking `RUN` leaks into CI logs even if the layer is clean.
- Build: `docker buildx build --secret id=npm_token,env=NPM_TOKEN .` or
  `--secret id=npmrc,src=$HOME/.npmrc .` — the value comes from the caller's environment.
- Dependency install scripts can read the mounted secret: use least-privilege, read-only
  registry tokens.

### SSH for private Git dependencies

```dockerfile
RUN --mount=type=ssh \
    --mount=type=cache,target=/root/.cache/uv \
    mkdir -p -m 0700 /root/.ssh \
 && ssh-keyscan git.example.com >> /root/.ssh/known_hosts \
 && uv sync --locked --no-install-project --no-dev
```

- Build with `docker buildx build --ssh default .` — every key in the forwarding agent
  (`ssh-add -l`) is usable by that `RUN`; expose only the deploy key the build needs.
- `ssh-keyscan` trusts whatever key the server presents; for stronger assurance write the
  provider's published host key into `known_hosts` instead.
- Prefer HTTPS tokens via a secret mount when the Git host supports it — simpler to scope.

## `COPY --link`

`COPY --link --from=<stage> …` creates a layer independent of the layers below it, so a
changed base image doesn't invalidate it and the layer can be reused via `--cache-from`.

- Use it for `COPY --from=<build stage>` into the runtime stage and for static files.
- Not when the destination path contains a symlink (not followed) or when the copy must
  merge with permissions created by an earlier `RUN`.
- `--chown` with `--link` only with **numeric** IDs (`--chown=10001:10001`).

## Registry build cache (CI)

Ephemeral CI runners have no local cache. Export/import BuildKit cache via the registry:

```bash
--cache-from type=registry,ref=registry.example.com/myapp/backend:buildcache \
--cache-to   type=registry,ref=registry.example.com/myapp/backend:buildcache,mode=max
```

Cache mounts (`type=cache`) are **not** part of exported cache — they live on the builder.
Use a separate cache repository/tag; it is never deployed.

## Platforms — `linux/amd64` by default

Cluster images are built for **`linux/amd64` only**, always with an explicit
`--platform` — a laptop on Apple silicon otherwise produces `linux/arm64` images that fail
on `amd64` nodes (`exec format error`).

```bash
docker buildx build --platform linux/amd64 …                     # default for every cluster image
```

- **Local Compose on Apple silicon runs natively (`arm64`)** — no `platforms` setting in
  `compose.yaml`; the dev images never leave the laptop.
- **Cross-build trick for platform-independent output**: run the stage on the builder's
  native platform. A Vite build produces static files, so the SPA build stage uses
  `FROM --platform=$BUILDPLATFORM node:… AS build` and only the nginx runtime stage is
  per-platform — fast on any builder.
- **Not** for the Python venv or Node `node_modules` with native addons — wheels and
  native modules must match the target platform; those stages build for
  `$TARGETPLATFORM` (the default). Built on a non-amd64 machine they run under QEMU
  emulation — much slower; CI uses amd64 runners.

### Exception: multi-arch for ARM servers

Only when a target environment actually runs ARM nodes (documented in the project README):

```bash
docker buildx build --platform linux/amd64,linux/arm64 … --push   # one image index, both platforms
```

- Multi-platform images need an image index: `--push` to a registry, or the containerd
  image store locally (default in Docker Desktop and Engine ≥ 29).
- Every native dependency (wheels, npm addons) must exist for both platforms; the build
  time roughly doubles under emulation — prefer native ARM runners.
- SBOM/provenance and scans then exist per platform (see below).

## SBOM and provenance attestations — every CI build

Every image built in CI carries an SBOM and **max-level provenance** (images live in
private registries only):

```bash
docker buildx build --sbom=true --provenance=mode=max --push …
```

- Provenance `mode=min` is the BuildKit default; `mode=max` adds build arguments, the
  full build definition and layer metadata. **`mode=max` exposes build-arg values** —
  secrets therefore never go through `ARG` (they never do anyway: secret mounts).
- Attestations need an image index: works with `--push` and the `docker-container`
  driver; with the classic `docker` driver only with the containerd image store.
- Inspect (talks to the registry): `docker buildx imagetools inspect <image>@<digest> --format '{{ json .SBOM.SPDX }}'`
  and `--format '{{ json .Provenance.SLSA }}'`; per platform of a multi-platform image
  `--format '{{ json (index .SBOM "linux/amd64").SPDX }}'`.

## Scanning — Trivy

Trivy is the scanner (no Docker Scout). Three scans, all in CI:

```bash
trivy image --scanners vuln,secret --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
  registry.example.com/myapp/backend@"${DIGEST}"            # pushed image, by digest
trivy config --severity HIGH,CRITICAL --exit-code 1 .       # Dockerfile, compose, rendered manifests
trivy fs --scanners secret --exit-code 1 .                  # secrets committed to the repo
```

- Fail the pipeline on fixable HIGH/CRITICAL; unfixable findings are reviewed, accepted
  ones go into `.trivyignore` with a reason and an expiry date.
- Rendered Helm output per environment is scanned with `trivy config <rendered-dir>`
  (`references/helm.md`).
- Locally only if Trivy is already installed — never via `docker run aquasec/trivy`.

## Opt-in: signing and verification (cosign)

**Not part of the default pipeline.** Add it only when the project or the client
requires signed artifacts — and only together with a place that verifies them; an
unverified signature is decoration.

Sign **by digest**, never by tag (a tag can be moved after signing). Signing runs in CI
after the push, with the CI's OIDC identity (keyless) or a KMS key — never a key file in
the repo.

```bash
# CI, after push — DIGEST from --metadata-file (containerimage.digest)
cosign sign registry.example.com/myapp/backend@"${DIGEST}"            # keyless (OIDC)
cosign sign --key <kms-uri> registry.example.com/myapp/backend@"${DIGEST}"

# Verification (talks to the registry and transparency log)
cosign verify registry.example.com/myapp/backend@"${DIGEST}" \
  --certificate-identity-regexp '^https://git\.example\.com/myapp/backend/' \
  --certificate-oidc-issuer https://gitlab.example.com
cosign verify --key cosign.pub registry.example.com/myapp/backend@"${DIGEST}"
```

- Signing pushes a signature to the registry → same approval rule as `docker push`.
- Where it is verified:
  - **OCI chart artifacts** — Flux `OCIRepository.spec.verify` (`references/gitops.md`).
  - **Container images** — `ValidatingAdmissionPolicy` can't check signatures (CEL has
    no registry access); image verification at admission needs a signature-aware
    controller (e.g. Sigstore policy-controller) chosen with the platform when the
    requirement comes up. Kyverno and OPA Gatekeeper are not used.

## CI pipeline (reference)

```bash
# 1. Lint
docker build --check .
command -v hadolint && hadolint Dockerfile

# 2. Build, attest, push (approval rules apply when run by hand)
docker buildx build \
  --platform linux/amd64 \
  --sbom=true --provenance=mode=max \
  --secret id=npm_token,env=NPM_TOKEN \
  --build-arg VERSION="${VERSION}" \
  --build-arg REVISION="$(git rev-parse HEAD)" \
  --build-arg CREATED="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --cache-from type=registry,ref=registry.example.com/myapp/backend:buildcache \
  --cache-to type=registry,ref=registry.example.com/myapp/backend:buildcache,mode=max \
  --metadata-file build-metadata.json \
  --tag registry.example.com/myapp/backend:"${VERSION}" \
  --push .

# 3. Trivy: image by digest, config, secrets (see "Scanning")
# 4. Opt-in only: cosign sign by digest
# 5. Promote tag + digest via GitOps
```

- Tags are immutable versions (`1.4.2`, `1.5.0-dev.42`); the registry enforces tag
  immutability where possible. The **digest** from `build-metadata.json` goes into the
  GitOps values (`references/gitops.md`).
- Rebuild on base image updates (Renovate/Dependabot bump tag + digest together).

## Local verification

```bash
docker image inspect backend:dev --format '{{.Config.User}}'          # numeric non-root
docker image inspect backend:dev --format '{{json .Config.Cmd}} {{json .Config.Entrypoint}}'
docker history --no-trunc backend:dev                                  # layer sizes, no secrets in commands
docker buildx imagetools inspect python:3.14.8-slim-trixie             # digest of a base image (registry — ask first)
```

- `docker history` shows only the final image's layers — credentials copied in an
  intermediate stage still sit in the builder cache. The static Dockerfile check
  (`references/security-checklist.md` §3.1) catches those.
- `docker image inspect` / `docker history` on local images are fine without asking.
  `docker build`, `docker build --check`, `docker compose build|up` and
  `docker buildx imagetools inspect` need a short confirmation first (they pull images or
  registry metadata); pushing, signing and `--push` need explicit approval.

## Review checklist

- [ ] `docker build --check` (and hadolint) pass in CI.
- [ ] Dependency steps use bind mounts for manifests and cache mounts for package caches;
      apt only in build stages with the `docker-clean` fix and `sharing=locked`.
- [ ] Credentials only via `--mount=type=secret` (`required=true` where mandatory) or
      `--mount=type=ssh`; no `StrictHostKeyChecking=no`.
- [ ] Runtime `COPY --from` uses `--link` (numeric `--chown` if any).
- [ ] `--platform linux/amd64` on every cluster image (multi-arch only for documented
      ARM targets); platform-independent stages on `$BUILDPLATFORM` only.
- [ ] `--sbom=true --provenance=mode=max` on every CI build; no secret in any build arg.
- [ ] Trivy image (by digest), config and secret scans gate the pipeline.
- [ ] Digest promoted via GitOps.
- [ ] Only if the project opted in to signing: signed by digest in CI and verified
      (Flux for charts, a signature-aware admission controller for images).
