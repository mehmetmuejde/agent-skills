# Performance

Performance rules adapted from Vercel's React best practices to a Vite SPA and React
Router framework mode with TanStack Query. Vercel rule ids in brackets. Ordered by
impact: waterfalls and bundle size first, micro-optimizations last.

**Measure first.** Use the browser Performance panel, React DevTools Profiler, Lighthouse
and a bundle visualizer (`rollup-plugin-visualizer`) before optimizing. Don't add
complexity for a gain nobody measured. Loop: **measure → diagnose the bottleneck → fix
it specifically → monitor** (bundle size, runtime).

### React DevTools Profiler

1. Start recording, perform the interaction, stop.
2. Which components re-rendered, for how long, and was it necessary?
3. Rough scale per commit: < 1 ms fine, < 10 ms acceptable, > 10 ms worth optimizing.

Memoize only when the Profiler shows the re-render, the work is measurably expensive
(> ~1 ms) and the dependencies are stable (`hooks-and-rendering.md`, Memoization). When
unsure whether an optimization is worth it, leave a note with the project's TODO marker
and ask the user instead of adding it speculatively.

## 1. Eliminate request waterfalls — CRITICAL

Each sequential request adds a full round trip. Typical SPA waterfalls: route chunk
loads → component mounts → parent query → child query.

### Start data loading in the route, not in the component [async-suspense-boundaries]

Route loaders run **in parallel** with the lazy route chunk download. Components read
from the already-filled Query cache.

```ts
// TanStack Router
export const Route = createFileRoute('/orders/$orderId')({
  loader: ({ context: { queryClient }, params }) =>
    queryClient.query({ ...orderQueries.detail(params.orderId), staleTime: 'static' }),
  component: OrderDetailsPage,
})
// in the page: const { data } = useSuspenseQuery(orderQueries.detail(orderId))
```

```ts
// React Router — client loader with the browser QueryClient
export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  await queryClient.query({ ...orderQueries.detail(params.orderId), staleTime: 'static' })
  return null
}
```

- `queryClient.query({ ...options, staleTime: 'static' })` returns cached data
  immediately if present and fetches otherwise ("ensure" semantics); the component's
  `useSuspenseQuery` then refetches in the background if the data is stale. Since
  TanStack Query 5.102 this replaces the deprecated `ensureQueryData`
  (`fetchQuery` → `query(options)`, `prefetchQuery` → `query(options).catch(noop)`).
  Use the old names only if the project is on an older 5.x version.
- The loader uses the **same `queryOptions`** as the component, so the cache key
  matches and the component doesn't refetch.
- Only `await` what the first paint needs. Secondary data: start it without awaiting
  (`void queryClient.query(opts).catch(noop)` — the error stays in the cache and is
  shown by the component that reads it) and let that section suspend or show a
  skeleton.

### Parallel, not sequential [async-parallel]

- Independent queries in one component: `useSuspenseQueries` / `useQueries`, or
  separate `useSuspenseQuery` calls in **sibling** components under one `<Suspense>`
  (sequential `useSuspenseQuery` calls in the *same* component run one after another).
- Independent requests inside one `queryFn` or loader: `Promise.all`.

❌
```ts
const user = await getUser(id)
const settings = await getSettings(id)
```
✅
```ts
const [user, settings] = await Promise.all([getUser(id), getSettings(id)])
```

### Partial dependencies [async-dependencies, server-parallel-nested-fetching]

Start everything that can start; chain only what depends on a previous result.

```ts
const userPromise = getUser(id)
const profilePromise = userPromise.then((user) => getProfile(user.profileId))
const [user, config, profile] = await Promise.all([userPromise, getConfig(), profilePromise])
```

For lists, chain per item so one slow item doesn't block the others:

```ts
const authors = await Promise.all(
  chatIds.map((id) => getChat(id).then((chat) => getUser(chat.authorId))),
)
```

No extra dependency (like `better-all`) for this — promise chaining is enough.

### Await late, check cheap conditions first [async-defer-await, async-cheap-condition-before-await]

Move `await` into the branch that needs the value; evaluate synchronous conditions
before awaiting a remote flag.

✅
```ts
if (!canEdit) return null
const draft = await loadDraft(id)
```

### Granular Suspense boundaries [async-suspense-boundaries]

Wrap each independently loading region in its own `<Suspense>` with a skeleton of the
final size (no layout shift). Don't suspend the whole page for a sidebar widget. Never
create a promise during render and pass it to `use()` in client components — a new
promise is created on every render; use Query instead.

### Avoid "chunk, then data" waterfalls

A lazily loaded component that starts its own query only after its chunk arrived is a
waterfall. Prefetch its data in the route loader or on intent (section 3).

## 2. Bundle size — CRITICAL

### Code-split every route [bundle-dynamic-imports]

- TanStack Router: `autoCodeSplitting` in the router Vite plugin (or `.lazy.tsx`
  route files).
- React Router framework mode splits per route module automatically; in data mode use
  the route `lazy` property.
- Plain SPA: `React.lazy(() => import('./SettingsPage'))` + `<Suspense>`.

### Lazy-load heavy components and libraries [bundle-dynamic-imports, bundle-conditional]

Editors, charts, maps, PDF/Office viewers, syntax highlighters, date-heavy libraries:
load them when the feature is used.

```tsx
const RichTextEditor = lazy(() => import('@/shared/ui/rich-text-editor'))
```

Large data (translations of other locales, geo data, animation frames): `import()` when
needed, not at module top level.

### Statically analyzable dynamic imports [bundle-analyzable-paths]

The bundler must see every possible target.

❌ `import(\`./locales/${lang}.ts\`)` with arbitrary input, or `import(PATHS[name])`
✅
```ts
const LOCALES = {
  de: () => import('./locales/de'),
  en: () => import('./locales/en'),
} as const
const messages = await LOCALES[lang]()
```

### Barrel files and the FSD public API [bundle-barrel-imports]

- Slice `index.ts` files stay (architecture boundary) but are small and explicit — no
  `export *`. Details: `structure.md`.
- `shared/ui` and `shared/lib` have one index per component/library; heavy components
  are lazy-loaded and never re-exported from an index many routes import.
- Third-party libraries with huge entry barrels (icon sets, big UI kits, `lodash`):
  import typed sub-paths where available; check the visualizer output.

### Defer non-critical third-party code [bundle-defer-third-party]

Analytics, session replay, chat widgets, feedback tools: load after the first render or
when the browser is idle — never in the critical path.

```ts
// src/app/main.tsx — after render
scheduleIdle(() => { void import('./analytics').then((m) => m.initAnalytics()) })
```

Error tracking is the exception: initialize it early (it must see startup errors), but
load optional integrations (replay, profiling) lazily.

### Keep an eye on the budget

- The bundle visualizer is part of every project:

```ts
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer'
plugins: [visualizer({ filename: 'stats.html', gzipSize: true, brotliSize: true })]
```

- Check it when adding a dependency, with every larger feature and before every
  hand-over; prefer smaller alternatives and platform APIs (`Intl`, `URL`,
  `structuredClone`).
- Typical findings: Moment.js (use `date-fns`/`Intl`/Temporal), full `lodash` (use
  `lodash-es` sub-paths or the platform), duplicate versions of one dependency, a whole
  UI library or icon set pulled in instead of single components.
- Set a size budget in CI for the initial chunk if the project defines one; without a
  project budget, aim for initial vendor JavaScript below ~300 KB gzip.

## 3. Preload on intent [bundle-preload]

Start loading code and data when the user signals intent (hover, focus, touchstart) —
typically 100–300 ms before the click.

- **TanStack Router**: `defaultPreload: 'intent'` on the router; `<Link preload="intent">`
  per link. Route loaders then run on hover and fill the Query cache.
- **React Router**: `<Link prefetch="intent">` (framework mode prefetches route modules
  and loader data; `"viewport"` and `"render"` exist for more aggressive cases).
- **Components/features**: start the `import()` and the data prefetch
  (`queryClient.query(opts).catch(noop)`) in `onMouseEnter`/`onFocus` handlers.

```tsx
<button
  type="button"
  onMouseEnter={preloadEditor}
  onFocus={preloadEditor}
  onClick={openEditor}
>
  Edit
</button>
```

- Resource hints [rendering-resource-hints]: `<link rel="preconnect">` to the API or
  CDN origin and `<link rel="preload">` for the main web font go directly into
  `index.html` (SPA) or the `links` export (React Router framework mode). React DOM's
  `preconnect`/`preload` functions are for dynamic cases.
- Third-party scripts that must be in `index.html` use `defer` or `async`
  [rendering-script-defer-async]. Vite's own bundle is already a deferred module.

## 4. Narrow subscriptions — re-render only what changed [rerender-derived-state, rerender-defer-reads]

- **Zustand**: select the smallest slice; select derived booleans; `useShallow` when
  selecting several fields.

```ts
const itemCount = useCartStore((s) => s.items.length)           // ✅
const hasItems = useCartStore((s) => s.items.length > 0)          // ✅ boolean
const { items, total } = useCartStore(useShallow((s) => ({ items: s.items, total: s.total })))
const cart = useCartStore()                                       // ❌ re-renders on any change
```

- **TanStack Query**: `select` to subscribe to a projection; only that projection's
  changes re-render.

```ts
const { data: orderTitle } = useQuery({ ...orderQueries.detail(id), select: (o) => o.title })
```

- **Router search params**: `Route.useSearch({ select: (s) => s.page })` (TanStack
  Router) instead of the whole search object.
- **Context**: split contexts by update frequency; memoize object values.
- Values only used inside handlers are read there (`getState()`, `getQueryData()`), not
  subscribed to.

More rendering rules (derived state, memoization, transitions, `<Activity>`, long lists):
`hooks-and-rendering.md`.

## 5. Rendering

- **Long lists** [rendering-content-visibility]: `content-visibility: auto` or
  virtualization with `@tanstack/react-virtual` (`hooks-and-rendering.md`).
- **Non-urgent updates** [rerender-transitions, rerender-use-deferred-value]:
  `useTransition` / `useDeferredValue` for expensive client-side filtering and tab
  switches.
- **Layout thrashing** [js-batch-dom-css]: don't interleave layout reads
  (`getBoundingClientRect`, `offsetWidth`) with style writes; prefer toggling CSS classes
  over writing inline styles; batch reads, then writes.
- **Animations**: CSS transitions/keyframes (CSS modules or the design system's
  tokens) rather than JavaScript animation loops; subtle page transitions on route
  changes are welcome when they respect reduced motion. Animate `transform` and
  `opacity` only. Animate a wrapper element
  instead of the `<svg>` itself [rendering-animate-svg-wrapper]. Respect
  `prefers-reduced-motion` (`accessibility.md`).
- **SVG assets** [rendering-svg-precision]: optimize with SVGO (reduced precision,
  removed metadata) at build time.
- **Images**: explicit `width`/`height` (no layout shift), `loading="lazy"` below the
  fold, modern formats, responsive `srcset`.

## 6. Background work [js-request-idle-callback]

Non-critical work (analytics events, persisting drafts, prefetching likely next data)
runs when the browser is idle. `requestIdleCallback` is missing in some browsers — use a
fallback:

```ts
// client-only module (never evaluated on the server)
export const scheduleIdle: (cb: () => void) => void =
  typeof window.requestIdleCallback === 'function'
    ? (cb) => window.requestIdleCallback(cb, { timeout: 2000 })
    : (cb) => window.setTimeout(cb, 1)
```

Not for anything the user is waiting for.

## 7. Caches and module state

- **Server data is cached by TanStack Query only.** No hand-written module-level caches
  for API responses.
- Module-level caches are allowed **only for pure memoization** of deterministic,
  non-sensitive computations (e.g. a slug or formatter cache) and must be **bounded**
  (size limit or LRU) [js-cache-function-results]. Never for app state, user data,
  auth state or anything that must be cleared on logout.
- Storage reads (`localStorage`) go through Zustand `persist`, which reads once at
  startup — no separate storage cache [js-cache-storage].
- In React Router framework mode, server-side module scope is shared by all requests —
  no request or user data there [server-no-shared-module-state].
- **Errors are never swallowed** — not in caches, prefetches, idle callbacks or dynamic
  imports. A failed `import()` shows an error boundary with retry; a failed prefetch is
  harmless but still not hidden behind an empty `catch {}`.

## 8. JavaScript micro-optimizations — only on measured hot paths

Apply these when profiling shows a hot loop (large lists, frequent handlers), not by
default:

| Rule | Use |
|---|---|
| [js-index-maps] | Build a `Map` by id once instead of repeated `.find()` |
| [js-set-map-lookups] | `Set`/`Map` for repeated membership checks instead of `.includes()` |
| [js-combine-iterations] | One loop instead of several `.filter()` passes over the same big array |
| [js-flatmap-filter] | `flatMap` instead of `.map().filter(Boolean)` |
| [js-early-exit] | Return as soon as the result is known |
| [js-length-check-first] | Compare lengths before expensive array comparisons |
| [js-min-max-loop] | One pass for min/max instead of sorting |
| [js-hoist-regexp] | Create regexes once at module scope (beware `g` flag state) |
| [js-tosorted-immutable] | `toSorted()` — this one is about correctness, always apply |

`js-cache-property-access` is not worth applying — modern engines optimize it.

## Vercel rules not used here

Next.js/RSC-specific rules do not apply: `server-cache-react`, `server-cache-lru`,
`server-dedup-props`, `server-serialization`, `server-parallel-fetching`,
`server-after-nonblocking`, `server-hoist-static-io`, `async-api-routes`,
`server-auth-actions` (its idea — every server endpoint checks auth itself — applies to
React Router `action`s and to the backend), `client-swr-dedup` (TanStack Query covers
deduplication; no SWR).

## Checklist before hand-over

- [ ] Every route code-split, with its own Suspense boundary/pending UI
- [ ] Bundle visualizer checked — no surprises, budget kept
- [ ] No request waterfalls on the main routes (network panel)
- [ ] Profiler: no unnecessary re-renders on the main interactions
- [ ] `console.*`/`debugger` dropped from the production build (`security.md`)
- [ ] i18n complete — no missing keys (`i18n.md`)
- [ ] Animations smooth (60 fps) and reduced-motion safe
