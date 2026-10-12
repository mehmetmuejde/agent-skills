# Security review — Docker, Compose, Helm, Kubernetes

Derived from the OWASP Secure Agent Playbook's IaC security review (skill + play) and
its Kubernetes secure-code prompt, limited to containers, Compose, Helm and Kubernetes.
Benchmarks: Kubernetes Pod Security Standards (restricted), CIS Kubernetes Benchmark,
NSA/CISA Kubernetes Hardening Guide, OWASP Kubernetes Security Cheat Sheet.

The review is **read-only**: no edits, no deployments, no requests against clusters.
Fixes go into the report.

## Phase 1 — Scope

- Artifacts: Dockerfiles, `.dockerignore`, `compose*.yaml`, Helm charts (templates +
  every environment's values), plain manifests, GitOps objects (Argo CD/Flux),
  SealedSecrets.
- Target environment (dev / staging / production) and data sensitivity.
- What's outside the repo (Gateway implementation policies, cluster settings like etcd
  encryption, audit logging, admission policies) → **Out of scope / not checked**, not
  a finding.

## Phase 2 — Automated scans (only if installed)

Trivy is the standard scanner (image, config, secrets); the other tools are extras.

```bash
docker build --check .                            # BuildKit build checks — short confirmation first (pulls registry metadata)
command -v trivy       && trivy config --severity HIGH,CRITICAL .
command -v trivy       && trivy fs --scanners secret .
command -v hadolint    && hadolint Dockerfile
command -v kubeconform && helm template … | kubeconform -strict -summary
command -v helm        && helm unittest charts/<app>        # if the plugin is installed
command -v kube-linter && kube-linter lint <rendered-dir>    # optional extra
```

Helm charts are reviewed **rendered** with each environment's values
(`helm template`, see `references/helm.md`) — template-only review misses value-driven
misconfigurations. Missing tools → note it, continue manually, never install.

## Phase 3 — Manual review

Grep hits are candidates; confirm each by reading the file and the rendered output.

### 3.1 Images and Dockerfiles

- [ ] Base images pinned by full tag (digest for production); no `latest`, no floating
      major-only tags; trusted registries only.
- [ ] Multi-stage; runtime stage without compilers, package managers' caches, uv, git,
      curl/wget unless needed.
- [ ] Numeric non-root `USER`; application files root-owned.
- [ ] No secrets in `ARG`, `ENV`, copied files or `RUN` arguments; build credentials via
      `--mount=type=secret`.
- [ ] Exec-form `CMD`; no dev servers (`fastapi dev`, `--reload`, `vite`) in runtime
      images; `--proxy-headers` only with a narrow trusted proxy list (never `*`).
- [ ] `.dockerignore` exists and excludes `.git`, `.env*`, keys, venvs, `node_modules`,
      caches, reports (`references/dockerignore.md`).
- [ ] SPA: CSP and security headers as HTTP headers in every nginx location; no
      secrets in the runtime config.

```bash
rg -n '^FROM\s+\S+:latest\b' -g '*Dockerfile*'                               # latest
rg -n '^FROM\s+[^:@\s]+(\s|$)' -g '*Dockerfile*'                             # no tag (stage names and ${ARG} refs are fine)
rg -n -i '^\s*(ARG|ENV)\s+\w*(PASS|SECRET|TOKEN|API_?KEY|PRIVATE)' -g '*Dockerfile*'
rg -n '^\s*USER\s+(root|0)\b' -g '*Dockerfile*'
rg -n 'fastapi dev|--reload|forwarded-allow-ips[ =]"?\*' -g '*Dockerfile*' -g '*.yaml' -g '*.yml'
rg -n 'COPY\s+\.?\s*\.env|ADD\s+http' -g '*Dockerfile*'
rg -n '^(COPY|ADD)\s.*(\.npmrc|\.pypirc|\.netrc|pip\.conf|id_(rsa|ed25519|ecdsa)|kubeconfig|\.pem\b|\.p12\b)' -g '*Dockerfile*'
rg -n 'StrictHostKeyChecking[ =]+no' -g '*Dockerfile*'
rg -n -i 'build-arg\s+\w*(PASS|SECRET|TOKEN|KEY)' -g '*.yml' -g '*.yaml' -g '*.sh' -g 'Makefile'   # secrets as build args in CI
```

Dockerfiles without a `USER` line run as root — check for its absence, not only for
`USER root`. Credentials copied in an **intermediate** stage never show in
`docker history` of the final image but stay in the builder cache — the static greps
above are the only reliable check.

### 3.2 Compose (local development)

- [ ] Ports bound to `127.0.0.1`; DB not published on all interfaces.
- [ ] No real credentials in `compose*.yaml`; `.env` git-ignored; `.env.example` only
      placeholders.
- [ ] No `privileged: true`, no Docker socket mount, no `network_mode: host`, no
      `pid: host`.

```bash
rg -n '^\s*-\s*"?\d+:\d+' -g 'compose*.y*ml' -g 'docker-compose*.y*ml'        # ports without host IP
rg -n 'privileged:\s*true|docker\.sock|network_mode:\s*host|pid:\s*host' -g '*compose*.y*ml'
git ls-files | rg '(^|/)\.env($|\.)' | rg -v '\.env\.example$'               # committed .env files
```

### 3.3 Pod security (Identity & privileges)

- [ ] Namespace PSS labels `enforce: restricted` (+ audit, warn).
- [ ] `runAsNonRoot: true`, numeric `runAsUser`/`runAsGroup` ≠ 0.
- [ ] `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`,
      `capabilities.drop: ["ALL"]`, no `add`.
- [ ] `seccompProfile.type: RuntimeDefault` (or `Localhost`); AppArmor/SELinux not
      disabled (`Unconfined`).
- [ ] No `privileged: true`, `hostNetwork`, `hostPID`, `hostIPC`, `hostPort`.

```bash
rg -n 'privileged:\s*true|allowPrivilegeEscalation:\s*true|host(Network|PID|IPC):\s*true|hostPort:' <rendered-dir>
rg -n 'runAsUser:\s*0\b|runAsNonRoot:\s*false|readOnlyRootFilesystem:\s*false|Unconfined' <rendered-dir>
rg -n -A3 'capabilities:' <rendered-dir> | rg -n 'add:'
```

### 3.4 Sensitive volume mounts

- [ ] No `hostPath` (especially `/`, `/etc`, `/proc`, `/var/run/docker.sock`,
      `/run/containerd`, `/var/lib/kubelet`).
- [ ] Writable paths only via `emptyDir` (with `sizeLimit`) or PVCs that need it.

```bash
rg -n 'hostPath:|docker\.sock|containerd\.sock|/proc|mountPath:\s*/etc\b' <rendered-dir>
```

### 3.5 Secrets management

- [ ] No `kind: Secret` with data/stringData in Git; only `SealedSecret` (scope
      `strict`).
- [ ] No credentials in ConfigMaps, Helm values, `env.value` literals, annotations,
      Argo CD `helm.parameters` or Flux `values`.
- [ ] Secrets mounted as files; `secretKeyRef` env only where unavoidable.
- [ ] Image pull credentials as sealed `dockerconfigjson`.

```bash
rg -n '^kind:\s*Secret\b' -g '*.y*ml'
rg -n 'stringData:' -g '*.y*ml'
rg -n -i '(password|secret|token|api_?key|private_?key)\s*[:=]\s*\S+' -g '*.y*ml' -g '!**/sealed-secrets/**'
rg -n 'sealedsecrets\.bitnami\.com/(cluster|namespace)-wide' -g '*.y*ml'
```

### 3.6 RBAC and ServiceAccounts

- [ ] Dedicated ServiceAccount per app; `automountServiceAccountToken: false` unless
      the app calls the API.
- [ ] No wildcards in `apiGroups`/`resources`/`verbs`; no `cluster-admin`; namespaced
      `Role` instead of `ClusterRole`.
- [ ] No `secrets` list/watch, `pods/exec`, `escalate`, `bind`, `impersonate`,
      `create` on `pods`/`*/token` for app accounts.

```bash
rg -n "(apiGroups|resources|verbs):.*\*|^\s*-\s*['\"]?\*['\"]?\s*$" <rendered-dir>
rg -n 'cluster-admin|ClusterRoleBinding' <rendered-dir>
rg -n 'serviceAccountName:\s*default|automountServiceAccountToken:\s*true' <rendered-dir>
```

### 3.7 Network security and exposure

- [ ] Default-deny NetworkPolicy (Ingress + Egress) per namespace; explicit allows for
      gateway → app, app → DB, DNS; no blanket `0.0.0.0/0` egress — if a broad range is
      unavoidable: port 443 only and `169.254.169.254/32` excluded.
- [ ] ResourceQuota with `services.loadbalancers: "0"` / `services.nodeports: "0"`
      in app namespaces.
- [ ] Services `ClusterIP`; no `NodePort`/`LoadBalancer` for apps; DB, admin tools,
      metrics, queues never exposed publicly.
- [ ] Gateway listeners with explicit hostnames and TLS; `allowedRoutes` restricted;
      health/metrics/docs not routed publicly (`references/gateway-api.md`).
- [ ] ReferenceGrants narrow.

```bash
rg -n 'type:\s*(NodePort|LoadBalancer)' <rendered-dir>
rg -n 'kind:\s*NetworkPolicy' -g '*.y*ml'                                   # present at all?
rg -n 'from:\s*All|0\.0\.0\.0/0' -g '*.y*ml'
```

### 3.8 Resources and availability (DoS)

- [ ] CPU and memory requests, memory limits on every container (incl. Jobs).
- [ ] Probes: startup, liveness (without DB), readiness.
- [ ] ≥ 2 replicas, PDB, topology spread for production.
- [ ] `emptyDir.sizeLimit` set; Job `activeDeadlineSeconds` and `backoffLimit` set.

### 3.9 Supply chain

- [ ] Images by tag + digest from trusted registries; chart versions pinned; `Chart.lock`
      committed; third-party charts only from verified sources.
- [ ] Trivy in CI: image by digest (`vuln,secret`), `config`, `fs --scanners secret`;
      fails on fixable HIGH/CRITICAL; base images updated by Renovate/Dependabot.
- [ ] SBOM and provenance on every CI build (`--sbom=true --provenance=mode=max`); no
      secret ever passes through a build arg (`mode=max` exposes them).
- [ ] `--platform linux/amd64` for cluster images; multi-arch only for documented ARM
      targets.
- [ ] Every chart has helm-unittest suites that run in CI.
- [ ] Opt-in only (project/client requirement): images and OCI charts signed by digest
      (cosign) and verified — Flux `OCIRepository.spec.verify` for charts, a
      signature-aware admission controller for images. Not a finding when the project
      hasn't opted in.
- [ ] Flux sources: no `insecure: true`; production `OCIRepository` by exact tag, semver
      without wildcards or digest; no cross-namespace `sourceRef`/`chartRef` in shared
      clusters; cloud registries via `spec.provider` (workload identity) instead of static
      secrets.

```bash
rg -n 'image:\s*\S+:latest\b|image:\s*[^:@\s]+\s*$' <rendered-dir>
rg -n 'targetRevision:\s*(HEAD|\*|main|master)\b' -g '*.y*ml'                 # chart sources (Git values refs are fine)
rg -n 'insecure:\s*true' -g '*.y*ml'                                             # Flux/registry sources without TLS
rg -n -B8 'sourceRef:|chartRef:' -g '*.y*ml' | rg 'namespace:'                    # cross-namespace refs: compare by hand
```

### 3.10 Encryption

- [ ] TLS terminates at the Gateway with managed certificates; HTTP only redirects.
- [ ] DB connections use TLS (`sslmode=verify-full` or equivalent) when the DB is
      outside the pod network.
- [ ] Secrets encrypted at rest in etcd — platform setting; out of scope unless the
      cluster config is in the repo.

### 3.11 Logging and monitoring

- [ ] Apps log to stdout/stderr (collected centrally); no secrets/PII in logs.
- [ ] Kubernetes audit logging and alerting exist — platform; note as out of scope if
      not in the repo.

### 3.12 Migrations, Helm and GitOps specifics

- [ ] Migrations as one-shot hook Job with the same image; not in app startup; prerequisite
      Secret synced earlier.
- [ ] securityContext hard-coded in templates, not weakenable via values.
- [ ] No `lookup`, `tpl` on untrusted values, or `--set` secrets in CI/GitOps.
- [ ] No manual `kubectl apply`/`helm upgrade` in scripts or docs for shared clusters;
      prune and self-heal/drift detection on.
- [ ] No destructive commands (`docker compose down -v`, `docker system prune -a
      --volumes`, `kubectl delete namespace`) in setup scripts, Makefiles or READMEs
      without a warning (`references/guardrails.md`).
- [ ] Flux: no deprecated APIs (`flux migrate -f . --dry-run`); HelmReleases use
      `RetryOnFailure`; failure Alerts configured.
- [ ] ValidatingAdmissionPolicy for digest pinning and registry allowlist (Kyverno /
      Gatekeeper are not used) — platform layer; out of scope if not in the repo.
- [ ] Argo CD AppProject restricts source repos, destinations, cluster-scoped kinds.

## Phase 4 — Findings

One block per finding, sorted by severity:

```markdown
### [SEVERITY] Title
- **Resource**: kind/name (file:line, rendered or template)
- **Issue**: what is misconfigured
- **Impact**: what an attacker or failure can achieve
- **Recommendation**: how to fix it
- **Example fix**: corrected YAML/Dockerfile snippet
```

Severity guide:

| Severity | Examples |
|---|---|
| Critical | Privileged container or Docker socket/hostPath `/` mount; plaintext production secret in Git; `cluster-admin` for an app; DB exposed via `LoadBalancer` |
| High | Runs as root / no `runAsNonRoot`; `allowPrivilegeEscalation` allowed; secrets in ConfigMap, image layer or any intermediate build stage; wildcard RBAC; no NetworkPolicies in production; `latest`/unpinned images in production; `cluster-wide` sealed scope for app secrets |
| Medium | Missing limits/probes; capabilities not dropped; no seccomp; writable root fs; SA token auto-mounted without need; missing PDB/replicas for production; `.dockerignore` missing |
| Medium (supply chain) | `StrictHostKeyChecking=no`; Flux source with `insecure: true`; no Trivy scan in CI; no SBOM/provenance; chart without helm-unittest suites; cluster image without `--platform linux/amd64` |
| Low | Missing OCI labels; no digest in dev; missing `HEALTHCHECK`; overly broad but internal egress; build checks not run |

## Phase 5 — Summary

- Counts per severity; the most critical risks first.
- Out of scope / not checked (cluster settings, Gateway implementation, registry).
- Tools that ran and those that were missing.
- Recommended ongoing checks: `docker build --check`, hadolint and Trivy (image,
  config, secrets) in the image pipeline; `helm lint` + helm-unittest + kubeconform +
  `trivy config` on rendered charts per environment; PSS `restricted` enforced;
  ValidatingAdmissionPolicy for digest pinning and the registry allowlist.
