---
name: docker-kubernetes
description: Apply for any work on containers and their deployment — Dockerfiles and multi-stage builds (FastAPI with uv, React SPA on nginx-unprivileged, React Router framework on Node), .dockerignore files, CI image builds (BuildKit, build checks, linux/amd64, SBOM/provenance, Trivy, opt-in cosign), Docker Compose for local development with PostgreSQL and Compose Watch, Helm charts and values per environment (helm-unittest), Kubernetes manifests (Deployments, probes, PDB, HPA, NetworkPolicy, quotas, RBAC, migration Jobs, ValidatingAdmissionPolicy), Gateway API (Gateway, HTTPRoute, TLS with cert-manager), Sealed Secrets (kubeseal), GitOps with Argo CD or Flux, troubleshooting, and container/Kubernetes security reviews. Also apply before running or suggesting any command that deletes Docker or cluster resources ("clean up", "prune", "reset the DB"). Holds the safety rules for deployment and destructive commands and the hardening rules that always apply; points to references per topic.
---

# Docker and Kubernetes

Rules for building, running and deploying the FastAPI backend and the React frontend.
This file holds what always applies; read the matching reference **before** working on
that topic. Backend and frontend skills only point here for container topics.

| Task | Read |
|---|---|
| Write or review a `.dockerignore` | `references/dockerignore.md` |
| Write or change a Dockerfile, base images, build secrets, signals/PID 1, nginx config, runtime config | `references/dockerfile.md` |
| CI image builds: BuildKit mounts, build checks, registry cache, target platform, SBOM/provenance, Trivy, opt-in cosign signing | `references/build-and-supply-chain.md` |
| Local development with Docker Compose, Compose Watch and PostgreSQL | `references/compose.md` |
| Deployments, probes, PDB, HPA, NetworkPolicy, quotas, RBAC, migration Jobs, admission policies | `references/kubernetes.md` |
| Helm chart layout, values per environment, helm-unittest (mandatory), linting and validation | `references/helm.md` |
| Argo CD / Flux, environments, promotion, drift, rollback, notifications | `references/gitops.md` |
| Gateway, HTTPRoute, TLS, routing `/api` and `/` | `references/gateway-api.md` |
| Secrets in Git: Sealed Secrets, kubeseal, scopes, key backup, rotation | `references/secrets.md` |
| Security review of Dockerfiles, Compose, Helm/Kubernetes, GitOps | `references/security-checklist.md` |
| Something fails: container, Compose stack, pod, rollout, route, certificate, Flux/Argo CD sync | `references/troubleshooting.md` |
| Any command that deletes or resets Docker, Compose, cluster or registry state | `references/guardrails.md` |

## Safety rules — always

Deployments and shared environments are never touched without the user's **explicit,
separate approval right before the command runs**. Earlier approvals don't carry over.

**Needs approval right before running** — name target, context and side effects first:

- `docker push`, `docker buildx build --push`, `docker login`, `helm push`,
  `cosign sign` / `cosign attest` (they write to the registry)
- `helm install` / `upgrade` / `uninstall` / `rollback` against any cluster
- Every mutating `kubectl` command (`apply`, `create`, `delete`, `patch`, `edit`,
  `scale`, `label`, `annotate`, `rollout restart|undo`) and `exec` / `port-forward`
  into a shared cluster
- `kubeseal` that talks to a cluster (`--fetch-cert`, `--validate`, `--re-encrypt`) and
  every sealing of real secret values
- `argocd app sync|rollback|delete`, `flux reconcile|suspend|resume`, any GitOps commit
  or push (git rules apply)
- Destructive local commands — name what is lost and offer the narrow alternative
  first (`references/guardrails.md`): `docker compose down -v`, `docker compose rm -v`,
  `docker volume rm|prune`, `docker system prune`, `docker image prune -a`, `docker rmi -f`,
  `docker builder prune -a`, `docker container prune`, `docker network prune`,
  `docker context rm`, and `docker rm -f` / `docker kill` / `docker stop` on containers
  you didn't start

**Allowed without asking** (read-only, nothing pulled, nothing removed):

- Reading files, `docker compose config --quiet`, `docker compose ps|logs`,
  `docker ps`, `docker system df`, `docker image inspect`, `docker history` on local
  images
- **Ask first** (short confirmation, same turn): `docker build`, `docker build --check`,
  `docker compose build|up` and `docker buildx imagetools inspect` — they pull images or
  registry metadata; stopping or removing even a container you started yourself
  (`docker rm <name>`, `docker compose down` without `-v`)
- `flux build kustomization --dry-run`, `flux migrate -f . --dry-run` (offline)
- `helm lint`, `helm template`, `helm unittest`, `kubeconform`, `hadolint`,
  `trivy config|image`, `kube-linter`, `cosign verify` — **only if already installed**
- `kubectl get|describe|logs` against a **local** cluster (kind, k3d, minikube, Docker
  Desktop). Check `kubectl config current-context` first; anything else counts as shared
  → ask, even for reads.

**Never**:

- Install, update or fetch tools — no `brew install`, no `helm plugin install`, no
  `npx`/`uvx`/`pipx run`/`docker run` of a scanner image. Check with `command -v <tool>`;
  missing → say so and skip that step.
- Handle real secret values: don't type, generate, print or log them. Prepare the command,
  the user runs it. Never run `kubectl get secret -o yaml|json` or decode Secret data.
- Commit a raw `kind: Secret`, a `.env` file, a kubeconfig or a sealing-key backup.
- Print a rendered Compose model (`docker compose config` without `--quiet`) or
  `flux debug hr --show-values` into logs or the chat — they contain interpolated
  secrets.

## Stack (binding)

- **Backend**: FastAPI, Python with uv (`uv.lock`), `fastapi run`, PostgreSQL, Alembic.
- **Frontend**: Vite SPA served as static files by `nginxinc/nginx-unprivileged`, or
  React Router framework mode served by a Node server (`react-router-serve`).
- **Base images**: as small as possible, always non-root — `python:<ver>-slim-trixie`,
  `node:<LTS>-trixie-slim` (build and SSR runtime), `nginxinc/nginx-unprivileged`
  (static SPA, listens on **8080**, UID **101**; the `-alpine-slim` variant is fine
  here). Alpine for Python images only after checking that all wheels exist for musl —
  otherwise builds compile from source and get bigger and slower.
- **Always multi-stage**: build tools, compilers, uv, dev dependencies and source maps
  stay in the build stage; the final image holds only what runs.
- **Kubernetes**: one Helm chart per app, values per environment, deployed only through
  GitOps (Argo CD or Flux). Traffic via Gateway API. Secrets via Sealed Secrets.
- **Local development**: Docker Compose with a local PostgreSQL.

Versions verified on 2026-10-10 (re-check the registry before pinning): Python
3.14.8, uv 0.13.0, Node 24.21.0 (Active LTS; Node 26 becomes LTS end of October 2026),
nginx-unprivileged 1.30.5 (stable), PostgreSQL 18.6, Gateway API 1.6, Helm 4.3,
Argo CD 3.5, Flux 2.9, cert-manager 1.21, Sealed Secrets 0.40.

## `.dockerignore` — mandatory

Every image has a `.dockerignore` next to its build context (or a
`<Dockerfile>.dockerignore`). It excludes everything the build doesn't need: VCS data,
virtualenvs, `node_modules`, caches, test/coverage output, build output, docs, `.env*`,
keys, IDE and local tool configuration, Dockerfiles, compose files, CI and deployment
config, local DB data, logs.

- Why: smaller context and faster builds; `COPY . .` doesn't bust the cache on every
  unrelated change; secrets and local files never land in a layer.
- Patterns match from the context root: use `**/__pycache__`, `**/*.pyc` — a bare
  `*.pyc` only matches at the root (unlike `.gitignore`).
- Allowlist style (`*` then `!` exceptions) is preferred when the layout is stable.

Complete examples and the trade-off: `references/dockerignore.md`.

## Images — always

- **Multi-stage**: build stage with toolchain, runtime stage without it (no uv, no
  compilers, no npm cache, no source maps unless intended).
- **Pin** every base image by full version tag; production images additionally by
  digest (`image:tag@sha256:…`). Never `latest`, never a floating major only.
- **Layer order for cache**: lockfile and manifest → dependency install (with
  `--mount=type=cache`) → source → build.
- **Non-root with a numeric UID**: `USER 10001:10001` (backend), `101` (nginx-unprivileged),
  `1000` (node). A user *name* makes `runAsNonRoot` unverifiable for the kubelet.
- **App files owned by root and read-only** for the runtime user; the image runs with a
  read-only root filesystem and gets writable `/tmp` from a volume.
- **No secrets in `ARG`, `ENV`, `COPY` or any layer** — build-time credentials only via
  `RUN --mount=type=secret`. Build args and env are visible in the image history.
- **Exec-form `CMD`/`ENTRYPOINT`** (`["fastapi", "run", …]`) so the process is PID 1 and
  receives `SIGTERM`; the server is started directly (no `npm start`, no shell wrapper
  without `exec`). One process per container; scale with replicas, not workers.
- **Build hygiene**: manifests bind-mounted and package caches cache-mounted in the
  dependency step; runtime `COPY --link --from=…`; `docker build --check` clean in CI.
- **Supply chain** (every CI build): `--platform linux/amd64` (multi-arch only as a
  documented exception for ARM servers), `--sbom=true --provenance=mode=max`, Trivy
  (image by digest, config, secrets), promote tag **and digest** via GitOps. cosign
  signing is opt-in — only when the project or client requires it
  (`references/build-and-supply-chain.md`).
- **Backend**: `fastapi run --proxy-headers` with the trusted proxy set via
  `--forwarded-allow-ips` or `FORWARDED_ALLOW_IPS` (gateway CIDR per environment). Never
  `fastapi dev` or `--reload` in an image that leaves the laptop.
- **Frontend**: one image for all environments — `VITE_*` is baked at build time, so
  environment-specific public values come from a runtime `config.json` written at
  container start. Never secrets.
- **Health**: `HEALTHCHECK` for Docker/Compose; Kubernetes ignores it and uses probes.
- **OCI labels**: `org.opencontainers.image.{source,revision,version,created}`.
- Lint with `hadolint`, scan with Trivy (`trivy image`, `trivy config`,
  `trivy fs --scanners secret`) — locally only if installed; no Docker Scout.

❌ `FROM python:latest` · ❌ `ARG DB_PASSWORD` · ❌ `COPY . .` before `uv sync` ·
❌ `USER app` · ❌ `CMD fastapi run` (shell form) · ❌ `.env` copied into the image
✅ `FROM python:3.14.8-slim-trixie@sha256:…` · ✅ `RUN --mount=type=secret,id=…` ·
✅ `USER 10001:10001` · ✅ `CMD ["fastapi", "run", "--proxy-headers"]`

## Compose (local development) — always

- PostgreSQL with `healthcheck` (`pg_isready`) and a **named volume**; the backend waits
  with `depends_on: condition: service_healthy`.
- Migrations run as a **one-shot service** (`alembic upgrade head`); the backend depends
  on it with `condition: service_completed_successfully`.
- Source sync with **Compose Watch** (`develop.watch`) — the standard; a source bind
  mount only as a documented exception, never both for one service. `fastapi dev` /
  Vite dev server only in the dev setup. On Apple silicon the dev images run natively
  (`arm64`).
- Published ports bound to `127.0.0.1`.
- `.env` is never committed; `.env.example` with placeholders is. Required variables
  use `${VAR:?message}`. Build credentials via `build.secrets`, never `build.args`.
- Validate with `docker compose config --quiet`; start with
  `docker compose up --build --watch` (short confirmation first).

## Kubernetes — always

- Namespace enforces Pod Security Standard **restricted** and carries a ResourceQuota
  (no LoadBalancer/NodePort) and a LimitRange — both from the environment base, not the
  app chart.
- Pod and container `securityContext`: `runAsNonRoot`, numeric `runAsUser`/`runAsGroup`,
  `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`,
  `capabilities.drop: ["ALL"]`, `seccompProfile.type: RuntimeDefault`.
- No `privileged`, `hostNetwork`, `hostPID`, `hostIPC`, `hostPath`, Docker socket.
- **Requests and memory limits** on every container; probes: startup + liveness
  (process only, never the DB) + readiness (DB and required services).
- ≥ 2 replicas with **PodDisruptionBudget** and topology spread; HPA owns `replicas`
  when enabled.
- **NetworkPolicy default-deny** (ingress + egress) per namespace, then explicit allows
  (gateway → app, backend → DB, DNS).
- Own **ServiceAccount** per app with `automountServiceAccountToken: false`; RBAC only
  if the app calls the API — namespaced Role, no wildcards, no ClusterRole.
- Images by **immutable tag + digest**; never `latest`. Enforced with a
  `ValidatingAdmissionPolicy` in the platform layer (Kyverno/OPA Gatekeeper are not used).
- Every chart has **helm-unittest** suites that run in CI (mandatory); `helm test`
  release tests are optional.
- **Migrations** as a one-shot Job (Helm hook / Argo CD hook), never in app startup;
  schema changes stay backward compatible with the running version (expand/contract).
- Config in ConfigMaps, credentials in Secrets created from SealedSecrets — never
  secrets in ConfigMaps, values files or plain env literals.
- Services are `ClusterIP`; the only entry point is the Gateway. No `NodePort` /
  `LoadBalancer` for apps, never expose the database.

## GitOps — always

- A change to a shared cluster is a commit; rollback is a Git revert.
- Flux: Kustomizations with `prune`, `wait`, `timeout`, `retryInterval` and `dependsOn`
  (base before apps); HelmReleases with `install/upgrade.strategy.name: RetryOnFailure`,
  `driftDetection.mode: enabled`, exact chart versions; error Alerts per cluster.
- Argo CD: AppProject with least privilege, automated sync with prune + self-heal,
  retry with backoff, sync waves (base before apps).
- Validate offline before committing: `helm template` per environment, `flux build
  kustomization --dry-run`, `flux migrate -f . --dry-run`.
- Repo layout: `envs/<env>/` for now; it will be aligned with the user's server setup
  (Helm + Flux CD) later — don't restructure existing repos until then.

## Sources

Built from the OWASP Secure Agent Playbook (CC BY 4.0) — `iac-security-review` skill and
play, limited to Docker, Compose, Helm and Kubernetes — and its secure-code prompts for
Kubernetes (SecCodePrompts, MIT License). Hardening follows the Kubernetes Pod Security
Standards, the CIS Kubernetes Benchmark and the NSA/CISA Kubernetes Hardening Guide.
Image builds follow the uv Docker integration guide (docs.astral.sh/uv) and the
`uv-docker-example` project; tool behaviour per the official docs of Docker, Helm,
Argo CD, Flux, Gateway API, cert-manager, Sealed Secrets, Sigstore and Kubernetes.

Practices adapted (rewritten, not copied) from these published skills:

- `docker/skills` (Apache-2.0): `docker-build-strategies`, `docker-compose-patterns`,
  `docker-destructive-guardrails`, `docker-project-foundations` — BuildKit mounts, build
  secrets/SSH, `COPY --link`, Compose Watch, `config --quiet`, destructive-command tiers.
- `fluxcd/agent-skills` (Apache-2.0): `gitops-knowledge`, `gitops-repo-audit`,
  `gitops-cluster-debug` — HelmRelease strategies, Kustomization ordering and health,
  notifications, repository audit checks, debugging chain.
- `github/awesome-copilot` (MIT): `multi-stage-dockerfile`.
- `affaan-m/ECC` (MIT): `docker-patterns`, `kubernetes-patterns`.
- Jeffallan's skill collection on GitHub (MIT): `kubernetes-specialist`
  (troubleshooting, quotas, chart testing).
- `wshobson/agents` (MIT): `helm-chart-scaffolding`, `k8s-security-policies`,
  `k8s-manifest-generator`, `gitops-workflow`.
