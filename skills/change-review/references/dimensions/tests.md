# Dimension: tests

Goal: every behavior change is covered by a test that would fail without the change.

## Procedure

1. **List the behavior changes** of the diff: new features, changed rules, fixed bugs,
   new error cases, new UI states. This list is part of the result.
2. For each item, find the test that covers it (`rg` in `tests/`, `*.test.ts(x)`,
   `*.spec.ts`, `*.stories.tsx`). No test → finding.
3. Check the quality of the tests that exist.

## Backend (pytest)

- Every changed endpoint: happy path + validation (422) + auth (401) + **other user's
  object (404)** + missing permission (403) where applicable.
- Every fixed bug: a regression test that reproduces it.
- Business rules tested at service level, not only through HTTP.
- Database behavior against real PostgreSQL (no SQLite stand-in); RLS changes have an
  isolation test.
- Migrations: are they exercised by the test setup (`alembic upgrade head`)?
- Coverage: CI threshold 80 % lines and branches — does the change lower it? Run
  `uv run --no-sync pytest --cov` only if the environment already exists; otherwise
  judge from the code and say so.

## Frontend (Vitest, Testing Library, Playwright, Storybook)

- Logic (hooks, utils, model) → unit tests; components → component tests with role-based
  queries (`getByRole`), user-event interactions, assertions on what the user sees.
- New or changed **shared UI component** → Storybook story for every state (default,
  loading, empty, error, disabled, long content); desktop viewport by default, mobile
  only if the project requires it.
- Critical user flows touched (login, checkout, forms that save data) → Playwright E2E
  test updated or added.
- Accessibility: a11y checks (Storybook addon-a11y, axe in Playwright) pass for new UI.
- Visual changes → visual regression baselines updated deliberately, not blindly.
- Coverage threshold 80 % lines and branches.

## Test quality

- Tests assert behavior, not implementation details (no testing of private functions,
  internal state, CSS class names).
- No test that passes without the change (assertion missing, mocked away the thing under
  test, `expect` inside a callback that never runs).
- No fixed sleeps/waits; time and randomness controlled.
- No test-only code paths in production code; use existing test helpers/fixtures
  instead of new copies.
- Snapshot tests only where targeted and small — no giant snapshots that get updated
  without reading.
- Flaky patterns: order dependence, shared mutable fixtures, real network.

## Report

Missing test for changed behavior = Major (Blocker if the change is in auth, payments or
data migration). Weak test = Minor. Include the behavior list in the finding or as
"Open questions" if unsure. Schema: `../output-format.md`.
