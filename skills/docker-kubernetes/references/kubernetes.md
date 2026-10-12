# Kubernetes workloads

What the rendered manifests must look like. How the Helm chart produces them:
`references/helm.md`. Names used below: namespace `myapp-prod`, apps `backend` and
`frontend`, gateway namespace `gateway-system`.

## Namespace — Pod Security Standard "restricted"

Namespaces are created by the platform / GitOps environment folder, not by an app chart.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp-prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

`restricted` rejects pods that run as root, allow privilege escalation, keep
capabilities other than `NET_BIND_SERVICE`, lack a seccomp profile or use host
namespaces/paths. Pin `enforce-version` to the cluster's minor version (`v1.xx`) if
upgrades must not tighten the policy unexpectedly.

## ResourceQuota and LimitRange — per namespace

Also part of the environment base (GitOps repo), not of an app chart. The quota caps what
a namespace can consume (a runaway HPA or a leaked Job loop can't starve the cluster);
the LimitRange gives defaults and bounds to containers that forget them (the charts set
their own — the LimitRange is the safety net).

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute
  namespace: myapp-prod
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.memory: 16Gi
    pods: "40"
    services.loadbalancers: "0"
    services.nodeports: "0"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: myapp-prod
spec:
  limits:
    - type: Container
      defaultRequest: { cpu: 50m, memory: 128Mi }
      default: { memory: 512Mi }
      max: { memory: 4Gi }
```

- With a `requests.*`/`limits.*` quota, every pod **must** declare those values (or get
  them from the LimitRange) — otherwise it is rejected.
- `services.loadbalancers: "0"` / `services.nodeports: "0"` enforce "only the Gateway is
  an entry point" at the API level.
- Size the quota for a rolling update: `maxSurge` pods and the migration Job run on top of
  the normal replicas.

## Backend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  labels:
    app.kubernetes.io/name: backend
    app.kubernetes.io/instance: backend
    app.kubernetes.io/part-of: myapp
    app.kubernetes.io/version: "1.4.2"
spec:
  # no "replicas" when an HPA manages the Deployment
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app.kubernetes.io/name: backend
      app.kubernetes.io/instance: backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: backend
        app.kubernetes.io/instance: backend
        app.kubernetes.io/component: api
      annotations:
        checksum/config: "<sha256 of the rendered ConfigMap>"
    spec:
      serviceAccountName: backend
      automountServiceAccountToken: false
      enableServiceLinks: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001          # makes mounted Secret files readable for the app group
        seccompProfile:
          type: RuntimeDefault
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: backend
              app.kubernetes.io/instance: backend
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: backend
              app.kubernetes.io/instance: backend
      containers:
        - name: backend
          image: registry.example.com/myapp/backend:1.4.2@sha256:<digest>
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8000
              protocol: TCP
          env:
            - name: FORWARDED_ALLOW_IPS
              value: "10.244.0.0/16"   # gateway pod CIDR of this cluster
          envFrom:
            - configMapRef:
                name: backend-config
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: secrets
              mountPath: /run/secrets/app
              readOnly: true
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
          startupProbe:
            httpGet:
              path: /healthz/live
              port: http
            periodSeconds: 2
            failureThreshold: 30
          livenessProbe:
            httpGet:
              path: /healthz/live
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /healthz/ready
              port: http
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
            secretName: backend-secrets
            defaultMode: 0440
```

Rules behind it:

- **securityContext** on pod *and* container as above — this is the PSS restricted
  baseline plus `readOnlyRootFilesystem`. Never `privileged`, `hostNetwork`, `hostPID`,
  `hostIPC`, `hostPath`, `hostPort`, the Docker/containerd socket, or added capabilities.
- **Probes** map to the backend's health endpoints:
  - `startupProbe` → `/healthz/live`; gives slow starts up to 60 s without loosening
    liveness.
  - `livenessProbe` → `/healthz/live`; checks only that the process responds. **Never the
    DB** — a DB outage would restart every pod and make it worse.
  - `readinessProbe` → `/healthz/ready`; checks DB and required services; a failing pod
    leaves the Service endpoints but isn't restarted.
- **preStop sleep** (Kubernetes ≥ 1.30, no shell needed) lets the gateway drop the
  endpoint before Uvicorn receives `SIGTERM`; `terminationGracePeriodSeconds` covers
  sleep + in-flight requests.
- **Resources**: requests on CPU and memory, a memory limit always. CPU limit generous
  (≥ 2–4× request) to avoid throttling; set it if the cluster's LimitRange/policy
  requires one. Without limits a single pod can starve the node (DoS).
- **Secrets as files** under `/run/secrets/app` (read with pydantic-settings
  `secrets_dir`), not as environment variables — env leaks into crash dumps, child
  processes and debug endpoints. `secretKeyRef` env only where a library insists.
- `enableServiceLinks: false` keeps the legacy `*_SERVICE_HOST` variables out of the env.
- One Uvicorn worker per pod; scale with the HPA.

## Frontend Deployment (differences)

Static SPA on nginx-unprivileged:

```yaml
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: frontend
          image: registry.example.com/myapp/frontend:2.0.1@sha256:<digest>
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: APP_PUBLIC_ENVIRONMENT
              value: production
            - name: APP_PUBLIC_API_BASE_URL
              value: /api
          volumeMounts:
            - name: tmp
              mountPath: /tmp   # pid, temp files and runtime config.json
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests: { cpu: 20m, memory: 32Mi }
            limits: { cpu: 500m, memory: 128Mi }
          readinessProbe:
            httpGet: { path: /healthz, port: http }
          livenessProbe:
            httpGet: { path: /healthz, port: http }
```

React Router framework server: `runAsUser: 1000`, port `3000`, probes on the app's
`/healthz` resource route, memory sized for Node (≥ 256Mi), `/tmp` as `emptyDir`.

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: backend
    app.kubernetes.io/instance: backend
  ports:
    - name: http
      port: 80
      targetPort: http
```

Only `ClusterIP`. The Gateway is the single entry point; no `NodePort`/`LoadBalancer`
per app, never a Service exposing PostgreSQL outside the cluster.

## PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backend
spec:
  maxUnavailable: 1
  unhealthyPodEvictionPolicy: AlwaysAllow
  selector:
    matchLabels:
      app.kubernetes.io/name: backend
      app.kubernetes.io/instance: backend
```

Requires ≥ 2 replicas (HPA `minReplicas: 2`); with one replica a PDB blocks node drains.

## HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

When the HPA is enabled, the Deployment has **no `replicas` field** — otherwise every
GitOps sync resets the replica count the HPA chose. Utilization needs CPU requests.

## NetworkPolicies

Default-deny lives in the environment folder of the GitOps repo (namespace-wide); each
app chart ships its own allow rules. Requires a CNI that enforces NetworkPolicies
(Calico, Cilium, …) — otherwise they are silently ignored.

```yaml
# Namespace-wide: deny all ingress and egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
---
# Namespace-wide: DNS for all pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - { protocol: UDP, port: 53 }
        - { protocol: TCP, port: 53 }
---
# Backend chart: gateway -> backend, backend (and migration Job) -> PostgreSQL
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: backend
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: gateway-system
      ports:
        - { protocol: TCP, port: 8000 }
  egress:
    - to:
        - ipBlock:
            cidr: 10.20.30.0/24   # managed PostgreSQL; in-cluster DB: podSelector instead
      ports:
        - { protocol: TCP, port: 5432 }
```

- The selector `app.kubernetes.io/name: backend` also matches the migration Job pods
  (same labels plus `app.kubernetes.io/component: migrations`), so they reach the DB.
- Frontend: ingress from `gateway-system` on 8080, no egress besides DNS (SPA) — SSR
  server additionally egress to the backend Service.
- Outbound calls to external APIs: explicit egress rules (CIDR or an egress gateway);
  no blanket `0.0.0.0/0`. If a broad range is unavoidable (SaaS APIs without fixed IPs),
  limit it to port 443 and exclude the cloud metadata endpoint:

```yaml
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 169.254.169.254/32    # cloud instance metadata (credential theft via SSRF)
              - 10.0.0.0/8            # cluster/VPC ranges: reach them only via explicit rules
      ports:
        - { protocol: TCP, port: 443 }
```
- Kubelet probes are not affected by NetworkPolicies on most CNIs.

## ServiceAccount and RBAC

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend
automountServiceAccountToken: false
```

- One ServiceAccount per app, never `default`. Token mounting off on the SA **and** the
  pod spec.
- The apps don't call the Kubernetes API → no Role, no RoleBinding.
- If an app must call the API: namespaced `Role` with explicit `apiGroups`, `resources`,
  `verbs` (and `resourceNames` where possible), `automountServiceAccountToken: true`
  only on that pod. No `*`, no `ClusterRole`/`ClusterRoleBinding`, never `cluster-admin`,
  no `secrets` `list`/`watch` (that reads all secrets of the namespace), no `pods/exec`,
  no `escalate`/`bind`/`impersonate`.

## Images

- Reference by **immutable tag + digest**: `registry.example.com/myapp/backend:1.4.2@sha256:…`.
  Never `latest`, never a mutable tag like `main` or `prod`.
- Only trusted registries (the project's own registry, official images). Registries with
  tag immutability enabled.
- Private registry: `imagePullSecrets` with a `kubernetes.io/dockerconfigjson` Secret
  from a SealedSecret (`references/secrets.md`).
- `imagePullPolicy: IfNotPresent` is safe with digests.

## Database migrations — one-shot Job

Never in the app's startup (several replicas would race, and a failed migration
crash-loops every pod). The Job uses the **same image digest** as the Deployment.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: backend-migrate
  labels:
    app.kubernetes.io/name: backend
    app.kubernetes.io/instance: backend
    app.kubernetes.io/component: migrations
  annotations:
    # Helm (also mapped to Argo CD PreSync automatically)
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "0"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: backend
        app.kubernetes.io/instance: backend
        app.kubernetes.io/component: migrations
    spec:
      restartPolicy: Never
      serviceAccountName: backend-migrate   # hook-created, see references/helm.md
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001          # makes mounted Secret files readable for the app group
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: migrate
          image: registry.example.com/myapp/backend:1.4.2@sha256:<digest>
          command: ["alembic", "upgrade", "head"]
          volumeMounts:
            - { name: tmp, mountPath: /tmp }
            - { name: secrets, mountPath: /run/secrets/app, readOnly: true }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits: { memory: 512Mi }
      volumes:
        - name: tmp
          emptyDir: {}
        - name: secrets
          secret:
            secretName: backend-secrets
            defaultMode: 0440
```

- Helm: `pre-install,pre-upgrade` hook — the Deployment rolls out only after a
  successful migration; a failed Job fails the release.
- Argo CD maps these Helm hooks to `PreSync` (and `hook-weight` to `sync-wave`). Native
  form: `argocd.argoproj.io/hook: PreSync` +
  `argocd.argoproj.io/hook-delete-policy: BeforeHookCreation`. Don't mix both annotation
  sets on one chart — once Argo CD hooks exist, Helm hooks are ignored.
- **Hooks run before the release's other resources exist.** Everything the Job reads
  (DB Secret, ConfigMap) must already be in the namespace: SealedSecrets are synced by a
  separate, earlier GitOps unit (`references/gitops.md`); config the Job needs is passed
  inline as env from values, not via the chart's ConfigMap.
- **Backward-compatible migrations** (expand/contract): during the rolling update old
  pods run against the new schema. Drop/rename columns only in a later release.
- The migration DB user may own the schema; the app user gets only DML rights (see the
  backend skill's database reference).
- No `ttlSecondsAfterFinished` on Jobs that GitOps applies as normal resources — the
  controller sees the TTL-deleted Job as drift, re-creates it and the migration runs
  again. Hook Jobs are cleaned up by `hook-delete-policy`.

## ConfigMap vs. Secret

| ConfigMap | Secret (from SealedSecret) |
|---|---|
| Log level, feature flags, public URLs, allowed origins, pool sizes | DB password/URL with credentials, API keys, signing keys, OIDC client secret, registry credentials |

- Never credentials in a ConfigMap, in Helm values, in `env.value` literals or in
  annotations.
- Config changes roll the pods via the `checksum/config` annotation. Secret rotation
  needs a rollout too (bump an annotation through Git, or use a reloader controller if
  the platform has one).
- Secrets at rest: the cluster should encrypt Secrets in etcd (platform responsibility —
  note it in reviews, don't assume).

## Admission policies — ValidatingAdmissionPolicy

PSS covers pod privileges. Rules beyond that — images only by digest and from the
project's registry, required labels, no `LoadBalancer` — are enforced at admission with
the built-in **`ValidatingAdmissionPolicy`** (GA since Kubernetes 1.30, CEL, no extra
controller). Kyverno and OPA Gatekeeper are not used. The policies are cluster-scoped and
live in the platform layer of the GitOps repo. VAP can't verify image signatures; that
only matters if a project opts in to signing (`references/build-and-supply-chain.md`).

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: images-by-digest-from-registry
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: >-
        object.spec.containers.all(c,
          c.image.startsWith('registry.example.com/') && c.image.contains('@sha256:'))
        && (!has(object.spec.initContainers) || object.spec.initContainers.all(c,
          c.image.startsWith('registry.example.com/') && c.image.contains('@sha256:')))
      message: "Images must come from registry.example.com and be pinned by digest."
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: images-by-digest-from-registry
spec:
  policyName: images-by-digest-from-registry
  validationActions: [Deny]          # start with [Warn, Audit], switch to Deny when clean
  matchResources:
    namespaceSelector:
      matchLabels:
        pod-security.kubernetes.io/enforce: restricted
```

- Roll out with `[Warn, Audit]` first; `Deny` and `Warn` can't be combined.
- Dev environments that allow tag-only images (`image.requireDigest: false`) need a
  binding that excludes them.
- Cluster-scoped objects → platform/GitOps layer, never an app chart.

## Review checklist

- [ ] Namespace labelled PSS `restricted` (enforce + audit + warn); ResourceQuota and
      LimitRange in the environment base.
- [ ] Pod/container securityContext complete; no host access, no privileged.
- [ ] Requests + memory limits; startup/liveness/readiness probes; liveness without DB.
- [ ] ≥ 2 replicas, PDB, topology spread; HPA owns replicas.
- [ ] Default-deny NetworkPolicy + explicit allows (gateway, DB, DNS); broad egress
      limited to 443 and excludes `169.254.169.254`.
- [ ] Dedicated ServiceAccount, token not mounted, no RBAC unless needed and then minimal.
- [ ] Images by tag + digest from trusted registries; enforced by a
      ValidatingAdmissionPolicy (platform layer).
- [ ] Migrations as hook Job with the same image; prerequisites exist before the hook;
      no `ttlSecondsAfterFinished` on GitOps-managed Jobs.
- [ ] Secrets mounted as files from SealedSecrets; nothing sensitive in ConfigMaps.
- [ ] Services `ClusterIP` only.
