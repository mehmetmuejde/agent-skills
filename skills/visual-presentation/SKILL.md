---
name: visual-presentation
description: Turn the result of a conversation into a PowerPoint deck (.pptx) that someone can read on their own and understand — every slide one full-sentence headline, one large visual and at most three short lines, details in the speaker notes. Use when the user wants worked-out content as slides, e.g. "mach mir eine Präsentation daraus", "fasse das als Präsentation zusammen", "erstell Folien dazu", "mach ein Deck daraus", "make a deck/slides from this", "turn this into a presentation", "summarize this as a PowerPoint". Shows a short outline for approval first, draws diagrams and charts as editable shapes, adds generated images where the tool can create them (otherwise placeholders with ready image prompts), never invents chart data, and checks overflow, contrast and alt text before delivery.
---

# Visual presentation

Turns what the user and the assistant worked out in a conversation into a short deck
that explains the topic **without a speaker**. Visuals carry the message; text is short
and plain. The deck is a .pptx file, 16:9, in the language of the conversation.

| Task | Read |
|---|---|
| Finding the core message, storyline, slide count, headlines, outline format | `references/storyline.md` |
| Choosing a slide type and its text limits | `references/slide-types.md` |
| Picking the visual, drawing diagrams and charts, image prompts, placeholders | `references/visuals.md` |
| Colors, fonts, sizes, grid, things that look generated | `references/design.md` |
| Writing speaker notes | `references/speaker-notes.md` |
| Alt text, reading order, contrast, language | `references/accessibility.md` |
| Tool check, deck spec, build script, PptxGenJS, no-code fallback, saving | `references/build.md` |
| Rendering and checking the result, reporting | `references/qa.md` |

## Defaults

Apply these unless the user asks for something else.

| Topic | Default |
|---|---|
| Output | `.pptx`, 16:9 (13.333 × 7.5 in), editable shapes and native charts |
| Language | the language of the conversation — slides, notes, alt text, image placeholders |
| Length | 8–12 slides; more only when the user asks for more |
| Mode | self-reading: understandable without a presenter |
| Slide | assertion headline (a full statement) + one visual + 1–3 short lines |
| Details | in the speaker notes, never as extra text on the slide |
| Design | white background, near-black text, one accent color, large visuals, readable fonts, WCAG AA contrast |
| Images | code-drawn diagrams for anything factual; generated images only where the tool can generate images; otherwise a placeholder with a ready image prompt |
| Workflow | short outline first, build only after the user approves it |

## Workflow

### 1. Collect — before writing anything

Go back through the conversation and list what was established: the result or decision,
the reasons, numbers (with where they came from), steps, trade-offs, open points and
next steps. Use only this material. Mark anything you add yourself as an assumption and
ask about it in the outline.

Then decide (details: `references/storyline.md`):

- **Core message** — one sentence a reader should remember if they forget everything else.
- **Reader** — who opens the file later, what they already know, what they should
  decide or do afterwards. Ask only if the conversation does not make it clear.
- **Storyline** — answer first, then why and how, then what next.

### 2. Outline — get approval

Show a compact outline and stop. Per slide: number, headline (the full statement) and
the planned visual (type plus what it shows; for images: generated or placeholder).
Below the list, one line each for language, slide count, accent color and where the
file will be saved. Ask for approval or changes in one question. Do not build before
the user says go; rework the outline as often as they want.

Format and example: `references/storyline.md` → "Outline for approval".

### 3. Check the tools

Find out what this environment can do — run code, import `python-pptx`, load
`pptxgenjs`, generate images, render slides to images (`references/build.md`).

- **Never install anything without asking.** Installing a package changes the user's
  system. If neither library is available, offer the options (install with their
  approval, run the build script on their machine, or receive the full deck spec) and
  let the user choose.
- **No code execution at all:** deliver the complete deck spec in Markdown — per slide
  headline, text lines, visual description or image prompt, alt text and notes — so
  the deck can be built by hand.

### 4. Build

1. Write the deck spec (JSON, format in `references/build.md`) from the approved outline.
2. Create the visuals: diagrams and charts as native shapes; images generated now if
   the tool can, else a placeholder carrying the prompt.
3. Build the .pptx — with `scripts/build_deck.py` when python-pptx is importable, or
   with your own python-pptx / PptxGenJS code that follows `references/design.md`.
4. Add speaker notes, alt text and the document language on every slide.

### 5. Check

Render the slides to images when a renderer exists and look at every one; otherwise run
the script's checks and go through the manual checklist. Fix, then check again
(`references/qa.md`).

### 6. Deliver

Give the file path, one line on what the deck says, what was checked and how, and the
list of image placeholders still to fill (with their prompts). Offer one round of
changes.

## Slide rules — always

**One message per slide.** If the message needs "and", it is two slides. Every slide
answers one question a reader would ask next.

**The headline is the message.** A full sentence that states the point — "Manual checks
take most of a release day", not "Release process". Present tense, active voice, at
most two lines (about 90 characters, better 60). Read only the headlines in order: they
must tell the whole story.

**One visual anchor per slide** — a diagram, chart, big number, image or a large
statement. Make it the largest element on the slide. Strip-the-text test: without the
lines under the headline, the visual and the headline still carry the point.

**Text limits.** 1–3 lines per slide, each one short sentence or phrase (≤ 90
characters). No paragraphs, no nested bullets. Labels inside diagrams ≤ 3 words where
possible. When content does not fit: split the slide or move details to the notes —
never shrink the font below the minimums in `references/design.md`.

**Plain words.** Short sentences, one term per concept, abbreviations spelled out once,
jargon replaced by what the thing does. No filler phrases ("let's dive into", "journey",
"exciting", "in conclusion") and no equivalents in other languages.

**Facts stay facts.** Every number, quote and chart comes from the conversation or from
a source the user gave, and charts state their source on the slide. Never invent,
inflate or "illustrate" data. If a needed number is missing, say so in the outline —
do not fill the gap.

**Generated images carry no text.** No words, letters, numbers, logos or slide chrome in
generated images; the slide supplies the text. Images show mood, scenes or concrete
objects — never data, structure or steps. A wrong image is regenerated, not painted over.

**Accessible by default.** Every slide has a real title, a sensible reading order
(headline → visual → lines), alt text on images and charts, contrast ≥ 4.5:1 for text
and ≥ 3:1 for lines and shapes, and color never as the only cue.

## Storyline — default shape

| Position | Slide |
|---|---|
| 1 | Title — the answer as a statement, plus a subtitle that names the topic |
| 2 | The result in one picture — what was decided or found |
| 3 … n-2 | One slide per supporting point — why, how, evidence, comparison, steps |
| n-1 | Honest limits — risks, open points, assumptions |
| n | What next — 1–3 concrete steps (no "Thank you", no "Questions?") |

Add a short overview slide only when the deck has more than 10 slides. Other shapes
(explainer, plan, comparison, analysis) are in `references/storyline.md`.

## Visual choice — quick map

| The slide says … | Use |
|---|---|
| how something works, steps, a flow | process diagram (boxes + labeled arrows) |
| A is better / different than B, before vs. after | comparison (two panels, the difference marked) |
| when things happen, phases | timeline |
| how much, how it changed | chart from real data (bar for comparing, line for trends) |
| one number matters | big number with what it means |
| 2–4 parallel items (risks, options, roles) | cards — sparingly |
| a scene, mood, metaphor, physical object | image (generated or placeholder) |
| one idea that needs weight | statement slide |

Relationships, hierarchies, cycles and matrices: `references/visuals.md`.

## Design — default theme

White background, text `#1F2937`, secondary text `#4B5563`, lines `#6B7280`, panels
`#F3F4F6`, one accent (default `#0F766E`, 5.5:1 on white). One Office-safe font family
(Calibri by default). Headline 28–32 pt, body 20 pt (minimum 18), diagram labels
≥ 16 pt, sources ≥ 12 pt. Left-aligned text, generous margins (≥ 0.5 in), the accent
only on what the reader must look at. No accent lines under titles, gradients, shadows,
emoji or clip art. Details: `references/design.md`.

## Files

Name the deck `YYYY-MM-DD-<topic-slug>.pptx` (lowercase ASCII, hyphens). Keep working
files beside it: `<topic-slug>.deck.json` and `<topic-slug>-assets/` for images.
Save where the user says. If they have not said: in a project, propose its scratch or
output folder (e.g. `.scratch/` when the project keeps one) and ask; in a chat sandbox,
use the environment's output folder. Never write into source folders or random
locations, and never overwrite an existing file without asking.

## Before you deliver

- [ ] Outline was approved; the deck follows it (or the changes were agreed)
- [ ] Headlines alone tell the story; each is a full statement
- [ ] Each slide: one visual anchor, ≤ 3 short lines, nothing overflows or overlaps
- [ ] All numbers trace back to the conversation or a named source
- [ ] Speaker notes on every content slide; image prompts listed for placeholders
- [ ] Alt text, titles, reading order, contrast, document language set
- [ ] Checks were run and reported honestly (rendered and viewed, or not)

## Sources

Rewritten in our own words from these published skills (no text or code copied):
nicobailon `visual-explainer` (MIT) — figures lead and words label, draw the mechanism,
every number gets a picture, slide budgets; jimliu `baoyu-slide-deck` (MIT) — message
hierarchy, narrative headlines, layout gallery, filler-phrase list; edu-ai-builders
`visual-cognition-slides` (MIT) — knowledge type → visual, dual coding;
zarazhangrui `frontend-slides` (MIT) — reading vs. speaking density, split instead of
shrink; wshobson `data-storytelling` (MIT) — insight first, headline formula,
uncertainty; minorun365 `slide-story` and `slide-figures` (Apache-2.0) — one slide one
theme, lean diagrams, literal and sparse illustrations, measure instead of guess;
MiniMax `pptx-generator` (MIT) — PptxGenJS build workflow and pitfalls.
Further ideas from skills read for inspiration only, without taking text or code.

Principles: Michael Alley's assertion-evidence approach (assertion-evidence.com);
W3C WAI "Making Presentations Accessible"; WCAG 2.2 (1.1.1, 1.3.2, 1.4.1, 1.4.3,
1.4.11, 3.1.1); Microsoft's guidance on accessible PowerPoint presentations.
Tools: python-pptx (MIT) and PptxGenJS (MIT) documentation.
