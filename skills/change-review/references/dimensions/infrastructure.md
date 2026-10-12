# Dimension: infrastructure

Runs when Dockerfiles, `.dockerignore`, Compose files, Helm charts/values, Kubernetes
manifests, Gateway API routes, Sealed Secrets, CI pipelines or deployment configs changed
and are in scope. The subagent gets the full path of the `docker-kubernetes` skill's
`SKILL.md`, reads it and its security checklist, and checks the diff against those
rules.

## Focus

- **`.dockerignore`** exists for every image and excludes everything not needed
  (`.git`, `.venv`, `node_modules`, caches, tests/reports, `.env*`, secrets, IDE and
  editor config files). New files/folders in the repo that should be ignored?
- **Dockerfile**: multi-stage, pinned base images (slim, non-root user with fixed UID),
  cache-friendly layer order, no secrets in `ARG`/`ENV`/layers, exec-form `CMD`,
  no build tools in the final stage.
- **Compose** (local dev): DB healthcheck + `depends_on: condition: service_healthy`,
  named volumes, no real secrets, `.env.example` updated.
- **Helm/Kubernetes**: securityContext (non-root, read-only root FS, drop all
  capabilities, no privilege escalation, seccomp `RuntimeDefault`), requests/limits,
  probes match real health endpoints, no `latest` tags, migrations as one-shot hook job,
  NetworkPolicies, ServiceAccount token not mounted unless needed.
- **Gateway API**: routes match the intended paths/hosts, TLS configured.
- **Secrets**: only Sealed Secrets in Git — never a plain `Secret` or values with real
  credentials; scope correct.
- **GitOps**: changes go through the GitOps repo/app; no manual `kubectl apply` steps in
  docs or CI against shared clusters.
- **CI**: tests, coverage threshold, lint and type checks still run; no secrets echoed;
  pinned action/image versions.

Validate read-only only if the tools are installed: `helm lint`, `helm template … |
kubeconform`, `hadolint`. Never build-push, deploy or apply.

## Report

Severity: secret in Git, root container in production, missing limits/probes that break
rollouts = Blocker/Major; hygiene = Minor. Schema: `../output-format.md`.
