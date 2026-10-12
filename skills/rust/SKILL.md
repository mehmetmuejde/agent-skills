---
name: rust
description: Apply for any Rust work — writing, reviewing or refactoring `.rs` files, `Cargo.toml`, workspaces and crates; setting up a new Rust project ("Rust-Projekt aufsetzen", "neues Crate anlegen"); web backends with axum or actix-web, tokio/async, sqlx or SeaORM on PostgreSQL, SQLite via rusqlite, CLI tools with clap, library crates (API, semver, features, MSRV); desktop and browser apps with egui/eframe, Tauri, Iced, Slint or Dioxus, multi-frontend workspaces with a UI-independent command core, background jobs, MCP/agent and JSON automation interfaces; performance, unsafe, FFI, WASM, no_std; tests (nextest, insta, proptest), clippy/cargo-deny tooling, CI and Dockerfiles. Holds the rules that always apply — ownership-first APIs, typed errors without panics, feature slices with ports, thin frontends, no blocking in async, strict lints — and points to references per topic.
---

# Rust

Rules for every Rust project. This file holds what always applies; read the matching
reference **before** working on that topic.

| Task | Read |
|---|---|
| Ownership, borrowing, types, iterators, naming, API basics | `references/idioms.md` |
| Error types, `thiserror`/`anyhow`, context, panics | `references/errors.md` |
| Project layout, feature slices, ports/adapters, workspace crates | `references/architecture.md` |
| Multi-frontend apps: layers, `App`, commands, events, jobs, egui/Iced/Slint/Dioxus/Tauri | `references/applications.md` |
| CLI JSON interface, MCP server, UI automation, parallel agent work | `references/agent-interfaces.md` |
| tokio, tasks, cancellation, channels, locks, timeouts, hosting a sync core | `references/async.md` |
| HTTP APIs with axum (primary) or actix-web | `references/web-backend.md` |
| PostgreSQL with sqlx or SeaORM, RLS; SQLite (rusqlite), browser storage, contract tests | `references/database.md` |
| Command-line tools: clap, config, exit codes, output | `references/cli.md` |
| Library crates: public API, semver, features, MSRV, docs | `references/library.md` |
| Profiling, benchmarks, allocations, release profile | `references/performance.md` |
| `unsafe`, FFI, PyO3, WASM (incl. desktop + browser from one workspace), `no_std` | `references/unsafe-ffi-wasm.md` |
| Tests, fakes, snapshots, property tests, coverage | `references/testing.md` |
| Toolchain pin, lints, rustfmt, cargo-deny, pre-commit, CI, Dockerfile | `references/tooling.md` |
| Input validation, secrets, TLS, auth, DoS limits, supply chain | `references/security.md` |

## Stack — defaults

- **Rust** stable **1.99.0**, pinned in `rust-toolchain.toml`; **edition 2024**;
  `rust-version` (MSRV) declared in `Cargo.toml`. See `references/tooling.md`.
- **Async**: tokio · **Web**: axum 0.8 **or** actix-web 4 — fixed per project
- **Database**: PostgreSQL with sqlx 0.9 **or** SeaORM 2 — fixed per project
- **Errors**: `thiserror` in libraries/domain/adapters, `anyhow` only in the binary
- **CLI**: clap 4 (derive) · **Serialization**: serde · **TLS**: rustls
- **Logging**: `tracing` (+ OpenTelemetry when the project needs traces)
- **Tests**: cargo-nextest, insta, proptest; criterion for benchmarks
- **Apps** (desktop/browser): UI framework per project (egui/eframe 0.36 is the
  reference); local storage SQLite via rusqlite 0.40 (`bundled`); browser build with trunk
- **Supply chain**: cargo-deny + cargo-audit; gitleaks via pre-commit

**Detect before writing.** Read `Cargo.toml` (workspace root and crate) first: edition,
MSRV, framework, ORM, existing error crates. Never introduce the second web framework or
ORM, never mix `async-std`/`smol` into a tokio project.

## Code — always

- **Borrow in parameters**: `&str`, `&[T]`, `&Path`, `impl AsRef<…>`; take ownership only
  when the value is stored or consumed. No `.clone()` to silence the borrow checker —
  restructure first.
- **Make invalid states unrepresentable**: newtypes for ids and validated values, enums
  instead of strings and bool flags, `Option` instead of sentinel values. Parse at the
  edge, then pass typed values inward.
- **Exhaustive `match`** on your own enums — no `_` arm that silently swallows new variants.
- **Integers**: `TryFrom` instead of `as` for narrowing; `checked_*`/`saturating_*` where
  overflow is possible from input.
- **Std first**: `LazyLock`/`OnceLock` instead of `once_cell`/`lazy_static`; a crate only if
  std can't do it reasonably.
- **Suppress lints with a reason**: `#[expect(clippy::lint_name, reason = "…")]`, never a
  bare `#[allow]`.
- **Comments explain why**; `///` docs on every public item that isn't self-explanatory,
  a `//!` doc at every crate root (what it is for, what it must not do).
- **Measure before optimizing** and record the numbers in docs or the ADR
  (`references/performance.md`).
- `foo.rs` + `foo/` for modules with children — no new `mod.rs` files.

Details: `references/idioms.md`.

## Errors — always

- Fallible functions return `Result`; propagate with `?`.
- **No `unwrap()`/`expect()`/`panic!`/`todo!`/`unimplemented!`/`unreachable!` in
  non-test code** — enforced by clippy workspace lints (deny) with `allow-*-in-tests` in
  `clippy.toml`; crate-root `#![deny]` is the documented alternative
  (`references/tooling.md`). A real invariant gets a local
  `#[expect(clippy::expect_used, reason = "…")]`.
- **`thiserror`** for library, domain and adapter crates: one error enum per module or
  concern, variants carry the data callers need, sources are chained (never stringified);
  errors other frontends branch on get stable `code()`s.
- **`anyhow`** only in the binary (`main`, CLI command handlers, composition root) and in
  tests — add `.context(…)` at every I/O boundary.
- Log an error **once**, where it is handled — not at every `?`.

Details: `references/errors.md`.

## Architecture — always

- **Feature slices**: one module per feature (`orders`, `users`), each with its domain
  types, service, ports and HTTP/CLI glue. No layer folders (`models/`, `services/`) for
  the whole app.
- **Domain without framework types**: no axum, actix, sqlx, SeaORM or clap types in domain
  code; persistence only through ports. Adapters translate at the edge.
- **Thin frontends**: HTTP handlers, CLI commands and UIs translate input into calls and
  render results — **no business logic** in them.
- **One path to the logic**: every frontend (UI, CLI, HTTP, agent, test) calls the same
  service/command; never a second implementation of the same rule.
- **Isolate platform code**: `cfg(target_arch)`, OS APIs, threads and file paths live in
  adapters and hosts, never in the domain.
- **Ports are traits** at real I/O boundaries (database, external APIs, clock,
  randomness): **generic by default**; `dyn` via constructor injection when the
  implementation is picked at runtime or per target (storage backend per platform, the
  `App` service of multi-frontend apps). Native `async fn` / `-> impl Future + Send` in
  traits; `async-trait` only for `dyn`.
- **Ports only with a real second implementation** (another backend or the in-memory fake
  the tests use) — no speculative interfaces, no generic `Repository<T>` before a second
  entity, no `common`/`utils` god-crates.
- **Composition root** in `main.rs`: config, pools, adapters, wiring. `main.rs` stays
  thin; logic lives in the library crate.
- **New crates only with a reason** (compile-time boundary, second port implementation,
  other target, heavy optional dependency, separate publish, measured build time) —
  otherwise a module.

Details: `references/architecture.md`.

## Applications with several frontends — always

For desktop/browser/CLI apps sharing one domain (feature slices still organize the
modules inside the core):

- Layers L0 domain → L1 application → L2 adapters ∥ L3 UIs → L4 hosts; adapters and UIs
  are siblings; enforced by a `cargo metadata` layer check in CI.
- **No framework dependencies in the core**: no UI, async runtime, DB driver or web API in
  L0/L1. The core is synchronous with a single owner; long work runs as step-based jobs.
- **One entry point**: `App::execute(Command)` — a serializable command enum with
  `Effect::{Read, Write, Destructive}`; destructive commands need explicit confirmation
  in every frontend, agents never confirm on their own.
- **Shared code compiles for desktop and `wasm32-unknown-unknown`** where the project has
  a browser build (checked in CI).

Details: `references/applications.md`, `references/agent-interfaces.md`.

## Async — always

- Never block a runtime thread: no `std::fs`, `std::thread::sleep`, blocking HTTP
  clients, sync DB drivers or CPU-heavy loops in `async fn` — use `spawn_blocking` (or
  rayon for parallel CPU work).
- **No lock guard across `.await`** (std or parking_lot). Default to `std::sync::Mutex` for
  short sections; `tokio::sync::Mutex` only if the guard must live across `.await`.
- Every external call has a **timeout**; every queue is **bounded**.
- Spawned tasks are owned: `JoinSet`/`TaskTracker`, cancellation via `CancellationToken`,
  graceful shutdown on `SIGTERM`.
- Libraries don't spawn tasks or pick the runtime for the caller.

Details: `references/async.md`.

## Unsafe — forbidden by default

`unsafe_code = "forbid"` workspace-wide. The only exception is a dedicated FFI/unsafe crate
that overrides it, documents every block with `// SAFETY:` and runs Miri in CI. See
`references/unsafe-ffi-wasm.md`.

## Security — always

- Validate all external input at the edge (size, range, format) into typed values.
- Secrets in `secrecy::SecretString`; never logged, never in `Debug` output, never in the
  repo or image.
- SQL only parameterized; HTTP clients and servers with timeouts and body limits; TLS via
  rustls.
- Authorization on every request, scoped by owner/tenant in the query itself.

Details: `references/security.md`; full reviews with the `appsec-review` skill
(`../appsec-review/SKILL.md`).

## Logging

`tracing` is the default; the binary installs the subscriber (`tracing-subscriber` with
`EnvFilter`, JSON in production). Libraries only emit events/spans — no `println!`, no
subscriber. `#[instrument(skip_all, fields(…))]` so arguments (secrets, bodies) are never
recorded by accident.

Exception: lean desktop/WASM apps without async or spans may use the `log` facade
(`env_logger` natively, a console logger in the browser). Decide once per project (ADR),
never mix both in one workspace.

## Repository hygiene — always

- **Toolchain pinned** in `rust-toolchain.toml` (exact version + rustfmt, clippy), matching
  `rust-version` for applications, the CI image and the Dockerfile builder image.
- **`Cargo.lock` committed** — for applications **and** libraries.
- **Lints in `Cargo.toml`** (`[workspace.lints]`, members `[lints] workspace = true`);
  CI runs `cargo clippy --all-targets --all-features --locked -- -D warnings`.
- **pre-commit** for commit **and** push: gitleaks on staged changes and on all unpushed
  commits, `cargo fmt --check`, clippy, `cargo deny check`. Never bypass with
  `--no-verify`.
- **cargo-deny + cargo-audit** in CI on every MR and on a schedule.
- **`docs/adr/`** at the project root for decisions that bind the whole project, and in
  every workspace crate / sub-project for decisions that only concern it (Nygard format,
  sequential `0001-…`).
- **`.scratch/`** for temporary notes — ignored through the global git ignore; never add it
  to the project `.gitignore`.
- **`.dockerignore`** always present next to every Dockerfile (excludes `target/`).
- **TODOs** use the project's TODO marker (e.g. `TODO(name): <description>`).

Details: `references/tooling.md`.

## Tests are part of the change

Every feature and bug fix ships with tests (bug fix: failing regression test first).
`cargo nextest run` plus `cargo test --doc` (nextest doesn't run doctests); CI enforces
**80 % line coverage** with cargo-llvm-cov. Fakes over mocks. See `references/testing.md`.

## Workflow

1. **Understand** the requirement; restate it, name the domain concepts involved.
2. **Find the affected crates/modules** — most features go domain → service/command →
   adapter(s) → frontend(s).
3. **Check the architecture**: does an existing service/command/port cover it? Is a new
   crate or dependency really needed? Is it platform-specific?
4. **Short plan** (files, commands, migrations, tests). Ask before binding decisions:
   new dependency, new crate, storage format change, public command/API change, license
   exception.
5. **Implement inside-out**: domain rules → service/command → port/adapter (+ migration) →
   frontends.
6. **Tests** at the level where the logic lives.
7. **Gate**: `cargo fmt`, clippy with `-D warnings`, tests, `cargo deny check` — in
   multi-frontend workspaces `cargo xtask ci` (also layers and wasm).
8. **Platform check**: wasm build of shared crates; after UI changes run the desktop /
   browser app and look at the result.
9. **Docs**: command table, guides, ADR for binding decisions — in the same change.
10. **Summary**: what changed, what was verified (and how), what was not, open questions.
    Never claim a build or test passed without having run it.

## Docker and Kubernetes

Dockerfiles, `.dockerignore`, Compose with a local PostgreSQL, Helm and Kubernetes are
covered by the `docker-kubernetes` skill (`../docker-kubernetes/SKILL.md`): multi-stage,
slim or distroless runtime, numeric non-root user, `linux/amd64`. The Rust-specific
multi-stage example is in `references/tooling.md`.

## Sources

Rewritten in our own words (no text or code copied) from these published skills:
Apollo GraphQL `rust-best-practices` (MIT); leonardomso `rust-skills` (MIT); affaan-m
`rust-testing` (MIT); pproenca `openai-codex-rust-patterns` (MIT, production patterns
from the open-source codex-rs workspace); existential-birds/beagle `rust-project-setup`,
`tokio-async-code-review`, `axum-code-review`, `rust-code-review`,
`rust-testing-code-review` (Apache-2.0); full-stack-skills/rust-skills `rust-workspace`,
`rust-module-layout`, `rust-api-design`, `rust-web-security`, `rust-dependencies`,
`rust-unsafe-ffi` (Apache-2.0); mohitmishra786 `rust-profiling` (MIT); rust-app-starter
(Mehmet Müjde, MIT/Apache-2.0) for the multi-frontend application architecture, agent
interfaces and local storage. Outdated points in
those sources were corrected against the official documentation: Rust API Guidelines,
Cargo Book, Edition Guide 2024, Clippy lint list, Tokio docs, axum/tower-http/sqlx/SeaORM
changelogs, cargo-deny book, Rust Performance Book, Rustonomicon and the ANSSI Secure
Rust Guidelines.
