# Output format

## Finding schema (subagents → orchestrator)

Every subagent returns its findings as a list in this shape — in any language, the
orchestrator writes the final report in the conversation language:

```
- dimension: correctness | design-and-reuse | breaking-changes | tests | security |
             backend | frontend | infrastructure | change-size
  severity: Blocker | Major | Minor | Nit
  confidence: High | Medium | Low
  location: path/to/file.py:42        # line in the source branch; range allowed: 42-57
  title: one line, states the problem
  problem: what is wrong and why it matters (impact, scenario)
  evidence: short code excerpt or the call path that proves it
  fix: concrete change — what to do, not "consider improving"
  comment: one-line review comment in the team's language, typed-by-hand style
           (comment-style.md)
  comment_alt: optional — the same comment in a second language, only if requested
  refs: optional — CWE, ASVS id, rule id (e.g. Vercel `rerender-derived-state`)
```

A finding without a concrete `location` is not a finding — it goes to "Open questions"
or, if it concerns the whole change, uses the most relevant file.

## Severity

| Severity | Meaning | Examples |
|---|---|---|
| **Blocker** | Must be fixed before merge | wrong behavior or data loss on a normal path; security Critical/High; breaking change without migration path; migration that can't run on production data; build/tests broken |
| **Major** | Should be fixed before merge | bug in an edge case; missing tests for changed behavior; missed reuse / parallel solution; architecture/boundary violation; real performance problem; accessibility barrier; security Medium |
| **Minor** | Fix soon, may follow up | unclear naming with risk of misuse, small duplication, typo or missing translation in user-facing text, missing story state, security Low |
| **Nit** | Optional polish | style beyond the formatter, typos in comments or identifiers, wording, typography; security Info |

Security mapping (from `appsec-review`): Critical/High → Blocker, Medium → Major,
Low → Minor, Info → Nit — shown as e.g. "Blocker (Security: High)".

## Confidence

- **High** — verified by reading the code path; reproducible reasoning.
- **Medium** — very likely, one assumption (e.g. caller behavior outside the diff).
- **Low** — suspicion only → not a finding; goes to "Open questions".

Blocker and Major need at least Medium.

## Report (chat, conversation language)

Translate the headings and labels into the report language.

```markdown
## Review: <title> (<MR/PR id>, <source> → <target>)

**Verdict:** <Ready to merge | Ready to merge after fixes | Not ready to merge> —
<1–2 sentences: what the change does and the main problem>
**Size:** <n> files, +<a>/−<d> lines · Scope: <Everything|Frontend|Backend|Infrastructure>
**Findings:** <x> Blocker · <y> Major · <z> Minor · <w> Nit

### Findings

1. **[Blocker] <title>** — `path/to/file.py:42` · Confidence: High · <dimension>
   <problem and impact, 1–3 sentences>
   ```python
   <short excerpt>
   ```
   **Fix:** <concrete change>
   <Refs: CWE-639, ASVS 8.2.2>
   💬 <one-liner to post>

2. **[Major] …**

### Positive
- <what is solved well — concrete, max. 5 points>

### Open questions
- <suspicion or question for the author, with location>

### Out of scope / not checked
- <outside the chosen scope in one sentence; areas not checked, e.g. proxy configuration>
```

Rules:

- Numbering is continuous across severities, so findings can be referenced ("fix 3").
- One finding = one problem. The same pattern in several places → one finding listing
  all locations.
- Code excerpts short (≤ 10 lines). Secrets always redacted.
- The verdict follows the findings: any Blocker → "Not ready to merge"; only Major →
  "Ready to merge after fixes".

## Platform comments (only after approval)

The posted comment is the finding's one-liner in the chosen language — exactly as
shown in the report after `💬`, without the language code, nothing added. Findings
without a line in the diff go into the short summary comment. Rules and examples:
`comment-style.md`.
