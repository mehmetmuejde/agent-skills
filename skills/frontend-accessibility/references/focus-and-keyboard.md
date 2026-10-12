# Focus and keyboard

## Focus rings [2.4.7, 1.4.11]

`:focus-visible` shows for keyboard and assistive-tech focus, not for mouse clicks on
buttons. Preference order:

```css
/* Best: keep the browser ring (adapts to platform and forced colors) */
:focus-visible { outline-offset: 2px; }

/* Custom ring only with a verified design token */
:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
```

- A custom ring must reach 3:1 against **every** color it crosses (fills, surfaces,
  images, hover/selected states) — `currentColor` passes only when that check does.
- Forced colors (Windows High Contrast): keep default adjustment or use system colors
  (`Highlight`); `forced-color-adjust: none` only after checking.
- `:focus-within` for compound controls (search field with icon inside the border).
- Never `outline: none` / `outline-none` without a replacement.

## Focus not obscured [2.4.11]

```css
html { scroll-padding-top: 64px; }   /* height of the sticky header */
/* sticky footer / cookie banner → scroll-padding-bottom */
```

In-page anchor targets get `scroll-margin-top`.

## Skip link [2.4.1]

First focusable element when navigation precedes the content:

```tsx
<a className="skip-link" href="#main">Skip to main content</a>
…
<main id="main" tabIndex={-1}>…</main>
```

```css
.skip-link { position: absolute; inset-inline-start: -999px; }
.skip-link:focus { inset-inline-start: 1rem; inset-block-start: 1rem; }
```

## tabindex

- `0` — adds a custom interactive element to the tab order.
- `-1` — focusable only programmatically: headings you move focus to, dialog containers,
  roving-tabindex members.
- Positive values — never; fix the DOM order instead [2.4.3].

**Roving tabindex** for composite widgets (tabs, toolbar, radio group, menu): one tab stop;
active item `tabIndex={0}`, others `-1`; arrow keys move focus and the `0`.
A combobox keeps DOM focus in the input and points `aria-activedescendant` at the
highlighted option.

## Dialogs — trap and restore

```tsx
dialogRef.current?.showModal()  // on open: background inert, Escape closes
dialogRef.current?.close()      // on close
triggerRef.current?.focus()     // return focus to the opener
```

- Custom overlay (no `<dialog>`): `role="dialog"`, `aria-modal="true"`,
  `aria-labelledby` → heading; set `inert` on the app content behind it.
- On open, focus the first focusable element — for destructive confirmations the
  **least destructive** action.
- On close, return focus to the trigger, or a logical container if the trigger is gone.
- Opening must not scroll the page unexpectedly; `overscroll-behavior: contain` on
  modal/drawer scroll areas.

## SPA route changes

Client-side navigation resets nothing and announces nothing. On every navigation:

1. Update `document.title` [2.4.2] (route `head`/`meta` of TanStack Router or React
   Router).
2. Move focus to the new view's `<h1 tabIndex={-1}>` or `<main>`.
3. Scroll to top on new navigation; restore scroll on back/forward.
4. Search-param-only updates (filter, sort, pagination) don't move focus — announce the
   result count in a `role="status"` region instead.

```tsx
export function PageHeading({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null)
  const { pathname } = useLocation() // the project's router hook
  useEffect(() => { ref.current?.focus() }, [pathname])
  return <h1 ref={ref} tabIndex={-1}>{children}</h1>
}
```

## After actions

- Item deleted → focus the next item or the list heading.
- Inline edit saved → focus back to the edit trigger.
- Form error → focus the first invalid field (`forms.md`).

## Keyboard patterns (WAI-ARIA APG)

| Widget | Keys |
|---|---|
| Dialog | Tab/Shift+Tab cycle inside; Escape closes |
| Tabs | Arrows move (wrap); Home/End first/last; Tab leaves to panel |
| Menu button | Enter/Space/ArrowDown open + first item; ArrowUp open + last; Escape closes, refocuses button |
| Disclosure/accordion | header `<button aria-expanded>`; Enter/Space toggle |
| Combobox | ArrowDown opens/moves; Enter accepts; Escape closes; typing filters |
| Listbox/radio group | arrows move selection; one tab stop |

- Escape dismisses the topmost layer: tooltip → menu → dialog.
- Tabs: automatic activation when panels render instantly, manual (Enter/Space) when
  switching is expensive.
- Single-key shortcuts can be turned off or remapped, or only work on focus [2.1.4].
- `autoFocus` sparingly — one primary input on desktop, avoid on mobile.
