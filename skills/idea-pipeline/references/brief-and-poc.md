# Stage 1: brief and proof of concept

## The brief — `IDEA.md`

One page, in the project folder, English. It is the single source of truth for the idea
until Stage 2 turns the lasting parts into README and ADRs.

```markdown
# <Working title>

Status: Brief | POC running | Verdict: go / pivot / drop | Published
Date: <YYYY-MM-DD>

## Idea
<One or two sentences: what it does, for whom.>

## Feasibility
Assessment: feasible | feasible with risks | blocker → chosen way around
- Technical: <key findings with source links; verified vs. assumed>
- Building blocks: <libraries, plugins, APIs to build on — link, licence, maturity>
- Constraints: <licences, policies, terms, costs>
- Inspiration: <only if asked — ideas taken from similar work>
- Open for the POC: <what research could not settle>

## Riskiest question
<The one question the POC must answer.> Further feasibility questions, if any:
- <question>

## Success criterion
<What must be visible at the end of the POC to say "go".>

## Stack
- <Choice> — <one-line reason>
- Skills: <skills to load>
- Tools: <MCP servers, CLIs, accounts used>
- Missing: <tools/skills/accounts that are needed but not available, or "none">

## Scope
In: <the minimum the POC builds>
Out: <explicitly not built — auth, deployment, polish, ...>
Shortcuts: <rules from the stack skills deliberately skipped in the POC, with reason>

## Timebox
<e.g. one session / two days>. POC code is throwaway unless Stage 2 keeps it.

## Visibility
Private | Client | Public open source | Undecided

## Results
<Filled after the POC: what worked, what didn't, measurements, screenshots.>

## Verdict
<go / pivot / drop — and why. Next step.>
```

Show the brief and wait for approval before building anything.

## The POC

- **Start with the riskiest question.** Build the part that could fail first. If the
  riskiest part fails, everything else was wasted effort.
- **Run it, don't just write it.** A POC counts only when it has run: a started server
  with a request that works, a playable scene, a built app on a simulator, a rendered
  model. Show the evidence — command output, screenshot, short recording.
- **Measure what the success criterion asks for** (frame rate, latency, accuracy, size)
  instead of describing it.
- **Keep a log in `IDEA.md` → Results** as you go: what was tried, what failed, why.
  Failed attempts are results too.
- **Stuck rule.** After two or three failed attempts at the same problem, stop and
  report what was tried and what is known; the user decides whether to pivot.
- **Synthetic data only** when the idea touches personal or sensitive data.
- **Timebox reached:** stop, fill Results, propose a verdict.

## The verdict

Propose one of three, with reason — the user decides:

- **Go** — the riskiest question is answered positively and the success criterion is
  met. Next: Stage 2 (if the idea should live on) or simply keep using it privately.
- **Pivot** — the idea is still interesting but the approach or scope must change.
  Update the brief (new riskiest question, new stack if needed), get approval, run a new
  POC. Keep the old Results section as history.
- **Drop** — the riskiest question is answered negatively or the effort clearly exceeds
  the value. Keep `IDEA.md` with the reason; it prevents re-trying the same dead end.
