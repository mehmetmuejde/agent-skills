# Structure — Feature-Sliced Design

The frontend follows Feature-Sliced Design (FSD, v2.1). This file covers layers,
slices, segments, public APIs, import rules, how routing frameworks fit in, and how the
FSD public API relates to the "avoid barrel files" performance rule. It holds the
binding conventions of this skill; the upstream FSD rulebook with its decision tree and
the topic deep dives live in `fsd/` (list at the end). Naming, design system and layouts:
`code-style.md`.

## Layers

Top to bottom. A module may import **only from layers strictly below** its own.

| Layer | Holds | Sliced? |
|---|---|---|
| `app` | Entry, providers (QueryClient, router, theme), global styles, app-wide init | no — segments only |
| `pages` | One slice per page/route: page UI, page-level data loading | yes |
| `widgets` | Discouraged — only a composed UI block reused across several pages that can't live in a page | yes |
| `features` | User interactions that bring business value (add-to-cart, login-form) | yes |
| `entities` | Business concepts (user, order): domain rules, domain types and mapping, entity UI | yes |
| `shared` | Business-agnostic code: API client, UI kit, libs, config, i18n | no — segments only |

- `processes` is deprecated — don't create it.
- Use only the layers you need. Most apps start with `app`, `pages`, `shared` and add
  `entities`/`features` only when the extraction rule holds.
- **Pages first — the extraction rule** (`fsd/rules.md`, Section 1): code stays in the
  page slice and moves to a lower layer only when **all three** hold:
  1. the same code is used in several places **right now**, not hypothetically;
  2. it has a reason to change that is independent of any one consumer;
  3. the boundary has a focused responsibility.

  A second consumer alone is not enough — duplication across pages is acceptable until
  then. Moving code down later is cheap; premature `entities`/`features` are not. The
  upstream decision tree (where is it used → infrastructure? → user action? → domain
  model? → app-wide?) is in `fsd/rules.md`, Sections 2–3.
- **Widgets are discouraged.** Don't create a `widgets` slice by default: a
  screen-specific composition stays in the page, a reused action with its UI goes to
  `features`, context-free UI to `shared/ui`, the app frame to `app`. Use `widgets` only
  for a composed block that is reused across several pages and can't live in a page.
  Existing widgets stay valid — no forced migration (`fsd/layer-structure.md`).
- No empty layer folders "just in case"; no `@/<layer>` alias for a layer that doesn't
  exist.

## Slices and segments

- A **slice** groups code by business domain (`entities/user`, `features/auth-by-email`).
  Names in kebab-case.
- A **segment** groups code inside a slice by technical purpose:

| Segment | Content |
|---|---|
| `ui` | Components, styles, stories |
| `model` | State (Zustand stores), Zod schemas, types, business logic, hooks |
| `api` | Request functions, query/mutation options, query key factories |
| `lib` | Slice-internal helpers with one clear focus |
| `config` | Constants, feature flags of this slice |

- Name segments by **purpose**, never by essence: no `components/`, `hooks/`, `types/`,
  `utils/`, `helpers/`.
- Tests and stories live next to the file they cover (`LoginForm.tsx`,
  `LoginForm.test.tsx`, `LoginForm.stories.tsx`).

```
src/
  app/            providers/, router/, styles/, main.tsx
  pages/
    order-details/
      ui/OrderDetailsPage.tsx
      api/order-details.loader.ts
      index.ts
  features/
    cancel-order/
      ui/CancelOrderButton.tsx
      api/use-cancel-order.ts
      model/cancel-order.schema.ts
      index.ts
  entities/
    order/          only once the extraction rule holds and there are domain rules
      model/order-status.ts      status transitions (canCancelOrder, …)
      ui/OrderStatusBadge.tsx
      index.ts
  shared/
    api/          client.ts, index.ts (+ generated client, never edited by hand)
      order/      get-order.ts, list-orders.ts, order.schema.ts, order.queries.ts
    auth/         session helpers (no tokens in JS — security.md), index.ts
    ui/           primitives/ (UI-library CLI zone), button/index.ts, dialog/index.ts, …
    lib/          dates/index.ts, …
    config/       env.ts, index.ts
    i18n/         setup + locales/ (i18n.md)
```

- File names inside a segment describe the domain, not the technical role:
  `model/order.schema.ts`, `api/fetch-profile.ts` — never `types.ts`, `utils.ts`,
  `helpers.ts` or one `endpoints.ts` holding every domain (`fsd/rules.md`, Rule 4-4).
- Shared holds no business logic — no rule the product enforces on its own data. Route
  constants, API endpoints, branding assets and transport types are fine there
  (Rule 4-5).
- Static assets live next to the code that uses them; global styles and fonts in
  `app/`; files served at fixed URLs in `public/`. No top-level `assets/` folder
  (`fsd/asset-handling.md`).

## Public API — `index.ts` per slice

Every slice has an `index.ts`. Code outside the slice imports **only** from it.

✅
```ts
// entities/order/index.ts
export { OrderStatusBadge } from './ui/OrderStatusBadge'
export { canCancelOrder } from './model/order-status'
```

```ts
// shared/api/index.ts
export { apiFetch } from './client'
export { orderQueries } from './order/order.queries'
export { type Order, orderSchema } from './order/order.schema'
```

❌ `export * from './ui'` — hides the interface and leaks internals.
❌ `import { OrderStatusBadge } from '@/entities/order/ui/OrderStatusBadge'` from
another slice — sidesteps the public API.

- Explicit named re-exports only; no `export *`, no `export * as ns`.
- Export the minimum other slices need. Internal helpers stay unexported.
- No extra `index.ts` per segment inside a slice (`features/x/ui/index.ts`) — one
  public API per slice is enough.
- **`shared/ui` and `shared/lib` have one index per component/library**, not one for the
  whole segment: `import { Button } from '@/shared/ui/button'`. A single
  `shared/ui/index.ts` would pull every component (and its heavy dependencies) into
  every consumer.
- Inside a slice, import **relatively** (`./model/...`); across slices, import
  **absolutely** via the alias (`@/entities/order`).

## Import rules

- Only downward: `pages → widgets → features → entities → shared`. `app` may import
  everything; `shared` imports nothing from above.
- **No cross-imports between slices on the same layer** (`features/a` must not import
  `features/b`). Compose them one layer higher (in the page or widget) instead.
- Exception for entities that genuinely reference each other: the `@x` notation.
  `entities/song/@x/artist.ts` is a public API of `song` made only for `artist`:

```ts
// entities/artist/model/artist.ts
import type { Song } from '@/entities/song/@x/artist'
```

  Use it sparingly and for types/schemas — not as a general escape hatch. Several `@x`
  files between the same entities mean the boundaries are wrong — merge them.
- Same-layer reuse in `features`/`widgets`, in this order: merge slices that always
  change together → move a shared domain rule down to an entity → compose both slices
  in the page/app (render props, slots) → as a last resort import the other slice's
  public API with a comment explaining why. Details: `fsd/cross-import-patterns.md`.
- Circular imports through a slice's own `index.ts` are a bug: inside the slice, import
  the file directly, never the slice's own public API.

## Enforce it with tooling

- **Steiger** (`steiger` + `@feature-sliced/steiger-plugin`, installed as exact dev
  dependencies; the old `@feature-sliced/steiger` package name is outdated) is the FSD
  linter. Run it (`steiger ./src`, e.g. as the `arch` script) locally and in CI next to
  Biome, knip and `tsc --noEmit`. Relevant rules: `fsd/forbidden-imports`, `fsd/no-cross-imports`,
  `fsd/no-public-api-sidestep`, `fsd/public-api`, `fsd/no-wildcard-exports`,
  `fsd/import-locality`, `fsd/segments-by-purpose`.

```ts
// steiger.config.ts
import { defineConfig } from 'steiger'
import fsd from '@feature-sliced/steiger-plugin'

export default defineConfig([...fsd.configs.recommended])
```

- Exceptions go into the Steiger config **with a comment explaining why** — and only
  after the user approved them, never as a reflex to silence a warning.
- `insignificant-slice` (a slice with zero or one consumer) means: merge it back into
  its consumer. `excessive-slicing` means: merge or group slices (slice groups,
  `fsd/layer-structure.md`).

- **Biome**: enable `performance/noReExportAll` (no `export *`). `noBarrelFile` is not in
  the recommended set; if the project enables it, exempt the public-API files — the
  slice `index.ts` is an architectural boundary, not a library barrel (see below):

```json
{
  "overrides": [
    {
      "includes": ["src/**/index.ts", "src/**/index.server.ts", "src/**/@x/*.ts"],
      "linter": { "rules": { "performance": { "noBarrelFile": "off" } } }
    }
  ]
}
```

- Biome `style/noRestrictedImports` can back up Steiger in the editor (it matches the
  import string, not the resolved path; globs need `**`), e.g. forbid deep imports into
  slices: `"group": ["@/entities/*/**", "@/features/*/**", "!@/entities/*",
  "!@/features/*"]` — but keep `@/entities/<slice>/@x/<consumer>` allowed.
- Path alias `@/*` → `src/*` in `tsconfig.json` and Vite (`resolve.alias` or
  `vite-tsconfig-paths`, whichever the project already uses).

## FSD public API vs. "avoid barrel imports"

The performance rule "import directly, avoid barrel files" (Vercel
`bundle-barrel-imports`) targets **third-party libraries with thousands of
re-exports**. It does not cancel FSD's public API. Resolution:

1. **Keep `index.ts` per slice** — it is the architecture boundary.
2. **Keep slice indexes small** and explicit (named re-exports, no `export *`), so the
   bundler can tree-shake them and readers see the interface.
3. **Heavy modules never sit in an index that many routes import.** Charts, editors,
   PDF viewers, maps: give them their own `shared/ui/<name>/index.ts` and load them
   lazily (`React.lazy` / route-level splitting) — see `performance.md`.
4. **Third-party libraries with large entry barrels** (icon sets, big UI kits,
   `lodash`, `date-fns`): import from typed sub-paths where the library ships them
   (`lodash-es/debounce`, `@mui/material/Button`). Check that the sub-path has type
   declarations — under `strict`, an untyped deep import becomes `any`. Vite pre-bundles
   dependencies in dev, so the main cost of big barrels shows up in **Vitest** run time
   and in **side-effectful modules** — measure before rewriting imports.
5. Modules with top-level side effects (CSS imports, registrations) are not re-exported
   from widely used indexes.

## Routing frameworks and FSD

### TanStack Router (file-based) or React Router data/declarative mode

- Route files (`src/routes/…` for TanStack file-based routing, or the route config in
  `app/router/`) stay **thin**: path, search-param schema, loader wiring, and the page
  component imported from `@/pages/<slice>`.
- The page UI and its data logic live in the page slice; the route file only connects
  them.
- **Code-based TanStack Router**: each page slice exports its route definition (or a
  route factory) through its `index.ts`; root route, layouts and the assembled tree live
  in one place in `app/` (e.g. `app/router.tsx`). Type factories generically and return
  an object:
  `export const createOrderRoutes = <TParent extends AnyRoute>(parentRoute: TParent) => ({ list, detail })`.
  A parameter typed as plain `AnyRoute` or an array return erases the path types from
  the router register — `navigate({ to })` then suddenly demands a `search` property.

### React Router framework mode

- React Router expects its own `app/` directory (`routes.ts`, `root.tsx`, route modules).
  Keep it at the **project root** and keep FSD code in `src/` — the FSD `app` layer is
  `src/app/`. Two different folders, no conflict. If the project prefers to avoid the
  name clash entirely, rename the FSD layers to `_app`/`_pages` (Steiger accepts this).
- Route modules in the root `app/routes/` are thin: `loader`/`action` call functions
  from the page slice, the default export renders the page component.
- Server-only code (session handling, secrets, direct backend calls with server
  credentials) lives in `*.server.ts` modules; export it through a separate
  `index.server.ts` public API so it can never be pulled into the client bundle.

```tsx
// app/routes/orders.$orderId.tsx  (React Router framework mode)
import { OrderDetailsPage, loadOrderDetails } from '@/pages/order-details'
import type { Route } from './+types/orders.$orderId'

export const loader = ({ params }: Route.LoaderArgs) => loadOrderDetails(params.orderId)
export default OrderDetailsPage
```

## Where things go — quick decisions

| Code | Place |
|---|---|
| API client (fetch wrapper, CSRF header, error mapping) | `shared/api` |
| Request functions, CRUD, query key factory + `queryOptions` of a resource | `shared/api/<resource>/` (the page's `api` while only that page uses them) |
| Request that carries domain rules or mapping of an established entity | `entities/<x>/api` |
| Mutation hook for one user action | `features/<action>/api` (or the page, if used once) |
| Zod schema of an API response (transport type) | `shared/api/<resource>/`, next to its request |
| Domain type or mapping the backend doesn't send | `entities/<x>/model` (the page's `model` until extracted) |
| Zod schema of a form | slice that owns the form, `model` segment |
| Zustand store for UI state of one feature | `features/<x>/model` |
| App-wide client state (theme, sidebar) | `shared/model` or `app/` providers — never in `entities` |
| Env access + validation | `shared/config/env.ts` |
| Design-system components | `shared/ui/<component>/` (built from `shared/ui/primitives/`, `code-style.md`) |
| Generated API client (e.g. Hey API from OpenAPI) | `shared/api/` — never edited by hand |
| Session helpers, CSRF token source | `shared/auth/` or `shared/api/` (`fsd/auth-and-api.md`) |
| App frame (AppShell, header, navigation, public vs. signed-in layout) | `app/layout/` |
| Neutral layout blocks (`PageContainer`, `Stack`, `Grid`) | `shared/ui/` |
| i18n setup and locale files | `shared/i18n/` |
| Login form used on one page / on several pages (page + modal) | `pages/login/` / `features/auth/` |
| Logout flow reused across screens | `features/logout/` (navigation stays in the page) |
| Route definitions | thin route files (see above), page UI in `pages/<slice>` |

## FSD deep dives — read only when the situation applies

Adapted from the official FSD agent skill (`feature-sliced/skills`, MIT). Don't preload
them.

| Situation | Read |
|---|---|
| Upstream rulebook: extraction rule, decision tree, placement table, MUST/SHOULD rules, anti-patterns | `fsd/rules.md` |
| Reviewing/reorganizing folders, what goes inside a layer or slice, where a layout belongs, routing widget-like code, slice groups | `fsd/layer-structure.md` |
| Setting up a new FSD project, deciding whether entities/features are needed yet, how a structure earns each layer | `fsd/growth-walkthrough.md` |
| Same-layer cross-imports, `@x`, choosing strategy A–D, merging boundaries | `fsd/cross-import-patterns.md` |
| Creating or removing an entity, too many entities, skipping the entities layer, CRUD placement, isolating business contexts | `fsd/excessive-entities.md` |
| Placing images, icons, fonts, PDFs, stylesheets | `fsd/asset-handling.md` |
| Migrating FSD v2.0 → v2.1, a non-FSD codebase → FSD, phasing out widgets or processes | `fsd/migration-guide.md` |
| Wiring FSD into Vite, React Router, Next.js, Nuxt, Astro; path aliases; server/client entry points | `fsd/framework-integration.md` |
| Session handling, login/logout flows, DTO and domain type placement, where a request function lives | `fsd/auth-and-api.md` |
| Placing TanStack Query factories, mutations, infinite queries, `useMutationState`, Redux in legacy code | `fsd/state-management.md` |
