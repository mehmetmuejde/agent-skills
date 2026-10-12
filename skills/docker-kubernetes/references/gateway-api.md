# Gateway API — traffic and TLS

Ingress is done with Gateway API (`gateway.networking.k8s.io/v1`), not with `Ingress`
objects. Split of responsibilities:

- **Platform** (`platform/` in the GitOps repo, namespace `gateway-system`): GatewayClass
  (from the chosen implementation), `Gateway`, cert-manager `ClusterIssuer`, HTTP→HTTPS
  redirect, implementation policies (TLS versions, body size, rate limits).
- **App charts**: one `HTTPRoute` each — backend `/api`, frontend `/`.

The implementation (Envoy Gateway, NGINX Gateway Fabric, Cilium, Istio, Traefik, a cloud
provider's controller, …) is a platform decision; don't assume one — check the
`GatewayClass` in the cluster config.

## Gateway with TLS (cert-manager)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: public
  namespace: gateway-system
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  gatewayClassName: <implementation class>
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      hostname: app.example.com
      allowedRoutes:
        namespaces:
          from: Same              # only the redirect route and ACME solver routes
    - name: https
      protocol: HTTPS
      port: 443
      hostname: app.example.com
      tls:
        mode: Terminate
        certificateRefs:
          - name: app-example-com-tls     # Secret created by cert-manager
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway.example.com/public: "true"
        kinds:
          - kind: HTTPRoute
```

- cert-manager needs Gateway API support enabled (`config.gatewayAPI.enabled: true` in its
  Helm values) and creates a `Certificate` for every listener with a non-empty
  `hostname`, `tls.mode: Terminate` and a `certificateRefs` name.
- **Explicit hostnames** on listeners — no catch-all listener that accepts any `Host`.
- `allowedRoutes` limited by namespace label — never `from: All`. App namespaces that
  may publish routes carry `gateway.example.com/public: "true"`.
- The certificate Secret lives in `gateway-system` next to the Gateway; no
  `ReferenceGrant` needed. A cross-namespace `certificateRefs` or `backendRefs` needs a
  `ReferenceGrant` in the target namespace — grant exactly that kind/name, nothing broader.
- Wildcard certificates (`*.example.com`) need DNS-01; otherwise HTTP-01 is fine.

### ClusterIssuer (HTTP-01 via the Gateway)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - http01:
          gatewayHTTPRoute:
            parentRefs:
              - name: public
                namespace: gateway-system
                kind: Gateway
                sectionName: http
```

Test against the Let's Encrypt staging directory first (rate limits).

### HTTP → HTTPS redirect

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: https-redirect
  namespace: gateway-system
spec:
  parentRefs:
    - name: public
      sectionName: http
  hostnames: ["app.example.com"]
  rules:
    - filters:
        - type: RequestRedirect
          requestRedirect:
            scheme: https
            statusCode: 301
```

The ACME solver route matches the exact challenge path and wins over this catch-all
redirect, so HTTP-01 keeps working.

## App routes

Path precedence is the same across all routes of a hostname: the **longest matching
prefix wins**, so `/api` goes to the backend and everything else to the frontend.
`PathPrefix` matches whole path segments: `/api` matches `/api` and `/api/users`, not
`/apiary`.

### Backend — `/api`

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: backend
  namespace: myapp-prod
spec:
  parentRefs:
    - name: public
      namespace: gateway-system
      sectionName: https
  hostnames: ["app.example.com"]
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: backend
          port: 80
      timeouts:
        request: 30s
```

- The backend serves its routes **under `/api`** itself (router prefix) — no
  `URLRewrite`, so URLs, OpenAPI paths and logs match what the browser sees.
- Health endpoints (`/healthz/*`) are outside `/api` → never reachable through the
  Gateway. Same for metrics. API docs are off in production anyway (backend skill).
- Streaming endpoints (SSE) need a longer or disabled request timeout on their own
  rule (`matches` on that path, `timeouts.request: 0s` = no timeout where supported).

### Frontend — `/`

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: frontend
  namespace: myapp-prod
spec:
  parentRefs:
    - name: public
      namespace: gateway-system
      sectionName: https
  hostnames: ["app.example.com"]
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: frontend
          port: 80
```

### Helm template (backend chart)

```yaml
{{- if .Values.route.enabled }}
{{- if empty .Values.route.hostnames }}
{{- fail "route.hostnames must list at least one hostname" }}
{{- end }}
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: {{ include "backend.fullname" . }}
  labels:
    {{- include "backend.labels" . | nindent 4 }}
spec:
  parentRefs:
    - name: {{ .Values.route.parentRef.name }}
      namespace: {{ .Values.route.parentRef.namespace }}
      sectionName: {{ .Values.route.parentRef.sectionName }}
  hostnames:
    {{- toYaml .Values.route.hostnames | nindent 4 }}
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: {{ .Values.route.pathPrefix }}
      backendRefs:
        - name: {{ include "backend.fullname" . }}
          port: 80
      timeouts:
        request: {{ .Values.route.requestTimeout }}
{{- end }}
```

## Cross-cutting concerns

- **Client IP**: the Gateway's data plane sets `X-Forwarded-For`. The backend trusts it
  only from the gateway pods (`FORWARDED_ALLOW_IPS` = their CIDR). Preserving the real
  client IP up to the Gateway (`externalTrafficPolicy: Local`, PROXY protocol) is
  implementation-specific — clarify with the platform.
- **Rate limiting and body size**: preferably at the Gateway via the implementation's
  policy resources (e.g. Envoy Gateway `BackendTrafficPolicy`/`ClientTrafficPolicy`,
  NGINX Gateway Fabric `ClientSettingsPolicy`); otherwise in the app. If that
  configuration isn't in the reviewed repo, it is out of scope, not a finding.
- **TLS settings** (minimum TLS 1.2, preferably 1.3; cipher suites) are implementation
  policies on the Gateway — check they exist.
- **Security headers**: the frontend's nginx/SSR server sets them; the backend sets its
  own. A `ResponseHeaderModifier` filter on a route can add HSTS centrally if the
  platform prefers that — don't set the same header twice with different values.
- Internal services (DB, admin tools, metrics) get no HTTPRoute on a public Gateway.

## Review checklist

- [ ] Gateway listeners with explicit hostnames; HTTPS terminates with a cert-manager
      certificate; HTTP only redirects.
- [ ] `allowedRoutes` restricted by namespace selector, no `from: All`.
- [ ] HTTPRoutes attach to the `https` section; `/api` → backend, `/` → frontend.
- [ ] Health, metrics, docs and admin paths not routed publicly.
- [ ] ReferenceGrants only where needed and narrowly scoped.
- [ ] Rate limits, body size and TLS policy present (or noted as out of scope).
