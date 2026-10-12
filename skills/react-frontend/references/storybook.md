# Storybook

Storybook (10.x) is mandatory for every **shared/reusable UI component** — everything in
`shared/ui`, plus entity/feature/widget UI that is used in more than one place. The
story is written together with the component, in the same change.

## 1. Setup

```ts
// .storybook/main.ts — Storybook 10 is ESM-only (no __dirname, no require)
import type { StorybookConfig } from '@storybook/react-vite'

const config: StorybookConfig = {
  framework: '@storybook/react-vite',
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(ts|tsx)'],
  addons: ['@storybook/addon-docs', '@storybook/addon-a11y', '@storybook/addon-vitest'],
}
export default config
```

```ts
// .storybook/preview.tsx
import type { Preview } from '@storybook/react-vite'

const preview: Preview = {
  parameters: {
    a11y: { test: 'error' }, // default is 'todo' — which never fails CI
  },
  initialGlobals: {
    viewport: { value: 'desktop', isRotated: false },
  },
  decorators: [
    (Story) => (
      <AppProviders /* theme, i18n, QueryClient with retry: false */>
        <Story />
      </AppProviders>
    ),
  ],
}
export default preview
```

- Storybook 9/10 moved the essentials into core: import test helpers from
  `storybook/test`, viewports from `storybook/viewport`, actions from
  `storybook/actions` (no `@storybook/test`, `@storybook/addon-viewport`,
  `@storybook/addon-actions` packages).
- The CSF Next format (`defineMain`, `definePreview`, `meta.story()`) is still a preview
  feature — use CSF3 (`Meta`/`StoryObj`) unless the project already uses CSF Next.
- `tsconfig` `moduleResolution` must be `bundler` (or `node16`/`nodenext`).

## 2. Stories cover every state

Each component's story file covers **all states it can be in**:

- default, with realistic content
- **loading** (skeleton/spinner), **empty**, **error**
- **disabled**, read-only, invalid (form controls)
- long/overflowing content (long names, many items, missing optional data)
- interactive states worth checking (open menu, selected tab) via `play` functions
- light/dark theme if the design system has both

```tsx
// shared/ui/order-card/OrderCard.stories.tsx
import type { Meta, StoryObj } from '@storybook/react-vite'
import { expect, fn } from 'storybook/test'
import { OrderCard } from './OrderCard'

const meta = {
  component: OrderCard,
  args: { order: buildOrder(), onCancel: fn() },
} satisfies Meta<typeof OrderCard>
export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
export const Loading: Story = { args: { order: undefined, isLoading: true } }
export const Cancelled: Story = { args: { order: buildOrder({ status: 'cancelled' }) } }
export const LongTitle: Story = { args: { order: buildOrder({ title: 'A'.repeat(120) }) } }

export const CancelFlow: Story = {
  play: async ({ args, canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Cancel order' }))
    await expect(args.onCancel).toHaveBeenCalledOnce()
  },
}
```

- Stories use the same typed data factories as the tests; no ad-hoc JSON.
- `play` functions query by role and name, like component tests (`canvas` and
  `userEvent` come from the play context).
- Components that fetch data get their data via props in stories where possible
  (presentational/container split); otherwise mock the network with MSW (see below).

## 3. Viewports

- **Default viewport: desktop** (set via `initialGlobals` in the preview).
- **Mobile/tablet stories only when the project requires responsive layouts.** Then add
  explicit stories per breakpoint for components whose layout changes:

```tsx
export const Mobile: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
}
```

- Built-in sets: `MINIMAL_VIEWPORTS` (`mobile1`, `mobile2`, `tablet`, `desktop`) and
  `INITIAL_VIEWPORTS` (device names) from `storybook/viewport`; project-specific
  breakpoints go into `parameters.viewport.options`.

## 4. Accessibility checks in stories

- `@storybook/addon-a11y` runs axe on every story. With `parameters.a11y.test: 'error'`
  violations fail the story test run in CI.
- To check against WCAG 2.2 AA rules explicitly, restrict the run:

```ts
parameters: {
  a11y: {
    test: 'error',
    options: { runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] },
  },
}
```

- Disabling a rule for one story needs a comment with the reason; `test: 'todo'` only as
  a temporary state with an issue reference.

## 5. Running stories as tests

`@storybook/addon-vitest` turns every story into a Vitest test (render + `play` + a11y)
running in Vitest browser mode:

```ts
// vitest.config.ts (excerpt) — a separate project next to the unit tests
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import { playwright } from '@vitest/browser-playwright'

const dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  test: {
    projects: [
      { extends: true, test: { name: 'unit', environment: 'jsdom' } },
      {
        extends: true,
        plugins: [storybookTest({ configDir: path.join(dirname, '.storybook') })],
        test: {
          name: 'storybook',
          browser: {
            enabled: true,
            headless: true,
            provider: playwright(),
            instances: [{ browser: 'chromium' }],
          },
        },
      },
    ],
  },
})
```

- The plugin applies the Storybook preview annotations itself; don't call
  `setProjectAnnotations` in a setup file.
- `@storybook/test-runner` is no longer maintained — don't introduce it.

## 6. Visual regression — Storybook + Playwright screenshots

Self-hosted visual regression: Playwright opens each story in isolation and compares a
screenshot.

```ts
// e2e/visual/stories.spec.ts
import { expect, test } from '@playwright/test'
import { storyIds } from './story-index' // read from Storybook's index.json

for (const id of storyIds) {
  test(`visual: ${id}`, async ({ page }) => {
    await page.goto(`/iframe.html?id=${id}&viewMode=story`)
    await page.evaluate(() => document.fonts.ready)
    await expect(page).toHaveScreenshot(`${id}.png`, { fullPage: true })
  })
}
```

- Run against a **static Storybook build** (`storybook build`, served by Playwright's
  `webServer`); `story-index` reads `index.json` and filters entries of `type: 'story'`
  (skip docs pages and stories tagged e.g. `no-visual`).
- **Stable rendering**: fonts self-hosted and awaited (`document.fonts.ready`);
  animations off (Playwright's `animations: 'disabled'` is the default for
  `toHaveScreenshot`; also `reducedMotion: 'reduce'`); caret hidden; fixed time via
  `page.clock` for dates; dynamic content (avatars, maps) masked with `mask`.
- **Stable environment**: screenshots are generated and compared in the **same
  container image** (the official Playwright Docker image) locally and in CI —
  rendering differs between operating systems.
- Tolerance via `maxDiffPixelRatio`/`threshold` in the config, kept small.
- Baselines are committed; updates (`--update-snapshots=changed`) are reviewed like code.
- Viewport: desktop by default; additional mobile screenshots only for projects with
  responsive requirements.

## 7. API mocking in Storybook

For components that need network data, use MSW handlers shared with the tests. The
`msw-storybook-addon` supports Storybook 10 but officially documents MSW 2; with MSW 3
verify compatibility first — or pass data via props and avoid network mocking in
stories altogether.
