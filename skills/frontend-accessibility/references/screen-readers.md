# Screen readers — announcements, alt text, media

## Visually hidden content

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
```

1 px, not 0 (some readers skip zero-size elements). Never `display: none` /
`visibility: hidden` for content that must be read. Tailwind ships `sr-only`.
Use for context sighted users get visually ("opens in a new tab").

## Choosing how to announce a change

Stop at the first match:

1. **Focus moves there anyway** (dialog opened, first invalid field) → nothing extra.
2. **Tied to a control** (field error, character count) → `aria-describedby`.
3. **Non-urgent, not tied to a control** (toast, "Gespeichert", result count, loading)
   → `role="status"` (polite).
4. **Urgent, not tied to a control** (form-level failure, session expiry) →
   `role="alert"` (assertive).

## Live regions [4.1.3]

- The region element is rendered **before** its text changes; mounting it together with
  the message is announced inconsistently.
- Default to polite; assertive interrupts the user.
- Short, self-contained messages (`role="status"` re-reads the whole region).
- Never move focus to a toast.
- Loading: `aria-busy="true"` on the updating region, announce "Loading …", then the outcome
  ("12 Ergebnisse"). Skeletons are `aria-hidden="true"` with one visually hidden status.
- Toast libraries must announce via a live region — verify once with a screen reader.

```tsx
<p role="status" className="sr-only">
  {isFetching ? 'Ergebnisse werden geladen …' : `${total} Ergebnisse`}
</p>
```

## aria-hidden

Removes the element and its subtree from assistive tech — for decorative icons and
visually duplicated content. Never on or above a focusable element; to hide something
interactive, also remove it from the tab order (`inert`).

## Alt text [1.1.1]

| Purpose | `alt` | Example |
|---|---|---|
| Decorative or redundant with adjacent text | `alt=""` | logo next to the company name |
| Informative | the meaning it adds | `alt="QR code for your ticket"` |
| Functional (image is link/button) | the action/destination | search icon → `alt="Search"` |
| Image of text | the exact text (better: real text) [1.4.5] | `alt="50 % off everything"` |
| Complex (chart, diagram) | short summary; full data as table/text nearby | `alt="Revenue per quarter, details below"` |

A missing `alt` is worse than an empty one — readers fall back to the file name.

## SVG

- Decorative: `aria-hidden="true"`.
- Meaningful inline: `role="img"` + `aria-label`, or `<title>` referenced via
  `aria-labelledby`.
- Simple cases: `<img src="icon.svg" alt="…">`.
- Charts: provide the data as a table or text alternative.

## Video and audio [1.2.x, 1.4.2]

- Prerecorded video: captions; prerecorded audio: transcript.
- Never autoplay with sound; always render controls; media controls keyboard-operable.
- Muted decorative loops stop under reduced motion and get a pause control if longer
  than 5 s.

## Manual screen-reader check

| Action | VoiceOver (macOS) | NVDA (Windows) |
|---|---|---|
| Start/stop | ⌘ + F5 | Ctrl + Alt + N |
| Next/previous item | VO + → / ← | ↓ / ↑ |
| Activate | VO + Space | Enter |
| Headings | VO + U (rotor) | H / Shift + H |
| Landmarks | VO + U | D / Shift + D |
| Form fields | VO + U | F / Shift + F |
