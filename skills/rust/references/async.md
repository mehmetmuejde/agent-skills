# Async with tokio

## Runtime

- Binaries: `#[tokio::main]` (multi-thread). `flavor = "current_thread"` for small CLIs
  that only await a few things.
- Enable only the tokio features you use (`rt-multi-thread`, `macros`, `net`, `time`,
  `signal`, `sync`, `fs`); `full` is fine for binaries, never for libraries.
- Libraries are runtime-agnostic where possible: they expose `async fn`s, don't call
  `tokio::spawn` internally and don't build runtimes. If a library must spawn, it takes a
  spawner or documents the tokio requirement behind a feature.
- `tokio_util` adds `CancellationToken`, `TaskTracker`, codecs; `futures` adds
  `StreamExt`/`buffer_unordered`.

## Never block the runtime

A task that runs more than roughly 10–100 µs without reaching an `.await` stalls every
other task on that worker thread.

| Work | Use |
|---|---|
| Blocking I/O (std file APIs, sync DB drivers, blocking SDKs) | `tokio::task::spawn_blocking` (or `tokio::fs`) |
| CPU-heavy work (hashing passwords, image processing, compression, big JSON) | `spawn_blocking` for single jobs; rayon (bridged with a `oneshot`) for parallel batches |
| Sleeping | `tokio::time::sleep`, never `std::thread::sleep` |
| Calling async from sync code inside the runtime | restructure; `Handle::block_on` only from a non-runtime thread |

```rust
let hash = tokio::task::spawn_blocking(move || hash_password(password.expose_secret()))
    .await
    .context("password hashing task failed")??;
```

`spawn_blocking` tasks can't be cancelled; long batch jobs check a cancellation flag
themselves.

## Locks

- **No guard across `.await`.** Clone the data out or restructure; clippy's
  `await_holding_lock` (on by default) catches std/parking_lot guards.
- `std::sync::Mutex` is the default for short critical sections — faster than the async
  mutex. `tokio::sync::Mutex` only when the guard **must** live across `.await` (e.g.
  serializing access to one connection).
- `RwLock` only for clearly read-heavy data; a plain `Mutex` is often faster.
  Read-mostly config/snapshots: `arc_swap::ArcSwap` or a `watch` channel.
- Counters and flags: atomics (`AtomicU64::fetch_add`, `Ordering::Relaxed` for pure
  counters).
- Edition 2024 shortens `if let` temporaries: a guard created in the `if let` scrutinee is
  dropped before the `else` branch — code that used to deadlock now often just works, but
  keep lock scopes explicit anyway (`let value = { let g = m.lock()…; g.clone() };`).

## Owning tasks — structured concurrency

- Never fire and forget. A dropped `JoinHandle` **detaches** the task — it keeps running,
  its panics and errors vanish.
- A group of tasks lives in a `JoinSet`: dropping the set aborts all tasks, `join_next`
  collects results and panics.

```rust
let mut set = tokio::task::JoinSet::new();
for url in urls {
    let client = client.clone();
    set.spawn(async move { fetch(&client, &url).await });
}
while let Some(joined) = set.join_next().await {
    match joined {
        Ok(Ok(page)) => pages.push(page),
        Ok(Err(err)) => tracing::warn!(error = &err as &dyn std::error::Error, "fetch failed"),
        Err(join_err) => tracing::error!(%join_err, "fetch task panicked"),
    }
}
```

- Long-lived background workers: `tokio_util::task::TaskTracker` + `CancellationToken`.
- A struct that owns a background task aborts it on drop (store an
  `AbortOnDropHandle` from `tokio_util::task`, or call `abort()` in `Drop`).
- Bound concurrency: `Semaphore::acquire_owned()` per task, or
  `stream::iter(items).map(work).buffer_unordered(8)`.

## Cancellation and shutdown

Dropping a future cancels it at its current `.await`. Design for that.

```rust
let token = CancellationToken::new();
let tracker = TaskTracker::new();

for worker in workers {
    let token = token.child_token();       // child: cancelled with the parent
    tracker.spawn(async move { worker.run(token).await });
}
tracker.close();

shutdown_signal().await;                   // SIGTERM or Ctrl-C
token.cancel();                            // 1. ask nicely
let drained = tokio::time::timeout(Duration::from_secs(25), tracker.wait()).await;
if drained.is_err() {
    tracing::warn!("workers did not stop in time");   // 2. give up after the grace period
}
```

- Hand sub-tasks a `child_token()`; cancelling a child doesn't cancel the parent.
  Dropping a token does **not** cancel anything — call `cancel()`.
- The grace period stays below the orchestrator's (`terminationGracePeriodSeconds`).
- Workers check the token in their `select!`:

```rust
loop {
    tokio::select! {
        biased;                                   // check cancellation first
        () = token.cancelled() => break,
        msg = rx.recv() => match msg {
            Some(job) => handle(job).await?,
            None => break,                        // all senders gone
        },
    }
}
```

### Cancellation safety in `select!`

The losing branches are dropped. That is safe only if the future loses no data when
dropped.

| Safe in `select!` loops | Not safe — progress is lost |
|---|---|
| `mpsc::Receiver::recv`, `broadcast::Receiver::recv`, `watch::Receiver::changed` | `AsyncReadExt::read_exact`, `read_to_end`, `read_to_string` |
| `TcpListener::accept`, `tokio::time::sleep`, `CancellationToken::cancelled` | `AsyncWriteExt::write_all` |
| `AsyncReadExt::read` (single read) | `Mutex::lock` / `Semaphore::acquire` (lose queue position) |

For unsafe operations: run them in their own task and `select!` on the `JoinHandle`, or
keep the future pinned outside the loop (`let fut = std::pin::pin!(op);` then `&mut fut`)
so it resumes instead of restarting. Use `std::pin::pin!`, not `pin_mut!` from older
crates.

## Timeouts

- Every network call, DB query and external process has a timeout:
  `tokio::time::timeout(Duration::from_secs(5), call).await` → `Err(Elapsed)`.
- Client-level timeouts too: `reqwest::Client::builder().timeout(…).connect_timeout(…)`,
  pool `acquire_timeout` (sqlx).
- Streams get an **idle** timeout per `next()`, not just a total one — a peer that sends
  one byte a minute never trips a total timeout late enough.
- Server side: tower-http timeout and body-deadline layers (`web-backend.md`).

## Channels

| Need | Channel |
|---|---|
| Work queue, many producers → one consumer | `mpsc::channel(n)` — **bounded**, gives backpressure |
| Reply to one request | `oneshot` |
| Fan-out events to all subscribers | `broadcast` — handle `RecvError::Lagged` |
| Latest value (config, state, shutdown flag) | `watch` |

- Unbounded channels only when the producer is itself bounded (e.g. internal events from a
  bounded source); input from the outside is always bounded.
- `send().await` on a full channel waits — that's the backpressure; `try_send` when the
  caller must not wait (then decide: drop, error, or 503).
- A closed channel (`SendError`, `recv() == None`) means the other side is gone: stop
  cleanly, don't spin.
- **Actor pattern** for a resource that one task should own (a connection, a file, a
  device): an `enum Command { Get { key, reply: oneshot::Sender<…> }, … }` over a bounded
  `mpsc`. Not for everything — shared state behind a short `Mutex` is simpler where it
  works.

## Futures and `Send`

- Futures passed to `tokio::spawn` or returned from axum handlers must be `Send`: don't
  hold `Rc`, `RefCell` borrows or std mutex guards across `.await`.
- Auto traits leak through `impl Future` and `async fn`; a library that promises `Send`
  futures asserts it in a test:
  `fn assert_send<T: Send>(_: T) {} assert_send(client.fetch(id));`.
- Edition 2024 `impl Trait` in return position captures all in-scope lifetimes; use
  `+ use<>` / `+ use<'a>` to capture less when a returned future must outlive a borrow.

## Hosting a synchronous application core

Multi-frontend applications keep their core **synchronous** (`applications.md`): one
owner, `App::execute`, background work as step-based jobs. tokio lives only in hosts and
network adapters that need it.

- A tokio host (HTTP server, MCP over HTTP, control channel) **owns `App` on a dedicated
  thread** and talks to it through a channel — the actor pattern above: requests carry the
  `Command` and a `oneshot::Sender` for the result; the actor thread loops over
  `blocking_recv()`, calls `execute`, `poll`s jobs and answers.
- For rare calls, `spawn_blocking` with the `App` behind one host-level `Mutex` is
  acceptable; keep the lock inside the blocking closure, never across `.await`.
- Never call `block_on` inside async code to reach the core.
- **Browser (wasm32)**: no tokio runtime. Async browser APIs run through
  `wasm_bindgen_futures::spawn_local`; those futures are `!Send` (single thread), so the
  core must not require `Send` futures there (`unsafe-ffi-wasm.md`).

## Testing async code

`#[tokio::test]` runs on a **current-thread** runtime by default;
`#[tokio::test(flavor = "multi_thread")]` when the test needs parallelism. Time-dependent
code: `#[tokio::test(start_paused = true)]` (tokio feature `test-util`) +
`tokio::time::advance` — no real sleeps. See `testing.md`.
