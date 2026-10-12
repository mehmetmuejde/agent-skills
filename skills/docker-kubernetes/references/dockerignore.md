# .dockerignore

Every image has one. No exceptions, also not for "small" images.

## Why

- **Build context size**: everything not ignored is sent to the builder on every build.
  A stray `node_modules`, `.venv` or `.git` turns a 2 MB context into gigabytes.
- **Cache busting**: `COPY . .` hashes every file in the context. A changed log, coverage
  report or editor file invalidates that layer and everything after it.
- **Secrets leakage**: what is in the context can end up in a layer — `.env`, keys,
  kubeconfigs, `.git` history with old credentials. A deleted file stays readable in the
  lower layer; `docker history` and image extraction expose it.
- **Reproducibility**: a host `.venv` or `node_modules` (other OS/arch) copied into the
  image breaks or silently shadows the locked install.

## Matching rules (differ from `.gitignore`)

- Patterns are matched **from the context root**. `*.pyc` matches only at the root;
  use `**/*.pyc`. `__pycache__` matches only `./__pycache__`; use `**/__pycache__`.
- `**` matches any number of directories. Trailing slashes are ignored (`.venv/` ==
  `.venv`), so a pattern can't be limited to directories.
- `!pattern` re-includes; **the last matching line wins** — put re-excludes after the
  `!` exceptions.
- Lines starting with `#` are comments.
- Excluding `Dockerfile` and `.dockerignore` is fine: the builder still reads them, they
  are just not copyable into the image.
- With several Dockerfiles in one context, use `<name>.Dockerfile.dockerignore` (or
  `Dockerfile.dockerignore`) next to the Dockerfile; it takes precedence over the
  context's `.dockerignore`.

## Allowlist vs. denylist

| | Allowlist (`*` then `!`) | Denylist |
|---|---|---|
| New file in the repo | Excluded until added — safe by default | Included until someone ignores it |
| Secret dropped into the repo by accident | Not in the context | In the context, possibly in a layer |
| Maintenance | Must add every new top-level file/folder the build needs; a missing entry fails the build loudly | Must remember every new junk/secret path; a missing entry fails silently |
| Fits | Stable layouts (backend with `app/`, `migrations/`; frontend with `src/`, `public/`) | Repos with many, changing top-level files |

**Default: allowlist** when the layout is stable. Use the denylist when the build needs
most of the repo; then keep it complete — the full lists below are the baseline.

Verify what is sent: build a throwaway stage that lists the context, or check with
`docker build --no-cache --progress=plain .` and a temporary `RUN find . -maxdepth 2` in
the build stage (remove it again). Building needs a short confirmation first.

## Backend — allowlist (preferred)

```dockerignore
# Exclude everything, then allow only what the image needs
*

!pyproject.toml
!uv.lock
!README.md
!app
!alembic.ini
!migrations

# Re-exclude junk inside the allowed folders
**/__pycache__
**/*.py[cod]
**/.pytest_cache
**/.mypy_cache
**/.ruff_cache
**/.DS_Store
**/*.log
**/.env
**/.env.*
```

- `README.md` only if `pyproject.toml` references it (`readme = "README.md"`) and the
  project is built as a package — otherwise drop the line.
- Add `!scripts` etc. only for folders the runtime or migration Job really uses.

## Backend — denylist (complete)

```dockerignore
# Version control
.git
.gitignore
.gitattributes

# CI, deployment and container files
.github
.gitlab
.gitlab-ci.yml
.gitea
.woodpecker*
.pre-commit-config.yaml
Dockerfile*
*.Dockerfile
.dockerignore
compose*.yaml
compose*.yml
docker-compose*.yaml
docker-compose*.yml
charts
helm
deploy
k8s
gitops

# Python environments, caches, build output
.venv
venv
**/__pycache__
**/*.py[cod]
**/.pytest_cache
**/.mypy_cache
**/.ruff_cache
.tox
.nox
.coverage
.coverage.*
coverage.xml
htmlcov
build
dist
**/*.egg-info

# Tests and documentation (not needed at runtime)
tests
docs
*.md
!README.md

# Secrets and local configuration
.env
.env.*
**/*.pem
**/*.key
**/*.crt
**/*.p12
**/*.pfx
secrets
.secrets
kubeconfig*
*.kubeconfig
**/.netrc
**/.pypirc
**/.npmrc
**/id_rsa*
**/id_ed25519*
**/id_ecdsa*
**/*.agekey

# Local data and logs
pgdata
.data
**/*.sqlite
**/*.sqlite3
**/*.db
**/*.log
logs

# Editors and OS
.idea
.vscode
*.code-workspace
**/*.swp
**/.DS_Store
**/Thumbs.db

# Local tool configuration
**/.claude
**/.cursor
.cursorrules
.windsurfrules
.aider*
.continue
**/CLAUDE.md
**/CLAUDE.local.md
**/AGENTS.md
**/GEMINI.md
**/AGENT.md
.mcp.json
.claudeignore
.cursorignore
**/.windsurf
**/.codex
**/.gemini
**/.agents
.clinerules
**/.roo
.roomodes
**/.kiro
**/.junie
**/.amazonq
**/.augment
**/.opencode
**/.specstory
.aiignore
```

`tests` is excluded because the runtime image doesn't run them; tests run in CI against
the build stage or a dedicated test target, not inside the production image.

## Frontend — allowlist (preferred)

```dockerignore
*

!package.json
!package-lock.json
!pnpm-lock.yaml
!pnpm-workspace.yaml
!.npmrc
!index.html
!vite.config.ts
!react-router.config.ts
!tsconfig*.json
!src
!app
!public
!nginx

# Re-exclude inside allowed folders
**/node_modules
**/*.test.ts
**/*.test.tsx
**/*.spec.ts
**/*.spec.tsx
**/*.stories.tsx
**/*.stories.ts
**/__snapshots__
**/.DS_Store
**/*.log
**/.env
**/.env.*
```

- Keep only the lockfile you use. `.npmrc` only if it holds **no token** — registry
  tokens come in via a build secret (`references/dockerfile.md`).
- `src` for a Vite SPA, `app` for React Router framework mode; drop the other.
- Excluding tests/stories works only if the build doesn't type-check or import them
  (`tsc -b` with a tsconfig that includes them fails) — then re-include or split the
  tsconfig.

## Frontend — denylist (complete)

```dockerignore
# Version control
.git
.gitignore
.gitattributes

# CI, deployment and container files
.github
.gitlab
.gitlab-ci.yml
.gitea
.woodpecker*
.husky
Dockerfile*
*.Dockerfile
.dockerignore
compose*.yaml
compose*.yml
docker-compose*.yaml
docker-compose*.yml
charts
helm
deploy
k8s

# Dependencies and build output (rebuilt inside the image)
**/node_modules
dist
build
.react-router
.vite
.cache
.turbo
.eslintcache
**/*.tsbuildinfo

# Tests, Storybook, reports
coverage
storybook-static
playwright-report
test-results
blob-report
e2e
.storybook
**/__snapshots__

# Documentation
docs
*.md

# Secrets and local configuration
.env
.env.*
**/*.pem
**/*.key
**/*.p12
secrets
kubeconfig*
**/.netrc
**/id_rsa*
**/id_ed25519*
# .npmrc: only re-include (!.npmrc) when it holds no token — tokens come via a build secret

# Logs
**/*.log
npm-debug.log*
pnpm-debug.log*

# Editors and OS
.idea
.vscode
**/*.swp
**/.DS_Store
**/Thumbs.db

# Local tool configuration
**/.claude
**/.cursor
.cursorrules
.windsurfrules
.aider*
.continue
**/CLAUDE.md
**/CLAUDE.local.md
**/AGENTS.md
**/GEMINI.md
**/AGENT.md
.mcp.json
.claudeignore
.cursorignore
**/.windsurf
**/.codex
**/.gemini
**/.agents
.clinerules
**/.roo
.roomodes
**/.kiro
**/.junie
**/.amazonq
**/.augment
**/.opencode
**/.specstory
.aiignore
```

- `.env*` is excluded on purpose: environment-specific values come from the runtime
  config, not from the build. If the build needs a committed, non-secret
  `.env.production` with defaults, re-include exactly that file (`!.env.production`) —
  never `.env.local`.
- `dist`/`build` are excluded because the image builds them itself. Only a deliberate
  "copy prebuilt artifacts" Dockerfile re-includes them.

## Review checklist

- [ ] Every Dockerfile has a `.dockerignore` (or `<name>.Dockerfile.dockerignore`).
- [ ] `.git`, `.env*`, keys, credential files (`.netrc`, `.pypirc`, `.npmrc` with a
      token, SSH keys, kubeconfigs), `node_modules`/`.venv`, caches and reports are
      excluded. The `.dockerignore` is defence in depth — credentials still never go
      through `COPY`, `ARG` or `ENV`.
- [ ] Nested patterns use `**/`.
- [ ] Re-excludes come after `!` exceptions.
- [ ] No `COPY . .` in a Dockerfile whose context has no `.dockerignore`.
