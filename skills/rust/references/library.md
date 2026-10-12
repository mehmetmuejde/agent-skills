# Library crates

Applies to crates published on crates.io and to internal crates other teams depend on.
General API basics: `idioms.md`. Errors: `errors.md`.

## Public API

- **Small surface.** `lib.rs` is a facade: private modules plus deliberate `pub use`
  re-exports. No glob re-exports (`pub use foo::*`) — they publish things by accident.
- Everything nameable is API: public items, re-exports, trait impls, auto traits
  (`Send`/`Sync`/`Unpin`) of public types, and `#[doc(hidden)]` items that users can still
  reach. All of it is under semver.
- **Re-exporting a dependency's types couples your semver to theirs** — a major bump of
  that dependency becomes a major bump of yours. Re-export deliberately (and then also
  re-export the crate: `pub use url;`), otherwise wrap.
- Private fields + constructors/accessors for anything that may grow; plain public fields
  only for real data structs that are `#[non_exhaustive]`.
- `#[non_exhaustive]` on public enums and structs that will gain variants/fields
  (errors, options, events). Adding it later is itself a breaking change — decide at
  1.0 at the latest.
- **Sealed traits** for traits users may call but not implement
  (`pub trait Backend: private::Sealed`), so you can add methods later.
- Builders for types with many optional settings; `build()` returns `Result` when
  validation can fail. Mark builder methods `#[must_use]`.
- Common traits on public types where they make sense: `Debug` (always), `Clone`,
  `PartialEq`/`Eq`, `Hash`, `Default`, `Display` for user-facing values, `serde` behind a
  feature. Don't implement `Copy` on types that may later hold heap data — removing `Copy`
  is breaking.
- Generic inputs, concrete outputs: `fn open(path: impl AsRef<Path>) -> Result<Store>`.
- No `anyhow` or `Box<dyn Error>` in public signatures; a typed error enum (`errors.md`).
- No global state, no `println!`, no tracing subscriber, no `std::process::exit`. Emit
  `tracing` events and let the application decide.
- Async libraries don't spawn tasks or require a specific runtime unless that's their
  purpose (`async.md`).

## Semver

| Change | Bump (≥ 1.0) |
|---|---|
| Bug fix, docs, internal refactor | patch |
| New public item, new variant on a `#[non_exhaustive]` enum, new optional feature | minor |
| MSRV increase | minor (documented in the changelog) |
| Removing/renaming a public item, changing a signature, new variant on an exhaustive enum, adding a field to an exhaustive struct with public fields, removing a trait impl or an auto trait, removing a feature | major |

- Before 1.0, `0.x` → `0.(x+1)` is the breaking bump; `0.x.y` → `0.x.(y+1)` is everything
  else.
- **`cargo semver-checks`** in CI for every published crate (compares against the last
  release on crates.io). It catches most, not all, breaks — review the rest.
- Deprecate before removing: `#[deprecated(since = "1.4.0", note = "use `open_with` instead")]`,
  remove in the next major.
- Release a fix before yanking a broken version; yank only versions that are harmful.
- `cargo publish --workspace` (stable since Rust 1.90) publishes workspace crates in
  dependency order.

## Features

- **Strictly additive.** Enabling a feature only adds API or capability; two features
  never conflict. Cargo unifies features across the dependency graph — "either backend A
  or B" via features breaks other people's builds. Mutually exclusive backends become
  separate crates or runtime configuration.
- `default` features stay minimal; users opt in.
- Optional dependencies via `dep:` so no implicit feature named after the crate appears:

  ```toml
  [features]
  default = []
  serde = ["dep:serde"]
  tokio = ["dep:tokio"]

  [dependencies]
  serde = { version = "1", features = ["derive"], optional = true }
  tokio = { version = "1", features = ["net"], optional = true }
  ```

  ```rust
  #[derive(Debug, Clone)]
  #[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
  pub struct Config { /* … */ }
  ```

- Test the feature matrix: `cargo hack check --feature-powerset --no-dev-deps`
  (or `--each-feature` when the powerset is too large).
- Document features in the crate docs and in `[package.metadata.docs.rs]`
  (`all-features = true`, `rustdoc-args = ["--cfg", "docsrs"]`). docs.rs builds with
  nightly, so `#![cfg_attr(docsrs, feature(doc_cfg))]` in `lib.rs` shows feature badges;
  `doc(cfg)` itself is still unstable — keep it behind `cfg_attr(docsrs, …)`.
- Applications don't define features for their own code paths — use configuration.

## MSRV

- Declare `rust-version` in `Cargo.toml`; with edition 2024 the floor is 1.85.
- The MSRV is a promise: CI builds and tests on exactly that version
  (`cargo +1.xx check --all-features` or a dedicated job).
- Policy (written in the README): raise it deliberately, in a minor release, when a
  feature or dependency needs it — not on every toolchain update.
- Resolver 3 (default for edition 2024) prefers dependency versions compatible with your
  `rust-version` when updating the lockfile.
- Clippy reads `rust-version` and won't suggest newer APIs.

## Cargo.lock — committed

Commit `Cargo.lock` for libraries too (the Cargo default since 2023): reproducible CI,
`git bisect`, MSRV builds. Because the lockfile hides new dependency releases, add a
**scheduled CI job** that runs `cargo update` and the full test suite, so breakage from
upstream shows up before users report it. Consumers of your crate don't use your lockfile.

## Documentation

- Crate-level docs in `lib.rs` (`//!`): what it is, a quick start, feature list. Often
  `#![doc = include_str!("../README.md")]` so README examples are compiled as doctests.
- Every public item documented (`missing_docs = "warn"` for library crates via
  `#![warn(missing_docs)]` in `lib.rs`).
- Sections where they apply: `# Examples` (runnable), `# Errors`, `# Panics`, `# Safety`
  (for `unsafe fn`).
- Examples are doctests: they compile and run with `cargo test --doc`. Use `?` in
  examples (hidden `# fn main() -> Result<(), Box<dyn std::error::Error>> {` lines), not
  `unwrap`.
- Intra-doc links (`[`Store::open`]`); CI builds docs with `RUSTDOCFLAGS="-D warnings"
  cargo doc --no-deps --all-features` to catch broken links.
- Larger runnable examples in `examples/` (built by `cargo test`).

## Manifest for publishing

```toml
[package]
name = "acme-store"
version = "0.3.0"
edition = "2024"
rust-version = "1.85"
description = "Embedded key-value store with typed tables"
license = "MIT OR Apache-2.0"
repository = "https://github.com/acme/acme-store"
documentation = "https://docs.rs/acme-store"
readme = "README.md"
keywords = ["database", "kv", "embedded"]
categories = ["database-implementations"]
include = ["src/**/*", "README.md", "LICENSE-*", "CHANGELOG.md"]

[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["--cfg", "docsrs"]
```

- `include` keeps tests, fixtures and CI files out of the package; check with
  `cargo package --list`.
- No git or path dependencies in published crates (path deps need a `version` too).
- `CHANGELOG.md` with an "Unreleased" section, updated in the same change.
- `cargo publish --dry-run` in CI; actual publishing only from a tagged release
  (approval required — it's irreversible).

## Macros in libraries

- `macro_rules!` exported with `#[macro_export]` use `$crate::` paths; internal helpers
  they need live in `#[doc(hidden)] pub mod __private` (documented as not covered by
  semver).
- Procedural macros in a separate `<name>-macros` crate, re-exported by the main crate;
  compile-fail tests with `trybuild`.
