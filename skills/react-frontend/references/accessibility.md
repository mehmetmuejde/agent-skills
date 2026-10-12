# Accessibility

Accessibility is built in with every component and page — never added later. Target:
**WCAG 2.2 level AA**. WCAG success criteria in brackets.

A feature is not done until it works with keyboard only, has correct names and roles,
passes the automated checks (Storybook a11y addon, axe in Playwright) and has
role-based tests.

This file is the React-specific implementation. The complete rule set (semantics, ARIA,
forms, screen readers, contrast, motion, WCAG table) and the audit procedure live in the
`frontend-accessibility` skill.

## 1. Semantic HTML first

Use the native element before reaching for ARIA. Native elements bring role, name,
keyboard behavior and focusability for free.

| Need | Use | Not |
|---|---|---|
| Action | `<button type="button">` | `<div onClick>` |
| Navigation | `<a href>` / router `<Link>` | `<button onClick={navigate}>` |
| Form field label | `<label htmlFor>` (or wrapping `<label>`) | placeholder as label |
| Group of fields | `<fieldset>` + `<legend>` | `<div>` with bold text |
| Page regions | `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>` | anonymous `<div>`s |
| Lists, tables | `<ul>/<ol>`, `<table>` with `<th scope>` and `<caption>` | div grids for tabular data |
| Modal | `<dialog>` with `showModal()` or a tested headless library | hand-rolled overlay `<div>` |

- One `<h1>` per page; heading levels don't skip [1.3.1].
- `<html lang="…">` is set and updated when the UI language changes [3.1.1].
- ARIA only when no native element fits; then follow the WAI-ARIA Authoring Practices
  pattern for that widget (tabs, combobox, menu, tree) completely — role, states,
  keyboard. Bad ARIA is worse than none.
- Complex widgets (combobox, date picker, menu, dialog) come from a tested headless
  library already used by the project (e.g. React Aria, Radix) rather than being
  hand-built.

❌
```tsx
<div className="btn" onClick={save}>Save</div>
```
✅
```tsx
<button type="button" onClick={save}>Save</button>
```

## 2. Keyboard

- Everything that works with a pointer works with the keyboard [2.1.1]; no keyboard
  traps [2.1.2].
- Tab order follows the visual order; never use a positive `tabIndex`. `tabIndex={-1}`
  only for programmatic focus targets (headings, containers).
- Custom widgets implement the expected keys (arrow keys in tabs/menus/listboxes,
  `Escape` closes overlays, `Enter`/`Space` activate).
- A "Skip to main content" link is the first focusable element [2.4.1].
- Drag-and-drop has a non-dragging alternative (buttons, menu) [2.5.7].

## 3. Visible focus

- Every focusable element has a clearly visible focus indicator [2.4.7] with at least
  3:1 contrast against its surroundings [1.4.11]. Style `:focus-visible`; never
  `outline: none` without a replacement.
- Focused elements are not hidden behind sticky headers, cookie banners or toasts
  [2.4.11] — use `scroll-padding-top` for sticky headers.

## 4. Focus management

### Route changes (SPA and React Router framework mode)

Client-side navigation does not reset focus or announce anything. On every route
change:

1. Update `document.title` to a unique, descriptive page title [2.4.2] (TanStack Router
   `head`/route meta, React Router `meta` export or `<title>` rendered in the route).
2. Move focus to the page's `<h1>` (with `tabIndex={-1}`) or to `<main>`, so screen
   readers announce the new page and keyboard users start at the content.
3. Don't steal focus on search-param-only updates (filters, sorting, pagination) —
   announce the result count in a live region instead.

```tsx
// Page heading that receives focus after navigation
export function PageHeading({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null)
  const pathname = useLocation().pathname // router hook of the project
  useEffect(() => { ref.current?.focus() }, [pathname])
  return <h1 ref={ref} tabIndex={-1}>{children}</h1>
}
```

### Dialogs, drawers, popovers

- Opening moves focus into the dialog (first field or the dialog heading); focus is
  trapped inside a modal; the rest of the page is inert.
- `Escape` closes; closing returns focus to the element that opened it.
- The dialog has an accessible name (`aria-labelledby` pointing to its heading).
- Native `<dialog>` + `showModal()` provides the trap, inertness and `Escape`; a headless
  library provides the same. Don't build this by hand.

### After actions

- After deleting an item, move focus to a sensible neighbor (next item, list heading).
- After submitting a form with errors, move focus to the first invalid field or an error
  summary (`forms.md`).

## 5. Names, labels, text alternatives

- Every form control has a visible label linked to it [1.3.1, 3.3.2, 4.1.2]. Placeholder
  text is not a label.
- Icon-only buttons have an accessible name: `aria-label="Delete order 1042"` (specific,
  not just "Delete"). The icon itself is `aria-hidden="true"`.
- Images: meaningful → `alt` describes the content/purpose; decorative → `alt=""`
  [1.1.1].
- Links describe their target ("Order 1042 details", not "click here") [2.4.4].
- Fields that collect personal data use the matching `autoComplete` token
  (`email`, `given-name`, `current-password`, `one-time-code`) [1.3.5].
- Login/OTP fields allow paste and password managers [3.3.8]; don't re-ask for data
  the user already entered in the same flow [3.3.7].

## 6. Color, contrast, sizing

- Text contrast ≥ 4.5:1, large text (≥ 24px or ≥ 18.66px bold) ≥ 3:1 [1.4.3]; UI
  component boundaries, icons and focus indicators ≥ 3:1 [1.4.11]. Enforce via design
  tokens, not per component.
- Color is never the only carrier of meaning (errors, status, chart series) — add text,
  icons or patterns [1.4.1].
- Pointer targets at least 24×24 CSS px or enough spacing [2.5.8].
- Layout works at 320 CSS px width without horizontal scrolling [1.4.10] and at 200 %
  zoom [1.4.4]; use `rem` for font sizes; don't break with increased text spacing
  [1.4.12].
- Supports light/dark and Windows High Contrast (`forced-colors`) without losing
  borders or focus indicators.

## 7. Motion

- Respect `prefers-reduced-motion`: disable or reduce non-essential animations,
  parallax, auto-scrolling.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- Anything that moves, blinks or auto-updates for more than 5 seconds can be paused,
  stopped or hidden [2.2.2]. Nothing flashes more than 3 times per second [2.3.1].

## 8. Async status — live regions

Screen-reader users must learn about results that appear without a page load [4.1.3].

- Status messages ("Saved", "12 results", "Loading…") → `role="status"` (polite).
- Errors that need immediate attention → `role="alert"` (assertive). Use sparingly.
- The live region element must **exist in the DOM before** its content changes;
  rendering it together with the message is often not announced.
- Toast libraries must announce via a live region — verify it with a screen reader once.
- Containers that are refreshing get `aria-busy="true"`; skeletons are
  `aria-hidden="true"` with one visually hidden "Loading …" status text.

```tsx
<p role="status" className="sr-only">
  {isFetching ? 'Loading results…' : `${total} results`}
</p>
```

## 9. Testing accessibility

Automated checks find only part of the issues — they complement, not replace, keyboard
and screen-reader checks.

- **Component tests query by role and name** (Testing Library priority:
  `getByRole` → `getByLabelText` → `getByText`; `getByTestId` only as last resort). A
  test that can't find an element by role usually means the element lacks one.

```tsx
await user.click(screen.getByRole('button', { name: 'Cancel order' }))
expect(screen.getByRole('alert')).toHaveTextContent('Order could not be cancelled')
```

- **Keyboard paths in tests**: `user.tab()`, `user.keyboard('{Escape}')`, assert
  `toHaveFocus()` for dialogs and route changes.
- **Storybook**: `@storybook/addon-a11y` runs axe on every story; violations fail the
  story test run (configuration in `storybook.md`).
- **Playwright**: `@axe-core/playwright` scan on every critical page/state with WCAG
  2.x A/AA tags (configuration in `testing.md`).
- **Biome**: keep the `a11y` rule group enabled (it is part of the recommended set) —
  e.g. `useAltText`, `useButtonType`, `useValidAnchor`, `useKeyWithClickEvents`,
  `useHtmlLang`. Fix findings instead of suppressing them; a per-line suppression needs a
  reason in the comment.
- **Manual, per feature**: complete the flow keyboard-only; check focus visibility,
  focus order and 200 % zoom. For critical flows: one pass with a screen reader
  (VoiceOver or NVDA).

### Before hand-over

- axe (Storybook addon, Playwright, or axe DevTools on the running page): 0 violations.
- Lighthouse accessibility score ≥ 90 on the main pages — a floor that catches
  regressions, not proof of WCAG conformance.
- Keyboard-only pass through every changed flow; screen-reader spot check (VoiceOver on
  macOS, NVDA on Windows).
