# Data and state

Three kinds of state, three homes:

| State | Home | Never in |
|---|---|---|
| **Server state** — anything that comes from the backend | TanStack Query cache | `useState`, Zustand, Context |
| **URL state** — filters, sorting, pagination, selected tab, search text | Typed search params of the router | Zustand, `useState` |
| **Client state** — UI-only state (theme, sidebar open, draft wizard step) | `useState` locally; Zustand when shared across distant components | Query cache |

Forms have their own state (`forms.md`).

More rules for where state lives:

- Keep state as local as possible — `useState` for local UI state (dialog open,
  toggles); lift it only as far as needed.
- `useReducer` only after asking the user (it's rarely needed next to Query and
  Zustand). **No Redux** in new code. React Context only if the project already uses
  it for that purpose — otherwise Zustand.
- No module-level `Set`/`Map`/arrays for tracking state — they bypass React, leak
  between tests and survive logout.
- Tables: TanStack Table (headless) on top of the Query data.

## Data flow

```
request function (api segment) → hook (query/mutation, transformation, logic) → component (render, interaction)
```

- Every endpoint is one exported request function; hooks build on them; components
  call hooks. No additional abstraction layers (repositories, services, adapters)
  without the user's approval.
- **Never import an HTTP client** (`fetch` wrappers, Axios, generated clients) directly
  in hooks or components — that bypasses the shared client's CSRF header, error mapping
  and 401 handling (`security.md`).
- A generated client (e.g. Hey API from OpenAPI) lives in `shared/api/` and is never
  edited by hand; own extensions sit next to it. Generated responses are still parsed
  with Zod at the boundary (generate the Zod schemas too, or write them).

## 1. Server state — TanStack Query

### API boundary

- Request functions use the shared API client (`shared/api`) and live by ownership
  (`structure.md`, `fsd/auth-and-api.md`, request placement rule):
  - used by one page or feature only → that slice's `api` segment;
  - plain resource access and CRUD shared by several slices → `shared/api/<resource>/`,
    however many slices call it;
  - carries domain rules or mapping of an established entity (permission checks,
    status transitions, a model composed from several responses) →
    `entities/<x>/api`.
- Existing request functions in `entities/<x>/api` without domain rules keep working;
  move them when that slice is being changed anyway — no repository-wide sweep.
- Every response is parsed with a Zod schema **before** it enters the cache. The
  component works with typed, validated data.

```ts
// shared/api/order/get-order.ts
export async function getOrder(id: string, signal?: AbortSignal): Promise<Order> {
  const response = await apiFetch(`/orders/${encodeURIComponent(id)}`, { signal })
  return orderSchema.parse(await response.json())
}
```

- Pass the `signal` from the `queryFn` context to `fetch` so cancelled queries abort
  the request.

### Query key factory + `queryOptions`

One factory per resource, next to its request functions (`shared/api/<resource>/`, or
the owning page/feature while only it uses them). Keys are hierarchical arrays so
invalidation can target a whole group. Components, loaders and prefetches use the same
options object.

```ts
// shared/api/order/order.queries.ts
import { queryOptions, keepPreviousData } from '@tanstack/react-query'

export const orderQueries = {
  all: () => ['orders'] as const,
  lists: () => [...orderQueries.all(), 'list'] as const,
  list: (filters: OrderFilters) =>
    queryOptions({
      queryKey: [...orderQueries.lists(), filters] as const,
      queryFn: ({ signal }) => listOrders(filters, signal),
      placeholderData: keepPreviousData, // keep old page visible while paging
    }),
  details: () => [...orderQueries.all(), 'detail'] as const,
  detail: (id: string) =>
    queryOptions({
      queryKey: [...orderQueries.details(), id] as const,
      queryFn: ({ signal }) => getOrder(id, signal),
    }),
}
```

- Every input of the `queryFn` is part of the key. A missing key part means stale or
  wrong data.
- No hand-written string keys in components.

### Reading data

- With a route loader that ensured the data: `useSuspenseQuery(orderQueries.detail(id))`
  — `data` is always defined; loading and error states are handled by the route's
  `<Suspense>`/pending component and error boundary.
- Without a loader: `useQuery(...)` and handle `isPending`, `isError`, empty data
  explicitly — every state has UI (skeleton, error with retry, empty state).
- Dependent query: `enabled: Boolean(parentId)` or, better, fetch both in one loader.
- Projections: `select` (re-renders only when the projection changes).

### Client setup

```ts
// src/app/providers/query-client.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // project decision; 0 refetches on every mount
      retry: (count, error) => !isClientError(error) && count < 2, // no retry on 4xx
    },
  },
})
```

- One `QueryClient` per browser app, created **outside** components. Components and
  hooks reach it through `useQueryClient()` — never by importing the instance; only
  loaders and app wiring use the module instance or router context.
- `staleTime` per kind of data: master/reference data `Infinity` (or very long),
  lists 1–5 min, badges/counters ~30 s. `refetchInterval` only deliberately per query,
  never as a global default. Keep `refetchOnWindowFocus: true` (the TanStack default).
- React Router framework mode with SSR: create a **new `QueryClient` per request** on the
  server (never share it across requests — it would leak user data between users), then
  dehydrate/hydrate the cache to the client (section 2).
- Query Devtools only in development (lazy import guarded by `import.meta.env.DEV`).

### Mutations

```ts
// features/cancel-order/api/use-cancel-order.ts
export function useCancelOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (orderId: string) => cancelOrder(orderId),
    onSuccess: (_data, orderId) =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: orderQueries.detail(orderId).queryKey }),
        queryClient.invalidateQueries({ queryKey: orderQueries.lists() }),
      ]),
  })
}
```

- After a successful mutation, **invalidate** every affected query (or write the
  returned entity with `setQueryData` when the response contains it). Returning the
  promise from `onSuccess` keeps the mutation pending until the refetch finished.
- `isPending` disables the submit button and shows progress; errors are shown to the
  user (toast, inline message) — never ignored.
- **Optimistic updates** only where latency matters (toggles, reordering):
  - simplest: render the pending `mutation.variables` in the UI while `isPending`
    (other components: `useMutationState({ filters: { mutationKey } })`);
  - cache-based: in `onMutate(variables, context)` call
    `context.client.cancelQueries(...)`, snapshot with `getQueryData`, write with
    `setQueryData`, return the snapshot; restore it in
    `onError(error, variables, onMutateResult, context)`; invalidate in `onSettled`.
- Mutations are never retried automatically unless the endpoint is idempotent.

### Errors

- Query errors bubble to the nearest error boundary when using Suspense
  (`useSuspenseQuery`); reset with `QueryErrorResetBoundary` + the boundary's reset.
- `401` from any request triggers the logout flow (`security.md`) — centrally in the API
  client or a `QueryCache`/`MutationCache` `onError`, not in every component.
- Global error toasts for background refetch failures go through `QueryCache({ onError })`
  — one place, no duplicates. `5xx` responses show one generic message centrally.
- Other own async calls (outside Query mutations) handle **both** outcomes: success
  feedback and error feedback (e.g. a toast via the project's toast library — Sonner or
  similar, announced through a live region). Mutations use `onSuccess`/`onError`/
  `onSettled` for this. No silent errors: every error is shown to the user or reported.
- At least one global error boundary at the root, in addition to the per-route
  boundaries (`hooks-and-rendering.md`).

## 2. Routing data

### TanStack Router

- Router context carries the `QueryClient`:
  `createRootRouteWithContext<{ queryClient: QueryClient }>()` and
  `createRouter({ routeTree, context: { queryClient } })`.
- Loaders call `context.queryClient.query({ ...options, staleTime: 'static' })`
  (TanStack Query ≥ 5.102; older 5.x: `ensureQueryData(options)`); components use
  `useSuspenseQuery` with the same options.
- `defaultPreload: 'intent'` for preloading on hover/focus. Because Query owns the
  caching, set `defaultPreloadStaleTime: 0` so the router always calls the loader and
  Query decides whether to refetch.
- Loader inputs from search params go through `loaderDeps`, picking only the fields the
  loader needs (`loaderDeps: ({ search }) => ({ page: search.page })`) — never the whole
  search object.
- Auth guard: `beforeLoad` throws `redirect({ to: '/login', search: { redirect:
  location.href } })` — the target is validated on the login page (`security.md`).
- Register the router type once (`declare module '@tanstack/react-router' { interface
  Register { router: typeof router } }`) so links, params and search are type-checked.

### React Router

- **Data mode** (SPA, `createBrowserRouter` + `RouterProvider` from
  `react-router/dom`): `clientLoader`/`loader` functions use the app's `queryClient`
  module instance (or a `createContext<QueryClient>()` value provided via the router's
  `getContext` option) and call `queryClient.query(...)`; components use
  `useSuspenseQuery`/`useQuery` with the same options.
- **Framework mode, SPA** (`ssr: false`): route data comes from `clientLoader`; add a
  `HydrateFallback` to the root.
- **Framework mode, SSR** (React Router framework only): the server `loader` creates a
  new `QueryClient` per request, awaits the queries, and returns
  `{ dehydratedState: dehydrate(queryClient) }`; the route component wraps its content in
  `<HydrationBoundary state={loaderData.dehydratedState}>`. The browser `QueryClient` is
  created once in the root (`useState(() => new QueryClient(...))`) with a `staleTime`
  above 0 so hydrated data isn't refetched immediately.
- Mutations from forms can use route `action`s (validate with Zod inside the action,
  then invalidate Query keys on the client) or `useMutation` — pick one pattern per
  project.
- `action`s, server `loader`s and `middleware` are public HTTP endpoints: they
  authenticate and authorize themselves and validate input; a route guard in the UI is
  not protection (React Router framework only).
- Server-only modules are named `*.server.ts` (or live in a `.server/` folder); the
  React Router Vite plugin fails the build if client code imports them.

## 3. URL state — typed search params

Anything the user expects to survive reload, back/forward and link sharing belongs in
the URL: filters, sort, page, selected tab, search text.

- Define a Zod schema per route for its search params, with defaults and `.catch()` for
  invalid values, so bad URLs never crash the page.

```ts
const orderSearchSchema = z.object({
  page: z.number().int().min(1).default(1).catch(1),
  status: z.enum(['open', 'shipped', 'cancelled']).optional().catch(undefined),
  q: z.string().max(100).optional().catch(undefined),
})
```

- **TanStack Router**: pass the Zod 4 schema directly — `validateSearch:
  orderSearchSchema` (no adapter package needed; `@tanstack/zod-adapter` is only for
  Zod 3). Read with `Route.useSearch({ select: (s) => s.page })`, write with
  `navigate({ search: (prev) => ({ ...prev, page: prev.page + 1 }) })`. TanStack Router
  parses search values as JSON, so numbers arrive as numbers.
- **React Router**: search params are strings — use `z.coerce.number()` for numbers.
  Parse `useSearchParams()` (component) or `new URL(request.url).searchParams` (loader)
  through the schema in one helper per route; components never read raw strings.
- Never parse `window.location.search` by hand in components.
- Debounce text-input-driven URL updates (or use `useDeferredValue`) and use
  `replace` for keystroke-level updates so history isn't flooded.

## 4. Client state — Zustand

Use Zustand only for **client** state shared by components far apart in the tree.
Local state stays in `useState`; server data never goes into a store.

```ts
// features/sidebar/model/sidebar.store.ts
type SidebarState = { isOpen: boolean; toggle: () => void; reset: () => void }

export const useSidebarStore = create<SidebarState>()((set, _get, store) => ({
  isOpen: true,
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  reset: () => set(store.getInitialState(), true),
}))
```

- One store per concern, in the `model` segment of the owning slice. No global
  "app store".
- Actions live in the store; components call actions, not `setState` directly.
- **Always select narrowly**: `useSidebarStore((s) => s.isOpen)`; several fields via
  `useShallow` (from `zustand/react/shallow`). Never `useSidebarStore()` without a
  selector.
- In handlers, read without subscribing: `useSidebarStore.getState()`.
- Every store has a `reset` action (used by logout and tests).
- Form state stays in the form library — not duplicated into Zustand or the Query cache.
  Exception: the **draft** of a long or multi-step form may be persisted in a dedicated
  store (non-sensitive fields only, `partialize`), restored as the form's
  `defaultValues`.

### Persisted state

Only non-sensitive preferences (theme, layout, dismissed hints) — no tokens, no
personal data, no permissions [ASVS 14.3.3].

```ts
export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({ ...initialPreferences, setTheme: (theme) => set({ theme }) }),
    {
      name: 'app-preferences',
      version: 2,
      partialize: (s) => ({ theme: s.theme, density: s.density }), // only data, no actions
      migrate: (persisted, version) => migratePreferences(persisted, version),
      storage: createJSONStorage(() => localStorage),
    },
  ),
)
```

- `version` + `migrate` for every shape change; `migrate` validates the old data with
  Zod and falls back to defaults instead of crashing [client-localstorage-schema].
- `partialize` stores the minimum.
- Storage can throw (private mode, quota) — the app still works with defaults; log the
  failure, don't swallow it silently.
- Logout: `reset()` + `usePreferencesStore.persist.clearStorage()` for stores holding
  user-specific data.
- React Router framework mode: storage doesn't exist on the server — persisted values
  are applied after hydration (or via the pre-paint script for the theme), so render
  the server-safe default first.

## 5. Real-time data

WebSocket / Server-Sent Events updates are written into the Query cache
(`queryClient.setQueryData` or `invalidateQueries`) from one subscription in the app or
feature layer — components keep reading through Query.
