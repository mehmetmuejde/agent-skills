# FSD v2.1 rulebook

The upstream Feature-Sliced Design v2.1 rules (fsd.how, official FSD agent skill
`feature-sliced/skills`, MIT), condensed. The other files in `fsd/` refer to the numbered
sections and rules here. Strictness can be adjusted to project scale and team context.

**How this relates to `../structure.md`:** `structure.md` holds this skill's binding
project conventions (layer table, `index.ts` rules, Steiger/Biome setup, routing
wiring). This file adds the upstream reasoning and decision procedure. Where the two
differ, `structure.md` wins; each difference is marked **This skill:** below.

How to use: for a placement decision start with the decision tree (Section 2), use the
placement table (Section 3) as a quick reference, check violations against Section 4,
resolve same-layer cross-imports with Section 7. Load the other `fsd/` files only when
their situation applies (list in `../structure.md`).

## 1. Core philosophy

Principle: **"Start simple, extract when needed."**

### The extraction rule

Place code in `pages/` first. Duplication across pages is acceptable and does not by
itself require extraction. Extract to a lower layer only when **all three** hold:

1. The same code is used in multiple places **right now**, not hypothetically.
2. It has a reason to change that is independent of any one consumer.
3. The boundary has a focused responsibility.

### Layers

Not all layers are required — most projects start with `app/`, `pages/`, `shared/`. Add
`features/` and `entities/` only when they provide clear value; no empty layer folders
"just in case".

```text
app/       → app initialization, providers, routing
pages/     → route-level composition, owns its own logic
widgets/   → reusable UI blocks
features/  → reusable user interactions (extraction rule)
entities/  → reusable business domain models (extraction rule)
shared/    → infrastructure without business logic (UI kit, utils, API client)
```

`processes/` is deprecated in v2.1 (migration: `migration-guide.md`).

**Widgets.** The upstream layer reference **discourages** actively adopting `widgets/`:
UI blocks usually carry data fetching, state and event handling, so the boundary to
`features/` blurs. Not creating a widget means routing the block by responsibility: a
screen-specific composition stays in `pages`, a reused action with its UI goes to
`features`, context-free UI to `shared`, an app-wide layout to `app`. Discouraged is
not deprecated — an existing widgets layer stays valid (`layer-structure.md`).

### The import rule

A module imports only from layers strictly below it. Cross-imports between slices of the
same layer are forbidden, with the narrow exceptions in Section 7.

```ts
// Allowed
import { Button } from '@/shared/ui/button' // features → shared
import { useUser } from '@/entities/user'    // pages → entities

// Violation
import { loginUser } from '@/features/auth'     // entities → features (upward)
import { likePost } from '@/features/like-post' // features → features (same layer)
```

## 2. Decision framework

**Step 1 — where is the code used?**
- Only one page → keep it in that `pages/` slice.
- 2+ pages but the duplication is manageable → separate copies per page are valid.
- An entity or feature with a single consumer → keep it at the consumer (Steiger:
  `insignificant-slice`).

**Step 2 — reusable infrastructure without business logic?** Shared allows no business
logic, but business-*themed* code is fine (company logo, page layout), and so is UI logic
(autocomplete, search bar). Exchanging data with the backend and CRUD boilerplate are not
business logic. Business logic is a rule the product enforces on its own data (applying a
discount to an order). If the code fits no exclusion and still doesn't clearly enforce a
product rule, go back to Step 1 and place it by usage.
- UI components → `shared/ui/` · utilities → `shared/lib/`
- API client, route constants → `shared/api/` or `shared/config/`
- Session handling → `shared/auth/` (no tokens in browser storage — `../security.md`)
- CRUD once several slices call it → `shared/api/` (a single caller keeps it, Step 1)

**Step 3 — a complete user action that several consumers share, with a focused
responsibility and its own reason to change?** Yes → `features/`. Uncertain, single use
or speculative → keep it in the page.

**Step 4 — a business domain model that several consumers share, with a focused
responsibility and its own reason to change?** Yes → `entities/`. Otherwise → page.

**Step 5 — app-wide configuration?** Global providers, router, theme → `app/`.

**Golden rule: when in doubt, keep it in `pages/`.**

## 3. Quick placement table

| Scenario | Single use | Confirmed multi-use |
|---|---|---|
| User profile form | `pages/profile/ui/ProfileForm.tsx` | `features/profile-form/` |
| Product card | `pages/products/ui/ProductCard.tsx` | `entities/product/ui/` if the entity owns it |
| API request (read or CRUD) | `pages/product-detail/api/fetch-product.ts` | `shared/api/` (no domain rules) |
| Session state | `shared/auth/` | `shared/auth/` |
| Login form | `pages/login/ui/LoginForm.tsx` | `features/auth/` |
| Generic card layout | | `shared/ui/card/` |
| Modal manager | | `shared/ui/modal-manager/` |
| Modal content | `pages/<page>/ui/SomeModal.tsx` | |
| Date formatting | | `shared/lib/format-date/` |

"Confirmed multi-use" means the extraction rule holds, not that a second consumer
appeared: two similar copies that keep drifting apart stay in their pages
(`growth-walkthrough.md`, Snapshot 1). Entity UI carries the Section 6 caution even when
the rule holds.

## 4. Architectural rules (MUST)

Breaking one must be an intentional, documented decision (code comment or ADR).

**4-1. Import only from lower layers.** `app → pages → widgets → features → entities →
shared`. No upward imports, no same-layer cross-imports except through the other slice's
public API as a last resort (Section 7, Strategy D).

**4-2. Public API.** Every slice exports through `index.ts`; outside consumers never
import internal files. Environment-specific entry points (`index.server.ts`) only when
one index can't keep a runtime boundary (`framework-integration.md`).
Upstream for Shared: one index per segment (`shared/ui/index.ts`), or — where that hurts
bundling — one per component/library folder; the folder is then the boundary and reaching
past it (`@/shared/ui/button/Button.tsx`) is still a violation.
**This skill:** `shared/ui` and `shared/lib` always have one index per component/library,
never one segment-wide index (`structure.md`).

**4-3. No cross-imports between slices on the same layer.** Resolve with Section 7;
never reach into another slice's internals.

**4-4. Domain-based file naming (no desegmentation).** Name files after the domain or
concern they serve, not their technical role: `model/user.ts`, `model/order.ts`,
`api/fetch-profile.ts` — not `model/types.ts`, `model/utils.ts`, `api/endpoints.ts` with
every domain in one file. A segment with a single concern may use the slice name
(`features/auth/model/auth.ts`).

**4-5. No business logic in `shared/`.** Business calculations, domain rules and
workflows belong to whoever owns the rule — the page while one page owns it
(`pages/profile/model/reputation.ts`), an entity once that boundary is earned
(`entities/user/model/reputation.ts`). Shared **may** hold application-aware code: route
constants, API endpoints, branding assets, transport types (`ProductDTO`).

## 5. Recommendations (SHOULD)

**5-1. Pages first.** What stays in pages: large single-page UI blocks; page-specific
forms, validation, data fetching, state, business logic and API integrations; code that
looks reusable but is simpler to keep local. Evolution: start with everything in
`pages/profile/`; extract the model to `entities/user/` when a second page consumes it
*and* the extraction rule holds. A response type several pages read stays in
`shared/api`.

**5-2. Be conservative with entities.** Almost every layer can import them, so changes
propagate widely.
1. Start without entities — `shared` + `pages` + `app` is valid FSD; thin clients rarely
   need entities.
2. Don't split slices prematurely.
3. Business logic doesn't automatically require an entity — types in `shared/api` and
   logic in the current slice's `model/` may be enough.
4. CRUD is infrastructure: with its consumer while there is one, in `shared/api/` once
   several slices call it.
5. Auth/session data goes to `shared/auth/` or `shared/api/`, not a `user` entity.
Details: `excessive-entities.md`.

**5-3. Start with minimal layers.** `app/`, `pages/`, `shared/` is a complete project;
add `features/`/`entities/` only for a real use case.

**5-4. Validate with Steiger.** Key rules: `insignificant-slice` (a slice with zero or
one reference — merge it into its consumer; pages and slices used only from `app/` may
have one reference) and `excessive-slicing` (too many slices in one layer — merge or
group). Install and run as in `../structure.md` (`steiger` +
`@feature-sliced/steiger-plugin`, `steiger ./src`).

## 6. Anti-patterns (AVOID)

- Entities created prematurely; single-use code extracted.
- CRUD in entities — plain CRUD is `shared/api/`; an operation with business rules goes
  to whoever owns the rule (entity, feature or the page running the workflow).
- A `user` entity just for auth data.
- `@x` abuse — it is a compromise for the entities layer only, when merging boundaries
  is impossible. Features and widgets use strategies A–D.
- Technical-role file names (Rule 4-4).
- Careless entity UI — it tempts cross-imports; import entity UI only from higher layers
  (features, pages, app), never from other entities.
- God slices — split `user-management/` into `auth/`, `profile-edit/`,
  `password-reset/`.
- A top-level `assets/` segment — assets live next to their code; global styles and
  fonts go to `app/` (`asset-handling.md`).

## 7. Cross-import resolution

Cross-imports are a code smell, not an absolute prohibition.

- **Entities**: usually caused by splitting entities too finely → merge boundaries
  first. `@x` is a last resort, documented, minimal.
- **Features/widgets**, in preferred order:
  - **A — slice merge**: two slices always change together → merge.
  - **B — push to entities**: a shared domain responsibility moves to the entity that
    owns it; UI stays in the feature.
  - **C — compose from an upper layer (IoC)**: the page or app imports both and connects
    them via render props, slots or DI.
  - **D — public API access**: when reuse is genuinely unavoidable, only through the
    slice's `index.ts`; never into `model/`, `store/` or internal files.
- Strictness depends on context: early-stage products may accept some cross-imports for
  speed; long-lived or regulated systems benefit from strict boundaries. A deliberate
  cross-import gets a comment explaining why the other strategies don't apply.

Code for each strategy: `cross-import-patterns.md`.

## 8. Segments and structure

- Standard segments: `ui`, `model`, `api`, `lib`, `config` (table in `../structure.md`).
  Custom segments are allowed when named by purpose (`routes`, `i18n`, `auth`).
- `app` and `shared` have no slices, only segments, which may import each other.
- `pages`, `widgets`, `features`, `entities`: slices first, segments inside.
- **Slice groups** (optional): a folder grouping related slices on one layer for
  navigation only — no segments, no `index.ts`, no shared code; isolation rules stay
  (`layer-structure.md`).

## 9. Shared layer

Infrastructure without business logic, organized by segments: `ui/` (UI kit), `lib/`
(utilities), `api/` (API client, route constants, CRUD helpers, base types), `auth/`
(session handling), `config/` (environment, app settings). No `assets/` segment —
assets live with the code that uses them (`asset-handling.md`). Shared must never hold
the business rules an entity or feature owns, nor import from those layers.
