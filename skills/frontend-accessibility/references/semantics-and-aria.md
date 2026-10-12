# Semantics and ARIA

## The rules of ARIA

1. If a native element with the needed semantics and behavior exists, use it.
2. Don't change native semantics unless you really have to.
3. Every interactive ARIA control must be fully keyboard-operable — a role is a promise
   of the complete key model, states and behavior.
4. Every interactive element has an accessible name.

No ARIA is better than bad ARIA — screen readers trust the roles.

## Button vs link vs div

| Element | For | Gets for free |
|---|---|---|
| `<a href>` / router `<Link>` | Navigation, anything that changes the URL | Cmd/Ctrl/middle-click, copy link, Enter |
| `<button type="button">` | Actions: submit, toggle, open, delete | focus, Enter **and** Space, form semantics |
| `<div onClick>` | nothing | no role, no focus, no keyboard |

A "button" that navigates is a styled link; a "link" that performs an action is a
styled button. The full polyfill for a non-native button is `role="button"` +
`tabIndex={0}` + Enter/Space handlers — which is why the native element is always less
code.

## Element choice

| Need | Use | Not |
|---|---|---|
| Group of fields | `<fieldset>` + `<legend>` | `<div>` with bold text |
| Tabular data | `<table>`, `<caption>`, `<th scope>` | div grid |
| Lists | `<ul>`/`<ol>` + `<li>` | stacked divs |
| Modal | `<dialog>` + `showModal()` or the project's headless dialog | overlay `<div>` |
| Disclosure | `<details>`/`<summary>` or `<button aria-expanded aria-controls>` | clickable heading |
| Complex widgets (combobox, menu, date picker, tree) | the project's accessible headless library (e.g. React Aria, Radix) | hand-built |

## Landmarks, headings, title

- `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>` — exactly one visible `<main>`.
- Several landmarks of one type get labels: `<nav aria-label="Hauptnavigation">`,
  `<nav aria-label="Breadcrumb">`.
- Headings are structure, not styling: pick the level by outline, style with CSS. One
  `<h1>` per view, no skipped levels (convention, recommended).
- `<title>` per view, most specific first: `Rechnungen · Einstellungen · Produkt`
  [2.4.2].
- `<html lang>` matches the UI language; parts in another language get `lang` [3.1.1,
  3.1.2]. Brand names and code tokens: `translate="no"`.

## Accessible names

Precedence: `aria-labelledby` > `aria-label` > native label (`<label>`, text content,
`alt`) > `title`.

- Prefer visible text or `aria-labelledby`; `aria-label` is invisible, drifts out of sync
  and translation tools handle it inconsistently.
- Icon-only buttons: `aria-label`, icon `aria-hidden="true"`. Specific names in lists:
  "Delete order 1042", not five times "Delete".
- **Label in name** [2.5.3]: visible "Send" with `aria-label="Submit message"`
  breaks voice control ("click Send"). Start the name with the visible text.

```tsx
// ✅ name from visible text
<button><TrashIcon aria-hidden="true" /> Delete</button>

// ✅ icon-only
<button aria-label="Delete"><TrashIcon aria-hidden="true" /></button>
```

## Common ARIA mistakes

| Mistake | Why it fails |
|---|---|
| `aria-label` on a plain `<div>`/`<span>` | generic role can't be named; mostly ignored |
| `<button role="button">` | redundant noise |
| `aria-labelledby`/`aria-describedby` → missing id | silently no name/description |
| `role="menu"` on site navigation | promises app-menu arrow keys; use `<nav>` + list |
| `aria-hidden="true"` on or above focusable elements | tab stops that don't exist for screen readers |
| role without required states (`aria-selected`, `aria-expanded`, `aria-checked`) | state never announced |

## Disabled states

- Native `disabled`: removes from tab order, blocks activation, excluded from submit.
- `aria-disabled="true"`: only announces — keeps focus and hover; you must block
  activation in the handler and style it (incl. forced colors).
- Tooltips on natively disabled controls never open for keyboard/touch — put the reason
  as visible text beside the control, or use `aria-disabled`.
- Never both `disabled` and `aria-disabled` on one element.
- Disabled controls are exempt from contrast minimums.
