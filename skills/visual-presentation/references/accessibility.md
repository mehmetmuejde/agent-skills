# Accessibility

A deck that is read alone is also read with screen readers, zoomed in, printed in gray
or on a weak projector. These rules make it work for everyone; most of them also make
it clearer.

## Titles and structure

- Every slide has a real title — the headline sits in the title placeholder, not in a
  free text box. Screen readers and the slide outline navigate by these titles.
- Titles are unique; two slides on the same subject get distinguishing headlines.
- The document title and language are set in the file properties.

## Reading order

Screen readers read shapes in the order of the slide's shape tree — normally the order
they were created, back to front. PowerPoint shows and changes it in the Reading Order
pane (Review → Check Accessibility). Create shapes in this order:

1. headline (title placeholder)
2. the main visual — within a diagram, in the reading direction (left to right, step by step)
3. the lines under or beside the visual
4. footer elements (source, slide number)

When you add shapes later, move them to the right position in the order.

## Alt text

| Element | Alt text |
|---|---|
| Image with meaning | what it shows and why it is there, 1–2 sentences, ≤ about 150 characters |
| Chart | the claim plus the key values ("Checklist takes 3 h, test run 2 h, scan 1.5 h, sign-off 0.5 h") |
| Diagram from native shapes | the shapes' own text is read; add alt text to a group if you group them |
| Placeholder | "Image placeholder: <what the image will show>" |
| Decorative shape or image | mark as decorative (or no alt text) so it is skipped |

Do not start with "Image of …"; do not repeat the headline word for word. Write alt
text in the deck language.

## Text and color

- Text contrast ≥ 4.5:1 against its background; large text (≥ 18 pt regular or ≥ 14 pt
  bold) ≥ 3:1. Lines, arrows, chart bars and shape borders that carry meaning ≥ 3:1.
  The default tokens in `references/design.md` meet these.
- Color is never the only cue: add a label, a different shape, a line style or a
  position. A highlighted bar also carries its value label; the preferred option also
  carries a heading.
- No text inside generated images; all text is real text on the slide, so it can be
  read, searched, translated and resized.
- Minimum sizes: body 18 pt, diagram labels 16 pt, footnotes 12 pt.

## Language, tables, links, motion

- Set the language on the text (the `lang` attribute on every run, or the proofing
  language in PowerPoint) so screen readers pronounce it correctly.
- Tables: a header row, no merged or empty cells, simple structure.
- Links: descriptive link text ("Release dashboard"), not a raw URL or "click here".
- No automatic slide advance, no animation needed to understand a slide.

## Checking

- In PowerPoint: Review → Check Accessibility (lists missing alt text, titles,
  reading order problems, low contrast).
- Script-built decks: `scripts/build_deck.py` sets titles, reading order, alt text,
  language and warns about accent contrast; the visual check in `references/qa.md`
  still applies.
