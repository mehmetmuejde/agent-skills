# Dimension: security

Delegates to the `appsec-review` skill. The subagent gets the full path of its
`SKILL.md`, reads it and runs **Review mode** on this diff.

## Instructions for the subagent

1. Read `appsec-review/SKILL.md` and follow its review workflow with the worktree and
   merge base of this review as scope. Diff-scoped, but read the surrounding code of
   every changed hunk.
2. Load only the checklists for the domains the diff touches (backend, frontend,
   LLM/agents, MCP, dependencies).
3. Always run the **secrets scan** on the diff and, if manifests or lockfiles changed,
   the **dependency audit** (installed scanners only — never install anything).
4. Pay special attention to **removed controls**: deleted or weakened auth
   dependencies, permission checks, validation (`extra="forbid"`, length limits),
   ownership filters, CSRF checks, CORS restrictions, security headers, sanitizing,
   tests for any of these.
5. Return findings in `appsec-review`'s schema (severity Critical–Info, confidence, CWE,
   ASVS id, principle tag). Do **not** write the final report — the orchestrator merges.

## Mapping for the orchestrator

Critical/High → Blocker, Medium → Major, Low → Minor, Info → Nit. Keep the security
severity in the label: "Blocker (Security: High)". Keep CWE/ASVS ids in `refs`.
