# Building the .pptx

## 1. Check what the environment can do

Run these checks quietly before building; do not ask the user what you can find out.

| Capability | Check |
|---|---|
| Code execution | can you run a shell or a Python cell at all? |
| python-pptx | `python3 -c "import pptx; print(pptx.__version__)"` |
| PptxGenJS | `node -e "require('pptxgenjs')"` (exit code 0) |
| Image generation | does the assistant have an image tool in this environment? |
| Renderer for QA | `soffice --version` (LibreOffice) and `pdftoppm -v` (Poppler) |

## 2. Choose the path

| Situation | Path |
|---|---|
| python-pptx importable | write the deck spec, run `scripts/build_deck.py`, add custom shapes with python-pptx if needed |
| only PptxGenJS available | write your own Node script following `references/design.md` and the PptxGenJS notes below |
| code execution, but neither library | **stop and ask.** Offer: (a) install `python-pptx` with the user's approval, (b) the user runs `scripts/build_deck.py` on their own machine with the spec you deliver, (c) the full deck spec in Markdown to build by hand |
| no code execution | deliver the Markdown deck spec (format below) |

Installing packages changes the user's system — never run `pip install`, `npm install`
or similar without an explicit yes for that exact command. Do not try workarounds
(vendoring, downloading wheels) either.

## 3. Deck spec (JSON)

One file describes the whole deck. The script reads it; it is also the reviewable
source when the user wants changes. Example: `scripts/example-deck.json`.

```json
{
  "title": "Document title",
  "lang": "de-DE",
  "accent": "0F766E",
  "font": "Calibri",
  "author": "",
  "slides": [ { "type": "…", "headline": "…", "lines": ["…"], "notes": ["…"] } ]
}
```

Fields shared by all slides: `type`, `headline` (required), `lines` (0–3 strings),
`notes` (string or list of strings). Type-specific fields:

| Type | Fields |
|---|---|
| `title` | `subtitle`, `meta`, optional `image` |
| `statement` | — (uses `headline` and `lines`) |
| `process` | `steps`: strings or `{label, detail?, arrow?}` (`arrow` = verb on the arrow to the next step); `highlight`: index of the step in the accent |
| `comparison` | `left`, `right`: `{label, items[]}`; `highlight`: `"left"` or `"right"` (default right) |
| `timeline` | `events`: `[{when, label}]`; `highlight`: index |
| `chart` | `chart`: `{kind: column\|bar\|line, categories[], values[], source, highlight?, number_format?, series?, alt?}` — `source` is required |
| `number` | `number` (≤ 6 characters), `label` |
| `image` | `image`: `{alt, path?, prompt?}` — with `path` the picture is placed; without it a placeholder carries the `prompt` |
| `cards` | `cards`: `[{title, text?}]`; `highlight`: index |
| `closing` | `steps`: 1–3 strings |

Image paths are relative to the spec file. `number_format` uses Excel syntax, e.g.
`0"%"` or `0.0" h"`.

## 4. Run the script

`scripts/build_deck.py` lives in this skill's folder — call it with its full path; the
spec and output paths are in the user's working folder.

```bash
python3 scripts/build_deck.py deck.json --check          # validate only, no python-pptx needed
python3 scripts/build_deck.py deck.json out/2026-05-04-topic.pptx
```

The script:

- creates a 13.333 × 7.5 in deck with the theme from `references/design.md`
- puts every headline into the title placeholder, adds shapes in reading order, writes
  alt text, speaker notes, slide numbers, the document title and language
- refuses charts without `source`, images without alt text, unknown types
- warns about long headlines, more than 3 lines, missing notes, accent contrast below
  4.5:1, and text that probably overflows its box (an estimate — still check visually)
- never overwrites an existing file and never installs anything

Exit code 2 means errors in the spec; fix them and run again. Treat warnings as tasks:
shorten or split rather than ignore them.

For diagram types the script does not draw, build the deck first and then open it with
python-pptx to add shapes on the slide (use the same tokens, sizes and grid), or write
the whole deck with your own code.

## python-pptx notes

- Setting `text_frame.text` replaces runs and drops their formatting — set text per run
  and apply font, size, color and `lang` on each run.
- New presentations start at 10 × 7.5 in; set `slide_width = 12192000` and
  `slide_height = 6858000` (EMU) for 16:9.
- Use a layout with a title placeholder ("Title Only") so each slide has a real title.
- Alt text: set the `descr` attribute on the shape's `cNvPr` element.
- Arrowheads on connectors need an `a:tailEnd` element in the line properties.
- Charts are native (`add_chart` with `CategoryChartData`): the data stays editable.
- Turn off auto-fit (`MSO_AUTO_SIZE.NONE`) and keep fixed sizes; split content
  instead of shrinking it.

## PptxGenJS notes

- `pres.layout = "LAYOUT_WIDE"` for 13.333 × 7.5 in.
- Colors are 6-digit hex **without** `#`; a `#` or an 8-digit hex with alpha corrupts
  the file. Use the `transparency` property for opacity.
- Option objects are modified in place — create a fresh object for every call (a
  small factory function), never share one between shapes.
- Speaker notes: `slide.addNotes("…")`. Alt text: `altText` on images and charts.
- Titles: use a master slide with a title placeholder, or at least add the headline
  first on each slide so it comes first in the reading order.
- Set `margin: 0` on text boxes that must line up with shapes; text boxes have inner
  padding by default.
- Keep slide creation synchronous and write the file once at the end
  (`pres.writeFile({ fileName })`).

## Without code execution: Markdown deck spec

Deliver the whole deck as text so it can be built in any slide tool. Start with the
design tokens (colors, font, sizes from `references/design.md`), then per slide:

```text
## Slide 3 — chart
Headline: Manual release preparation takes most of a working day
Visual: horizontal bar chart, bars in gray, "Checklist" bar in accent #0F766E;
        Checklist 3.0 h · Test run 2.0 h · Scan 1.5 h · Sign-off 0.5 h;
        value labels at the bar ends; no legend, no gridlines
Source line: Source: release log, March 2026
Lines:
- The checklist alone takes three hours.
- Automation removes the first three bars.
Alt text: Bar chart: checklist 3 h, test run 2 h, scan 1.5 h, sign-off 0.5 h.
Notes:
- Point: …
- Source: …
```

For image slides add the image prompt (and say whether it is to be generated or is a
placeholder). For diagrams list every box label, every arrow with its verb, and which
element is highlighted.

## Saving

- File name `YYYY-MM-DD-<topic-slug>.pptx`, lowercase ASCII with hyphens; working files
  beside it: `<topic-slug>.deck.json` and `<topic-slug>-assets/`.
- Location: where the user says. Otherwise propose the project's scratch or output
  folder (for example `.scratch/` when the project keeps one) and ask; in a chat
  sandbox use the environment's output folder so the user can download the file.
- Never write into source folders, the home directory or the desktop unasked; never
  overwrite — add `-v2`, `-v3` or ask.
