# Dimension: change size

Checked by the orchestrator itself in step 3, not by a subagent.

## Limits

Count changed lines (`git diff --shortstat <merge-base>`) **without** generated or
mechanical files: lockfiles (`uv.lock`, `pnpm-lock.yaml`, `package-lock.json`),
generated API clients, snapshots, migrations generated without manual edits, pure
renames/moves, formatter-only changes.

| Change | Limit |
|---|---|
| Mechanical (rename, move, formatting, dependency bump) | no limit |
| Normal feature/fix | ≤ 800 changed lines |
| Complex logic (auth, payments, concurrency, data migrations, state machines) | ≤ 500 changed lines |

## Over the limit

Report one finding (Major; Minor if it is already split into clean commits that can be
reviewed one by one) with a **concrete staging proposal** based on the actual diff:

1. Look at dependencies between the changed parts: what is needed by what (schema →
   migration → service → router → frontend API → UI).
2. Name the **smallest coherent stage that can land first** — compiles, is tested and
   changes no behavior on its own (e.g. "migration + model + service with tests, no
   route yet").
3. List the following stages in order, each with its files.
4. Mention parts that can go out independently (refactorings, renames, dependency bumps)
   as separate MRs.

The review still runs completely — the size finding is advice for the next change, not
a reason to skip the review.
