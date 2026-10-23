# Stage 2: harden and publish

Only after a **go** verdict and only when the idea should live on. Every step below that
creates, pushes or publishes something needs its own approval right before it runs —
publishing to a public host is effectively irreversible (forks, caches, indexing).

## 1. Settle the target

Ask, with a recommendation based on the brief:

- **Private** → private repository on the user's own Git server (or a private repo on
  the public host if there is none).
- **Client** → wherever the client's rules say; their licence and hosting rules win.
- **Public open source** → public repository on a public host (e.g. GitHub). Ask
  whether the public repo is the primary one, or a mirror of a private primary on the
  user's own server — that decides where issues, CI and releases live.

Also ask: **keep the POC history or start fresh?** Recommend a fresh history for a public
repo — POC history often contains experiments, local paths and secrets.

## 2. From POC to project

Propose this as a plan (steps, effort, risks) and wait for approval:

1. **Decide what survives.** Keep the parts that proved themselves; rewrite shortcuts
   listed in `IDEA.md` → Shortcuts following the stack skills' conventions.
2. **ADRs** — record the binding decisions from the brief (stack, engine, storage,
   hosting) in `docs/adr/`, Nygard format.
3. **README** — what it is, how to run it, how to develop it, licence. Turn `IDEA.md`
   into README + ADRs; keep `IDEA.md` out of the public repo unless the user wants it.
4. **Tests and CI** — the minimum the stack skill requires, running in CI.
5. **Repository hygiene** — `.gitignore`, `.dockerignore` where relevant, no AI helper
   files committed (agent instruction files, local agent settings), no local paths, no generated junk.

## 3. Public open source — extra checks

Only for public repositories:

- **Licence** — ask; recommend MIT for libraries and tools unless the user has another
  default. Check that every dependency's and asset's licence is compatible, and that
  asset credits are complete.
- **Secrets and personal data** — scan the full tree (and history, if kept) for keys,
  tokens, `.env` files, personal data, client names, internal hostnames.
- **Security review** — run `appsec-review` on the code before it goes public.
- **No AI traces** — commit messages, code comments and files follow the user's rules
  for AI mentions (see `commit-ai-guard` where installed).
- **Community files** — `CONTRIBUTING.md` and `SECURITY.md` only if the project invites
  contributions; a short README section is enough otherwise. Don't add a code of
  conduct, issue templates or badges unasked.
- **Release** — tag and release only when the user asks.

## 4. Create and push

Each of these is its own approval, with the risks named:

1. `git init` / fresh history and the first commit (`commit-messages` format).
2. Creating the remote repository — name, visibility, description.
3. The first push. For a public repo, state plainly that the content becomes public
   immediately and cannot be fully retracted.
4. Optional mirror setup between the user's Git server and the public host.

## Done

Repository exists with the agreed visibility, README and ADRs are in place, CI is green,
and the brief's Status says "Published" with the repository URL.
