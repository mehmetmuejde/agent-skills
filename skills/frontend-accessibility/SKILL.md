---
name: frontend-accessibility
description: Apply whenever UI is built or changed — components, pages, forms, dialogs, menus, tabs, tables, icons, images, animations, toasts, route changes — and for accessibility audits ("a11y", "Barrierefreiheit", "WCAG", "Screenreader", "Tastatur-Navigation", "accessibility review"). Accessibility is developed together with the UI, never added later. Target WCAG 2.2 AA (also the bar for BFSG / EN 301 549). Covers semantics and ARIA, keyboard and focus, accessible names, forms and errors, live regions, contrast and color, target sizes, motion, zoom/reflow, and testing with Testing Library, Storybook addon-a11y, Playwright + axe and manual keyboard/screen-reader checks. Framework-agnostic rules with React examples.
---

# Frontend accessibility

Accessibility is part of every UI change — designed, built and tested with it. A UI task
is not done until it works keyboard-only, every control announces name, role and state,
the automated checks pass and the tests query by role.

**Target: WCAG 2.2 level AA** — in the EU the European Accessibility Act (national laws
such as BFSG, EN 301 549) makes it mandatory for many products. A finding cites a WCAG A/AA criterion or a concrete task an
assistive-technology user cannot complete. AAA criteria and conventions (one `<h1>`,
44 px targets) are recommendations, never blockers.

| Task | Read |
|---|---|
| Choosing elements, landmarks, headings, ARIA, accessible names, disabled states | `references/semantics-and-aria.md` |
| Focus rings, tab order, skip link, dialogs, route changes, widget key maps | `references/focus-and-keyboard.md` |
| Labels, autocomplete, input types, validation errors, submit behavior | `references/forms.md` |
| Announcing changes, live regions, toasts, alt text, SVG, media | `references/screen-readers.md` |
| Contrast, color, target sizes, motion, zoom, reflow, content handling | `references/visual-and-motion.md` |
| Automated and manual testing, CI | `references/testing.md` |
| Audit/review of existing UI, report format | `references/audit.md` |
| Looking up a WCAG 2.2 criterion | `references/wcag.md` |

## Core rules — always

**Native first.** `<button>` for actions, `<a href>` / router `<Link>` for navigation,
`<label>`, `<fieldset>`, `<table>`, `<dialog>`, landmarks. Never `<div onClick>`. No ARIA
is better than bad ARIA; a role promises the full keyboard model. Complex widgets
(combobox, menu, date picker) come from the project's accessible headless library, not
hand-built.

**Every interactive element has an accessible name** [4.1.2]. Icon-only buttons get
`aria-label`, the icon `aria-hidden="true"`. The visible label text is part of the
accessible name [2.5.3]. Links say where they go — no "click here" [2.4.4].

**Keyboard** [2.1.1, 2.1.2]. Everything that works with a pointer works with the keyboard;
no traps. Tab order = visual order; never a positive `tabIndex`. Escape closes the
topmost overlay. Drag and gestures have a single-pointer alternative [2.5.7, 2.5.1].

**Visible focus** [2.4.7, 1.4.11]. Style `:focus-visible`; never `outline: none` without a
verified replacement (≥ 3:1 against every adjacent color). Focus is not hidden behind
sticky headers/banners [2.4.11] — `scroll-padding-top`.

**Focus management.** Dialogs: focus moves in on open, is trapped, background inert,
returns to the trigger on close. SPA route change: update `document.title` [2.4.2] and
move focus to the new `<h1>` (`tabIndex={-1}`) or `<main>`.

**Forms** [1.3.1, 3.3.1, 3.3.2]. Visible `<label>` for every control — a placeholder is not
a label. Correct `type`, `inputMode`, `autoComplete` [1.3.5]. Errors inline, linked with
`aria-describedby`, field `aria-invalid="true"`, focus the first invalid field on submit.
Validate on submit — don't disable submit until valid. Never block paste [3.3.8].

**Announce dynamic changes** [4.1.3]. Field-specific → `aria-describedby`; non-urgent
(saved, result count, loading) → `role="status"`; urgent form-level error →
`role="alert"`. The live region exists in the DOM **before** its text changes.

**Color and contrast** [1.4.3, 1.4.11, 1.4.1]. Text ≥ 4.5:1 (large ≥ 3:1), UI boundaries,
icons and focus rings ≥ 3:1 — enforced through design tokens. Color is never the only
cue.

**Targets** [2.5.8]. ≥ 24×24 CSS px or enough spacing; aim for 40 px desktop / 44 px
touch. Decorative overlays get `pointer-events: none`.

**Motion and time** [2.3.3, 2.2.2]. Animations opt-in via
`@media (prefers-reduced-motion: no-preference)`; parallax/autoplay off under reduced
motion. Anything moving > 5 s can be paused. Toasts with actions or errors stay until
dismissed.

**Zoom and reflow** [1.4.4, 1.4.10]. Works at 200 % text size and 320 CSS px width without
horizontal scrolling. Never `maximum-scale=1` / `user-scalable=no`.

**Page basics.** `<html lang>` set and updated with the UI language [3.1.1]; one visible
`<main>`; headings form an outline; skip link first when navigation precedes `<main>`
[2.4.1].

**Images.** Meaningful → `alt` describes the purpose; decorative → `alt=""`; functional
(image is the link/button) → the action [1.1.1].

## Testing duty

Every UI change ships with:

- component tests that query by role and name (`getByRole`) and cover keyboard paths
  (`user.tab()`, `{Escape}`, `toHaveFocus()`),
- Storybook stories whose addon-a11y check runs as **error** (fails CI),
- Playwright + `@axe-core/playwright` scans (WCAG 2.x A/AA tags) on critical pages and
  states,
- a manual keyboard-only pass of the flow; a screen-reader pass (VoiceOver/NVDA) for
  critical flows.

Automated tools find only part of the problems — a clean axe run is not WCAG
conformance. Details: `references/testing.md`.

## Before you finish — scan the change for

| Pattern | Fix |
|---|---|
| `<div onClick` / `<span onClick` | `<button>`, or `<a href>` when it navigates |
| `role="button"`/`role="tab"` without key handling | native element or the APG key map |
| `outline: none` / `outline-none` without `focus-visible` replacement | keep browser ring or verified custom ring |
| positive `tabIndex` | fix DOM order, use `0` / `-1` |
| `<img` without `alt` | `alt=""` or a purpose description |
| icon button without name | `aria-label`, icon `aria-hidden` |
| input without `<label>` / placeholder as label | visible linked label |
| `disabled={!isValid}` on submit | keep enabled, validate on submit |
| `{msg && <div role="status">…}` | render the empty region first, update its text |
| `aria-live="assertive"` on success messages | `role="status"` |
| `aria-hidden` on or above a focusable element | remove it or make the subtree `inert` |
| `onPaste` + `preventDefault` | allow paste |
| `maximum-scale=1` / `user-scalable=no` | remove |
| sticky header without `scroll-padding-top` | pad the scroller |
| drag/gesture without button alternative | add a single-pointer path |
| `transition: all`, motion without reduced-motion guard | list properties, wrap in `no-preference` |

## Reporting

Audits and reviews report in the conversation language, one finding per root cause with all locations,
WCAG criterion, user impact and concrete fix — format in `references/audit.md`.
Severity maps to the code-review skill: HIGH → Blocker/Major, MEDIUM → Major/Minor,
LOW → Minor.

## Sources

Combined from: Addy Osmani's web-quality-skills `accessibility` (MIT), Jakub Krehel's
`better-accessibility` (MIT), ibelick's `fixing-accessibility` (MIT), Vercel's Web
Interface Guidelines (MIT); W3C WCAG 2.2 and WAI-ARIA Authoring Practices.
