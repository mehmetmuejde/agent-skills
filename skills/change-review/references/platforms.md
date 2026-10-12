# Platforms

Detect the platform from `git remote get-url origin` or the link the user gave.
Reading is always fine; **every write command (comments, review status, labels) needs
explicit approval for this review.**

## GitHub — `gh`

Read:

```sh
gh pr view <n> --json number,title,body,author,baseRefName,headRefName,headRefOid,url,files
gh pr diff <n> --name-only
git fetch origin pull/<n>/head:review/pr-<n>        # works for forks too
git worktree add ../<repo>-review-PR<n> review/pr-<n>
```

Write (after approval):

```sh
# summary comment
gh pr comment <n> --body-file summary.md

# inline comments as one review without a status
gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input review.json
```

`review.json`:

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "<summary>",
  "comments": [
    { "path": "app/features/orders/router.py", "line": 42, "side": "RIGHT", "body": "..." }
  ]
}
```

`event` stays `"COMMENT"` — `APPROVE` / `REQUEST_CHANGES` only with separate approval.
`line` must be a line that is part of the diff.

## GitLab — `glab`

Read:

```sh
glab mr view <n> --output json        # title, description, source/target branch, diff_refs
glab mr diff <n>
git fetch origin merge-requests/<n>/head:review/mr-<n>
git worktree add ../<repo>-review-MR<n> review/mr-<n>
```

Write (after approval):

```sh
# summary comment
glab mr note <n> --message "$(cat summary.md)"

# inline comment = discussion with a position (one call per finding)
glab api projects/:id/merge_requests/<n>/discussions --method POST \
  -f body="$(cat finding.md)" \
  -f "position[position_type]=text" \
  -f "position[base_sha]=<diff_refs.base_sha>" \
  -f "position[start_sha]=<diff_refs.start_sha>" \
  -f "position[head_sha]=<diff_refs.head_sha>" \
  -f "position[new_path]=app/features/orders/router.py" \
  -f "position[new_line]=42"
```

`diff_refs` come from `glab mr view <n> --output json`. Approving (`glab mr approve`)
only with separate approval.

## Gitea — MCP tools

Use the Gitea MCP tools that are available in the session (list them first; names
differ between servers): get pull request, get diff/files, create comment/review.

Read:

```sh
git fetch origin pull/<n>/head:review/pr-<n>        # Gitea exposes refs/pull/<n>/head
git worktree add ../<repo>-review-PR<n> review/pr-<n>
```

Write (after approval): create a review with inline comments via the MCP tool if it
supports positions; otherwise one summary comment with all findings, each with
`path:line`. Fallback without MCP: the `tea` CLI, only if it is already installed.

## Local branch (no platform)

```sh
git worktree add ../<repo>-review-<branch> <branch>
```

Target branch: ask if it isn't obvious (`main`/`develop`). No posting step.

## Ticket key as id

If the branch name or description carries a ticket key (e.g. `PROJ-123`), use it as
`<id>` for the worktree folder and mention it in the report title.
