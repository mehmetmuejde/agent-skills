---
name: grill-me
description: A relentless interview to sharpen a plan, decision or design until nothing is left silently assumed. Run with /grill-me.
disable-model-invocation: true
license: MIT (see LICENSE)
---

# Grill me

Interview the user relentlessly until you reach a shared understanding of the plan,
decision or design they name. Map it as a **design tree**: every decision branches into
the decisions that hang off it.

## Rounds

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are
already settled — the questions you can ask *now* without guessing at answers you haven't
heard yet. Ask the whole frontier in one round, each question with your recommended
answer, then wait for the user's answers before the next round.

If the agent has a structured question tool, use it: the recommended option first and
marked as recommended. If the tool limits how many questions fit in one call, ask the
questions with the most downstream decisions first; the rest follow in the next call of
the same round. Without such a tool, number the questions and word each one so "yes"
accepts your recommended answer:

```
**Q1 - <question title>**: <question body, may include multiple choices>

Recommended: <your recommended answer>

---

**Q2 - <question title>**: <question body>

Recommended: <your recommended answer>
```

Each round reshapes the tree: settled decisions push the frontier outward and unblock
questions that depended on them. Recompute the frontier and ask the next round. A
question whose answer depends on another question still open belongs to a *later* round.

## Facts vs. decisions

Finding **facts** is your job, never the user's. When a question needs a fact from the
environment (code, files, tools, docs), look it up yourself or dispatch a subagent —
don't ask the user for anything you could find out. Only the questions that depend on
that fact wait for it; ask the rest of the frontier now. The **decisions** are the
user's: put each one to them and wait.

## Done

The session is done when the frontier is empty: every branch visited, nothing left
silently assumed. Summarise the settled decisions briefly. Do not act on them until the
user confirms the shared understanding.

## Sources

Adapted from the `grill-me` and `grilling` skills of
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT, Copyright (c) 2026 Matt
Pocock — see [LICENSE](LICENSE)).
