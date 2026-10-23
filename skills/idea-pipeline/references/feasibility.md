# Stage 0b: feasibility research

The user has decided to build the idea. This stage never questions *whether* to build
it — it finds out *how* it can be built and what could get in the way, before a brief is
written or a line of code exists. Whether similar products exist is irrelevant to that
decision; never recommend using an existing product instead of building.

## What to find out

Two questions, each answered with sources:

1. **Technical feasibility** — Can the riskiest question from the intake be solved with
   the intended platform and stack? APIs and their limits (rate limits, quotas, access
   restrictions, deprecations), device and OS capabilities, engine features, performance
   reports, known hard problems. Libraries, plugins and building blocks that make the
   implementation faster, with their maturity (last release, maintenance) and licence.
2. **Constraints** — What could block it outside the code? Licences of key dependencies
   and assets, app store or platform policies, terms of service of used APIs, costs
   (API pricing, accounts, hosting), legal topics (personal data, regulated domains).

**Inspiration (optional)** — only when the user asks for it: how others solved similar
problems (UI patterns, game mechanics, architecture). Inspiration feeds ideas into the
brief; it is never a reason to change or stop the idea.

## How to research

- **Parallel agents.** If the agent can dispatch subagents, start one per question in
  parallel (plus one for inspiration if asked; fewer for small ideas — a pure local tool
  rarely needs the constraints agent). Without subagents, research the questions
  yourself in turn.
- **Brief each agent completely** — it knows only its prompt: the idea in one sentence,
  the kind of thing, the target platform, the riskiest question, the stack candidates,
  exactly which question it answers, and that the idea will be built regardless of
  competing products. Ask it to return:
  - findings as short bullets, each with a source URL and the date of the source
  - a clear split between **verified** (source says so) and **assumed** (inferred)
  - **blockers** — anything that makes the intended approach infeasible or much more
    expensive, with a way around it where one exists
- **Fresh sources.** Prefer official docs, changelogs, repositories and recent reports;
  flag anything older than about two years for fast-moving topics (APIs, AI, app stores).
- **Local facts are not research.** Available tools, CLIs and accounts are checked in
  the environment (see stack-routing), not searched for online.
- Don't let an agent's confident tone stand in for evidence: a finding without a source
  is an assumption.

## Result

Merge the agents' answers into the **Feasibility** section of `IDEA.md` (see
brief-and-poc) and give a short assessment to the user:

- **Feasible** — no blockers found; the POC answers what research couldn't.
- **Feasible with risks** — named risks; the riskiest question for the POC may change
  to the biggest risk found.
- **Blocker** — the intended approach doesn't work as imagined. Present the ways around
  it (other API, other platform, other stack, reduced scope) with a recommendation; the
  user picks one. The goal stays building the idea.

The user's decision on this assessment is the gate to the brief.
