# Dimension: correctness

Goal: find everything that makes the code behave differently from what the MR/PR says it
should do. Read the description first, then the changed code **and** its callers and
callees. Don't stop after the first finding — go through every changed function.

## Check

**Logic**
- Does the change do what the description/ticket says — completely? Missing cases?
- Conditions: inverted, off-by-one, `<` vs `<=`, wrong operator precedence, `and`/`or`
  mixed up, truthiness traps (`0`, `""`, `[]` treated as "missing").
- Null/None/undefined paths: optional values used without a check; `.first()` /
  `scalar()` returning `None`; optional chaining hiding a real error.
- Edge cases: empty lists, one element, very large input, duplicates, unicode,
  time zones, DST, leap years, money in floats.
- State machines: invalid transitions possible? Status set before the action succeeded?

**Errors**
- Exceptions swallowed (`except: pass`, empty `catch`, `.catch(() => {})`) or turned into
  success.
- Fail-open: on error the operation continues as if validation/authorization passed.
- Error paths leave half-written state (missing transaction, no rollback, file written
  but DB not).
- Retries without limit or backoff; retries of non-idempotent operations.

**Concurrency and async**
- Check-then-act races (stock, balances, unique "active" records) without lock,
  constraint or atomic update.
- Blocking calls inside `async def` (sync DB, `requests`, `time.sleep`, file I/O).
- Missing `await`; fire-and-forget tasks without error handling.
- React: stale closures, effects racing (no abort/ignore on unmount or param change),
  state updates after unmount, `setState` based on stale value instead of functional
  update.

**Data**
- Migrations: does the migration match the model? Default values for existing rows?
  Nullable → non-nullable without backfill?
- Serialization: field renamed in one place only; date/decimal formats; enum values.
- Pagination/sorting stable? Total counts consistent with filters?

**Resources**
- Unclosed files, sessions, clients; clients created per request; missing timeouts.
- Unbounded loops/recursion, N+1 queries in loops, loading whole tables into memory.

## Report

Every finding with a concrete scenario: input/state → wrong result. Severity:
wrong result on a normal path or data loss = Blocker; edge case = Major.
Schema: `../output-format.md`.
