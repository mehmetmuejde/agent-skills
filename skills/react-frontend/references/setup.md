# Setting up a new React project

Procedure for turning an empty (or nearly empty) directory into a production-ready
React + TypeScript project. Talk to the user in the conversation language; code,
comments and repository content in English. The binding rules come from `SKILL.md`,
`structure.md`, `code-style.md`, `data-and-state.md`, `security.md` and `tooling.md`.

Every step needs the user's approval; installing packages and running generators get
their own, separate approval right before they run.

## Versions — current at setup time, then pinned

- **npm packages**: add them without a version so the package manager resolves the
  latest stable release, and pin exactly (`save-exact=true` in `.npmrc`, or
  `pnpm add -E` / `npm i -E`). Version numbers in this skill's examples reflect the
  time of writing — resolve the current ones instead of copying them.
- **Node**: the current **LTS** major, not the newest odd/"current" release:

```bash
curl -s https://nodejs.org/dist/index.json \
  | python3 -c "import json,sys; print(next(r['version'] for r in json.load(sys.stdin) if r['lts']))"
```

  Use its major in `.nvmrc` and `engines` (`tooling.md`).
- **Package manager**: `npm view pnpm version` (or the npm version) → `packageManager`.
- **Never pre-releases** (`alpha`, `beta`, `rc`, `next`, `canary`).
- If a new **major** of React, Vite, the router, TanStack Query or TypeScript breaks
  something this skill assumes (APIs, config format), say so before writing files —
  don't silently paper over it.
- Report the resolved versions in the plan so the user sees what they get.

## Step 1 — assess

```bash
pwd
ls -la
test -f package.json && head -30 package.json || echo "no package.json"
command -v pnpm && pnpm --version || echo "pnpm not installed"
node --version
test -d .git && echo "git repo present" || echo "no git repo"
```

- A required tool is missing (package manager, gitleaks, semgrep, pre-commit): tell the
  user how to install it — **don't install it yourself**.
- Local Node major older than the current LTS: point it out, don't change it.

## Step 2 — propose a plan, wait for approval

The plan names the resolved versions, the structure and every file to be written.

### Structure — start minimal

```
src/
├── app/                    # providers, router tree, global styles
│   ├── providers/          # QueryClient, theme, i18n providers
│   ├── layout/             # AppShell, header, navigation — the app frame
│   └── router.tsx
├── pages/
│   └── <first-page>/       # one slice per route
│       ├── ui/             # <FirstPage>Page.tsx and its components
│       ├── api/            # the page's request functions and queries
│       ├── model/          # schemas, state, logic without UI
│       └── index.ts        # public API (page component + route definition)
└── shared/
    ├── ui/
    │   ├── primitives/     # UI-library CLI zone — never edited
    │   └── button/ …       # own design system, built from primitives
    ├── api/                # API client (+ generated client, if any)
    ├── lib/                # helpers without business logic
    ├── config/             # env validation, constants
    └── i18n/               # i18n setup + locales
```

`features/` and `entities/` are created only once the extraction rule holds;
`widgets/` is discouraged (`structure.md`, Layers). Every slice exports through
`index.ts`; Steiger checks the rules (`structure.md`).

Project-level folders and files that belong to every setup:

- `docs/adr/` — Architecture Decision Records at the project root, plus one per
  sub-project in a monorepo or multi-repo setup. Short Nygard format (Title, Status,
  Context, Decision, Consequences), files `0001-short-title.md`, written when a binding
  decision is approved; superseded ADRs get a new status, never deleted.
- `.dockerignore` — always present once the project has a Dockerfile (`docker.md`).
- `.scratch/` — if temporary notes are wanted (plans, research, drafts), keep them in a
  `.scratch/` folder at the project root that is excluded through the **global** git
  ignore file (`~/.config/git/ignore`), not the project's `.gitignore`.

### Tooling

| Tool | Purpose |
|---|---|
| npm or pnpm (one per project, `tooling.md`) | package manager |
| Vite | bundler, dev server |
| TypeScript (strict) | type checking |
| Biome | lint + format, incl. a11y and `noRestrictedImports` for primitives |
| knip | unused files, exports and dependencies |
| Steiger + `@feature-sliced/steiger-plugin` | FSD rules |
| pre-commit + gitleaks | hooks on commit and push (`tooling.md`) |
| Vitest + Testing Library + jsdom | unit/component tests |
| MSW | API mocking |
| Storybook, Playwright | stories, E2E (`storybook.md`, `testing.md`) |
| rollup-plugin-visualizer | bundle analysis (`performance.md`) |
| semgrep (CI) | SAST — installed by the user, not via the package manager |

### Files to be written

- `package.json` (devDependencies, scripts incl. `arch: steiger ./src`, `engines`,
  `packageManager`), `.npmrc` (`save-exact=true`, `engine-strict=true`), `.nvmrc`
- `tsconfig.json` (strict, see `SKILL.md`)
- `biome.json` (recommended + a11y, `noNestedComponentDefinitions`, `noReExportAll`,
  `noConsole`, `noRestrictedImports` for `@/shared/ui/primitives` outside `src/shared/ui/`)
- UI-library config (e.g. `components.json` for shadcn/ui with its `ui` alias pointing
  to `@/shared/ui/primitives`)
- `knip.json`, `steiger.config.ts`, `.pre-commit-config.yaml`
- `vite.config.ts` (alias, visualizer, production minify settings — `security.md`),
  Vitest config and test setup (`testing.md`)
- `index.html`, `src/app/main.tsx`
- `src/shared/config/env.ts` (Zod-validated env), `src/shared/api/` (API client with
  CSRF header and central 401 handling — `security.md`)
- `src/app/providers/` (QueryClient defaults — `data-and-state.md`), `src/app/router.tsx`
- the first page slice as a blueprint (UI, query, test, story)

## Step 3 — write the files one step at a time

After the approval, one step at a time; **wait for a new approval after each step**:

1. Directory structure (`.gitkeep` in empty folders that must exist)
2. `package.json` + `.npmrc` + `.nvmrc`
3. `tsconfig.json`
4. `biome.json`
5. `knip.json` + `steiger.config.ts`
6. `vite.config.ts` + Vitest config + test setup
7. `index.html`, `src/app/main.tsx`
8. `src/shared/config/env.ts` + `src/shared/api/` client
9. `src/app/providers/` (TanStack Query defaults)
10. `src/app/router.tsx` + the first page slice as a blueprint

## Step 4 — install (separate approval)

```bash
pnpm install            # or: npm install
pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Step 5 — smoke tests

```bash
pnpm exec biome check .
pnpm exec tsc --noEmit
pnpm exec steiger ./src
pnpm exec knip
pnpm exec vitest run
pnpm dev
```

Report whether everything is green. On failures: report them to the user — don't start
fixing on your own.

## Related

- Container image: `docker.md`
- Rules: `structure.md`, `code-style.md`, `data-and-state.md`, `security.md`,
  `testing.md`, `performance.md`, `tooling.md`
