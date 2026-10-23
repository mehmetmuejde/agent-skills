---
name: idea-pipeline
description: Use when the user has a new project or software idea and wants to turn it into something real fast — "ich habe eine neue Idee", "neue Projektidee", "lass uns X bauen", "new idea", "quick POC for ...", "can we build ...". Runs a staged pipeline with an approval gate at every stage — intake interview, feasibility research with parallel web-research agents on how to build it (technical limits, building blocks, licences, policies, costs — never whether competitors exist), one-page idea brief, stack and tool routing (web, native Apple, desktop, CLI, games with Godot/Babylon.js/Unity/Unreal, 3D assets with Blender, agents/MCP), a timeboxed proof of concept with a go/pivot/drop verdict, and — only on go — hardening and publishing as a private or public open-source repository. Not for changes to an existing project; use brainstorming for those.
---

# Idea pipeline

The user has decided to build the idea — the pipeline implements it, it doesn't judge
whether it should exist. It turns a raw idea into a tested proof of concept quickly, and — only if it proves itself —
into a maintained private or public repository. Speed comes from asking the right
questions once, writing one short Markdown brief and building the smallest thing that
answers the riskiest question. Nothing is built on assumptions the user hasn't confirmed.

Talk to the user in the conversation language. Everything written into the project —
brief, code, README, ADRs — in English.

## Stages

| Stage | Result | Read first |
|---|---|---|
| 0a Intake | Settled answers to the intake questions | [references/intake.md](references/intake.md) |
| 0b Feasibility | Researched assessment: feasible / risks / blocker with ways around it | [references/feasibility.md](references/feasibility.md) |
| 1a Brief | `IDEA.md` — one page, approved | [references/brief-and-poc.md](references/brief-and-poc.md) |
| 1b Routing | Stack, skills and tools, recorded in `IDEA.md` | [references/stack-routing.md](references/stack-routing.md) |
| 1c POC | Running proof of concept + verdict go / pivot / drop | [references/brief-and-poc.md](references/brief-and-poc.md) |
| 2 Publish | Hardened repo, private or public | [references/publish.md](references/publish.md) |

Stage 1 is the main loop: most ideas end there, either dropped or parked with a verdict.
Stage 2 only starts on an explicit **go** and only when the idea is meant to live on.

## Rules that always apply

- **Feasibility before building.** No brief and no POC without the feasibility research
  of Stage 0b — never skip it, also not for ideas that look simple. It checks *how* the
  idea can be built, never *whether* it should be: existing competitors are no argument
  against building. A blocker pauses the pipeline until the user picks a way around it.
- **Gate every stage.** Show the result of a stage, wait for the user's approval, then
  start the next one. An approval covers one stage, never the next.
- **Facts are your job, decisions are the user's.** Check which tools, CLIs, MCP servers
  and accounts are actually available yourself (see stack-routing) — never ask the user
  for something you can find out, never assume a tool exists.
- **Recommend, don't survey.** Every question comes with a recommended answer. Every
  stack choice names one default and why; alternatives only when they change the outcome.
- **Smallest thing that answers the question.** The POC answers the feasibility questions
  in the brief, nothing else. No auth, no deployment, no polish, no tests beyond what
  proves the point — unless that *is* the risky part.
- **Timebox.** Agree on a timebox in the intake. When it runs out, stop and give the
  verdict with what is known — don't silently keep going.
- **POC code is throwaway by default.** Stage 2 decides what survives. Say so in the brief.
- **Use the existing skills.** Once the stack is chosen, load the matching skills (e.g.
  `react-frontend`, `rust`) and follow their conventions even in a POC — where a skill's
  rule would slow the POC down without affecting the verdict, note the shortcut in
  `IDEA.md` instead of silently skipping it.
- **Respect the agent's approval rules.** Creating a folder for the project is part of
  the stage; `git init`, commits, creating remote repositories, installing tools or
  adding MCP servers, and anything public each need their own approval.
- **Missing capability = finding.** If the idea needs a tool, MCP server or skill that
  isn't there, record it in `IDEA.md` and offer options (install, `find-skills`, manual
  step) instead of improvising around it.

## Flow

1. **Intake** — ask the intake rounds (references/intake.md). Look up the environment
   in parallel: available MCP servers, CLIs, accounts (references/stack-routing.md).
2. **Feasibility** — research technical feasibility and constraints with parallel
   research agents (references/feasibility.md); inspiration from similar work only when
   the user asks. Present the assessment with sources; on a blocker, propose ways around
   it and let the user pick one.
3. **Brief** — write `IDEA.md` in the project folder the user chose, including the
   feasibility findings, stack proposal and the open questions for the POC. Show it,
   wait for approval.
4. **Routing** — confirm stack, skills and tools; load the stack skills.
5. **POC** — build it within the timebox, run it, show it (screenshot, run output,
   playable build). Record what worked, what didn't, and the verdict proposal in
   `IDEA.md`. The user decides: **go**, **pivot** (back to step 3 with the new angle) or
   **drop** (keep `IDEA.md` as a record, stop).
6. **Publish** (only on go) — follow references/publish.md: target (private / public),
   cleanup, ADRs, README, license, CI, security review, then the repository itself —
   each irreversible step with its own approval.

## Done

- **Dropped or parked:** `IDEA.md` holds the verdict and the reason. Nothing else to do.
- **Published:** repository exists, README explains how to run it, ADRs record the stack
  decisions, CI is green, and the user has confirmed visibility and license.

After a pipeline run, ask whether something in this skill slowed the run down or was
missing — and offer to improve the skill (the stack table and tool list grow with use).
