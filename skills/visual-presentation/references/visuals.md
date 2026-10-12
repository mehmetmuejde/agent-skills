# Visuals

The visual carries the message; the text labels it. Test every slide: remove the lines
under the headline — the visual plus headline must still make the point. If the visual
only decorates (an icon next to a sentence, a stock photo of people in a meeting), it
does not count as a visual.

## What kind of knowledge is it?

| Knowledge | Reader should … | Show it as |
|---|---|---|
| Concept ("what is X") | explain it in their own words | analogy to something familiar drawn side by side; one example and one non-example |
| Procedure ("how to do X") | follow the steps | numbered flow; branch where a decision changes the path; wrong way → right way |
| Mechanism ("how X works") | see what moves where | the actual path through the parts, arrows labeled with verbs |
| Relationship ("X and Y") | see direction and strength | linked nodes, overlap circles, 2×2 matrix, cause → effect chain |
| Change over time | see order and turning points | timeline; before/after at the same scale |
| Quantity, trend, scale | compare sizes and changes | bars, a line, one large number with a familiar comparison |
| Way of thinking ("why think like this") | notice the shift | old view vs. new view as two panels |
| Story, case | remember what happened | scene image or a short sequence of moments |

## Content → slide type

| Content | Type | Notes |
|---|---|---|
| steps, pipeline, workflow | `process` | 2–5 steps; more → group or split over two slides |
| options, before/after | `comparison` | draw the difference, not two lists of praise |
| phases, roadmap | `timeline` | highlight "now" or the next milestone |
| quantities | `chart` | only with real numbers and a source |
| one decisive number | `number` | add what it means ("5× more release windows") |
| parallel items | `cards` | max 4; titles short |
| feeling, scene, object | `image` | literal, not decorative |
| hierarchy, cycle, matrix, network | custom shapes | see "Diagrams" below |

## Diagrams

Draw diagrams as native shapes (rectangles, ovals, connectors, text) — they stay sharp,
editable and searchable, and they get the content exactly right. Never use a generated
image for a diagram.

- **Draw the mechanism, not the name.** A request travelling through the parts beats a
  box labeled "System". Label every arrow with a verb or value ("sends", "every 30 s").
- **Draw the difference.** For options, use the same drawing twice and change only the
  part that differs.
- **Lean labels.** One short label per box (≤ 3 words), no sub-titles or explanation
  sentences inside the diagram — those go to the notes.
- **Few elements.** ≤ 6 boxes per slide; more than 4 side by side → group related ones
  on a light panel. Complex diagrams: build them up over 2–4 slides, adding one part per
  slide with the same positions.
- **Shape and color both carry meaning.** The element the slide is about gets the
  accent fill; everything else is neutral. States also differ in shape, line style or
  a label — never only in color.
- **Layout.** Left to right or top to bottom; ≥ 0.4 in between boxes; arrows long enough
  to show their shaft; text at least 16 pt; nothing touches the slide margin.
- **Real boundaries only.** Draw a frame around things only when it is a real boundary
  (a system, a team, a network) — not to make the diagram look structured.
- **Show what is out of scope** in light gray when it helps the reader place the topic.

Patterns for custom diagrams:

| Pattern | Use for | Drawing |
|---|---|---|
| hub and spoke | one thing connected to many | center node in accent, 3–6 outer nodes, labeled connectors |
| cycle | recurring process | 3–5 nodes on a circle, arrows clockwise |
| 2×2 matrix | two criteria | two labeled axes, four quadrants, items placed, the target quadrant tinted |
| layers / stack | levels, architecture tiers | full-width bands, top = closest to the user |
| funnel | narrowing stages | bars of decreasing width with the count on each |
| tree | hierarchy, breakdown | root on the left or top, max 3 levels |
| overlap circles | shared and separate parts | 2–3 circles, labels in each region |

## Charts

- **Only real data.** Values come from the conversation or a source the user named.
  Put the source on the slide ("Source: …"). No invented, extrapolated or "example"
  numbers. If the data is missing, use a diagram or say in the outline that the number
  is needed.
- **Estimates are labeled** as estimates; ranges are shown as ranges.
- Bar/column for comparing categories, line for change over time. Avoid pie charts with
  more than three slices, 3D, dual axes and stacked charts the reader has to decode.
- Label values directly at the bars; no legend for a single series; no gridlines.
- The bar the headline talks about gets the accent, the rest neutral gray.
- Use native charts (editable data), not pictures of charts.
- Every number on a slide gets a picture: a bar, a big number with a comparison, a
  marked span on a timeline. A number hidden in a sentence is lost.

## Images

Use an image only when it adds something a diagram cannot: a scene, a physical object,
a mood that frames the topic, a real screenshot. Use them sparingly — a few per deck,
never the same one twice, never as filler.

- **Literal.** The image shows the noun the slide talks about, not a vague mood.
  Positive images (smiles, thumbs up) only on genuinely positive slides.
- **Real things stay real.** Products, interfaces and results are shown as screenshots
  or photos supplied by the user, never as generated look-alikes.
- **Fit.** Show screenshots whole (scale to fit, never crop away content); photos may
  fill their area. Keep one aspect ratio for images that sit side by side.

### Generated images — when the tool can generate images

Write one prompt per image and keep a consistent style line for the whole deck:

```text
<subject: the literal thing from the headline>, <style: e.g. flat vector illustration |
soft natural-light photo>, white or very light background, palette of neutral grays
with one <accent color name + hex> accent, simple composition with empty space on the
<side where nothing overlaps>, no text, no letters, no numbers, no logos, no watermark,
no borders or frames, <aspect ratio of the slot, e.g. 4:3>
```

- Generate at the aspect ratio of the slot (split image ≈ 3:2, title image ≈ 4:5).
- Check each result: does it show the right thing, is there any text or garbled
  lettering, does it clash with the palette? If anything is wrong, regenerate with a
  corrected prompt — never cover errors with shapes.
- Never put the headline or labels into the image; text belongs on the slide.
- Do not generate real people, real brands or real products.
- Save images as `slide-NN-<slug>.png` in the assets folder and reference them in the
  deck spec.

### Placeholders — when the tool cannot generate images

Put a dashed placeholder box where the image goes, carrying the label "Image placeholder"
(in the deck language) and the full prompt. Copy the prompt into the speaker notes as
well, and list all prompts in the delivery message so the user can generate the images
elsewhere and drop them in. The slide must still work with the placeholder — the
headline and lines carry the message.

### Other sources

Stock photos only when the user asks for them; then use licenses that allow reuse
(public domain/CC0 or the provider's free license), credit where the license requires
it, and note the source in the speaker notes.

## Icons

Only with a text label next to them, from one consistent set or drawn as simple native
shapes. No emoji, no clip art, no mixing of icon styles.
