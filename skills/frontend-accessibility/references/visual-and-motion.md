# Contrast, color, targets, motion, zoom

## Contrast [1.4.3, 1.4.11]

| Applies to | Minimum (AA) |
|---|---|
| Text | 4.5:1 |
| Large text (≥ 24 px, or ≥ 18.66 px bold) | 3:1 |
| UI component boundaries, states, icons, meaningful graphics, focus rings | 3:1 |

- Enforce through design tokens (text/surface pairs verified once), not per component.
- Check hover, active, selected, focus and dark mode — every state is a new pair.
- Interactive states increase contrast compared to rest.
- Inactive (disabled) controls and logos are exempt.
- Placeholder text that carries information must meet 4.5:1.

## Color is never the only cue [1.4.1]

Errors, status, required fields, chart series, links in running text: add text, icon,
pattern or underline.

## Target size [2.5.8]

- AA: at least 24×24 CSS px, or a 24 px circle centered on the target doesn't overlap
  another target (spacing exception); inline text links are exempt.
- Recommended: 40×40 desktop, 44×44 touch where density allows.
- Keep the visual small, make the hit area big:

```css
.icon-button { min-width: 44px; min-height: 44px; display: inline-grid; place-items: center; }

/* or a pseudo-element on the wrapper/button — never on <input> */
.checkbox-control { position: relative; }
.checkbox-control::after {
  content: ""; position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%); width: 44px; height: 44px;
}
```

- Extended hit areas must not overlap each other.
- Decorative layers over interactive content (glows, scrims, gradients) get
  `pointer-events: none` (and `aria-hidden` if they are elements).
- Anything that looks clickable is clickable across its whole visual extent.

## Pointer and gestures [2.5.1, 2.5.2, 2.5.7]

- Every drag has a single-pointer alternative (move up/down buttons, "Verschieben nach …"
  menu).
- Multi-point or path gestures (pinch, swipe) have single-pointer alternatives.
- Actions fire on click/up-event, not on pointer down.
- `touch-action: none` only on surfaces with own pan/zoom/drag, scoped to that surface.

## Motion [2.3.1, 2.3.3, 2.2.2]

Motion is opt-in:

```css
@media (prefers-reduced-motion: no-preference) {
  .card { transition: transform 200ms ease-out; }
}
```

```tsx
<div className="motion-safe:transition-transform motion-safe:hover:-translate-y-1" />
```

| Disable under reduced motion | Replace | Keep |
|---|---|---|
| parallax, autoplay video/GIF, looping decoration, large movement | slide/scale → opacity crossfade; smooth scroll → instant | spinners, progress, instant state changes, brief press feedback |

- Animate `transform`/`opacity` only; never `transition: all`.
- Anything moving, blinking or auto-updating > 5 s has a visible pause/stop [2.2.2].
- Nothing flashes more than 3 times per second [2.3.1].
- Toasts with an action, an error or needed information stay until dismissed; timed
  toasts ≥ 5 s and pause on hover/focus. Never put the only "Undo" in a timed
  toast.

## Zoom, resize, reflow [1.4.4, 1.4.10, 1.4.12, 1.3.4]

- Content and functions survive 200 % text size.
- At 320 CSS px width (400 % zoom on 1280 px) only vertical scrolling — except truly 2D
  content (tables, maps, code), which scrolls in its own container.
- `rem` for font sizes; media queries in `rem`/`em` where the codebase allows.
- Text containers use `min-height`, not fixed `height`; layouts survive increased text
  spacing.
- Never `maximum-scale=1` or `user-scalable=no` in the viewport meta.
- No orientation lock.

## Content handling

- Long and user-generated content: `truncate` / `line-clamp` / `break-words`; flex
  children `min-w-0`; provide the full text (tooltip alone is not enough for keyboard
  and touch — use a disclosure or the detail view).
- Empty states are designed, not broken UI.
- Content on hover/focus (tooltips, popovers) is dismissible (Escape), hoverable and
  persistent [1.4.13].
- Dates and numbers via `Intl.DateTimeFormat` / `Intl.NumberFormat`.

## Themes

- Light, dark and forced colors keep borders, focus indicators and states visible.
- `color-scheme` set on `<html>` for dark themes; native `<select>` gets explicit
  colors.
