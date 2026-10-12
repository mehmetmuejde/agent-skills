# Hooks and rendering

Rules for components, state, effects and rendering. No React Compiler is used, so
manual memoization rules apply — but **measure first** (React DevTools Profiler) before
adding `memo`/`useMemo`/`useCallback` for performance. Vercel rule ids in brackets.

## Components

### Never define components inside components [rerender-no-inline-components]

A component defined in another component's body is a new type on every render: React
unmounts and remounts it, state and DOM are lost (inputs lose focus, animations restart,
effects re-run).

❌
```tsx
function UserProfile({ user }: Props) {
  const Avatar = () => <img src={user.avatarUrl} alt="" />
  return <Avatar />
}
```
✅
```tsx
function Avatar({ src }: { src: string }) {
  return <img src={src} alt="" />
}
function UserProfile({ user }: Props) {
  return <Avatar src={user.avatarUrl} />
}
```

Render helpers that return JSX (`renderRow(item)`) are fine — they are called, not
mounted. Biome's `noNestedComponentDefinitions` catches this; enable it (it is not in
the recommended set).

### Render is pure

- No side effects during render: no requests, no subscriptions, no writes to refs that
  other code reads, no `Math.random()`/`Date.now()` that must stay stable (put them in
  state initializers or event handlers).
- Never mutate props or state. Use `toSorted()`, `toReversed()`, `toSpliced()`, `with()`
  and spread instead of `sort()`, `reverse()`, `splice()`, index assignment
  [js-tosorted-immutable]. Requires `lib: ["ES2023", …]` in `tsconfig.json` and a browser
  target that ships these APIs (Vite transpiles syntax, it does not polyfill APIs).

❌ `const sorted = users.sort(byName)` — mutates the prop.
✅ `const sorted = users.toSorted(byName)`

### Keys

Stable ids from the data. Index keys only for static lists that never reorder, filter or
insert. A changing `key` is also the tool to **reset** a subtree's state on purpose.

### Conditional rendering with numbers [rendering-conditional-render]

`&&` renders `0` and `NaN`. Use a ternary or a real boolean when the left side can be a
number.

❌ `{count && <Badge count={count} />}` → renders "0"
✅ `{count > 0 ? <Badge count={count} /> : null}`

## State

### Derive, don't sync [rerender-derived-state-no-effect]

If a value can be computed from props/state, compute it during render. No extra state,
no effect that copies it.

❌
```tsx
const [fullName, setFullName] = useState('')
useEffect(() => setFullName(`${first} ${last}`), [first, last])
```
✅
```tsx
const fullName = `${first} ${last}`
```

- Expensive derivation: `useMemo` (after measuring), not state + effect.
- Reset state when an id changes: pass `key={id}` to the component instead of an
  effect that calls `setState` on prop change.
- Server data is never copied into `useState` — read it from TanStack Query
  (`data-and-state.md`).

### Functional updates [rerender-functional-setstate]

When the next state depends on the previous one, use the updater form. Prevents stale
closures and keeps callbacks stable.

❌ `setItems([...items, item])` inside a `useCallback` with `[]` deps → stale `items`
✅ `setItems((prev) => [...prev, item])`

Plain values (`setOpen(false)`, `setName(value)`) need no updater.

### Lazy initial state [rerender-lazy-state-init]

Pass a function when the initial value is expensive (parsing, building an index,
reading storage). Otherwise it runs on every render.

❌ `useState(buildSearchIndex(items))`
✅ `useState(() => buildSearchIndex(items))`

### Refs for transient values [rerender-use-ref-transient-values]

Values that change often but don't drive the UI (pointer position, timer ids, "is
dragging" flags read in handlers) go into `useRef`. Updating a ref does not re-render.
Don't read refs during render to decide what to show.

## Effects

Effects synchronize with **external systems** (DOM APIs, subscriptions, timers,
non-React widgets). They are not for data flow inside React.

### Interaction logic belongs in event handlers [rerender-move-effect-to-event]

❌
```tsx
const [submitted, setSubmitted] = useState(false)
useEffect(() => {
  if (submitted) { void register(); toast('Registered') }
}, [submitted])
```
✅
```tsx
async function handleSubmit() {
  await register()
  toast('Registered')
}
```

Rule of thumb: "this runs **because the user did X**" → event handler. "This runs
**because the component is visible**" → effect.

### Narrow dependencies [rerender-dependencies]

- Depend on primitives, not whole objects: `[user.id]`, not `[user]`.
- Depend on a derived boolean when only the threshold matters:
  `const isMobile = width < 768` → `[isMobile]`.
- Never silence the exhaustive-deps lint rule (Biome `useExhaustiveDependencies`);
  restructure instead (move logic into the effect, into a handler, or use an Effect
  Event).

### One concern per effect [rerender-split-combined-hooks]

Unrelated side effects with different dependencies go into separate effects; the same
applies to `useMemo` computations with independent inputs.

✅
```tsx
useEffect(() => { trackPageView(pathname) }, [pathname])
useEffect(() => { document.title = `${title} | App` }, [title])
```

### Always clean up

Every subscription, listener, timer, observer and `AbortController` created in an
effect is released in its cleanup. Effects run twice in development (Strict Mode) — that
must be harmless.

### Effect Events — `useEffectEvent` [advanced-use-latest, advanced-event-handler-refs, advanced-effect-event-deps]

Stable in React ≥ 19.2 (check the project's `react` version). Use it to read the latest
props/state inside an effect **without** making the effect re-run.

```tsx
import { useEffect, useEffectEvent } from 'react'

function ChatRoom({ roomId, onConnected }: Props) {
  const handleConnected = useEffectEvent(onConnected)

  useEffect(() => {
    const connection = createConnection(roomId)
    connection.on('connected', handleConnected)
    connection.connect()
    return () => connection.disconnect()
  }, [roomId]) // never list handleConnected
}
```

- Never put the Effect Event into a dependency array; its identity changes every render.
- Call it only from effects (or subscriptions they create), never during render and
  never pass it to child components.
- On React < 19.2: store the latest callback in a ref updated in an effect, and read
  `ref.current` inside the subscription.

### App-wide initialization runs once [advanced-init-once]

Init that must run once per page load (error tracking setup, i18n init, reading a
runtime config) belongs in `src/app/` — module scope of the entry or before
`createRoot(...).render()` — **not** in `useEffect(() => …, [])` of a component, which
runs twice in development and again on remount.

### No async data fetching in effects

Server data is loaded via TanStack Query or a route loader (`data-and-state.md`).
`useEffect` + `fetch` + `useState` duplicates requests, races, and has no cache. The
only remaining effect-based I/O is non-HTTP (WebSocket, `EventSource`) — and even
those feed the Query cache via `queryClient.setQueryData`.

## Subscriptions — subscribe as narrowly as possible

### Subscribe to derived values [rerender-derived-state]

Subscribe to the boolean you need, not to a continuous value.

❌ `const width = useWindowWidth(); const isMobile = width < 768` — re-renders on every
pixel.
✅ `const isMobile = useMediaQuery('(max-width: 767px)')` — re-renders only when the
boolean flips.

Implement such hooks with `useSyncExternalStore`, which also handles SSR via its
`getServerSnapshot` argument:

```tsx
import { useSyncExternalStore } from 'react'

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query)
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
    () => false, // server snapshot (React Router framework mode)
  )
}
```

### Don't subscribe to what you only read in a handler [rerender-defer-reads]

If a value is only needed inside a callback, read it there instead of subscribing:

- Zustand: `useCartStore.getState().items` inside the handler.
- TanStack Query: `queryClient.getQueryData(key)` inside the handler.
- Router search params: subscribe with a selector (`Route.useSearch({ select })`) to
  the one field the UI shows. Never parse `window.location.search` by hand — it bypasses
  the typed search-param schema.

### Global listeners: share and make passive [client-event-listeners, client-passive-event-listeners]

- Many components needing the same global event (keydown, resize, online/offline):
  one subscription in a small external store read via `useSyncExternalStore` or a
  Zustand store fed by a single listener registered in `src/app/`.
- `touchstart`, `touchmove`, `wheel` listeners that never call `preventDefault()` get
  `{ passive: true }`.

## Memoization (no React Compiler)

Default: no `memo`/`useMemo`/`useCallback`. Add them when the Profiler shows a real
cost, or when referential stability is required (a dependency of an effect, a prop of a
memoized child, a context value).

When you memoize, do it correctly:

- **Memoized child for early returns** [rerender-memo]: move expensive work into a
  `memo` child so a parent's early return (`if (loading) return <Skeleton />`) skips it.
- **Stable non-primitive defaults** [rerender-memo-with-default-value]: a default prop
  `onClick = () => {}` or `items = []` on a `memo` component breaks memoization. Hoist
  it: `const NOOP = () => {}` at module scope.
- **No `useMemo` for cheap primitive expressions** [rerender-simple-expression-in-memo]:
  `const isLoading = a.isLoading || b.isLoading` — plain.
- **Split independent computations** [rerender-split-combined-hooks].
- **Context values** that are objects are memoized (`useMemo`) or split into separate
  contexts; otherwise every consumer re-renders on every provider render.
- **No custom `memo` comparators** that ignore props (e.g. comparing only `item.id`) —
  they create stale callbacks. Fix the unstable prop instead.
- **Static JSX and constants** [rendering-hoist-jsx]: large static elements (SVG
  illustrations), regexes [js-hoist-regexp], and constant objects/arrays go to module
  scope. A `RegExp` with the `g` flag keeps `lastIndex` state — don't share it.

## Concurrent rendering

### `useTransition` — non-urgent client updates [rerender-transitions, rendering-usetransition-loading]

Wrap state updates that trigger expensive re-renders (switching a large tab, applying
a filter to a big client-side table) in `startTransition`; use `isPending` for feedback.

- For **server data**, loading state comes from TanStack Query (`isPending`,
  `isFetching`, `placeholderData`), not from a transition around `fetch` +
  `setState`.
- Transitions do not cancel in-flight requests; out-of-order responses are possible.
  Query keys (one cache entry per input) solve that.
- Not for high-frequency values like scroll position — use a ref or
  `requestAnimationFrame`.

### `useDeferredValue` — keep input responsive [rerender-use-deferred-value]

```tsx
const [query, setQuery] = useState('')
const deferredQuery = useDeferredValue(query)
const results = useMemo(() => filterItems(items, deferredQuery), [items, deferredQuery])
const isStale = query !== deferredQuery
```

The expensive computation must be memoized on the **deferred** value, otherwise it still
runs on every keystroke. Show staleness (`aria-busy`, reduced opacity) while
`isStale`.

### `<Activity>` — keep hidden UI alive [rendering-activity]

Stable in React ≥ 19.2. `<Activity mode={visible ? 'visible' : 'hidden'}>` keeps the
state and DOM of a hidden subtree (tabs, side panels with expensive content) instead of
unmounting it.

- Hidden content is hidden from assistive technology and cannot be focused; effects
  are cleaned up while hidden and re-run when shown — effects must handle that.
- Use it for UI that is toggled often and is expensive to rebuild; not for everything
  that can be hidden.

## Long lists [rendering-content-visibility]

Pick by size and measured cost:

1. **Up to a few hundred simple rows**: render normally.
2. **Long, variable content that should stay in the DOM** (chat, feed, searchable with
   Ctrl+F): CSS `content-visibility: auto` with `contain-intrinsic-size` on each item —
   the browser skips layout/paint off-screen.

```css
.message-item {
  content-visibility: auto;
  contain-intrinsic-size: auto 80px;
}
```

3. **Thousands of rows / large tables**: virtualize with `@tanstack/react-virtual`.

```tsx
const parentRef = useRef<HTMLDivElement>(null)
const virtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 48,
  overscan: 8,
})
// render virtualizer.getVirtualItems() inside a container of virtualizer.getTotalSize();
// rows with variable height: <div key={item.key} data-index={item.index} ref={virtualizer.measureElement}>
```

Virtualized lists remove off-screen rows from the DOM: keep the scroll container
keyboard-focusable, expose the total count (`aria-rowcount`/`aria-setsize` +
`aria-posinset`), and don't virtualize lists that users search with the browser.

## Server rendering and hydration — React Router framework only

- No browser APIs during render (`window`, `document`, `localStorage`,
  `matchMedia`): read them in effects, event handlers, `clientLoader`, or via
  `useSyncExternalStore` with a server snapshot.
- Render output must match between server and client. Values that legitimately differ
  (current time, locale-formatted dates) are rendered client-only or wrapped with
  `suppressHydrationWarning` on that single element
  [rendering-hydration-suppress-warning] — never to hide real bugs.
- **Theme without flash** [rendering-hydration-no-flicker]: a small inline script in
  the document `<head>` sets the theme class from storage before paint. In the SPA, put
  it directly into `index.html`. It must be allowed by the CSP (hash or nonce) — see
  `security.md`. No `dangerouslySetInnerHTML` with dynamic content for this.
- Module-level variables in code that runs on the server are shared across requests —
  never store request or user data there [server-no-shared-module-state].

## Error handling in components

- Every route has an error boundary (TanStack Router `errorComponent`, React Router
  `ErrorBoundary` export); large independent widgets get their own boundary.
- Errors are never swallowed: no empty `catch {}`, no `.catch(() => {})`. Either handle
  them visibly (message, retry) or rethrow / report them.
