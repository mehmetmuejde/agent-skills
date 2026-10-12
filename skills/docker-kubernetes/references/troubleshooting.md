# Troubleshooting

Read-only diagnosis first, fix through files and Git afterwards. Most commands here only
read — but against a **shared** cluster even reads need approval (safety rules). Local
Docker commands that build, pull or run something (`docker build`, `docker compose
up|build|exec`, `docker buildx imagetools inspect`) need a short confirmation first;
stopping or removing any container, even your own, too (`references/guardrails.md`).
Check the context before anything else:

```bash
kubectl config current-context        # kind-*, k3d-*, minikube, docker-desktop → local
```

Never `kubectl get secret -o yaml|json`, never decode Secret data, never
`flux debug hr --show-values` when values come from Secrets. Mutating "debug" commands
(`kubectl exec`, `port-forward`, `debug`, `rollout restart`, `delete pod`) need approval on
shared clusters.

## Order of investigation

1. **What does the controller say?** Status conditions and events of the object closest
   to the symptom (Pod → ReplicaSet → Deployment → HelmRelease/Application → source).
2. **What does the process say?** Container logs, including the previous container.
3. **What changed?** Last Git commit in the GitOps repo, image tag/digest, chart version.
4. **Fix in Git**, not in the cluster — a manual fix is reverted by the next sync.

## Docker and Compose (local)

```bash
docker compose ps -a                                   # state, health, exit codes
docker compose logs --tail=100 backend                 # app logs
docker compose logs --tail=50 migrate                  # one-shot migration output
docker inspect --format '{{json .State.Health}}' <container>   # healthcheck history
docker compose config --quiet                          # validates the model, prints nothing
docker system df                                       # disk usage by type
# Short confirmation first (they run or build something):
docker compose exec backend python -c "import socket; print(socket.gethostbyname('db'))"
docker build --progress=plain --no-cache --target builder .    # see every step (no secrets in RUN!)
```

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend starts before DB is ready | `depends_on` without `condition: service_healthy` | Healthcheck on `db` + condition |
| `migrate` exits non-zero, backend never starts | Migration error; backend waits on `service_completed_successfully` | Read `migrate` logs, fix the migration |
| `exec format error` in the cluster | Image built on Apple silicon (`arm64`) for `amd64` nodes | CI builds with `--platform linux/amd64` (`references/build-and-supply-chain.md`) |
| `permission denied` writing a file | Non-root user + read-only/root-owned path | Write only to `/tmp`; mount a volume for real data |
| Container stops only after 10 s | Process ignores SIGTERM (shell-form `CMD`, `npm start` wrapper) | Exec-form `CMD`, start the server directly (`references/dockerfile.md`) |
| Port works in container, not from host | Port not published or bound to another interface | `ports: ["127.0.0.1:8000:8000"]`, app listens on `0.0.0.0` |
| Dependency layer rebuilt on every change | `COPY . .` before install, missing `.dockerignore` | Lockfile first, bind/cache mounts, `.dockerignore` |
| Code change not picked up | Compose started without `--watch`, path not listed under `develop.watch`, or a `rebuild` path changed | `docker compose up --build --watch`; check the watch paths in `compose.yaml` |
| `Bind for 127.0.0.1:5432 failed: port is already allocated` | Local PostgreSQL or another stack on the port | Change the host port, don't stop foreign services |
| Old DB schema/data after switching branches | Named volume `pgdata` persists | Migrate down/up; dropping the volume is destructive (`references/guardrails.md`) |

Exit codes: `0` ok · `1` app error · `126/127` command not executable / not found ·
`137` SIGKILL (often OOM — check `docker inspect --format '{{.State.OOMKilled}}'`) ·
`143` SIGTERM.

## Kubernetes workloads

```bash
kubectl get pods -n <ns> -o wide
kubectl describe pod <pod> -n <ns>                     # events, last state, probe failures
kubectl events -n <ns> --for pod/<pod>                 # events for one object
kubectl events -n <ns> --types=Warning
kubectl logs <pod> -n <ns> -c <container>
kubectl logs <pod> -n <ns> -c <container> --previous   # the crashed container
kubectl logs job/backend-migrate -n <ns>               # migration hook
kubectl rollout status deployment/backend -n <ns>
kubectl rollout history deployment/backend -n <ns>
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=backend
kubectl top pod -n <ns> --containers                   # needs metrics-server
kubectl auth can-i --list -n <ns> --as=system:serviceaccount:<ns>:backend
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].image}'
```

| Status / symptom | Check | Typical causes |
|---|---|---|
| `Pending` | `describe pod` → Events | Requests exceed free capacity, ResourceQuota exhausted, PVC not bound, node selector/taints |
| `ImagePullBackOff` / `ErrImagePull` | Events message | Wrong tag/digest, missing `imagePullSecrets` (SealedSecret not yet unsealed), registry auth, wrong platform |
| `CreateContainerConfigError` | Events | Referenced ConfigMap/Secret/key missing — often the SealedSecret wasn't synced before the app |
| Pod rejected (`violates PodSecurity "restricted"`) | ReplicaSet events (`kubectl describe rs`) | Missing `runAsNonRoot`, `seccompProfile`, `capabilities.drop`, `allowPrivilegeEscalation: false` |
| `CrashLoopBackOff` | `logs --previous`, `describe` (exit code) | App error at startup, missing env/secret file, read-only fs write, wrong command |
| `OOMKilled` (exit 137) | `describe` → Last State | Memory limit too low (Node heap: `NODE_OPTIONS=--max-old-space-size`), leak |
| Restarts without crash in logs | `describe` → liveness failures | Liveness checks the DB or is too strict; slow start without `startupProbe` |
| `Running` but `0/1 Ready` | Readiness probe events, `/healthz/ready` | DB unreachable (NetworkPolicy egress, wrong CIDR, credentials) |
| Service has no endpoints | `get endpointslices`, labels vs selector | Selector mismatch, no ready pods |
| Pod can't resolve names | Logs (`Name or service not known`) | Missing allow-DNS NetworkPolicy |
| `connection refused`/timeouts between pods | `get networkpolicy -n <ns>` | Default-deny without an allow rule; CNI must enforce policies |
| Rollout stuck | `rollout status`, new ReplicaSet events | New pods never ready; `maxUnavailable: 0` keeps old pods — that's the safety net |
| Migration hook failed, release failed | `logs job/<name>-migrate` | Failing migration, missing Secret at hook time, NetworkPolicy to DB |

Never "fix" a NetworkPolicy problem by deleting policies — add the missing allow rule in
the chart and let GitOps apply it.

## Gateway API and TLS

```bash
kubectl get gateway -n gateway-system
kubectl describe gateway public -n gateway-system      # listener conditions: Accepted, Programmed, ResolvedRefs
kubectl get httproute -n <ns>
kubectl describe httproute backend -n <ns>             # status.parents[].conditions
kubectl get certificate,certificaterequest -n gateway-system
kubectl describe certificate app-example-com-tls -n gateway-system
kubectl get order,challenge -n gateway-system          # ACME progress
```

| Symptom | Cause |
|---|---|
| HTTPRoute `Accepted: False` (`NotAllowedByListeners`) | Namespace lacks the label from `allowedRoutes`, wrong `sectionName`, hostname not covered by the listener |
| `ResolvedRefs: False` (`BackendNotFound`/`RefNotPermitted`) | Wrong Service name/port; cross-namespace backend without `ReferenceGrant` |
| 404 for `/api/...` | Backend doesn't serve under `/api` itself, or the route attached to the wrong listener |
| Certificate not ready, challenge pending | HTTP-01 route not reachable (redirect route catching it, DNS not pointing to the Gateway), Let's Encrypt rate limit |
| Client IPs all equal the gateway | `FORWARDED_ALLOW_IPS` not set to the gateway CIDR, or the LB doesn't preserve the source IP |

## Sealed Secrets

```bash
kubectl get sealedsecret -n <ns>
kubectl describe sealedsecret backend-secrets -n <ns>   # events/conditions, never the data
kubectl logs -n kube-system deploy/sealed-secrets-controller --tail=100   # name per install
```

- `no key could decrypt secret`: sealed for another cluster/controller key, or the key
  backup wasn't restored after a rebuild → re-seal for this cluster.
- Name/namespace mismatch with `strict` scope → seal again with the correct name and
  namespace.
- Secret exists but pods don't see new values → pods need a rollout (Git-driven
  annotation bump or a reloader).

## Helm (offline)

```bash
helm lint charts/backend --strict -f <env-values>
helm template backend charts/backend -n <ns> -f <env-values> --debug   # render errors with context
helm template … --show-only templates/deployment.yaml
```

`--debug` prints the rendered output even when YAML is invalid — the fastest way to find
broken indentation. `helm get values|manifest|history` read the release from the cluster
(shared → approval).

## Flux

```bash
flux check                                             # controllers and CRDs
flux get all -A --status-selector ready=false          # everything not ready
flux get kustomizations -A
flux get helmreleases -n <ns>
flux get sources oci -A
flux events -n <ns> --for HelmRelease/backend
flux logs --kind=HelmRelease --name=backend -n <ns> --level=error
flux tree kustomization myapp-prod-apps                # what a Kustomization manages
flux debug hr backend -n <ns> --show-status
```

Offline, no cluster:

```bash
flux build kustomization myapp-prod-apps --path ./envs/prod/apps \
  --kustomization-file ./flux/prod/apps.yaml --dry-run  # render what would be applied
flux migrate -f . --dry-run                             # deprecated Flux APIs in the repo
```

Chain to follow: source (`GitRepository`/`OCIRepository` `Ready`, `FetchFailed`) →
Kustomization (build/apply/health-check errors, `dependsOn` not ready) → HelmRelease
(`Released`, `TestSuccess`, install/upgrade failure message) → workloads (above).

| Symptom | Cause |
|---|---|
| Source `FetchFailed` | Auth secret missing/expired, wrong URL/tag, Cosign verification failed, wrong `layerSelector` media type |
| Kustomization `dependency not ready` | Base Kustomization (namespace, SealedSecrets) failing first — fix that one |
| `HealthCheckFailed` | Applied but pods not ready → debug the workload; `timeout` too short |
| `immutable field` on apply | Selector/Job spec changed — needs a new name or `force` (approval) |
| HelmRelease retrying | `install/upgrade.strategy: RetryOnFailure` retries every `retryInterval`; fix the cause in Git |
| Stale revision, no error | Object or source `suspend: true`, or controller overloaded |

`flux reconcile`, `suspend`, `resume` change cluster state → approval.

## Argo CD

```bash
argocd app get backend-prod                    # sync + health status, conditions
argocd app diff backend-prod                   # Git vs. live
argocd app history backend-prod
argocd app resources backend-prod
kubectl get application -n argocd backend-prod -o jsonpath='{.status.conditions}'
```

All of these talk to the Argo CD server → shared environment, ask first.
`OutOfSync` with `replicas` → the chart still renders `replicas` with HPA enabled;
`ComparisonError` → render error (often `lookup` or missing values file);
`SyncFailed` at `PreSync` → the migration hook (Job logs above).

## Report

For every finding: symptom, evidence (condition/event/log line), root cause, fix as a
file change (chart, values, GitOps repo) — plus what must be done by someone with
cluster access, if anything.
