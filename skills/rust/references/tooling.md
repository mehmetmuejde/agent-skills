# Tooling, configuration and CI

## Toolchain — pinned

```toml
# rust-toolchain.toml (committed, at the workspace root)
[toolchain]
channel = "1.99.0"
components = ["rustfmt", "clippy"]
targets = ["wasm32-unknown-unknown"]   # only if the project has a browser build
profile = "minimal"
```

- An exact version, not `stable`: everyone and CI build with the same compiler and clippy
  (new clippy lints otherwise break CI on their own).
- Upgrading Rust is one change touching `rust-toolchain.toml`, `rust-version` (for
  applications), the CI image and the Dockerfile builder image — plus fixing new lints.
- Installing or updating a toolchain on a machine is a system change — ask first.
- UI frameworks raise their MSRV quickly (egui 0.36 needs 1.95); a framework update can
  force a toolchain bump — plan them together.

## Manifest — single package

```toml
[package]
name = "shop"
version = "0.1.0"
edition = "2024"
rust-version = "1.99"          # applications: the pinned toolchain; libraries: see library.md
publish = false                # applications and internal crates

[dependencies]
anyhow = "1"
thiserror = "2"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "net", "signal", "time"] }

[lints.rust]
unsafe_code = "forbid"

[lints.clippy]
pedantic = { level = "warn", priority = -1 }
unwrap_used = "deny"
expect_used = "deny"
```

Abbreviated — use the full lint set from the workspace example below; in a single
package it lives in `[lints.rust]`/`[lints.clippy]`.

## Manifest — workspace (virtual)

```toml
# Cargo.toml at the root — no [package]
[workspace]
resolver = "3"
members = [
    "crates/shop-domain",
    "crates/shop-postgres",
    "crates/shop-http",
    "crates/shop-server",
]

[workspace.package]
version = "0.1.0"
edition = "2024"
rust-version = "1.99"
license = "MIT OR Apache-2.0"   # project/client decision
publish = false

[workspace.dependencies]
# External crates: versions and default features decided once, here
anyhow = "1"
axum = { version = "0.8", features = ["macros"] }
serde = { version = "1", features = ["derive"] }
sqlx = { version = "0.9", default-features = false, features = [
    "runtime-tokio", "tls-rustls-ring-webpki", "postgres", "macros", "migrate", "uuid", "time",
] }
thiserror = "2"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "net", "signal", "time"] }
tracing = "0.1"
# Internal crates
shop-domain = { path = "crates/shop-domain" }
shop-postgres = { path = "crates/shop-postgres" }
shop-http = { path = "crates/shop-http" }

[workspace.lints.rust]
unsafe_code = "forbid"
missing_debug_implementations = "warn"

[workspace.lints.clippy]
# Groups first, with lower priority, so single lints below can override them
pedantic = { level = "warn", priority = -1 }
# Never crash in non-test code (tests are exempted in clippy.toml)
unwrap_used = "deny"
expect_used = "deny"
panic = "deny"
todo = "deny"
unimplemented = "deny"
unreachable = "deny"
# Suppressions need #[expect(…, reason = "…")]
allow_attributes = "warn"
allow_attributes_without_reason = "warn"
# Hygiene
dbg_macro = "warn"
mod_module_files = "warn"
undocumented_unsafe_blocks = "deny"
# Useful nursery lints, opted in one by one
redundant_clone = "warn"
needless_collect = "warn"
# Pedantic noise
must_use_candidate = "allow"
unused_async_trait_impl = "allow"   # fakes and extractors implement async traits without awaiting

[profile.dev.package."*"]
opt-level = 2          # fast dependencies in debug builds; own crates stay quick to compile

[profile.release]
lto = "thin"
codegen-units = 1

[profile.profiling]
inherits = "release"
debug = true

# Only with a browser build: size-optimized bundle (selected by trunk, unsafe-ffi-wasm.md)
[profile.web]
inherits = "release"
lto = "fat"
opt-level = "s"
codegen-units = 1
panic = "abort"
strip = true
```

```toml
# crates/shop-domain/Cargo.toml
[package]
name = "shop-domain"            # one prefix for the whole workspace → easy to find and rename
description = "Order and user domain: types, rules, port traits — no I/O."
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
publish.workspace = true

[dependencies]
serde = { workspace = true }
thiserror = { workspace = true }

[lints]
workspace = true
```

- `resolver = "3"` must be set explicitly in a virtual manifest (there is no package
  edition to infer it from); it is MSRV-aware when updating the lockfile.
- `members` listed explicitly — no `"crates/*"` glob that silently picks up experiments.
  Alternative: globs (`["crates/*", "apps/*", "xtask"]`) when a layer check fails on every
  unregistered crate (`applications.md`) — then nothing slips in silently either.
- Members use `[lints] workspace = true` and **no own `[lints.*]` entries** — Cargo
  rejects the combination. A crate that must differ (FFI) gets a full own table
  (`unsafe-ffi-wasm.md`).
- Profiles only in the root manifest; member profiles are ignored.
- Rust 1.99 (edition 2024 members): `serde = { workspace = true, default-features = false }`
  now really turns default features off; before, it was ignored with a warning.
- Library crates add `#![warn(missing_docs, clippy::print_stdout, clippy::print_stderr)]`
  in `lib.rs`; binaries print on purpose.
- Every dependency version is declared once in `[workspace.dependencies]`; members use
  `{ workspace = true }` and add features locally.
- Pedantic findings are fixed or suppressed locally with a reason. If a lint is wrong for
  the whole project, allow it in `[workspace.lints.clippy]` with a comment — and record a
  significant one in an ADR.

### Crate checklist

- Name with the workspace prefix (`shop-*`), a one-sentence `description` (its
  responsibility), all package fields inherited (`*.workspace = true`), `[lints]
  workspace = true`.
- The crate root starts with a `//!` doc: what the crate is for and what it must not do.
- Registered where the workspace tracks crates: the layer check and the wasm check list
  for browser-shared crates (`applications.md`), `members` if listed explicitly.
- A new crate needs a reason (`architecture.md`, "When to split").

### Never-crash lints — workspace lints or crate roots

Production code never calls `unwrap`, `expect`, `panic!`, `todo!`, `unimplemented!` or
`unreachable!`. Two ways to enforce it:

- **Recommended — workspace lints** (above) plus the `allow-*-in-tests` options in
  `clippy.toml`. One place, every new crate is covered automatically. Side effect: the
  lints also reach integration tests, examples and benches; code inside `#[test]`
  functions is exempt, helpers outside them (`tests/common/`) return `Result` or use a
  local `#[expect(…, reason = "…")]`.
- **Alternative — crate-root attributes** (the rust-app-starter template uses this):

  ```rust
  //! What this crate is for, what it must not do.
  #![deny(
      clippy::unwrap_used,
      clippy::expect_used,
      clippy::panic,
      clippy::todo,
      clippy::unimplemented,
      clippy::unreachable
  )]
  ```

  At `lib.rs`/`main.rs` they cover only that target, so integration tests and examples
  stay free to unwrap. Price: every new crate must remember the block. Pick one per
  workspace — don't mix.

## clippy.toml

```toml
# clippy.toml — configuration only; lint levels live in Cargo.toml
allow-unwrap-in-tests = true
allow-expect-in-tests = true
allow-panic-in-tests = true
allow-dbg-in-tests = true
allow-print-in-tests = true
disallowed-methods = [
    { path = "std::process::exit", reason = "return an ExitCode from main so destructors run" },
    { path = "std::thread::sleep", reason = "blocks async workers; use tokio::time::sleep or restructure" },
]
```

The `allow-*-in-tests` options cover `#[test]` functions and `#[cfg(test)]` code;
`allow-panic-in-tests` is needed once `clippy::panic` is denied. There is no exemption
for `todo!`/`unimplemented!`/`unreachable!` — tests use `panic!` with a message instead.
`msrv` isn't needed — clippy reads `rust-version` from `Cargo.toml`.

## Target-specific dependencies

For workspaces with a native and a browser build:

```toml
[target.'cfg(not(target_arch = "wasm32"))'.dependencies]
directories = { workspace = true }

[target.'cfg(target_arch = "wasm32")'.dependencies]
web-sys = { workspace = true, features = ["Window"] }
```

- Matching modules: `#[cfg(not(target_arch = "wasm32"))] pub mod native;` /
  `#[cfg(target_arch = "wasm32")] pub mod web;` — only in adapters and hosts, never in
  domain/application.
- A host binary that only makes sense on one target gets a **stub `main` on the other**
  (prints a hint, exits with code 2), so `cargo build --workspace` keeps working on every
  target.

## Features in applications

- Features are **additive**; never use a feature to switch between incompatible
  implementations (`library.md`) — choose the implementation in the host.
- Test-support code for other crates (in-memory doubles, the adapter contract suite):
  a `contract-tests`-style feature, enabled only from `[dev-dependencies]` of the crates
  that use it, with `#[cfg(any(test, feature = "contract-tests"))]` on the module.

## xtask — project automation in Rust

- A workspace binary `xtask/` plus an alias in `.cargo/config.toml`:

  ```toml
  [alias]
  xtask = "run --package xtask --"
  ```

- `cargo xtask ci` runs everything CI runs (fmt, clippy native + wasm32, tests, layer
  check, wasm check, cargo-deny); single commands like `cargo xtask layers` or
  `cargo xtask wasm` for the parts. Plain Rust, cross-platform, no shell scripts; keep its
  dependencies minimal (e.g. `serde_json` to read `cargo metadata`). It stays outside the
  layer model.
- A layer check reads `cargo metadata --format-version 1`, maps every workspace crate to
  its layer and fails on forbidden edges or unregistered crates (`applications.md`).

## rustfmt

```toml
# rustfmt.toml
style_edition = "2024"
```

- Defaults otherwise (100 columns). `cargo fmt --all` before committing; CI and the
  pre-commit hook run `cargo fmt --all -- --check`.
- `imports_granularity` and `group_imports` are nightly-only options — not used; stable
  rustfmt is the standard.

## cargo-deny + cargo-audit

```toml
# deny.toml
[graph]
all-features = true

[advisories]
yanked = "deny"
unmaintained = "workspace"     # unmaintained direct dependencies fail; transitive ones don't
ignore = [
    # { id = "RUSTSEC-0000-0000", reason = "not reachable: we never call X; ticket #123" },
]

[licenses]
allow = [
    "MIT",
    "Apache-2.0",
    "Apache-2.0 WITH LLVM-exception",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Zlib",
    "Unicode-3.0",
    "CDLA-Permissive-2.0",
]
confidence-threshold = 0.9

[licenses.private]
ignore = true                  # own crates with publish = false need no license field

[bans]
multiple-versions = "warn"
wildcards = "deny"
allow-wildcard-paths = true    # internal path dependencies of unpublished crates
deny = [
    { crate = "openssl-sys", use-instead = "rustls" },
    { crate = "native-tls", use-instead = "rustls" },
]

[sources]
unknown-registry = "deny"
unknown-git = "deny"
allow-registry = ["https://github.com/rust-lang/crates.io-index"]
```

- Current cargo-deny config: the old keys `[advisories] vulnerability`/`notice`/
  `severity-threshold` and `[licenses] unlicensed`/`copyleft`/`deny`/`default` were
  removed and now produce errors — vulnerabilities always fail, licenses are a pure
  allowlist. `unmaintained` and `unsound` take a scope (`all`, `workspace`,
  `transitive`, `none`); the `version = 2` line is no longer needed.
- The license list is a project/client decision; add licenses only after checking them.
  A license needed by one crate only goes into an exception for that crate, with a
  comment giving the reason:
  `exceptions = [{ crate = "some-crate", allow = ["MPL-2.0"] }]` in `[licenses]`.
- No new dependency without `cargo deny check` passing — and without asking first.
- `cargo deny check` checks advisories, bans, licenses and sources; `cargo audit` checks
  the RustSec database (cargo-deny uses the same database — `cargo audit` stays as the
  second, independent gate and for its `--json` report).
- Both run on every MR and on a schedule (new advisories appear without code changes).

## Git hooks — pre-commit

```yaml
# .pre-commit-config.yaml
default_install_hook_types: [pre-commit, pre-push]
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1                       # pin; update with `pre-commit autoupdate`
    hooks:
      - id: gitleaks                   # staged changes, on commit
        stages: [pre-commit]

  - repo: local
    hooks:
      - id: gitleaks-push              # all commits not yet on any remote, on push
        name: gitleaks (unpushed commits)
        entry: gitleaks git --redact --verbose --log-opts="--branches --not --remotes"
        language: system
        pass_filenames: false
        stages: [pre-push]
      - id: cargo-fmt
        name: cargo fmt
        entry: cargo fmt --all -- --check
        language: system
        pass_filenames: false
        files: '(\.rs|rustfmt\.toml)$'
      - id: cargo-clippy
        name: cargo clippy
        entry: cargo clippy --workspace --all-targets --all-features --locked -- -D warnings
        language: system
        pass_filenames: false
        files: '(\.rs|Cargo\.toml|Cargo\.lock|clippy\.toml)$'
      - id: cargo-deny
        name: cargo deny
        entry: cargo deny check
        language: system
        pass_filenames: false
        files: '(Cargo\.toml|Cargo\.lock|deny\.toml)$'
        stages: [pre-push]
```

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

- `pre-commit` itself comes from the system (e.g. `uv tool install pre-commit` or the OS
  package manager) — installing it is a tool install, ask first. The `gitleaks-push`
  hook needs a local `gitleaks` binary; the commit hook builds its own.
- `--locked` in the clippy hook also fails when `Cargo.lock` is out of date.
- A gitleaks false positive goes into `.gitleaks.toml` (allowlist with a reason) or a
  `gitleaks:allow` comment — never `--no-verify`.
- Hooks are a convenience, CI is the gate.

## CI gates

Every MR runs (in this order, fail fast on the cheap ones):

| Gate | Command |
|---|---|
| Secrets | gitleaks over the MR's commits |
| Format | `cargo fmt --all -- --check` |
| Lints | `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings` |
| Tests + coverage | `cargo llvm-cov nextest --workspace --all-features --locked --profile ci --fail-under-lines 80` |
| Doctests | `cargo test --doc --workspace --all-features --locked` |
| Snapshots | covered by the test run (insta never writes in CI); `cargo insta test --check` if used |
| Docs | `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --all-features --locked` |
| Supply chain | `cargo deny check` and `cargo audit` |
| sqlx offline data | `cargo sqlx prepare --workspace --check` against a migrated database (sqlx projects) |
| Image | Docker build per the `docker-kubernetes` skill (SBOM, provenance, Trivy, `linux/amd64`) |

Libraries additionally:

| Gate | Command |
|---|---|
| MSRV | `cargo +<msrv> check --workspace --all-features --locked` |
| Feature combinations | `cargo hack check --feature-powerset --no-dev-deps` |
| Semver | `cargo semver-checks` (published crates) |
| Latest dependencies (scheduled) | `cargo update && cargo nextest run` |

- Builds use `--locked` everywhere; `SQLX_OFFLINE=true` for sqlx projects.
- Cache `~/.cargo/registry`, `~/.cargo/git` and `target/` keyed by `Cargo.lock` and the
  toolchain; since Rust 1.99 Cargo disables incremental compilation when `CI` is set.
- CI images pin the tools: cargo-nextest 0.9.148, cargo-llvm-cov 0.9.1, cargo-deny
  0.20.2, cargo-audit 0.22.2, cargo-insta 1.49.0, sqlx-cli 0.9.0, cargo-hack 0.6.45,
  cargo-semver-checks 0.51.0 (as of October 2026 — bump deliberately).
- Scheduled pipeline (weekly): `cargo deny check`, `cargo audit`, latest-dependencies run.
- Workspaces with a browser build add the wasm check of shared crates and clippy for
  `--target wasm32-unknown-unknown`; multi-frontend workspaces add the layer check
  (`cargo xtask ci` bundles them).
- GitHub Actions: pin every third-party action by **full commit SHA** (with the version as
  a comment: `uses: actions/checkout@<full-sha> # vX.Y.Z`), not by tag — tags can be moved.
- Dependency update MRs via Renovate/Dependabot, with a minimum release age before new
  versions are proposed.

## Dockerfile — Rust service

General rules (multi-stage, pinning by tag + digest, numeric non-root user, read-only root
filesystem, `linux/amd64`, SBOM/provenance, Trivy, `.dockerignore`) are in the
`docker-kubernetes` skill: `../../docker-kubernetes/references/dockerfile.md` and
`../../docker-kubernetes/references/dockerignore.md`. Rust specifics:

```dockerfile
# syntax=docker/dockerfile:1

# cargo-chef image = official rust:1.99.0-slim-trixie + cargo-chef; matches rust-toolchain.toml
ARG CHEF_IMAGE=lukemathwalker/cargo-chef:0.1.78-rust-1.99.0-slim-trixie
ARG RUNTIME_IMAGE=gcr.io/distroless/cc-debian13:nonroot

# ---------------------------------------------------------------- chef
FROM ${CHEF_IMAGE} AS chef
WORKDIR /app

# ---------------------------------------------------------------- planner
FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

# ---------------------------------------------------------------- builder
FROM chef AS builder
ENV SQLX_OFFLINE=true
COPY --from=planner /app/recipe.json recipe.json
# Dependencies only: this layer is reused until Cargo.toml/Cargo.lock change
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/usr/local/cargo/git,sharing=locked \
    cargo chef cook --release --locked --recipe-path recipe.json
COPY . .
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/usr/local/cargo/git,sharing=locked \
    cargo build --release --locked --bin shop-server \
 && cp target/release/shop-server /app/shop-server

# ---------------------------------------------------------------- runtime (default target)
FROM ${RUNTIME_IMAGE} AS runtime
ARG VERSION=0.0.0-dev
ARG REVISION=unknown
LABEL org.opencontainers.image.title="shop-server" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"
COPY --link --from=builder /app/shop-server /usr/local/bin/shop-server
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/shop-server"]
CMD ["serve"]
```

- **Builder and runtime match**: Debian 13 (trixie) builder → `distroless/cc-debian13`
  (glibc, libgcc, CA certificates; no shell, no package manager). Fully static musl builds
  can use `distroless/static-debian13:nonroot`.
- **Non-root**: distroless `nonroot` is UID/GID 65532 — set it numerically. Fallback
  without distroless: `debian:trixie-slim` with a created user `10001:10001`, as in the
  `docker-kubernetes` skill.
- `cargo chef cook` compiles only dependencies, so source changes rebuild just your
  crates; the cache mounts keep the registry download out of the layers. In CI, layer
  reuse comes from the registry cache (`--cache-from`/`--cache-to`, see the
  `docker-kubernetes` skill).
- The binary handles `SIGTERM` itself (graceful shutdown, `web-backend.md`) and runs as
  PID 1 in exec form — no init process needed.
- **Migrations**: the same image with `CMD ["migrate"]` (or `args` in the Job) runs the
  migration Job; the server never migrates on startup.
- **Health**: distroless has no shell or curl — Kubernetes uses HTTP probes; for Compose
  a `healthcheck` subcommand of the binary (`["/usr/local/bin/shop-server", "healthcheck"]`).
- TLS via rustls: no OpenSSL in the runtime image. Outbound TLS needs CA certificates —
  included in distroless `cc`/`static`; with `webpki-roots` they are compiled in.
- The pinned builder version equals `rust-toolchain.toml`; otherwise rustup downloads a
  second toolchain during the build.
- Pin both images by digest in production (`…@sha256:…`), updated by Renovate.

```dockerignore
# .dockerignore — allowlist
*

!Cargo.toml
!Cargo.lock
!rust-toolchain.toml
!.cargo/config.toml
!src
!crates
!migrations
!.sqlx

# Re-exclude junk inside the allowed folders
**/target
**/*.rs.bk
**/.DS_Store
**/.env
**/.env.*
```

Add `!benches`, `!tests` or `!examples` only if `Cargo.toml` declares targets there
explicitly — Cargo checks declared target paths even when building another target.
