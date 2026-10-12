# Slide types

Every slide is exactly one of these types. The `type` value is what the deck spec and
`scripts/build_deck.py` use (fields: `references/build.md`). All types share the
headline rules and the 1–3 line limit.

| Type | Use for | Visual | Holds at most |
|---|---|---|---|
| `title` | opening | optional image on the right | headline (the answer) + subtitle + one meta line (date, author) |
| `statement` | one idea that needs weight; a turn in the story | the large sentence itself | headline (≤ 15 words) + 1–2 lines |
| `process` | steps, flows, how something works, overview of sections | boxes with labeled arrows | 2–5 steps, labels ≤ 3 words, optional detail ≤ 6 words per step, arrow verbs |
| `comparison` | before/after, option A vs. B, old vs. new | two panels, the preferred one in the accent | 2 × 4 items, each ≤ 8 words |
| `timeline` | phases, milestones, history | line with dated points, one highlighted | 2–6 events, label ≤ 8 words |
| `chart` | quantities, changes, rankings | native bar/column/line chart, one bar highlighted | ≤ 8 categories, one series, source line |
| `number` | one number that matters | the number very large + what it means | number ≤ 6 characters, label ≤ 10 words |
| `image` | scene, mood, object, screenshot | one large image or placeholder | image + 1–3 lines |
| `cards` | 2–4 parallel items: risks, roles, options | equal panels, one may be highlighted | 2–4 cards, title ≤ 3 words, text ≤ 10 words |
| `closing` | what happens next | numbered steps | headline + 1–3 steps, each ≤ 12 words |

## Layout per type

- **Wide visuals** (`process`, `comparison`, `timeline`, `cards`): visual across the
  full width, lines in a band below it.
- **Split visuals** (`chart`, `number`, `image`): visual on the left (about 60 % of the
  width), lines in a column on the right. Without lines the visual takes the full width.
- **`title`**: headline lower left, subtitle under it; an image, if any, on the right.
- **`statement`**: headline large in the middle band, lines under it.
- Slide number bottom right on every slide except the title slide.

## Rhythm across the deck

- Do not use the same type more than twice in a row; vary wide and split layouts.
- `cards` at most twice per deck — rows of identical boxes on every slide read as a
  template, not as thinking.
- `number` at most twice per deck; one hero number loses its force when repeated.
- `statement` at most twice; it works as a pause, not as a format.
- Every content slide has a visual anchor; a slide that is only text lines is a sign
  that the visual is missing — go back to `references/visuals.md`.

## Types the script does not draw

Relationships, hierarchies, cycles, 2×2 matrices, layered stacks, architecture
diagrams and tables are built with your own python-pptx or PptxGenJS code after the
script has created the deck, or instead of it — following `references/visuals.md` and
`references/design.md`. Keep the same grid: headline at the top, visual area from
1.8 in down, lines below or to the right.

Tables: only when the reader must look up values. At most 5 rows × 4 columns, a header
row, no merged cells, left-aligned text and right-aligned numbers. Anything larger is a
chart, or goes into the notes.
