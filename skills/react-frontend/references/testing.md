# Testing

Tests are written **with** the feature, in the same change — never as a follow-up.

| Level | Tool | Scope |
|---|---|---|
| Unit | Vitest | Pure functions, Zod schemas, store actions, query key factories, hooks |
| Component | Vitest + Testing Library + user-event | One component or feature slice through its UI |
| Stories | Storybook (+ a11y addon, + interaction tests) | Every shared/reusable UI component in all states — `storybook.md` |
| Visual regression | Playwright screenshots of Storybook stories | Shared UI components — `storybook.md` |
| End-to-end | Playwright (+ axe) | Critical user flows against the real app |

## 1. Vitest setup and coverage

```ts
// vite.config.ts (or vitest.config.ts) — Vitest 5
export default defineConfig({
  // …plugins, resolve.alias
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/shared/lib/test/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'], // also report files no test imports
      exclude: [
        'src/**/*.stories.tsx',
        'src/**/*.test.{ts,tsx}',
        'src/shared/lib/test/**',
        'src/routeTree.gen.ts',
        'src/app/main.tsx',
      ],
      reporter: ['text', 'lcov', 'html'],
      thresholds: { lines: 80, branches: 80, functions: 80, statements: 80 },
    },
  },
})
```

```ts
// src/shared/lib/test/setup.ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup()) // RTL auto-cleanup needs a global afterEach otherwise
```

- Vitest 5 notes: `coverage.all` no longer exists — set `coverage.include` so untested
  files count; `clearMocks` is on by default; `vi.mock` must be at module top level;
  `test.projects` inherit the root config.
- `@testing-library/jest-dom` 7 matchers work at runtime with Vitest 5, but its type
  augmentation targets the old `Assertion` signature, so `toBeInTheDocument()` etc. can
  fail type-checking. If the project hits this, add a local declaration file that
  extends Vitest's `Matchers` interface with `TestingLibraryMatchers` from
  `@testing-library/jest-dom/matchers`, and remove it once jest-dom ships a fix.
- Projects split by environment (e.g. `unit` in jsdom, `storybook` in browser mode) go
  into `test.projects`.

- **Coverage thresholds: 80 % lines and 80 % branches**, enforced in CI by the threshold
  config — a run below the threshold fails. Raise thresholds when the project is above
  them; never lower them to make CI pass.
- Excluded from coverage: stories, test utilities, generated files (route tree, API
  types), entry files (`main.tsx`), type-only files. Nothing else is excluded to reach
  the number.
- Coverage is a floor, not the goal: every new branch of business logic gets a test
  that asserts behavior, not just executes it.
- CI runs `vitest run --coverage`; locally `vitest` in watch mode.

## 2. Component tests with Testing Library

- Test what the user sees and does. Query priority: `getByRole` (with `name`) →
  `getByLabelText` → `getByPlaceholderText` → `getByText` → `getByDisplayValue` →
  `getByAltText`/`getByTitle` → `getByTestId` (last resort).
- Interact with `userEvent.setup()` — never `fireEvent` for user interactions.
- Wait for async UI with `findBy…` or `waitFor` — never fixed timeouts.
- Assert outcomes visible to the user (text, role states like `toBeDisabled`,
  `toHaveAttribute('aria-invalid', 'true')`, `toHaveFocus`), not internal state, props
  or hook calls.
- `queryBy…` only to assert absence (`expect(screen.queryByRole('alert')).not.toBeInTheDocument()`).

```tsx
it('cancels an open order', async () => {
  const user = userEvent.setup()
  renderWithProviders(<OrderDetails orderId="1042" />)

  await user.click(await screen.findByRole('button', { name: 'Cancel order' }))
  await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Confirm' }))

  expect(await screen.findByRole('status')).toHaveTextContent('Order cancelled')
})
```

### Test utilities

One `renderWithProviders` in `src/shared/lib/test/` (or `test/`), used by every test:

- A **fresh `QueryClient` per test** with `retry: false` (errors surface immediately)
  and `gcTime: Infinity`.
- The router (TanStack Router `createMemoryHistory` / React Router
  `createMemoryRouter`) when the component uses router hooks.
- Theme/i18n providers the components need.
- Zustand stores are reset between tests (call each store's `reset` action in
  `afterEach`, or a shared reset helper).

### Structure and naming

- `describe` per component, hook or feature; each `it` names the expected behavior from
  the user's point of view — `'shows an error when the email is invalid'`, not
  `'calls validateEmail'` or `'sets isSubmitting to true'`.
- Arrange – Act – Assert, visibly separated; one behavior per test.
- Prefer a few clear, complete tests over many tiny ones that each check one detail.
  Every unit gets at least the happy path, the relevant edge cases and the error case.
- Every test asserts something; no `console.log` left in tests.

### Async and timers

- `findBy…` for elements that appear asynchronously; `waitFor` only with a **concrete
  assertion inside** — never an empty callback.
- Fake timers for debounce/throttle/time-based UI: `vi.useFakeTimers()` in `beforeEach`,
  **`vi.useRealTimers()` in `afterEach`** (otherwise they leak into later tests),
  `vi.setSystemTime(…)` for a fixed "now", `vi.advanceTimersByTime(ms)` to move on.
  With `user-event` and fake timers: `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`.

### Isolation

- Every test runs on its own — no order dependencies, no shared mutable state. Vitest
  isolates test files; inside a file, reset globals and stores in `beforeEach`/`afterEach`.
- Mock global APIs per test (`vi.stubGlobal`, restored afterwards), clean up fake
  timers, clear in-memory stores.

### Hooks

```tsx
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>{children}</QueryClientProvider>
)
const { result } = renderHook(() => useOrderSummary('1042'), { wrapper })
await waitFor(() => expect(result.current.data?.total).toBe(42))
act(() => result.current.toggleDetails())
```

### What to test

- Every feature: happy path, validation errors, server error, empty state, loading state,
  permission-dependent UI (button hidden/disabled).
- Hooks with logic: `renderHook` from `@testing-library/react`.
- Schemas, mappers, store actions, `safeRedirectTarget`-style security helpers: plain
  unit tests with edge cases.
- Bugs: first a failing test that reproduces it, then the fix.

### What not to do

- No tests of implementation details (state values, private functions, class names,
  number of renders).
- No mocking of the component under test's own modules to make it "unit" — mock at the
  network boundary instead. The more mocks, the further the test is from reality.
- Don't test React or libraries themselves (that Zod validates, that TanStack Query
  caches) — test your schema rules and your behavior.
- No snapshot tests of whole component trees (see section 5).

## 3. API mocking

Mock at the **network boundary** so the real API client, Zod parsing and Query logic
run in tests.

Use **MSW** (`msw` 3.x) when the app talks to an HTTP API:

```ts
// src/shared/lib/test/msw.ts
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

export const server = setupServer(
  http.get('/api/orders/:id', ({ params }) =>
    HttpResponse.json(buildOrder({ id: String(params.id) })),
  ),
)

// setup.ts
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

```ts
// in a test: override for one case
server.use(http.get('/api/orders/:id', () => new HttpResponse(null, { status: 500 })))
```

- MSW 3 renamed `onUnhandledRequest` to `onUnhandledFrame`, moved GraphQL to
  `msw/graphql`, and no longer patches timers (advance fake timers yourself). Cookies
  are read from the resolver's `cookies` argument, not `request.headers`.
- For the browser (local development without backend, Storybook) MSW 3 ships a Vite
  plugin (`msw/vite`); enable it only behind `import.meta.env.DEV`. Mock code never
  reaches the production bundle.

- Default handlers describe the happy path; individual tests override with
  `server.use(...)` for errors, empty data, slow responses.
- Unhandled requests fail the test (`onUnhandledFrame: 'error'`; `onUnhandledRequest`
  on MSW 2) — no silent passes.
- Mock data is built with typed factories (`buildOrder({ status: 'open' })`) that
  satisfy the Zod schemas — no hand-written partial JSON scattered across tests.
- The same handlers can serve Storybook stories and local development without a backend.

### Module mocks — `vi.mock` / `vi.fn`

For dependencies that are not HTTP (date libraries, browser APIs, analytics, a heavy
third-party widget):

```ts
const track = vi.fn()
vi.mock('@/shared/lib/analytics', () => ({ track }))          // hoisted to the top

const { mockNow } = vi.hoisted(() => ({ mockNow: vi.fn() }))   // values used inside vi.mock
vi.mock('date-fns', async (importOriginal) => ({
  ...(await importOriginal<typeof import('date-fns')>()),       // keep the rest real
  format: vi.fn(() => '2025-01-01'),
}))
```

- `vi.mock` is hoisted above the imports — variables from the test scope are not
  available inside its factory; use `vi.hoisted()`.
- Cleanup: `vi.clearAllMocks()` (call history — Vitest 5 does this between tests via
  `clearMocks`),
  `vi.resetAllMocks()` (also implementations), `vi.restoreAllMocks()` (spies back to the
  originals).
- Rule of thumb: MSW for anything that talks HTTP, `vi.mock` only for non-HTTP modules.

## 4. End-to-end tests with Playwright

E2E tests are a hard requirement for **critical user flows**: login/logout, the core
business flows, checkout/payment, permission boundaries (a user without the role can't
reach the page), and anything whose failure stops users from working.

### Rules

- **Role-based locators**: `page.getByRole('button', { name: 'Save' })`,
  `getByLabel`, `getByText`. CSS/XPath selectors only as a last resort; `getByTestId`
  for elements without an accessible role.
- **No fixed waits** (`waitForTimeout`). Rely on auto-waiting locators and web-first
  assertions (`await expect(locator).toBeVisible()`, `toHaveURL`, `toHaveText`).
- **Isolated tests**: each test creates its own data (via API calls in fixtures) and
  doesn't depend on another test's leftovers or order.
- **Page objects or fixtures** encapsulate repeated flows and locators; tests read as
  user stories.
- **Auth state reuse**: log in once in a setup project, save `storageState`, reuse it in
  all tests. One stored state per role. The auth file is git-ignored.
- Run against a production build (`vite build && vite preview`, or the React Router
  server build), not the dev server, in CI.
- Traces/screenshots/videos on failure (`trace: 'on-first-retry'`), retries only in CI.
- Every critical page gets an **axe scan** with WCAG A/AA tags.

```ts
// playwright.config.ts
export default defineConfig({
  testDir: './e2e',
  retries: process.env.CI ? 2 : 0,
  use: { baseURL: 'http://localhost:4173', trace: 'on-first-retry' },
  webServer: {
    command: 'npm run build && npm run preview -- --port 4173',
    url: 'http://localhost:4173',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
})
```

```ts
// e2e/auth.setup.ts
setup('authenticate', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill(process.env.E2E_USER_EMAIL ?? '')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await page.context().storageState({ path: 'playwright/.auth/user.json' })
})
```

```ts
// e2e/fixtures.ts — page objects as fixtures + accessibility scan
import AxeBuilder from '@axe-core/playwright'
import { test as base, expect } from '@playwright/test'

export const test = base.extend<{ ordersPage: OrdersPage; checkA11y: () => Promise<void> }>({
  ordersPage: async ({ page }, use) => { await use(new OrdersPage(page)) },
  checkA11y: async ({ page }, use) => {
    await use(async () => {
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze()
      expect(results.violations).toEqual([])
    })
  },
})
```

```ts
// e2e/cancel-order.spec.ts
test('user cancels an open order', async ({ ordersPage, checkA11y, page }) => {
  await ordersPage.open('1042')
  await checkA11y()
  await ordersPage.cancel()
  await expect(page.getByRole('status')).toHaveText('Order cancelled')
})
```

- Credentials for test users come from environment variables / CI secrets, never from
  the repo. `playwright/.auth/` is git-ignored.
- Accessibility-related browser settings can be tested per project or test
  (`reducedMotion`, `forcedColors`, `colorScheme` options).
- Desktop Chrome is the default project; add Firefox/WebKit and mobile device projects
  only when the project's browser support matrix requires them.

## 5. Snapshot tests — only sparingly

- No snapshots of rendered component trees — they break on every markup change and get
  updated blindly.
- Allowed, targeted: small serialized outputs that must not change unnoticed
  (generated query keys, a mapper's output, an error message catalogue), preferably as
  inline snapshots.
- Visual appearance is covered by visual regression screenshots (`storybook.md`), not
  DOM snapshots.

## 6. CI

- Pipeline: `biome ci` → `tsc --noEmit` (type check) → `steiger ./src` →
  `vitest run --coverage` → Storybook tests (a11y + interactions) → build →
  Playwright E2E (+ visual regression).
- All steps are blocking. A flaky test is fixed or quarantined with an issue — not
  retried until green.
- Tests in CI always run once (`vitest run`), never in watch mode.

## 7. Anti-patterns

- `getByTestId` as the default query; asserting CSS classes or DOM structure.
- `fireEvent` instead of `user-event`; `waitFor` with an empty body; fixed timeouts.
- Testing implementation details (internal state, private functions, render counts).
- Excessive mocking; mocking the unit's own modules.
- Snapshots of dynamic, data-driven components.
- Tests that depend on each other or on execution order.
- Fake timers that are never restored; tests without assertions; `console.log` in tests.
