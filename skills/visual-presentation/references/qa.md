# Checking the deck

Assume the first build has problems — the job of this step is to find them. Do at least
one round of fix and re-check before delivering.

## With a renderer

```bash
soffice --headless --convert-to pdf --outdir <dir> deck.pptx
pdftoppm -r 110 -png <dir>/deck.pdf <dir>/slide
```

Look at every slide image, one by one, at full size. If the environment allows a
separate review pass (a second agent or a fresh look without the code in view), use it:
reviewing what you meant to build hides what you actually built.

Converters substitute fonts that are not installed (Calibri → Carlito, for example).
Metrics stay close, but leave some room rather than filling boxes to the edge.

Do not install a renderer to run this step — if none is there, use the path below.

## Without a renderer

1. Run `scripts/build_deck.py … --check` and the build; read every warning.
2. Re-open the file and list each slide's title, shapes and notes (python-pptx) — checks
   that nothing is missing, every slide has a title and notes, images have alt text.
3. Search the slide text for leftovers: `lorem`, `xxx`, `TODO`, `TBD`, `placeholder`
   (intended image placeholders excepted), template words, file names.
4. Tell the user which visual checks are still open and give them the manual checklist.

## What to look for — in this order

1. **Overflow** — text running out of its box or off the slide, headlines with a third
   line, labels cut inside shapes. Most common problem; fix by shortening or splitting.
2. **Overlap** — text over shapes, arrows through labels, images covering text.
3. **Spacing** — elements closer than 0.3 in, content closer than 0.5 in to the edge,
   uneven gaps between boxes of the same row.
4. **Contrast and color** — light text on light fills, accent used for more than the
   one focus element, meaning carried by color alone.
5. **Content** — every number matches the conversation, sources are present, nothing
   important is missing (completeness test in `references/storyline.md`), headlines
   alone tell the story.
6. **Language** — one language throughout, spelling, the same term for the same thing.
7. **Consistency** — headline position, sizes, arrow style and image style identical
   across slides.

One problem found is a reason to check every slide for the same problem.

## Manual checklist for the user

When the slides could not be rendered, hand over this list:

- [ ] Open the deck and go through it in Slide Show — no text cut off or overlapping
- [ ] Review → Check Accessibility shows no errors
- [ ] Image placeholders replaced (prompts are in the speaker notes)
- [ ] Numbers on chart slides match the sources named on the slides
- [ ] Slides read well when printed in grayscale

## Reporting

Report what was checked and how, separately:

- machine checks (script validation, structure check) — passed or what was fixed
- visual check — "all n slides rendered and viewed" or "not possible here: no renderer"
- open items — placeholders to fill, assumptions to confirm, warnings left on purpose

Never say "looks good" for slides nobody has looked at.
