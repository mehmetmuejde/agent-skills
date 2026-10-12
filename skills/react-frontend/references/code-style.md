# Code style — naming, files, design system, TypeScript

Conventions that keep the code base greppable and consistent. Where code lives is
`structure.md`; TypeScript compiler and Biome settings are in `SKILL.md`.

## Files and size

- **One component per file, one hook per file.**
- Guideline **~150 lines per component** (at most ~180 for very simple ones). As soon
  as logic can be extracted cleanly, move it into a hook (`use…`) or split the component
  into sub-components (composition).
- Encapsulate logic in hooks wherever it makes a component easier to read: components
  render and handle interaction, hooks fetch, transform and hold the logic.
- Tests and stories sit next to the file (`OrderCard.tsx`, `OrderCard.test.tsx`,
  `OrderCard.stories.tsx`) — no global `__tests__/` folder.

## Naming

- **Folders** (slices, segments, `shared/ui` components): kebab-case —
  `pages/user-profile/`, `features/edit-profile/`, `shared/ui/date-picker/`.
- **Files inside segments** are named by domain, not by kind: `model/user.ts`,
  `api/fetch-profile.ts` — not `model/types.ts`, `api/index-api.ts`.
- **Components**: PascalCase, prefixed with the slice name so they stay recognizable in
  search results and stack traces. Long, descriptive names are fine — the name shows
  where the component belongs:

```
pages/user-profile/ui/
  UserProfilePage.tsx
  UserProfileHeader.tsx
  UserProfileEditButton.tsx
```

- **Hooks**: camelCase with `use` prefix (`useUserProfile`).
- Consistent prefixes separate own code from library code and make slices easy to
  navigate — for people and for coding agents alike: reading one slice should be enough
  to understand that part of the product, and new work mostly becomes new files instead
  of edits to shared ones.

## Props — whole object or single fields

If a component needs half or more of an object's fields, pass the object; don't drill
every field separately.

❌ `<UserCard userId={u.id} userName={u.name} userEmail={u.email} userAvatar={u.avatar} />`
✅ `<UserCard user={u} />`

Single fields only when the component needs one or two of them and should stay
independent of the whole object. Optional props are marked with `?`.

## Design system — primitives vs. own components

```
shared/ui/
  primitives/      # UI-library CLI zone (e.g. shadcn/ui) — never edited by hand
  button/          # own design system, built from primitives
    Button.tsx
    index.ts
  dialog/  data-table/  page-header/  stack/  …
```

- `shared/ui/primitives/` holds what the UI library's CLI generates (its `components.json`
  `ui` alias points there). It is updated only through the CLI and **never edited**.
- The own design system lives next to it, one folder per component with its own
  `index.ts`. It wraps primitives with the project's variants, sizes and tokens.
- **App code imports only the own design system** (`@/shared/ui/button`), never
  `@/shared/ui/primitives/…`. Only `shared/ui/` itself uses the primitives. Enforce it
  with Biome `style/noRestrictedImports` for `@/shared/ui/primitives` and its sub-paths,
  switched off by an override for `src/shared/ui/**` (check the option shape against
  the current Biome docs).
- A component is missing? Build it in the design system from primitives — not ad hoc
  in a page.
- With a UI library that has no primitives layer (Mantine, MUI, …) the same applies to
  its components: use them, don't re-create them.

### Prefer design-system components and props over new markup and CSS

- Use the design-system components for everything they cover instead of hand-styled
  native elements (`<button className="…">`, `<div className="card">`). The design
  system renders the semantic element (`accessibility.md`).
- **Never write new CSS before checking** whether an existing component, variant,
  spacing prop or theme token can already do it. Custom styling only when the library
  demonstrably can't express it.
- Unsure whether a component exists? Check the library docs and types — don't guess.

## Layouts

- **App frame** — AppShell, header with navigation, sidebar, separate layouts for public
  and signed-in areas → `app/layout/`. These know which pages exist and who is signed in.
- **Neutral layout building blocks** — `PageContainer`, `Stack`, `Grid`, `Section` →
  `shared/ui/` as part of the design system. They know nothing about the app.
- Domain pieces inside the frame (user menu with the current user, logout button) come
  from `entities/` or `features/` and are only placed by the AppShell. More cases:
  `fsd/layer-structure.md`, "Where should layouts be placed?".

## TypeScript style

- No `any`; if one is truly unavoidable, a lint suppression with a reason.
- No magic numbers or strings: named constants. Constants don't live inline in
  components or hooks — global ones in `shared/config/`, slice-local ones in the slice's
  `config/` or `model/` segment.
- Fixed value sets are defined once (Zod `z.enum`/literal union or the project's chosen
  construct) and reused — never repeated as loose strings.

## Comments and TODOs

- Comments in English. Document complex components and non-obvious decisions (why, not
  what).
- TODOs use the project's TODO marker (one greppable convention per project).
