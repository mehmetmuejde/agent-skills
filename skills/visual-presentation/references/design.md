# Design

Neutral, light and plain. The content is the design: a calm white page, one accent that
points at what matters, large visuals and readable text.

## Canvas

16:9, 13.333 × 7.5 in (PowerPoint "Widescreen"). In PptxGenJS use `LAYOUT_WIDE`; if you
must use `LAYOUT_16x9` (10 × 5.625 in), scale every measure below by 0.75.

| Zone | Position |
|---|---|
| Side margins | 0.6 in left and right |
| Headline | top 0.45 in, height up to 1.25 in (two lines) |
| Visual area | from 1.8 in down to about 6.8 in |
| Lines | band at 5.8–6.9 in under wide visuals, or a column on the right (from x = 8.6 in) next to split visuals |
| Slide number | bottom right, 12 pt, secondary text color |

Same positions on every slide: the headline never jumps. Gaps between elements 0.3–0.5 in;
pick one value and keep it. The visual takes at least half of the slide area.

## Colors

| Token | Hex | Use | Contrast on white |
|---|---|---|---|
| paper | `#FFFFFF` | background | — |
| ink | `#1F2937` | headlines, body text | 14.7:1 |
| muted | `#4B5563` | secondary text, sources, slide numbers | 7.6:1 |
| line | `#6B7280` | arrows, outlines, neutral bars and dots | 4.8:1 |
| panel | `#F3F4F6` | light fills behind ink text | ink on panel 13.4:1 |
| accent | `#0F766E` (default) | the one thing to look at; highlighted step, bar, panel | 5.5:1; white on accent 5.5:1 |

- **One accent.** It marks the element the headline is about — at most about 10 % of the
  slide. Everything else is neutral.
- **Another accent** (the user's brand, a topic color): check it against white. Text in
  the accent needs ≥ 4.5:1; white text on an accent fill needs ≥ 4.5:1; accent shapes
  need ≥ 3:1. Darken the color until it passes. `scripts/build_deck.py` warns when it
  does not.
- No second accent, no gradients, no transparency effects, no colored backgrounds.

## Type

One Office-safe family for everything: **Calibri** by default (Arial, Segoe UI or
Aptos are fine alternatives). Safe fonts render the same on other machines and in
converters, so overflow checks stay valid. Embedding fonts or using web fonts is not
worth the risk for a deck that will be passed around.

| Element | Size | Weight |
|---|---|---|
| Title slide headline | 40–44 pt | bold |
| Statement slide headline | 36–40 pt | bold |
| Headline | 28–32 pt | bold |
| Body lines | 20 pt (minimum 18) | regular |
| Diagram labels | 16–20 pt (minimum 16) | bold for box labels |
| Big number | 72–96 pt | bold, accent |
| Source, footnote, slide number | 12 pt (minimum 12) | regular, muted |

- Left-align text; center only labels inside shapes.
- Bold only headlines and labels — never whole sentences in the body.
- No all-caps sentences, no italics beyond a few words, no underlines except links.
- Line spacing about 1.1–1.2; space between lines ≈ 0.35 × font size.

## Things that make slides look generated

Avoid all of these:

- an accent line or bar under the headline; colored stripes on the side of cards
- gradients, glow, heavy shadows, glassmorphism, 3D effects, word art
- everything centered; three centered slides in a row
- the same "icon + bold title + one line" card row on slide after slide
- emoji as icons, clip art, decorative stock photos
- more than one accent color; purple-on-white "tech" palettes
- internal words on the slide: "Option A", "placeholder text", template names, file
  names, notes to self, the user's instructions (intended image placeholders are the
  only exception)
- text squeezed with "shrink to fit"; font sizes below the minimums above
- summary boxes on every slide repeating the headline

## Consistency

Same grid, same type sizes, same arrow style, same corner radius (small, or none), same
icon style and the same image style across the deck. If you style one slide specially,
the rest look unfinished — keep it plain everywhere instead.
