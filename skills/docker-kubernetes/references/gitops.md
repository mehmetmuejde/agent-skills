# GitOps — Argo CD or Flux

Git is the only way into a shared cluster. Nobody runs `kubectl apply` or
`helm upgrade` against dev, staging or production by hand — a change is a commit, the
GitOps controller applies it. Which controller is used is fixed per project; detect it
from the repo (`Application`/`AppProject` → Argo CD, `HelmRelease`/`Kustomization` with
`*.toolkit.fluxcd.io` → Flux).

## Flow

1. App repo CI: test → build image → scan → push image (immutable tag + digest) →
   package and push the chart (if it changed).
2. Promotion: a commit/merge request in the GitOps repo sets `image.tag` +
   `image.digest` (and the chart version) in `envs/<env>/…-values.yaml`.
3. The controller syncs the environment from Git; drift is reverted.
4. Rollback: **revert the Git commit**. No `helm rollback`, `kubectl rollout undo` or
   `argocd app rollback` by hand — the next sync would undo it anyway.

## GitOps repo layout

```
gitops/
  envs/
    dev/
      namespace.yaml              # PSS labels
      network-policies.yaml       # default-deny + DNS
      sealed-secrets/
        backend-secrets.yaml      # SealedSecret, sealed for this cluster
        registry-credentials.yaml
      backend-values.yaml
      frontend-values.yaml
    staging/ …
    prod/ …
  platform/                       # Gateway, cert-manager issuers, controllers (platform team)
  argocd/ or flux/                # controller objects per environment
```

- One folder per environment; **promotion = copying a version from one folder to the
  next** in a reviewed commit (dev → staging → prod).
- Dev may be updated automatically (image automation on dev only); staging and
  production only through reviewed merge requests with an exact tag **and digest**.
- Secrets per environment are sealed for that cluster — never copy sealed files between
  environments (`references/secrets.md`).
- **Ordering**: namespace, policies, quotas and SealedSecrets are applied *before* the
  app releases, so migration hooks find their Secret.
- The controller itself (Argo CD, or Flux via the Flux Operator's `FluxInstance` — Flux
  recommends it over `flux bootstrap`) is installed and upgraded by the platform team,
  not from an app repo.
- **Layout status**: the `envs/<env>/` layout above is the current standard. It will be
  aligned with the user's server setup (Helm + Flux CD) later — until then don't
  restructure existing repos. For orientation: Flux's reference layout names the same
  layers `clusters/<cluster>/` (entry point per cluster), `infrastructure/` (controllers,
  then their configs) and `apps/` (base + per-environment overlays); never mix both
  layouts in one repo.

## Argo CD

### AppProject — least privilege

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: myapp
  namespace: argocd
spec:
  sourceRepos:
    - https://git.example.com/myapp/gitops.git
    - registry.example.com/charts
  destinations:
    - server: https://kubernetes.default.svc
      namespace: myapp-*
  clusterResourceWhitelist: []          # apps may not create cluster-scoped objects
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
    - group: ""
      kind: LimitRange
```

### Environment base (namespace, policies, SealedSecrets) — synced first

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-prod-base
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-1"     # before the apps in an app-of-apps
spec:
  project: myapp-platform                  # may create the Namespace
  source:
    repoURL: https://git.example.com/myapp/gitops.git
    targetRevision: main
    path: envs/prod
    directory:
      recurse: true
      include: "{namespace.yaml,network-policies.yaml,sealed-secrets/*.yaml}"
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### App — chart from the OCI registry, values from the GitOps repo

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: backend-prod
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: myapp
  sources:
    - repoURL: registry.example.com/charts      # Helm OCI repository registered in Argo CD
      chart: backend
      targetRevision: 1.4.0                     # exact chart version
      helm:
        releaseName: backend
        valueFiles:
          - $values/envs/prod/backend-values.yaml
    - repoURL: https://git.example.com/myapp/gitops.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 5
      backoff:
        duration: 10s
        factor: 2
        maxDuration: 5m
    syncOptions:
      - ServerSideApply=true
      - PruneLast=true
      - CreateNamespace=false
```

- **Ordering** with app-of-apps: the parent Application syncs the base Application in
  wave `-1` and the app Applications in wave `0`; Argo CD waits until a wave is healthy.
  Argo CD has a built-in health check for `SealedSecret`.
- **Hooks**: Helm `pre-install`/`pre-upgrade` hooks become `PreSync`; the migration Job
  runs before the Deployment changes.
- **HPA**: the chart omits `replicas` when autoscaling is on; otherwise add
  `ignoreDifferences` for `/spec/replicas` — but omitting is the fix.
- Argo CD renders with `helm template` — `lookup` and other cluster-dependent template
  functions don't work; don't use them in charts.
- **Helm test hooks** (`helm.sh/hook: test`) have no Argo CD equivalent and are not run.
- **Retry** with backoff covers transient failures (CRD not yet established, webhook
  not ready); a permanent error still needs a fix in Git.
- Notifications (argocd-notifications) on `on-sync-failed` and `on-health-degraded` for
  staging/production — configured by the platform.
- Read-only inspection (`argocd app get|diff`) talks to the Argo CD server — shared
  environment, ask first. `argocd app sync|rollback` needs approval.

## Flux

### Ordering with Kustomizations

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: myapp-prod-base
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: gitops
  path: ./envs/prod/base          # namespace, network policies, quotas, sealed-secrets
  prune: true
  wait: true
  timeout: 5m
  retryInterval: 2m
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: myapp-prod-apps
  namespace: flux-system
spec:
  interval: 10m
  dependsOn:
    - name: myapp-prod-base
  sourceRef:
    kind: GitRepository
    name: gitops
  path: ./envs/prod/apps          # OCIRepository + HelmRelease per app
  prune: true
  wait: true
  timeout: 10m                    # covers migration hook + rollout
  retryInterval: 2m
```

(With Flux, the environment folder is split into `base/` and `apps/` so each
Kustomization has its own path.)

### Chart source and release

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: backend-chart
  namespace: myapp-prod
spec:
  interval: 10m
  url: oci://registry.example.com/charts/backend
  ref:
    tag: 1.4.0                     # exact version for staging/production
  layerSelector:
    mediaType: "application/vnd.cncf.helm.chart.content.v1.tar+gzip"
    operation: copy
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: backend
  namespace: myapp-prod
spec:
  interval: 10m
  releaseName: backend
  chartRef:
    kind: OCIRepository
    name: backend-chart
  timeout: 10m                     # each Helm operation, incl. the migration hook Job
  install:
    strategy:
      name: RetryOnFailure
      retryInterval: 5m
  upgrade:
    strategy:
      name: RetryOnFailure
      retryInterval: 5m
  test:
    enable: false                  # optional: true if the chart ships a helm test hook
  driftDetection:
    mode: enabled
  values:
    image:
      tag: "1.4.2"
      digest: "sha256:<digest>"
    proxy:
      trustedCidrs: "10.244.0.0/16"
    networkPolicy:
      database:
        cidr: 10.20.30.0/24
    route:
      hostnames: ["app.example.com"]
```

- Values sit inline in the per-environment HelmRelease (or in `valuesFrom` a ConfigMap
  generated from the values file) — never secrets there.
- Order SealedSecrets before apps with Kustomization `dependsOn`; HelmRelease
  `dependsOn` is for ordering between releases.
- Helm hooks run natively (helm-controller uses the Helm SDK); keep `disableHooks` off.
- **`RetryOnFailure`** (Flux's recommendation; the legacy `install/upgrade.remediation`
  retries are flagged for migration): a failed install/upgrade is retried every
  `retryInterval` without uninstall or rollback. A failed migration hook leaves the old
  pods running (the Deployment changes only after the hook succeeded); the fix goes
  through Git.
- Values from a ConfigMap (`valuesFrom`) instead of inline: label the ConfigMap
  `reconcile.fluxcd.io/watch: Enabled` so a change reconciles immediately instead of at
  the next interval.
- Opt-in only — signed chart artifacts (when the project or client requires signing,
  `references/build-and-supply-chain.md`):
  `OCIRepository.spec.verify` with `provider: cosign` and `matchOIDCIdentity`
  (`issuer`/`subject` regexes of the CI identity) — the source refuses unsigned charts.
- `flux get`, `flux diff kustomization` read from the cluster — shared environment,
  ask first. `flux reconcile|suspend|resume` need approval.

### Notifications

Every staging/production cluster reports failed reconciliations:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: team-chat
  namespace: flux-system
spec:
  type: slack                      # or msteams, googlechat, gitlab, github, generic, …
  secretRef:
    name: team-chat-webhook        # webhook URL in key "address" — from a SealedSecret
---
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: failures
  namespace: flux-system
spec:
  providerRef:
    name: team-chat
  eventSeverity: error
  eventSources:
    - kind: Kustomization
      name: "*"
    - kind: HelmRelease
      name: "*"
      namespace: myapp-prod
    - kind: OCIRepository
      name: "*"
      namespace: myapp-prod
```

### Offline validation (no cluster)

```bash
flux build kustomization myapp-prod-apps --path ./envs/prod/apps \
  --kustomization-file ./flux/prod/myapp-prod-apps.yaml --dry-run   # what would be applied
flux migrate -f . --dry-run                                         # deprecated Flux APIs
```

Pipe rendered output into `kubeconform` (if installed); `flux schema validate` needs the
`schema` plugin — use it only if it is already installed. `flux diff kustomization` does
a server-side dry run → cluster access → approval.

## Drift

- Argo CD: `selfHeal: true` reverts manual changes; `prune: true` removes resources
  deleted from Git.
- Flux: `prune: true` on Kustomizations; `driftDetection.mode: enabled` on HelmReleases.
  Fields owned by another controller go into `driftDetection.ignore` (HelmRelease) or
  `spec.ignore` (Kustomization) — e.g. `/spec/replicas` if a chart can't omit it.
- Emergency change in the cluster = incident: document it and put the same change into
  Git immediately, otherwise the controller reverts it.
- Suspending sync/reconciliation is an approval-only action and must be undone.

## Review checklist

- [ ] No manual deployment commands in docs, scripts or CI against shared clusters.
- [ ] Exact chart version and image tag + digest for staging/production.
- [ ] SealedSecrets and namespace policies synced before the apps.
- [ ] Argo CD AppProject restricts repos, destinations and cluster-scoped resources.
- [ ] Prune and self-heal/drift detection enabled.
- [ ] Flux: `timeout` + `retryInterval` on Kustomizations, `RetryOnFailure` strategies on
      HelmReleases, error Alerts; no deprecated APIs (`flux migrate -f . --dry-run`).
- [ ] Argo CD: retry with backoff; failure notifications for staging/production.
- [ ] Rollback documented as Git revert.
