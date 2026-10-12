# Agent and automation interfaces

Agents and other automation clients use **the same commands as humans**
(`applications.md`). Never build agent-only shortcuts into the core; a machine interface
is one more frontend at L4.

## Machine interface ladder

Build the rungs in this order; each one reuses the command enum, its JSON Schema and the
`Effect` metadata.

1. **CLI with JSON** — always first, it costs little:
   - `<app> commands` lists the commands; `<app> commands --schema` prints the JSON Schema
     of the command format.
   - `<app> exec '<json>' --json` runs any command (`-` reads the JSON from stdin).
   - Output envelope on stdout, nothing else on stdout:
     `{"ok": true, "result": …}` or
     `{"ok": false, "error": {"code": "not_found", "message": "…"}}` — `code` is
     `AppError::code()`.
   - **Stable, documented exit codes**, e.g. `0` success, `1` user error or refused
     command, `2` usage error (clap), `3` internal/storage error (`cli.md`).
   - **Destructive guard**: commands with `Effect::Destructive` are refused unless
     `--allow-destructive` is given (error code e.g. `confirmation_required`).
2. **MCP server** (Model Context Protocol) — stdio transport first (`rmcp` 3.5, features
   `server`, `transport-io`, `macros`, `schemars`); a streamable HTTP transport later, only
   with token authentication (`security.md`).
3. **HTTP/REST or RPC** — a server host accepting `Command` JSON (`web-backend.md`,
   authorization per `Effect` in `security.md`).

## MCP design

- **One tool per command variant.** Name = command name; description = the variant's doc
  comment; input schema = the variant's `params` schema from `schemars`.
- **Annotations from `Effect`**: `readOnlyHint` for `Read`, `destructiveHint` for
  `Destructive`, `idempotentHint` where it is true.
- **Destructive tools need `confirm: true` and a user-side allow-list**; otherwise return
  an error that explains what would happen. The agent never sets the confirmation on its
  own — a human approves the specific action (`security.md`).
- **Resources** for read-only views (e.g. `app://items`), refreshed from `AppEvent`s.
- **Long jobs**: return the job id; offer `get_job` / `cancel_job`; send MCP progress
  notifications when the client supports them.
- **Headless by default** (no UI needed). An "attach to the running desktop app" mode
  needs a local, **authenticated control channel** — e.g. JSON lines over loopback TCP,
  bound to `127.0.0.1`, a token per request, request size and connection caps
  (`security.md`).

## UI automation and screenshots

- Drive the real UI through its test harness (`egui_kittest` for egui), not OS-level
  synthetic input.
- Screenshots: kittest with the `wgpu` + `snapshot` features, or a headless CPU
  rasterizer.
- Give widgets **accessibility labels** so automation finds them by name
  (`labelled_by`, `applications.md`).

## Working rules for automated and parallel work

- Run the full gate before declaring work done; report what was verified and what was not
  (`testing.md`).
- One feature per change; docs and ADRs go into the same change.
- Ask the human before binding decisions: new crate, new dependency, storage format,
  public command changes, license exceptions.
- **Parallel work**: one git worktree per task, a separate `CARGO_TARGET_DIR` per
  worktree (never one shared, globally set target dir — parallel builds block on its lock
  and invalidate each other's artifacts), separate ports and separate data directories —
  never two runs against the same database file.
