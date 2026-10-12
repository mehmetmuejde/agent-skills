# Dimension: frontend conventions

Runs when React/TypeScript files changed and are in scope. The subagent gets the full
path of the `react-frontend` skill's `SKILL.md`, reads it and the references that match
the changed code (hooks-and-rendering, performance, data-and-state, forms,
accessibility, testing, storybook, structure), and checks the diff against those rules.
When UI code changed — markup, styling, forms, animation, copy — it also reads
`../web-interface-guidelines.md` and checks against it.

## Focus

- **Components**: newly built button, dialog, table wrapper or input next to an existing
  primitive in `shared/ui/` or the design system (report under design and reuse if that
  dimension hasn't); components over roughly 150 lines — do they do more than one
  thing?; props as a long list of single fields where an object belongs, or the reverse;
  no components defined inside components; vendored or generated UI primitives edited by
  hand or imported directly where the project wraps them in its own design system.
- **Hooks and rendering**: derived state computed in render instead of effects; logic in
  event handlers instead of effects; functional `setState`; effect dependencies narrow
  and complete (stale closures, needless runs); cleanup for subscriptions, timers,
  listeners and aborted requests; hook names start with `use` and follow the project's
  file/export conventions; ternary instead of `&&` with numbers; no mutation
  (`toSorted()` etc.); lists with a stable `key` (no index when order can change).
- **Data and state**: server data only via TanStack Query (query key factory,
  invalidation after mutations), query hooks in the owning slice, HTTP only through the
  shared API client (`shared/api`); Zustand only for client state with narrow selectors
  — no global store for something only one component needs; URL state (filters, tabs,
  pages) in typed search params; persisted state versioned; prop drilling across more
  than two levels; loading and error states for every query.
- **Performance**: request waterfalls (sequential awaits, fetch in child after parent),
  missing preloading on intent, heavy imports or barrel imports in shared indexes,
  missing lazy routes and suspense boundaries, long lists without virtualization; new
  objects/functions created in render and passed to memoized children; memoization only
  where measured.
- **Accessibility — always** (rules from the `frontend-accessibility` skill; give the
  subagent the full path of its `SKILL.md` too): semantic elements (`button`, not `div`
  with `onClick`), accessible names/labels, meaningful `alt`, keyboard operation,
  visible focus (no `outline: none` without replacement), focus management in
  dialogs/route changes (trap, return, Escape), error messages linked to fields,
  contrast, reduced motion. An inaccessible interactive element is a Major.
- **Forms**: schema validation at the boundary (Zod / TanStack Form), not only in the
  UI; accessible errors; error messages without technical details; disabled/pending
  states.
- **Structure**: Feature-Sliced Design layers and public APIs, no `export *`; pages
  first — code moved to `features/` or `entities/` before the extraction rule holds
  (used in several places now, own reason to change, focused responsibility) is a
  finding; a new `widgets/` slice for a block that isn't reused across several pages is
  a finding (existing widgets are not); new plain CRUD/resource requests or query
  factories in `entities/<x>/api` instead of `shared/api` are a finding.
- **Tooling**: run only if `node_modules` exists — `npx --no-install biome check`,
  `npx --no-install steiger ./src`; TypeScript without `any`/`@ts-ignore` without
  reason.

Hard-coded or one-language UI texts are checked by the design-and-reuse dimension
(language section). Security topics (XSS, token storage, open redirects) belong to the
security dimension — report them here only if the security dimension doesn't run.

## Web Interface Guidelines

`../web-interface-guidelines.md` (Vercel, MIT) is a rule list for UI details: forms,
focus states, animation, typography, content handling, images, navigation, touch,
theming, locale, hydration, copy. Where it conflicts with the project's design system
or the `react-frontend` / `frontend-accessibility` skills, the project rules win. Use
its "Anti-patterns" list as a quick scan of the diff.

## Report

Cite the rule (reference file + section, Vercel rule id if applicable) in `refs`.
Severity: a11y barrier or performance problem with user impact = Major (from the
guidelines: missing labels, keyboard access, focus states); convention = Minor/Nit;
pure typography and copy details from the guidelines = Nit. Schema:
`../output-format.md`.
