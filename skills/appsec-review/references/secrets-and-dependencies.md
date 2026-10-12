# Secrets scan and dependency audit

Both procedures are read-only. Scanners run **only if already installed** — never install
a tool, never run `uvx`/`npx`/`pipx run` to fetch one, never run a command with `--fix`.
If nothing suitable is available, say so and ask the user how to proceed.

Check availability first:

```bash
command -v gitleaks trufflehog detect-secrets osv-scanner pip-audit pnpm npm
```

---

## Part A — Secrets scan

Runs in every review (step 2 of the workflow), on the reviewed files/diff; on a
whole-codebase review also over the git history.

### A1. Scanner (if installed)

| Tool | Current files | Git history | Notes |
|---|---|---|---|
| gitleaks ≥ 8.19 | `gitleaks dir <path> --redact -v --no-banner` | `gitleaks git <repo> --redact -v --no-banner` | Older versions: `gitleaks detect --no-git --source <path>` / `gitleaks detect --source <repo>`. Branch only: `--log-opts="origin/main..HEAD"` |
| trufflehog | `trufflehog filesystem <path> --no-verification` | `trufflehog git file://<repo> --no-verification` | **Always `--no-verification`** — verification sends the found credential to the provider. Verify only with explicit approval. |
| detect-secrets | `detect-secrets scan <path> --all-files` | — | Baseline-aware |

Don't write report files into the repository; read the output from stdout (or write to
the session's scratch/temp directory).

### A2. Pattern search (no scanner, or in addition)

```bash
rg -n --hidden -g '!.git' -g '!node_modules' -g '!*.lock' -e '<pattern>'
```

`\|` in the table is Markdown escaping — use a plain `|` in the regex.

| Pattern | Secret |
|---|---|
| `AKIA[0-9A-Z]{16}` / `ASIA[0-9A-Z]{16}` | AWS access key id |
| `sk-(proj-)?[A-Za-z0-9_-]{20,}` | OpenAI API key |
| `sk-ant-[A-Za-z0-9_-]{20,}` | Anthropic API key |
| `AIza[0-9A-Za-z_-]{35}` | Google API key |
| `gh[pousr]_[A-Za-z0-9]{36,}` / `github_pat_[A-Za-z0-9_]{22,}` | GitHub tokens |
| `glpat-[A-Za-z0-9_-]{20,}` | GitLab personal access token |
| `xox[abposr]-[A-Za-z0-9-]{10,}` | Slack token |
| `(sk\|rk)_live_[0-9A-Za-z]{20,}` | Stripe live key |
| `SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}` | SendGrid key |
| `-----BEGIN ([A-Z]+ )?PRIVATE KEY-----` | Private key |
| `eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.` | JWT (may contain or be a credential) |
| `[a-z+]+://[^/\s:@]+:[^/\s@]+@` | Credentials in a connection string / URL |
| `AccountKey=[A-Za-z0-9+/=]{40,}` | Azure storage key |
| `(?i)(password\|passwd\|secret\|api_?key\|token\|client_secret)\s*[:=]\s*["'][^"'\s]{8,}["']` | Generic assignment |

High-risk files: `.env*` (except `.env.example` with placeholders), `docker-compose*.yml`
(`environment:`), `*.tfvars`, `kubeconfig`, `credentials*.json`, `service-account*.json`,
`.npmrc`, `.pypirc`, `pip.conf`, `uv.toml` (index credentials), CI files
(`.github/workflows/*`, `.gitlab-ci.yml`), `settings.py`/`config.py` defaults, MCP client
configs (`env` blocks), notebooks (`*.ipynb` outputs), test fixtures copied from
production.

### A3. Triage — for each hit

1. **Real?** Drop placeholders (`changeme`, `xxx`, `<token>`, `your-key-here`), documented
   examples, test values that are obviously fake. Keep anything that looks like a real
   key format.
2. **Active and where?** Production or development credential? Was it rotated (replaced
   in a later commit)? Is the file meant to be ignored (`.gitignore`) but tracked?
3. **Blast radius**: what service, which permissions, which data; how long exposed
   (`git log -S '<prefix>' --oneline` with a non-secret prefix only).

### A4. Reporting rules

- **Never reproduce a secret.** Redact to type plus at most 4 leading characters:
  `AKIA****`, `sk-ant-****`. Applies to the report, logs, tool calls and commit messages.
- Don't send a found secret to any external service (no validity checks against the
  provider) without explicit approval.
- Severity: live production secret with broad rights → Critical; production secret with
  narrow rights or live third-party key with cost exposure → High; development/test
  credential reachable from outside → Medium; local-only dev default → Low; revoked → Info.
- CWE-798 (hard-coded credentials), CWE-312/CWE-532 (cleartext in files/logs); ASVS
  13.3.1; tag Boundary Control.

### A5. Remediation to recommend (in this order)

1. **Rotate/revoke at the provider first** — a secret that was ever committed is
   compromised; deleting it from the code doesn't help (clones, forks, CI caches).
2. Check the provider's audit logs for use since the commit date.
3. Move the secret to the environment/secret store; reference via settings.
4. Optional history rewrite (`git filter-repo`) — a git action that needs its own
   approval; never part of the review.

### A6. Preventive controls (report presence as "Confirmed controls" or as a Low/Info gap)

- `.gitignore` covers `.env`, keys, local configs.
- Pre-commit secret scanning (e.g. gitleaks hook) and a CI scan step.
- `.env.example` with placeholders; settings fail on missing secrets instead of falling
  back to defaults.

---

## Part B — Dependency audit (SCA)

Runs on request, or when the scope changes a manifest or lockfile: `pyproject.toml`,
`uv.lock`, `requirements*.txt`, `package.json`, `pnpm-lock.yaml`, `package-lock.json`,
Dockerfile base images.

### B1. Scanner (if installed), in order of preference

| Tool | Command | Notes |
|---|---|---|
| osv-scanner | v2: `osv-scanner scan source -r .` · v1: `osv-scanner -r .` | Reads `uv.lock`, `pnpm-lock.yaml`, `package-lock.json` directly; queries osv.dev with package names/versions |
| pip-audit | `uv run --no-sync pip-audit` | Only if pip-audit is already in the project environment. **`--no-sync`** — a plain `uv run` syncs (installs) the environment. Audits the installed env, which may differ from `uv.lock` |
| pnpm | `pnpm audit --json` (`--prod` for runtime deps only) | Never `pnpm audit --fix` |
| npm | `npm audit --json` | Needs `package-lock.json`; never `npm audit fix` |

No scanner available → stop this part, tell the user which scanners would work for the
detected ecosystems, and ask. Fallback only with the user's consent: for a diff that adds
or bumps a handful of packages, look them up manually on <https://osv.dev> or the GitHub
Advisory Database.

### B2. Analyse each vulnerability

1. **Reachability** — is the vulnerable package/function imported and called on a path
   that receives untrusted input? Who pulls it in (read-only:
   `uv tree --frozen --invert --package <pkg>`, `pnpm why <pkg>`)?
2. **Context** — runtime vs dev/build-only dependency; server vs browser; exposure of the
   affected feature.
3. **Fix** — patched version available? Patch/minor vs major bump? Direct or transitive
   (transitive: `pnpm.overrides`, uv `override-dependencies`/`constraint-dependencies`)?

Severity: start from the advisory's CVSS; not reachable → at most Low (still listed);
dev-only tooling → one level lower; a **malicious package** (malware advisory, `MAL-`
ids) → Critical regardless of reachability.

### B3. Health flags (beyond CVEs)

| Flag | What to look for |
|---|---|
| Unmaintained | No release for ≥ 2 years, archived repo, deprecated on the registry (e.g. `python-jose`, `passlib`, `request`) |
| Typosquatting | Name close to a popular package, very new, few downloads, unexpected maintainer |
| Dependency confusion | Private package names resolvable from the public registry; `--extra-index-url`; uv `index-strategy = "unsafe-best-match"`; `.npmrc` without scoped registry [15.2.4] |
| Install scripts | New dependency with `postinstall`/build scripts |
| License | Missing license or license incompatible with the project (copyleft in proprietary code) — a decision for the user, not a vulnerability |
| Pinning | Lockfile missing or not committed; CI installs without `--frozen`/`--frozen-lockfile`/`npm ci`; Docker base images on `latest` |
| Footprint | New package for a trivial task (Dependency Stewardship) |

### B4. Output (section "Dependency audit" in the report)

- Scanner and version, ecosystems, number of direct/transitive dependencies.
- Critical/High as numbered findings (CWE-1395 "Dependency on Vulnerable Third-Party
  Component", advisory id, ASVS 15.2.1, OWASP A03:2025, tag Dependency Stewardship).
- Medium/Low as a compact list: package, version, advisory, severity, fixed in,
  reachable yes/no.
- Health flags.
- Upgrade commands **as text only** (`uv lock --upgrade-package <pkg>`,
  `pnpm update <pkg>@<version>`) — the review never runs them.

## Sources

OWASP Secure Agent Playbook (CC BY 4.0), plays `secrets-scan` and `sca-audit`, adapted
to uv/pnpm and the read-only rule. OWASP Top 10:2025 A03 Software Supply Chain Failures.
