# Tooling — versions, hooks, audit

## Node and package manager — pinned

Everyone (local, CI, Docker) uses the same Node and package-manager version.

```sh
# .nvmrc  (committed; read by nvm, fnm and CI setup actions)
24
```

```jsonc
// package.json
{
  "engines": { "node": ">=24 <25" },
  "packageManager": "pnpm@12.10.1"   // or "npm@<version>" — exact version, used by Corepack
}
```

- `.nvmrc` holds the major (or exact) **LTS** version; the Docker build stage uses the
  same major (`node:24-slim`).
- `engines` documents the supported range; set `engine-strict=true` in `.npmrc` so an
  install with the wrong Node fails. `save-exact=true` in the same file pins every added
  dependency to an exact version.
- `packageManager` pins the package manager (npm **or** pnpm — fixed per project, never
  mixed); the lockfile (`package-lock.json` / `pnpm-lock.yaml`) is committed.
- CI installs with the lockfile only: `npm ci` / `pnpm install --frozen-lockfile`.
- Upgrading Node is one change: `.nvmrc`, `engines`, Docker base image, CI.

## Git hooks — pre-commit

Same tool as the backend, so a monorepo has one hook setup. Runs on commit **and** push;
secrets must never reach the repository.

```sh
pre-commit install --hook-type pre-commit --hook-type pre-push
# with uv available: uv tool run pre-commit install …  (no global install required)
```

```yaml
# .pre-commit-config.yaml
default_install_hook_types: [pre-commit, pre-push]
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1                         # pin; update with `pre-commit autoupdate`
    hooks:
      - id: gitleaks                     # staged changes, on commit
        stages: [pre-commit]

  - repo: local
    hooks:
      - id: gitleaks-push                # all commits not yet on any remote, on push
        name: gitleaks (unpushed commits)
        entry: gitleaks git --redact --verbose --log-opts="--branches --not --remotes"
        language: system
        pass_filenames: false
        stages: [pre-push]
      - id: biome
        name: biome check
        entry: npx --no-install biome check --write --no-errors-on-unmatched --files-ignore-unknown=true
        language: system
        types_or: [javascript, jsx, ts, tsx, json, css]
      - id: typecheck
        name: tsc --noEmit
        entry: npx --no-install tsc --noEmit
        language: system
        pass_filenames: false
        types_or: [ts, tsx]
        stages: [pre-push]
      - id: unit-tests
        name: vitest (related)
        entry: npx --no-install vitest related --run
        language: system
        types_or: [ts, tsx]
        stages: [pre-push]
      - id: npm-audit
        name: dependency audit
        entry: npm audit --omit=dev --audit-level=high   # pnpm: pnpm audit --prod --audit-level high
        language: system
        pass_filenames: false
        files: ^(package\.json|package-lock\.json|pnpm-lock\.yaml)$
        stages: [pre-push]
```

- Hooks use the project's own binaries (`npx --no-install` / `pnpm exec`), so the
  versions from `package.json` apply.
- In a monorepo, scope hooks with `files: ^frontend/` and run commands in that folder
  (`entry: bash -c 'cd frontend && …'`).
- A gitleaks false positive goes into `.gitleaks.toml` (allowlist with reason) or a
  `gitleaks:allow` comment — never `--no-verify`.
- Hooks are a convenience, CI is the gate: CI runs gitleaks over the MR's commits,
  `biome ci`, `tsc --noEmit`, Steiger, knip, Vitest with coverage, Storybook tests,
  Playwright, the dependency audit and SAST (e.g. `semgrep`).
- System tools (pre-commit, gitleaks, semgrep) are installed by the user — when one is
  missing, say how to install it instead of installing it yourself.

## Dependency audit

- `npm audit --omit=dev --audit-level=high` / `pnpm audit --prod --audit-level high` in
  CI on every MR and on a schedule; `osv-scanner` as an alternative across ecosystems.
- Accepted risks are documented (ticket, expiry) — no blanket ignores.
- New dependency → check maintenance, size (bundle impact) and whether the stack already
  covers it.
- A leaked secret is rotated immediately — removing the commit is not enough. Remember
  that everything in `VITE_*` is public anyway.
