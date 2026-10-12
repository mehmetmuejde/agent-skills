# Testing accessibility

Automated checks catch only part of the barriers (missing names, contrast, ARIA misuse) —
keyboard and screen-reader behavior needs tests and manual passes. Run all layers.

## 1. Component tests — Vitest + Testing Library

- Query priority: `getByRole` → `getByLabelText` → `getByText`; `getByTestId` only as
  last resort. If `getByRole` can't find it, the element probably lacks a role or name.
- Test keyboard paths with `user-event`: `user.tab()`, `user.keyboard('{Escape}')`,
  `'{ArrowDown}'`, and assert `toHaveFocus()`.
- Test announcements: `getByRole('status')` / `getByRole('alert')` contain the message.
- Test dialog focus: opens → focus inside; Escape → closed and focus back on trigger.

```tsx
await user.click(screen.getByRole('button', { name: 'Cancel order' }))
const dialog = screen.getByRole('dialog', { name: 'Cancel order?' })
expect(within(dialog).getByRole('button', { name: 'Keep order' })).toHaveFocus()
await user.keyboard('{Escape}')
expect(screen.getByRole('button', { name: 'Cancel order' })).toHaveFocus()
```

## 2. Storybook — addon-a11y

- Every shared component has stories for all states (default, hover/focus via play,
  error, disabled, loading, long content).
- `@storybook/addon-a11y` runs axe on every story; set the test mode to **error** so
  violations fail the Storybook test run in CI (the default only warns/todo).
- Disable a rule per story only with a comment explaining why.
- Desktop viewport by default; mobile viewport stories when the project is responsive.

## 3. E2E — Playwright + axe

```ts
import AxeBuilder from '@axe-core/playwright'

test('checkout page has no detectable a11y violations', async ({ page }) => {
  await page.goto('/checkout')
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(results.violations).toEqual([])
})
```

- Scan every critical page **and** state (dialog open, form with errors, empty state).
- Use role-based locators (`getByRole`) — they double as accessibility checks.
- Add one keyboard-only E2E per critical flow (login, checkout, main form): complete it
  with `page.keyboard` only.

## 4. Lint

- Biome: keep the `a11y` rule group on (recommended set — e.g. `useAltText`,
  `useButtonType`, `useValidAnchor`, `useKeyWithClickEvents`, `useHtmlLang`). Fix
  findings instead of suppressing them; per-line suppressions only with a reason.

## 5. Manual — per feature

- [ ] Keyboard only: complete the flow; Tab order logical; focus always visible and not
      obscured; no traps; Escape works.
- [ ] 200 % zoom and 320 px width: nothing cut off, no horizontal scroll.
- [ ] Reduced motion on: no large movement, nothing essential lost.
- [ ] Forced colors / high contrast: borders, focus and states visible.
- [ ] Critical flows: one pass with VoiceOver or NVDA — names, roles, states, announcements.

## 6. Rendered audit (optional)

When a running page is available: Lighthouse accessibility audit or axe on the rendered
page, then inspect the accessibility tree (names, roles, states, landmarks, headings) in
the browser DevTools. A score of 100 is not WCAG conformance.

Before hand-over, as a regression floor: axe violations = 0 and Lighthouse
accessibility ≥ 90 on the main pages, plus the manual checks above.

## CI

- Component tests + Storybook a11y (error mode) + Playwright axe scans run on every MR.
- Coverage thresholds apply as for all frontend tests (80 % lines and branches).
- New violations block the merge; existing ones are tracked, not silently disabled.
