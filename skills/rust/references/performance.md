# Performance

## Measure first

No optimization without a measurement that shows the problem and a second one that shows
the fix. Readable code is the default; clever code needs a benchmark next to it.

1. Reproduce with a release build (`--release` or the `profiling` profile) — debug builds
   are 10–100× slower and tell you nothing.
2. Profile to find where the time goes.
3. Benchmark the hot function, change it, compare against the saved baseline.
4. Keep the benchmark in the repo so regressions show up.
5. Record the numbers (before/after, machine, profile) in the docs or the ADR that
   justifies the change.

## Profiles

```toml
# Cargo.toml (workspace root — profiles only take effect there)
[profile.release]
lto = "thin"            # "fat" only if a benchmark shows a gain worth the build time
codegen-units = 1
# panic stays "unwind" for servers: tokio isolates a panicking task

[profile.profiling]
inherits = "release"
debug = true            # symbols for flamegraphs and profilers
strip = "none"

[profile.dev.package."*"]
opt-level = 2           # optimize dependencies in dev builds; your crate stays fast to compile
```

- `panic = "abort"` only for CLIs/embedded after checking nothing relies on unwinding
  (`catch_unwind`, task isolation, `Drop` during unwind).
- `opt-level = "s"`/`"z"` + `strip = true` for size-critical targets (WASM, embedded).
- `-C target-cpu=native` never for distributed binaries — the image must run on any
  `linux/amd64` node.

## Profiling tools

| Question | Tool |
|---|---|
| Where is CPU time spent? (Linux) | `perf record -g` + `perf report`, or `cargo flamegraph --profile profiling --bin app` |
| Where is CPU time spent? (macOS/Linux, interactive) | `samply record ./target/profiling/app` (opens the Firefox Profiler) |
| Who allocates how much? | `dhat` crate (heap profiling feature), heaptrack on Linux |
| Why is the binary big? | `cargo bloat --release --crates` |
| Which generics blow up compile time/size? | `cargo llvm-lines` |
| Is the async runtime starved? | `tokio-console` (needs `tokio_unstable` — dev only) |
| Is the database the bottleneck? | `EXPLAIN (ANALYZE, BUFFERS)`, `pg_stat_statements` |

These are tool installs — ask before installing. Profile the real workload (or a recorded
one), not a toy input.

## Benchmarks — criterion 0.8

```toml
[dev-dependencies]
criterion = "0.8"

[[bench]]
name = "parse"
harness = false
```

```rust
// benches/parse.rs
use std::hint::black_box;

use criterion::{criterion_group, criterion_main, Criterion};

fn bench_parse(c: &mut Criterion) {
    let input = include_str!("../tests/fixtures/orders.csv");
    c.bench_function("parse_orders", |b| {
        b.iter(|| shop::import::parse(black_box(input)))
    });
}

criterion_group!(benches, bench_parse);
criterion_main!(benches);
```

- `std::hint::black_box` — since criterion 0.6 the crate's own `black_box` is legacy; use
  std's.
- Compare against a baseline: `cargo bench -- --save-baseline main` on the main branch,
  then `cargo bench -- --baseline main` on the change.
- Benchmarks in shared CI runners are noisy: use them to catch large regressions, run
  precise comparisons on a quiet machine.
- `divan` is a lighter alternative; one benchmark framework per project.

## Allocation and copying

- Pre-size collections (`Vec::with_capacity`, `String::with_capacity`,
  `HashMap::with_capacity`).
- Reuse buffers in loops: `buf.clear()` keeps the capacity.
- `write!(&mut s, …)` into an existing `String` instead of `format!` in loops.
- Borrow instead of clone; `Arc<str>`/`Arc<[T]>` for shared immutable data; `Cow` when
  usually borrowed.
- `Box<str>`/`Box<[T]>` for large immutable collections that never grow.
- Box large enum variants (clippy `large_enum_variant`) so every value isn't as big as
  the largest.
- `smallvec`/`arrayvec`/`compact_str` only after a measurement shows small-collection
  allocations matter.
- A different global allocator (`mimalloc`) can help allocation-heavy servers — measure
  with the real workload before adopting it.

## Iterators and loops

- Iterator chains compile to the same code as hand-written loops and often enable bounds
  check elimination; prefer them for transformations.
- Avoid intermediate `collect()` between steps; chain instead.
- Slicing once (`let items = &items[..n];`) before a loop lets the compiler drop bounds
  checks inside it.
- `sort_unstable*` when stability doesn't matter.

## I/O

- `BufReader`/`BufWriter` around files and sockets; call `flush()?` explicitly at the end
  — `Drop` flushes but swallows the error.
- Lock stdout once for large outputs (`std::io::stdout().lock()`).
- Stream large payloads (files, DB result sets with `fetch()` streams) instead of loading
  everything into memory.

## Hashing

- Keep the default `HashMap` hasher (SipHash, DoS-resistant) for keys that come from
  outside.
- `rustc-hash` (`FxHashMap`) or `ahash` only for trusted, internal keys in hot paths, after
  measuring.

## Concurrency

- Parallel CPU work: `rayon` (`par_iter`) — outside the async runtime, or bridged via
  `spawn_blocking`.
- Shared counters: atomics with `Ordering::Relaxed`, not `Mutex<u64>`.
- Contended locks: shorten the critical section first, then shard; `RwLock` is not
  automatically faster.
- Read-mostly shared data: `arc_swap::ArcSwap` or a `watch` channel.

## Generics and code size

Heavy generic functions are monomorphized per type. If `cargo llvm-lines` shows one
dominating, keep a thin generic wrapper that converts the input and calls a non-generic
inner function:

```rust
pub fn load(path: impl AsRef<Path>) -> Result<Store, LoadError> {
    fn inner(path: &Path) -> Result<Store, LoadError> {
        // the actual work, compiled once
        Store::read_from(path)
    }
    inner(path.as_ref())
}
```

`dyn Trait` trades a little runtime cost for less code and shorter builds — a valid
choice outside hot paths.
