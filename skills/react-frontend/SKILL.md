---
name: react-frontend
description: Apply for any work on a React/TypeScript frontend — components, hooks, state, routing, data fetching, forms, styling, accessibility, i18n, tests, stories, performance and frontend security; also when setting up a new React project, containerizing a frontend or reviewing React code. Covers Vite SPAs and React Router framework mode (loaders, actions, SSR/hydration), TanStack Query for server state, TanStack Router or React Router, Zustand for client state, React Hook Form or TanStack Form with Zod, Feature-Sliced Design structure, Biome and strict TypeScript, Vitest + Testing Library, Playwright, Storybook. Holds the rules that always apply — derived state instead of effects, server data only in TanStack Query, accessibility built in, tests and stories with every feature, no tokens in browser storage — and points to references per topic.
---

# React frontend

Rules for every React frontend. This file holds what always applies; read the matching
reference **before** working on that topic.

| Task | Read |
|---|---|
| Folders, layers, slices, public API, imports, barrel files | `references/structure.md` |
| FSD deep dives: decision tree, cross-imports, entities, assets, auth/API placement, framework wiring, migration | `references/fsd/` (index at the end of `structure.md`) |
| Naming, file size, props, design system, layouts, constants | `references/code-style.md` |
| Components, hooks, effects, memoization, transitions, long lists, hydration | `references/hooks-and-rendering.md` |
| Waterfalls, bundle size, code splitting, preloading, re-render cost | `references/performance.md` |
| Server data, queries, mutations, loaders, search params, Zustand | `references/data-and-state.md` |
| Forms, validation, form errors | `references/forms.md` |
| Semantics, keyboard, focus, contrast, live regions, a11y testing | `references/accessibility.md` (React implementation) + the `frontend-accessibility` skill (full rules, audits) |
| Unit, component and E2E tests, coverage, API mocking | `references/testing.md` |
| Stories, Storybook a11y checks, visual regression | `references/storybook.md` |
| XSS, rendering HTML/Markdown/LLM output, auth, CSRF, CSP, env vars, logout | `references/security.md` |
| Node version, package manager, pre-commit + gitleaks, dependency audit | `references/tooling.md` |
| Translations, language switch, `<html lang>` | `references/i18n.md` |
| Setting up a new project | `references/setup.md` |
| Container image for the frontend | `references/docker.md` + the `docker-kubernetes` skill |

## Stack

- **React** 19 (≥ 19.2 for `useEffectEvent` and `<Activity>`) · **TypeScript** strict
- **Rendering**: Vite SPA **or** React Router framework mode (SSR + hydration). Rules
  marked *React Router framework only* apply only there. No Next.js, no React Server
  Components, no SWR.
- **Routing**: TanStack Router **or** React Router — fixed per project, detect it from
  the code, never mix.
- **Server state**: TanStack Query · **Client state**: Zustand
- **Forms**: React Hook Form + Zod **or** TanStack Form + Zod — fixed per project
- **Validation**: Zod at every boundary (API responses, forms, search params, env,
  storage, `postMessage`)
- **Tooling**: Biome (lint + format), Steiger (FSD rules), Vitest + Testing Library,
  Playwright, Storybook
- **No React Compiler** → memoization is manual, but only after measuring.

## Structure — Feature-Sliced Design

Layers `app → pages → widgets → features → entities → shared`; imports only downward;
no imports between slices of the same layer; every slice is imported only through its
`index.ts` with explicit named exports (no `export *`). `shared/ui` and `shared/lib` have
one index per component/library. Start with `app`, `pages`, `shared`; no empty layer
folders. Code stays in the page until the **extraction rule** holds — used in several
places right now, a reason to change independent of any one consumer, a focused
responsibility; all three, duplication is acceptable until then. **`widgets` is
discouraged**: only for a composed block reused across several pages that can't live in
a page (existing widgets stay valid). Details: `references/structure.md`, upstream
rulebook `references/fsd/rules.md`.

- **One component per file, one hook per file**, ~150 lines per component; components
  prefixed with their slice name (`references/code-style.md`).
- **Design system first**: use the own components from `shared/ui/`; never import
  `shared/ui/primitives/` (UI-library CLI output, never edited) outside `shared/ui/`. No
  new CSS before checking what the design system's components, props and tokens can do.

## Components and hooks — always

- **Never define a component inside another component** — it remounts on every render.
- **Derive, don't sync**: values computable from props/state are computed during
  render. No `useEffect` that copies props or state into state. Reset with `key`.
- **User actions run in event handlers**, not in effects triggered by state flags.
- **Effects only synchronize with external systems**, with narrow primitive
  dependencies, one concern per effect, and a cleanup. Never silence the
  exhaustive-deps rule.
- `setState(prev => …)` when the next value depends on the previous one;
  `useState(() => expensive())` for expensive initial values.
- **Never mutate props or state**: `toSorted()`, `toReversed()`, `toSpliced()`,
  `with()`, spread.
- `{count > 0 ? <X /> : null}` — never `&&` with a number on the left.
- No `fetch` in `useEffect`; server data comes from TanStack Query or a route loader.
- `memo`/`useMemo`/`useCallback` only after profiling or when referential stability is
  required.
- Errors are never swallowed: no empty `catch`, no `.catch(() => {})`. Every route has an
  error boundary; every query has loading, error and empty UI.

## Data and state — always

- **Request function → hook → component.** HTTP only through the client in
  `shared/api/`; never import an HTTP client in hooks or components.
- **Server data lives only in TanStack Query**, via a query key factory with
  `queryOptions`; responses are parsed with Zod in the request function.
- **Plain resource access, CRUD and query key factories live in `shared/api`** (or the
  page/feature that alone uses them); `entities/<x>/api` only for requests with domain
  rules or mapping of that entity.
- Mutations invalidate (or update) every affected query.
- **URL state** (filters, sorting, pagination, tabs) lives in typed, Zod-validated
  search params — never parsed by hand from `window.location`.
- **Zustand** only for shared client state; always with a selector; persisted stores
  use `version`, `migrate` and `partialize`, and hold no sensitive data.
- Load route data in the route loader (`queryClient.query({ ...options, staleTime:
  'static' })`, formerly `ensureQueryData`) and in parallel, not in nested components
  one after another.

## Accessibility — built in, never added later

Target: WCAG 2.2 AA. Part of the definition of done for every component and page. The
`frontend-accessibility` skill holds the complete rules and the audit procedure — load it
for every UI change.

- **Semantic HTML first**: `<button>` for actions, `<a>`/`<Link>` for navigation,
  `<label>` for every field, landmarks, one `<h1>` and ordered headings. ARIA only when
  no native element fits.
- **Keyboard**: everything reachable and operable with the keyboard; no positive
  `tabIndex`; no keyboard traps.
- **Visible focus** on every interactive element (`:focus-visible`, ≥ 3:1 contrast).
- **Focus management**: on route change set the page title and move focus to the `<h1>`
  or `<main>`; dialogs trap focus, close on `Escape` and return focus to the trigger.
- **Names**: icon buttons have `aria-label`; images have `alt` (`alt=""` if decorative).
- **Contrast** 4.5:1 for text, 3:1 for UI components; color never the only signal.
- **Reduced motion** respected; **live regions** (`role="status"`/`role="alert"`) for
  async results and errors.
- Tests query by role and accessible name; stories pass the a11y addon; critical pages
  pass axe in Playwright.

## Testing — written with the feature, not after

- **Vitest + Testing Library** unit and component tests for every feature, in the same
  change. Test behavior through the UI (roles, labels, `user-event`), not implementation
  details.
- **Coverage ≥ 80 % lines and ≥ 80 % branches**, enforced by Vitest thresholds in CI.
- **Playwright E2E** for every critical user flow (login, core business flows,
  payment/checkout, permissions): role-based locators, no fixed waits, reused auth
  state, axe scan on key pages.
- **Storybook story for every shared/reusable UI component**, covering all states
  (default, loading, empty, error, disabled, long content). Desktop viewport by default;
  mobile viewports only when the project requires responsive layouts.
- Visual regression via Storybook + Playwright screenshots; snapshot tests only
  sparingly and targeted.

## Security — always

- **No `dangerouslySetInnerHTML`** without DOMPurify; outside React use `textContent`,
  never `innerHTML`. Model output and Markdown never render as raw HTML.
- **No tokens or sensitive data in `localStorage`/`sessionStorage`/IndexedDB.** Auth is a
  backend-set `HttpOnly` session cookie; for OIDC prefer a backend-for-frontend.
- State-changing requests send the CSRF header; `credentials: 'include'` only to the
  own API.
- **`VITE_*` variables are public** — no secrets in them, ever.
- `?redirect=` targets are same-origin relative paths only (open redirect).
- **Logout** clears the server session, the TanStack Query cache and all persisted
  stores.
- CSP as an HTTP header with `object-src 'none'`, `base-uri 'none'`, `frame-ancestors`.
- `postMessage` handlers check `event.origin`; never merge untrusted objects (prototype
  pollution).
- The frontend never enforces authorization — the backend does [ASVS 8.3.1].

## TypeScript and Biome

- `strict` on (the default since TypeScript 7 — keep it explicit); also
  `noUncheckedIndexedAccess`, `verbatimModuleSyntax`, `moduleResolution: "bundler"`,
  `lib` with `ES2023` + `DOM`. TypeScript 7 defaults `types` to `[]` — list
  `"vite/client"` explicitly; `baseUrl` is gone, use `paths` (`"@/*": ["./src/*"]`).
- No `any` (use `unknown` and narrow), no non-null assertions to silence errors, no
  `@ts-ignore` (`@ts-expect-error` with a reason if unavoidable). No magic numbers or
  strings — named constants in `shared/config/` or the slice's `config`/`model`.
- Types of external data come from Zod schemas (`z.infer`/`z.output`), not hand-written
  interfaces that can drift.
- Biome: recommended rules plus `noNestedComponentDefinitions`, `noReExportAll` and
  `noConsole` (not in the recommended set); `noBarrelFile` stays off for slice
  `index.ts` files (`references/structure.md`).
- `biome ci`, `tsc --noEmit`, `steiger ./src` and `knip` pass locally and in CI. Don't
  disable rules inline without a comment explaining why.
- Comments in English; TODOs use the project's TODO marker.

## Repository hygiene — always

- **Node version pinned**: `.nvmrc` (LTS), `engines` in `package.json` with
  `engine-strict`, `packageManager` with the exact npm/pnpm version; lockfile committed.
- **pre-commit** installed for commit **and** push: gitleaks on staged changes and on all
  unpushed commits, Biome; `tsc`, related Vitest tests and the dependency audit on push.
  Never bypass with `--no-verify`.
- Dependency audit in CI on every MR and on a schedule.

Details: `references/tooling.md`.

## Docker and deployment

Container images, `.dockerignore`, Compose and Kubernetes are covered by the
[`docker-kubernetes`](../docker-kubernetes/SKILL.md) skill; the frontend workflow and
checklist are in `references/docker.md`. Every image has a `.dockerignore`.
Frontend-specific facts to respect there:

- `VITE_*` values are **baked into the bundle at build time**. One image for several
  environments needs runtime config: serve a `config.json` (or `config.js`) that is
  written at container start from environment variables and fetched/validated at app
  startup — still public, still no secrets.
- A **Vite SPA** is static files: serve them from a web server with a fallback to
  `index.html` for client-side routes, long cache for hashed assets, `no-cache` for
  `index.html`, and the security headers from `references/security.md`.
- **React Router framework mode** (SSR) needs a **Node server** at runtime
  (`react-router-serve` or a custom server) — it is not a static deployment.

## After writing

For a security review of the result, suggest the `appsec-review` skill.

## Sources

Combined from Vercel Engineering's React best practices
(github.com/vercel-labs/agent-skills, `react-best-practices`, MIT License) — adapted from Next.js to
Vite/React Router with TanStack Query; rule ids kept for traceability — and the OWASP
Secure Agent Playbook (CC BY 4.0; OWASP ASVS 5.0). Structure follows Feature-Sliced
Design (feature-sliced.design, fsd.how); `references/fsd/` is adapted from the official
FSD agent skill (github.com/feature-sliced/skills, MIT License). Accessibility targets
WCAG 2.2.
