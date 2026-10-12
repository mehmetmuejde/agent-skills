---
name: commit-messages
description: 'Apply when writing git commit messages or being asked to create a commit. Enforces Semantic/Conventional Commits format `<type>(<scope>): <subject>` matching the regex `^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([A-Za-z0-9._-]+\))?: .+$`. Subject in present-tense imperative, lowercase start, no trailing period, max 72 characters. Subject line only — no body/footer rules.'
---

# Commit messages

Commit subjects in **English**, unless the project's history clearly uses another
language. Explanations to the user in the conversation language.

## Up front

Commits are **never created on your own** — only when the user asks for one. This skill
only defines **what** the commit message looks like.

## Format

```
<type>(<scope>): <subject>
```

`<scope>` is optional, the rest is mandatory.

## Regex (binding)

Every subject line MUST match this regex:

```
^(?P<type>build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(?P<scope>\([A-Za-z0-9._-]+\))?: (?P<subject>.+)$
```

No match → reject the commit message and rephrase it.

## Allowed types

| Type       | Meaning                                                                    |
|------------|----------------------------------------------------------------------------|
| `feat`     | new feature for the user (not a build feature)                             |
| `fix`      | bug fix for the user (not a build fix)                                     |
| `docs`     | documentation changes (README, comments, ADRs)                             |
| `style`    | formatting, whitespace, semicolons — no production code changed           |
| `refactor` | restructuring production code without behaviour change (rename, extract …) |
| `perf`     | performance improvement (own type, not a generic `refactor`)               |
| `test`     | adding or restructuring tests — no production code changed                 |
| `build`    | build system, dependencies, bundler, compiler config                       |
| `ci`       | CI pipeline, GitHub Actions, GitLab CI, pre-commit hooks                   |
| `chore`    | maintenance, no production code (e.g. gitignore, scripts)                  |
| `revert`   | reverting an earlier commit                                                |

## Scope

- Optional, in parentheses directly after the type
- Allowed characters: `[A-Za-z0-9._-]` (letters, digits, dot, underscore, hyphen)
- Typical scopes: module, feature or package name (`auth`, `user-profile`, `api.users`,
  `ci`)
- Upper and lower case allowed — stay consistent per project

## Subject

- **Present-tense imperative**: `add`, `fix`, `remove` — NOT `added`, `fixes`, `removed`
- **Lower-case** first letter (except proper names/acronyms: `OAuth`, `API`)
- **No period** at the end
- **At most 72 characters** for the whole subject line (incl. `type(scope): `)
- Describes **WHAT** changes, not how

## Examples

### Good

```
feat: add hat wobble
fix(auth): handle expired refresh tokens
docs(readme): document new env variables
refactor(user-profile): extract avatar component
test(api.users): cover pagination edge cases
chore: update .gitignore
perf(query): cache user lookup
ci: pin actions/checkout to v4
build: bump fastapi to 0.115
revert: feat: add hat wobble
style: apply biome formatter
```

### Bad (with reason)

```
Add hat wobble                              # no type
feat add hat wobble                         # missing colon
Feat: add hat wobble                        # capitalised type
feat: Added hat wobble                      # past tense + capital letter
feat: add hat wobble.                       # trailing period
feat(): add hat wobble                      # empty scope
feat(user profile): add avatar              # space in scope
fix: this fixes the bug where users could not log in via OAuth on mobile  # >72 characters
```

## TODOs in commits

TODOs belong in the code (in the project's TODO format), **not** in the commit message.

## Sources

Based on [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) and
the Angular commit message guidelines; type descriptions and the "hat wobble" example
follow Josh Buchea's
[Semantic Commit Messages](https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716)
gist.
