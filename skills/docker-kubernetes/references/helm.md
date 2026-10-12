# Helm charts

One chart per app (`backend`, `frontend`). The chart holds secure defaults; everything
environment-specific lives in values files in the GitOps repo (`references/gitops.md`).
Rendered output must satisfy `references/kubernetes.md`.

## Layout

```
charts/backend/
  Chart.yaml
  values.yaml            # secure production defaults, no environment specifics, no secrets
  values.schema.json     # validates every values file
  .helmignore
  templates/
    _helpers.tpl
    deployment.yaml
    service.yaml
    serviceaccount.yaml
    configmap.yaml
    hpa.yaml
    pdb.yaml
    networkpolicy.yaml
    httproute.yaml
    migration-job.yaml
    NOTES.txt
    tests/
      test-ready.yaml     # helm test hook (optional, see "Chart tests")
  tests/
    deployment_test.yaml  # helm-unittest suites (mandatory, run in CI)
```

- Charts live in the app repo (or `charts/<app>/` in a monorepo) and are published by CI
  to an OCI registry. Values per environment live in the GitOps repo.
- **Not in an app chart**: Namespace, default-deny/DNS NetworkPolicies, Gateway,
  SealedSecrets, cluster-scoped resources (ClusterRole, CRDs). They belong to the
  environment or platform layer.
- No database subchart for staging/production — PostgreSQL is managed or run by an
  operator outside the app chart.

## `Chart.yaml`

```yaml
apiVersion: v2
name: backend
description: FastAPI backend
type: application
version: 1.4.0          # chart version (SemVer) — bump on every chart change
appVersion: "1.4.2"     # default image tag
kubeVersion: ">=1.30.0-0"   # preStop sleep needs 1.30; "-0" also matches provider versions like v1.30.4-eks-…
home: https://git.example.com/myapp/backend
sources:
  - https://git.example.com/myapp/backend
```

## Versioning

- `version` changes with **every** change to templates or defaults; published versions
  are immutable — never re-push a version.
- `appVersion` is the image version the chart deploys by default; CI sets it on release.
  Environments override `image.tag`/`image.digest` for promotion.
- GitOps pins exact chart versions for staging/production (no ranges).
- Subcharts are pinned in `Chart.yaml`; `Chart.lock` is committed.
- `helm package` / `helm push` run in CI. Manually only with approval (safety rules).

## `values.yaml` — secure defaults

```yaml
nameOverride: ""
fullnameOverride: ""
partOf: myapp

image:
  repository: registry.example.com/myapp/backend
  tag: ""                 # empty = Chart.appVersion
  digest: ""              # "sha256:…"
  requireDigest: true     # production default; dev may switch it off

imagePullSecrets: []      # e.g. [{ name: registry-credentials }] from a SealedSecret

replicaCount: 2           # used only when autoscaling is disabled
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70

resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits: { cpu: "1", memory: 512Mi }

terminationGracePeriodSeconds: 30

proxy:
  trustedCidrs: ""        # gateway pod CIDR(s), comma-separated — required

existingSecret: backend-secrets   # Secret created from a SealedSecret in the GitOps repo

config:                   # non-sensitive settings, rendered into the ConfigMap
  LOG_LEVEL: info
  ENVIRONMENT: production

migrations:
  enabled: true
  env: {}                 # non-sensitive settings the migration Job needs (no ConfigMap at hook time)

podDisruptionBudget:
  enabled: true
  maxUnavailable: 1

networkPolicy:
  enabled: true
  gatewayNamespace: gateway-system
  database:
    cidr: ""              # managed PostgreSQL CIDR — required when enabled
    port: 5432

route:
  enabled: true
  hostnames: []
  parentRef:
    name: public
    namespace: gateway-system
    sectionName: https
  pathPrefix: /api
  requestTimeout: 30s
```

The pod and container `securityContext` is **not** configurable through values — it is
hard-coded in the template. Weakening it takes a chart change and a review.

## Environment values (GitOps repo)

```yaml
# envs/prod/backend-values.yaml — only what differs from the defaults
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

```yaml
# envs/dev/backend-values.yaml
image:
  tag: "1.5.0-dev.42"
  requireDigest: false
autoscaling:
  enabled: false
replicaCount: 1
podDisruptionBudget:
  enabled: false
resources:
  requests: { cpu: 50m, memory: 128Mi }
  limits: { cpu: 500m, memory: 384Mi }
proxy:
  trustedCidrs: "10.244.0.0/16"
config:
  LOG_LEVEL: debug
  ENVIRONMENT: dev
networkPolicy:
  database:
    cidr: 10.30.0.0/24
route:
  hostnames: ["dev.app.example.com"]
```

No secrets in any values file — not even "just for dev". No `--set password=…`.

## `templates/_helpers.tpl`

```yaml
{{- define "backend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else if contains (include "backend.name" .) .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "backend.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "backend.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{ include "backend.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: {{ .Values.partOf }}
{{- end -}}

{{/* Image reference: immutable tag, digest required unless explicitly disabled */}}
{{- define "backend.image" -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if or (not $tag) (eq $tag "latest") -}}
{{- fail "image.tag must be an immutable version, never empty or latest" -}}
{{- end -}}
{{- if and .Values.image.requireDigest (not .Values.image.digest) -}}
{{- fail "image.digest is required (set image.requireDigest=false only for dev)" -}}
{{- end -}}
{{- if .Values.image.digest -}}
{{- printf "%s:%s@%s" .Values.image.repository $tag .Values.image.digest -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}
{{- end -}}

{{/* Pod security context shared by Deployment and migration Job — not configurable */}}
{{- define "backend.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "backend.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
capabilities:
  drop: ["ALL"]
{{- end -}}
```

## `templates/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "backend.fullname" . }}
  labels:
    {{- include "backend.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      {{- include "backend.selectorLabels" . | nindent 6 }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        {{- include "backend.selectorLabels" . | nindent 8 }}
        app.kubernetes.io/component: api
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
    spec:
      serviceAccountName: {{ include "backend.fullname" . }}
      automountServiceAccountToken: false
      enableServiceLinks: false
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
      securityContext:
        {{- include "backend.podSecurityContext" . | nindent 8 }}
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      topologySpreadConstraints:
        {{- range list "topology.kubernetes.io/zone" "kubernetes.io/hostname" }}
        - maxSkew: 1
          topologyKey: {{ . }}
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              {{- include "backend.selectorLabels" $ | nindent 14 }}
        {{- end }}
      containers:
        - name: backend
          image: {{ include "backend.image" . | quote }}
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8000
              protocol: TCP
          env:
            - name: FORWARDED_ALLOW_IPS
              value: {{ required "proxy.trustedCidrs is required" .Values.proxy.trustedCidrs | quote }}
          envFrom:
            - configMapRef:
                name: {{ include "backend.fullname" . }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: secrets
              mountPath: /run/secrets/app
              readOnly: true
          securityContext:
            {{- include "backend.containerSecurityContext" . | nindent 12 }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          startupProbe:
            httpGet: { path: /healthz/live, port: http }
            periodSeconds: 2
            failureThreshold: 30
          livenessProbe:
            httpGet: { path: /healthz/live, port: http }
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 3
          readinessProbe:
            httpGet: { path: /healthz/ready, port: http }
            periodSeconds: 5
            timeoutSeconds: 2
            failureThreshold: 3
          lifecycle:
            preStop:
              sleep:
                seconds: 5
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 64Mi
        - name: secrets
          secret:
            secretName: {{ required "existingSecret is required" .Values.existingSecret }}
            defaultMode: 0440
```

## `templates/migration-job.yaml`

```yaml
{{- if .Values.migrations.enabled }}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "backend.fullname" . }}-migrate
  labels:
    {{- include "backend.labels" . | nindent 4 }}
    app.kubernetes.io/component: migrations
  annotations:
    # Helm/Flux run these natively; Argo CD maps them to PreSync
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "0"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 600
  template:
    metadata:
      labels:
        {{- include "backend.selectorLabels" . | nindent 8 }}
        app.kubernetes.io/component: migrations
    spec:
      restartPolicy: Never
      serviceAccountName: {{ include "backend.fullname" . }}-migrate
      automountServiceAccountToken: false
      securityContext:
        {{- include "backend.podSecurityContext" . | nindent 8 }}
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: migrate
          image: {{ include "backend.image" . | quote }}
          command: ["alembic", "upgrade", "head"]
          {{- with .Values.migrations.env }}
          env:
            {{- range $name, $value := . }}
            - name: {{ $name }}
              value: {{ $value | quote }}
            {{- end }}
          {{- end }}
          volumeMounts:
            - { name: tmp, mountPath: /tmp }
            - { name: secrets, mountPath: /run/secrets/app, readOnly: true }
          securityContext:
            {{- include "backend.containerSecurityContext" . | nindent 12 }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
      volumes:
        - name: tmp
          emptyDir: {}
        - name: secrets
          secret:
            secretName: {{ .Values.existingSecret }}
            defaultMode: 0440
{{- end }}
```

Hooks run before the release's normal resources exist, so the app's ServiceAccount isn't
there on the **first** install. The Job gets its own ServiceAccount, created as a hook
right before it:

```yaml
# templates/migration-serviceaccount.yaml
{{- if .Values.migrations.enabled }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "backend.fullname" . }}-migrate
  labels:
    {{- include "backend.labels" . | nindent 4 }}
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation
automountServiceAccountToken: false
{{- end }}
```

The Secret the Job mounts must exist before the hook as well — it comes from a
SealedSecret synced by an earlier GitOps unit (`references/gitops.md`).

## Other templates (short)

- `service.yaml`: `ClusterIP`, port 80 → `targetPort: http`.
- `serviceaccount.yaml`: `automountServiceAccountToken: false`.
- `configmap.yaml`: `data: {{- toYaml .Values.config | nindent 2 }}` — non-sensitive
  only.
- `hpa.yaml` / `pdb.yaml`: guarded by `autoscaling.enabled` /
  `podDisruptionBudget.enabled`.
- `networkpolicy.yaml`: the app's allow rules (gateway → app, app → DB); `required` on
  `networkPolicy.database.cidr` when enabled.
- `httproute.yaml`: see `references/gateway-api.md`.

## `values.schema.json` (excerpt)

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "proxy", "existingSecret"],
  "properties": {
    "image": {
      "type": "object",
      "required": ["repository"],
      "additionalProperties": false,
      "properties": {
        "repository": { "type": "string", "minLength": 1 },
        "tag": { "type": "string", "not": { "const": "latest" } },
        "digest": { "type": "string", "pattern": "^(sha256:[a-f0-9]{64})?$" },
        "requireDigest": { "type": "boolean" }
      }
    },
    "replicaCount": { "type": "integer", "minimum": 1 },
    "existingSecret": { "type": "string", "minLength": 1 },
    "config": {
      "type": "object",
      "propertyNames": {
        "pattern": "^[A-Z][A-Z0-9_]*$",
        "not": { "pattern": "(PASSWORD|SECRET|TOKEN|API_?KEY|PRIVATE|CREDENTIAL)" }
      }
    }
  }
}
```

The `config` rule blocks obviously sensitive keys from landing in the ConfigMap.

## Chart tests

Two layers: **unit tests are mandatory** for every chart, release tests are optional.

**Unit tests (mandatory, offline, CI)** with the `helm-unittest` plugin — render
templates with given values and assert on the output; no cluster. Every chart has
`charts/<app>/tests/*_test.yaml` (excluded from the package via `.helmignore`) and CI
runs `helm unittest charts/<app>` on every change; a failing suite blocks the merge.
At minimum the suites cover the guard rails: immutable image reference with digest,
`latest` refused, no `replicas` with HPA, hard-coded securityContext, schema rejecting
secret-looking config keys.

```yaml
# charts/backend/tests/deployment_test.yaml
suite: deployment
templates:
  - templates/deployment.yaml
  - templates/configmap.yaml       # needed for the checksum/config annotation
values:
  - ../ci/test-values.yaml
tests:
  - it: renders an immutable image reference
    template: templates/deployment.yaml
    asserts:
      - isKind:
          of: Deployment
      - matchRegex:
          path: spec.template.spec.containers[0].image
          pattern: ^registry\.example\.com/myapp/backend:[0-9][^@]*@sha256:[a-f0-9]{64}$
  - it: omits replicas when autoscaling is enabled
    template: templates/deployment.yaml
    set:
      autoscaling.enabled: true
    asserts:
      - notExists:
          path: spec.replicas
  - it: refuses latest
    template: templates/deployment.yaml
    set:
      image.tag: latest
    asserts:
      - failedTemplate: {}
```

`ci/test-values.yaml` holds the required values (digest, `proxy.trustedCidrs`,
`networkPolicy.database.cidr`, hostnames) with dummy data. Locally, run
`helm unittest charts/backend` only if the plugin is installed — never install it; CI
images ship the plugin.

**Release tests (`helm test`, optional)** — a Pod with the `helm.sh/hook: test` annotation that
checks the deployed release. Use the app's **own image** (no extra `busybox`/`curl`
image) and the same security context, or PSS `restricted` rejects it:

```yaml
# templates/tests/test-ready.yaml
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "backend.fullname" . }}-test-ready
  labels:
    {{- include "backend.labels" . | nindent 4 }}
    app.kubernetes.io/component: chart-test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  securityContext:
    {{- include "backend.podSecurityContext" . | nindent 4 }}
  containers:
    - name: test
      image: {{ include "backend.image" . | quote }}
      command:
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://{{ include "backend.fullname" . }}/healthz/ready', timeout=5)"
      securityContext:
        {{- include "backend.containerSecurityContext" . | nindent 8 }}
      resources:
        requests: { cpu: 10m, memory: 64Mi }
        limits: { memory: 128Mi }
```

- The NetworkPolicy must allow the test pod: add an ingress rule from
  `podSelector: {app.kubernetes.io/component: chart-test}` on port 8000 in
  `networkpolicy.yaml`, and egress for the test pod (or it fails on default-deny).
- **Flux** runs tests with `HelmRelease.spec.test.enable: true`. **Argo CD does not run
  Helm test hooks** (no equivalent) — there they are dead code; rely on readiness
  probes and the sync health instead.
- `helm test <release>` by hand talks to the cluster → approval.

## `.helmignore`

```
.git
.DS_Store
*.swp
*.tmp
/ci/
/tests/
```

- Leading `/` anchors the pattern at the chart root. A bare `tests/` also matches
  `templates/tests/` and silently drops the `helm test` hooks from the package.
- **No `!` negations**: Helm's `.helmignore` treats a `!pattern` line as "ignore
  everything that doesn't match it" — `!README.md` excludes `Chart.yaml` and the chart
  no longer loads. Keep `README.md` in the package (registries display it).

## Validation (read-only, only if the tools are installed)

Run for **every environment's values**, not only the defaults:

```bash
# Lint
helm lint charts/backend --strict -f ../gitops/envs/prod/backend-values.yaml

# Render + validate against Kubernetes and CRD schemas (Gateway API, SealedSecret, …)
helm template backend charts/backend --namespace myapp-prod \
    -f ../gitops/envs/prod/backend-values.yaml \
  | kubeconform -strict -summary -kubernetes-version <cluster version, e.g. 1.34.0> \
      -schema-location default \
      -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

# Unit tests (mandatory in CI)
helm unittest charts/backend

# Misconfiguration scan on the rendered output (write it to the scratch folder)
trivy config <rendered-dir>
```

- `helm template` and `helm lint` need no cluster. `helm template --validate`,
  `helm install --dry-run=server` and `helm diff` talk to the API server — against a
  shared cluster only with approval.
- `helm template … --debug` for render errors with context.
- Missing tool → say so, skip, never install.
- Check the render manually for: no `latest`, digest present (staging/prod), no
  `replicas` with HPA, securityContext complete, no Secret objects, hook annotations on
  the Job.

## Frontend chart differences

- No migrations, usually no Secret (`existingSecret` optional).
- Public runtime config from values → env `APP_PUBLIC_*` (or a ConfigMap mounted as
  `/tmp/runtime-config/config.json`). The schema rejects keys that look like secrets.
- Port 8080, UID 101 (SPA) or port 3000, UID 1000 (React Router server).
- HTTPRoute path `/` (`references/gateway-api.md`).

## Review checklist

- [ ] One chart per app; no Namespace, Gateway, SealedSecret or cluster-scoped objects.
- [ ] Secure defaults in `values.yaml`; environment files contain only differences.
- [ ] securityContext hard-coded; image helper fails on `latest` and missing digest.
- [ ] `values.schema.json` present; `helm lint --strict`, kubeconform and
      `trivy config` pass for every environment.
- [ ] helm-unittest suites exist and run in CI (mandatory); they cover the guard rails
      (no `latest`, digest, no `replicas` with HPA, securityContext, schema).
- [ ] `kubeVersion` set; release test (optional) uses the app image, passes PSS
      `restricted` and is allowed by the NetworkPolicy.
- [ ] Chart version bumped; `Chart.lock` committed; no secrets in any values file.
