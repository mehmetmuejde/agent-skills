# Storyline

The deck is read later by someone who was not in the conversation. It has to answer
their questions in the order they come up: *What is the result? Why? How does it work?
What does it mean for me? What happens next?*

## From conversation to material

Make an inventory before planning slides. Go through the whole conversation and note:

| Kind | Examples |
|---|---|
| Result | the decision, the recommendation, the answer, the finished design |
| Reasons | why this option, which alternatives were dropped and why |
| Mechanism | how it works, steps, components, data flow |
| Numbers | measurements, estimates, costs, dates — each with its origin |
| Trade-offs | what gets worse, risks, limits, assumptions |
| Open points | what was not decided, what is still unknown |
| Next steps | who does what next |

Then sort every item:

- **keep** — core arguments, unique findings, numbers that support the message
- **simplify** — technical detail becomes a picture or goes to the notes; several
  examples become the best one
- **visualize** — process descriptions become flows, comparisons become side-by-side,
  tables of numbers become a chart or one highlighted number
- **leave out** — side topics, repetition, things the reader already knows

Completeness test: a reader who never saw the conversation can rebuild every main point
from the deck and its notes. If an important point has no slide or note, add it.

## Core message and reader

- **Core message:** one sentence, short enough to say in one breath (about 15 words).
  It becomes the title slide headline or the headline of slide 2.
- **Supporting points:** 3–5 points that make the core message believable. Order them
  by what the reader needs, not by the order of the conversation.
- **Reader:** role and prior knowledge, what they believe now, what they should decide
  or do after reading. Executives: outcome first, little detail. Technical readers:
  precise diagrams. General readers: concrete examples, analogies, no jargon.
- **Action:** what the last slide asks for.

## Storyline shapes

Default for a self-reading deck: **answer first**. The reader gets the result on the
first two slides and can stop there; the rest is evidence and detail. Do not build
suspense, do not hold back the conclusion.

| Content | Shape |
|---|---|
| Decision | result → reasons → alternatives compared → risks → next steps |
| Explainer (concept, system) | the idea in one picture → how it works (steps) → an example → limits → what to remember |
| Plan | goal → steps → timeline → risks and owners → first step |
| Comparison | recommendation → the difference drawn side by side → trade-offs → when the other option wins |
| Analysis | finding → evidence → cause → what it means → recommendation |
| Problem/solution | situation → complication → resolution → next steps |

Opening: the title slide states the answer; a hook (a surprising number, a contrast) is
fine on slide 2 if it *is* the evidence. Do not open with a definition or an agenda.

Closing: one slide with 1–3 concrete next steps, or the core message restated with what
it means for the reader. Never end on "Thank you" or "Questions?".

Overview slide: only above 10 slides — one row of 3–5 section names, drawn as a process.

## Slide count

- One supporting point = one slide. Count: title + result + supporting points + limits
  + next steps. That usually lands at 8–12.
- More material than 12 slides: merge points, move detail to notes, or ask the user
  whether a longer deck is wanted. Never shrink text to fit more.
- Less than 8 is fine when the conversation was short — do not pad.

## Headlines

- A full sentence that makes a claim: "Automated checks cut release time from a day to
  an hour", not "Release checks" or "Results".
- With data: specific number + effect + context ("Churn costs 2.4 M per year, most of it
  preventable").
- Present tense, active voice, concrete nouns. At most two lines; aim for 60 characters.
- A question headline is allowed only when the next slide answers it.
- One term per concept across the whole deck; spell out abbreviations on first use.
- Read all headlines in a row: they must tell the story alone. Check for monotony —
  all the same length, all the same sentence pattern, all starting with the same word
  reads as machine-made. Vary length and form.
- Avoid filler: "let's take a look", "dive into", "explore", "journey", "exciting",
  "revolutionary", "in conclusion", "to summarize" — and their equivalents in the deck
  language.

## Lines under the headline

At most three, each one short sentence or phrase. They add what the visual cannot show:
the consequence, the condition, the caveat. They never repeat the headline or describe
the picture ("This chart shows …"). If a line would need a sub-point, the point belongs
in the notes.

## Outline for approval

Show this before building anything. Keep it compact — the user reviews the story, not
the design.

```text
Deck: <title> — <core message>
Reader: <who> · Language: <language> · Slides: <n> · Accent: <color> · File: <path>

 1  Title      "<headline as a statement>"           visual: <image / none>
 2  Result     "<headline>"                          visual: <process diagram of …>
 3  Why        "<headline>"                          visual: <bar chart: … (source: …)>
 4  …
 n  Next       "<headline>"                          visual: <3 numbered steps>

Assumptions / gaps: <anything not established in the conversation, or "none">
Images: <generated now | placeholders with prompts>
```

Then ask one question: approve, or what to change. After changes, show the updated
outline again (only the changed rows if the deck is long).
