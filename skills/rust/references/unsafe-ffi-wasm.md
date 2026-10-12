# Unsafe, FFI, PyO3, WASM, embedded

## Unsafe — policy

- `unsafe_code = "forbid"` in `[workspace.lints.rust]`. `forbid` can't be lifted by an
  attribute in code, so a crate using the workspace lints can contain no `unsafe` at all.
- `unsafe` is allowed only in a **dedicated crate** (`*-sys`, `*-ffi`, or a small crate
  wrapping one primitive). Cargo can't combine `[lints] workspace = true` with a crate's
  own entries, so that crate gets its **own `[lints]` table** — a copy of the workspace
  table without `unsafe_code = "forbid"`, plus:

  ```toml
  [lints.rust]
  unsafe_op_in_unsafe_fn = "deny"     # warn by default in edition 2024; deny here

  [lints.clippy]
  undocumented_unsafe_blocks = "deny"
  multiple_unsafe_ops_per_block = "deny"
  missing_safety_doc = "deny"
  ```

  Modules inside that crate that need no `unsafe` start with `#![forbid(unsafe_code)]`.
- The unsafe crate exposes a **safe API**; business logic stays in safe crates. First
  question in every review: why doesn't an existing, audited crate cover this?

## Writing unsafe code

- Every `unsafe {}` block has a `// SAFETY:` comment that proves each precondition at
  this call site — not a restatement of what the code does.
- Every `unsafe fn` and `unsafe trait` documents its contract under `# Safety`.
- Inside an `unsafe fn`, unsafe operations still need explicit `unsafe {}` blocks
  (`unsafe_op_in_unsafe_fn`).
- One unsafe operation per block; keep blocks as small as possible.
- Edition 2024 syntax:
  - `unsafe extern "C" { … }` — a plain `extern` block is an error; items inside are
    `safe fn` or `unsafe fn` explicitly.
  - `#[unsafe(no_mangle)]`, `#[unsafe(export_name = "…")]`, `#[unsafe(link_section = "…")]`.
  - `&raw const x` / `&raw mut x` to create raw pointers without an intermediate reference.
  - References to `static mut` are rejected by the deny-by-default `static_mut_refs` lint
    — use atomics, `Mutex`, `OnceLock`, or `&raw mut`.
- Uninitialized memory: `MaybeUninit<T>`, never `mem::zeroed()`/`uninitialized()` for types
  with invalid bit patterns (references, `bool`, enums, `NonZero*`).
- Pointer–integer casts use the strict-provenance APIs (`ptr.addr()`, `with_addr`,
  `map_addr`; `expose_provenance`/`with_exposed_provenance` when unavoidable).
- Panic safety: code that temporarily breaks an invariant (`set_len`, `ptr::read`) uses a
  guard whose `Drop` restores it if user code panics in between.
- `unsafe impl Send/Sync` only with a written argument, and with the right bounds on
  generics (`unsafe impl<T: Send> Send for MyBox<T> {}`).
- Atomics: `Relaxed` for independent counters; `Release`/`Acquire` pairs to publish data;
  `SeqCst` only with a stated reason. Prefer `std`/`crossbeam` primitives over your own.

## Verifying unsafe code

Only for crates that contain **own** `unsafe` or **own** synchronization primitives:

- **Miri** (nightly): `cargo +nightly miri test` in CI for the unsafe crate; it detects
  undefined behavior such as out-of-bounds access, use-after-free, invalid values and
  aliasing violations. Tests that touch FFI or the network can't run under Miri — keep the
  pure parts testable separately.
- **loom** for own lock-free structures/atomics: model tests under
  `#[cfg(loom)]`, declared in `[lints.rust] unexpected_cfgs = { level = "warn",
  check-cfg = ['cfg(loom)'] }`, run with `RUSTFLAGS="--cfg loom" cargo test --release`.
- Sanitizers (ASan/TSan, nightly) and fuzzing (`cargo fuzz` + `arbitrary`) for parsers and
  FFI boundaries, on a schedule rather than every MR.
- CI jobs with write access to a shared build cache never get secrets.

Installing nightly, Miri or cargo-fuzz is a toolchain change — ask first.

## FFI — calling C from Rust

- Split: `foo-sys` (raw bindings, no logic, no dependencies besides `libc` if needed) and
  `foo` (safe wrapper with Rust types and errors).
- Bindings: `bindgen` — at build time in `build.rs` or pre-generated and committed
  (faster builds, no libclang needed for users); pick one per crate.
- The wrapper owns the conversions in **one** boundary module: `CStr`/`CString`, null
  checks, length + pointer pairs, error codes → `Result`.
- Memory is freed by the side that allocated it: a C-allocated object is released through
  the library's free function (wrap it in a type with `Drop`), never with Rust's
  allocator.
- `#[repr(C)]` on every struct passed across; `#[repr(transparent)]` for newtypes over a
  C type.
- Linking and build: `build.rs` minimal, no network access, writes only to `OUT_DIR`, uses
  `cargo::rerun-if-changed=…`; system libraries via `pkg-config`.

## FFI — calling Rust from C

```rust
/// Frees a `Parser` created by `parser_new`.
///
/// # Safety
///
/// `parser` must be null or a pointer returned by `parser_new` that was not freed yet.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn parser_free(parser: *mut Parser) {
    if !parser.is_null() {
        // SAFETY: per the contract, `parser` came from `Box::into_raw` in `parser_new`
        // and is freed exactly once.
        drop(unsafe { Box::from_raw(parser) });
    }
}
```

- Opaque handles: `Box::into_raw` in the constructor, `Box::from_raw` in the free
  function; C never sees the layout.
- Headers generated with `cbindgen` (in CI or `build.rs`), committed if consumers need
  them without Rust.
- Panics must not cross into C: since Rust 1.81 a panic leaving an `extern "C"` function
  aborts the process. Catch them (`std::panic::catch_unwind`) at the boundary and return
  an error code, or use `extern "C-unwind"` only when the foreign side supports unwinding.
- Return errors as codes/enums plus an optional "last error" accessor; never return
  pointers into Rust-owned temporaries.
- `crate-type = ["cdylib"]` (shared library) or `["staticlib"]`.

## Python extensions — PyO3 + maturin

- PyO3 0.29 with maturin (`maturin develop` locally, `maturin build --release` for wheels);
  `abi3-py3xx` feature for one wheel across Python versions.
- Current API: `Bound<'py, T>` smart pointers; `Python::attach` / `py.detach` (renamed from
  `with_gil` / `allow_threads` in 0.26). Release the interpreter (`py.detach(|| …)`) around
  long Rust computations.
- Errors: `impl From<MyError> for PyErr` mapping to the right Python exception; never
  panic — a panic becomes a `PanicException`.
- Keep the Python binding crate thin: it converts types and calls the safe core crate.
- PyO3 bindings normally need no hand-written `unsafe`; if the generated code conflicts
  with `forbid(unsafe_code)`, treat the binding crate like an FFI crate (own `[lints]`).

## WebAssembly — wasm-bindgen + wasm-pack

- Core logic in a normal crate (no I/O, no threads); a thin `*-wasm` crate with
  `crate-type = ["cdylib", "rlib"]` exports the API with `#[wasm_bindgen]`.
- Build with `wasm-pack build --target web` (or `bundler` for a bundler-based frontend);
  wasm-pack runs `wasm-opt`.
- Errors cross as `Result<T, JsError>`; structured values via `serde-wasm-bindgen`.
- Async: `wasm-bindgen-futures` — tokio's runtime doesn't run in the browser; keep
  runtime-specific code out of the core crate.
- Randomness: `getrandom` needs its `wasm_js` feature on `wasm32-unknown-unknown` — enable
  it in the final `*-wasm` crate, never in a reusable library.
- Size: release profile with `opt-level = "s"` (or `"z"`), `lto = true`,
  `codegen-units = 1`, `panic = "abort"`; check with `twiggy`.
- Tests: `wasm-bindgen-test` (`wasm-pack test --headless --firefox`) for the bindings;
  the core crate keeps normal tests.

## Desktop and browser from one workspace

Applications that ship a native and a browser build share their core and UI crates
(`applications.md`). The browser build uses `wasm32-unknown-unknown` and a full-app
bundler (trunk) instead of wasm-pack.

### Checklist for shared crates (domain, application, UI)

- [ ] `cargo check --target wasm32-unknown-unknown -p <crate>` passes — in CI for every
  shared crate (an `xtask wasm` command, `tooling.md`).
- [ ] No `std::time::Instant`/`SystemTime::now()` — they panic in the browser. Use
  `web-time` (same API, works on both).
- [ ] No `std::thread::{spawn, sleep}`, no blocking waits, no `std::fs`, no `std::net`.
- [ ] No `cfg(target_arch)` in domain/application; it lives in adapters and hosts.
- [ ] Randomness/UUIDs: `uuid` with its `js` feature as a wasm32 dependency (uses
  `crypto.getRandomValues`); other `getrandom` users need getrandom's `wasm_js` feature,
  enabled in the final crate.
- [ ] No C dependencies unless a wasm-capable clang is set up (e.g. SQLite in wasm).
- [ ] Panics abort in the browser (`panic = "abort"` in the web profile); never rely on
  unwinding.

### Runtime differences

| Area | Native | Browser |
|---|---|---|
| Threads | OS threads, rayon | none without COOP/COEP + atomics; use inline slices or Web Workers |
| Async | tokio (only in hosts that need it) | `wasm_bindgen_futures::spawn_local`, single-threaded, `!Send` futures |
| Storage | files, SQLite | IndexedDB / OPFS (async), localStorage (sync, ~5 MB) |
| Files | `std::fs` | `<input type=file>`, drag-and-drop, Blob downloads |
| Network | anything | `fetch`, WebSocket; CORS applies; no raw TCP, no database connections |
| GPU | wgpu: Metal/DX12/Vulkan | WebGL2 (glow) or WebGPU (wgpu) |
| Entry | `fn main` | `main` → `spawn_local(async { … WebRunner::start … })` |
| Logging | stderr | browser console |

### Patterns

- **Async browser API behind a sync port**: keep the state in memory, persist
  asynchronously and in order (snapshot or per-record writes), load everything before the
  UI starts (`database.md`).
- **Jobs without threads**: step-based tasks; an inline runner executes ≤ ~8 ms of steps
  per frame (`applications.md`).
- **CPU-heavy browser work**: a dedicated Web Worker running a second instance of the
  same wasm module; messages as JSON (`JobRequest` in, `JobState` out), binary data as
  transferables.
- **Build with trunk**: `<link data-trunk rel="rust" data-cargo-profile-release="web">`
  selects the size-optimized `[profile.web]` (`tooling.md`). If `wasm-opt` rejects the
  module (bulk memory, sign-ext, …), pass the features rustc emits via
  `data-wasm-opt-params="--enable-bulk-memory --enable-sign-ext …"`.
- **Size**: fat LTO and `opt-level = "s"` for the bundle, `opt-level = 3` for hot crates
  (`[profile.web.package.<crate>]`); measure the shipped size with `gzip -9 < app_bg.wasm
  | wc -c` and record the number (ADR or docs) so regressions are visible.

### Debugging in the browser

- The browser console shows log output (when the web host installs a console
  logger/subscriber) and panics (when a panic hook is installed).
- Query switches such as `?workers=0` help to isolate Web Worker problems.
- Start-up errors replace the loading text — never leave a blank canvas.

## Embedded and `no_std`

- `#![no_std]` crates use `core` (and `alloc` if a global allocator exists). Libraries
  that work in both worlds: `#![cfg_attr(not(feature = "std"), no_std)]` with a default
  `std` feature.
- Hardware access through `embedded-hal` 1.0 traits — they are the ports; drivers are
  generic over them, so they run on any chip and against mocks in host tests.
- Async firmware: Embassy (`embassy-executor`, `embassy-time`, HALs per chip family);
  RTIC as the interrupt-driven alternative — one per project.
- Logging with `defmt`; flashing/debugging with `probe-rs`.
- A panic handler is required (`panic-probe` with defmt, or `panic-halt`); `panic =
  "abort"` in both profiles.
- No heap by default: `heapless` collections with fixed capacity.
- Keep hardware-independent logic in a separate crate that builds and tests on the host.
