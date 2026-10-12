# Dimension: design and reuse

Goal: keep the codebase coherent — no second solution for a solved problem, boundaries
respected, code that the next person can change safely and read without stumbling.

## Reuse before building new — the most important check

For **every** new component, hook, service function, helper, type, schema, constant or
dependency in the diff, search the project for an existing equivalent:

```sh
rg -n "def <similar_name>|function <similarName>|const <similarName>" <worktree>
rg -n "<distinctive literal or regex from the new code>" <worktree>
rg -il "<concept: pagination|debounce|formatDate|money|slugify>" <worktree>/src <worktree>/app
```

- Equivalent exists → finding with the path of the existing one and what to use
  instead.
- Nearly equivalent → suggest extending the existing one with a parameter or a small
  generalisation instead of a parallel copy — but only if that doesn't bend the existing
  thing out of shape.
- New third-party dependency for something the stack already does (date handling,
  HTTP, validation, state) → finding.
- The reverse is also a finding: an abstraction with a single caller is not an
  improvement. Don't push for shared code just to claim reuse.

Commonly built twice:

- **Backend**: date handling, mapping errors to HTTP codes, pagination schemas, filter
  logic, loading the current user, mail senders, token helpers.
- **Frontend**: buttons, dialogs, table wrappers, inputs next to an existing primitive
  in `shared/ui/` or the project's design system; formatting helpers (money, dates);
  API call wrappers next to the shared client.

## Duplicates

Identical or nearly identical logic in several places — inside the change **and**
between the change and existing code, across files, even when names and variables
differ. Copy-paste with small variations is the most common case and the most dangerous,
because later fixes land in only one place. Repeated mapping/validation code, the same
query in several services → extract or reuse; one finding listing all locations.

## Architecture and boundaries

- **Backend**: feature slices respected — routers HTTP-only, business logic in services
  without FastAPI imports, other features only via their public API, no direct access to
  another feature's tables (see `fastapi-backend` → `references/structure.md`).
- **Frontend**: Feature-Sliced Design layers — imports only downward, no cross-imports
  between slices on the same layer, imports through the slice's public `index.ts` (see
  `react-frontend` → `references/structure.md`).
- Server data in TanStack Query, client state in Zustand, URL state in search params —
  not mixed.
- Configuration in settings/env, not hard-coded.

## Consistency

Does the change fit the rest of the project — naming, folder structure, error handling,
logging, test layout? A solution that is clean on its own but deviates from how the
project already does it is a finding: name the existing pattern and where it lives.

## Changeability

- Functions/components doing several things; deep nesting; long parameter lists;
  boolean flags that switch behavior → split.
- Names that don't say what the thing does, or say something else (least astonishment):
  hidden side effects in getters, `validate*` that also saves.
- Dead code, commented-out code, unused exports, leftover debug output.
- Comments explaining *what* instead of *why*; TODOs without owner/ticket.

## Language — typos and translations

- Typos in identifiers, comments, log messages and user-facing texts (UI copy, error
  messages, emails, API error details).
- Multilingual projects: new texts added to **all** language files? Keys used in code
  that exist in no language file? Texts hard-coded that should go through the
  translation layer (frontend copy, backend messages shown to users)?
- Terminology consistent with the existing texts (the same thing isn't called
  "customer" here and "client" there).

## Signs of unreviewed generated code

Watch for code that looks plausible but doesn't fit the project:

- comments that restate what the line already says,
- wrappers and helpers without a purpose of their own, wrappers around one call,
- invented APIs or options of a library, or names that differ from the real ones (check
  the installed version),
- generic names such as `data`, `result`, `handleThing`, `utils`,
- breaks in style with the surrounding file (naming, error handling, imports),
- defensive checks for states that cannot occur while the real edge case is unhandled,
- over-abstraction (factory/strategy for one implementation),
- tests that only cover the happy path, mirror the implementation instead of the
  behavior, or assert nothing.

Name such places without speculating about where they came from — the code is what
counts.

## Report

Severity: boundary violation or parallel solution to an existing one = Major; naming,
small duplication, typo or missing translation in user-facing text = Minor; typos in
comments/identifiers, taste = Nit (only if clearly better). Schema:
`../output-format.md`.
