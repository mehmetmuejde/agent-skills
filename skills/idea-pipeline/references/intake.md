# Stage 0: intake

Goal: enough settled answers to write a one-page brief — in **one or two rounds**, not a
long interview. Speed matters more than completeness; open points go into the brief as
"open" and get answered by the POC.

## How to ask

- Ask a whole round at once, each question with a recommended answer. With a structured
  question tool, the recommended option comes first and is marked; ask the questions
  with the most downstream impact first. Without one, number the questions so "yes"
  accepts the recommendations.
- Before asking, derive what you can from the user's description and the environment —
  don't ask what the user already said.
- If the idea is several independent products in one, say so and ask which one goes
  through the pipeline first.

## Round 1 — what and why

1. **One sentence.** What does it do, for whom? (Restate it yourself and ask for
   confirmation if the description already says it.)
2. **Kind of thing.** Web app · native app (iOS/macOS) · desktop app · CLI / developer
   tool · library · game (2D / 3D, desktop / browser / mobile) · 3D asset or scene ·
   agent / LLM / MCP server · editor extension · data or ML experiment · other.
3. **Target visibility** — decides how Stage 2 looks, not Stage 1:
   - **Private** — personal use, stays in a private repository
   - **Client** — for a client; their rules for code, licences and hosting apply
   - **Public open source** — published, licensed, others may use and contribute
   - **Undecided** — fine for Stage 1; asked again before Stage 2
4. **Riskiest question.** What would kill the idea if it didn't work? (Technical
   feasibility, performance, an API or device capability, a platform restriction, fun
   factor for a game, cost.) The POC is built around this.
5. **Timebox.** Recommended: one session for a technical spike, one to two days for
   something playable or clickable.

## Round 2 — only what Round 1 left open

Ask only the questions that matter for this kind of idea:

- **Platform and devices** — browser, macOS, iOS, Windows, Linux, console, VR.
- **Existing assets or constraints** — a design, an API, data, a preferred engine, a
  client's stack, an account or licence that already exists.
- **Data** — personal or sensitive data involved? (If yes: synthetic data only in the
  POC, and note it in the brief.)
- **Project location** — where the project folder goes (recommend the user's usual
  projects folder; never the home or downloads root without a subfolder).
- **Success criterion** — what has to be visible at the end of the POC to say "go"?

## Done

Every Round 1 question is answered or explicitly marked open. Summarise the answers in
two or three lines and move on to the feasibility research.
