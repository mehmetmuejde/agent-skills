# Hangs, responsiveness and SwiftUI update cost

A hang is the main thread not handling events. Apple's tools start reporting at
**250 ms**; 250–500 ms counts as a micro hang, **> 500 ms** as a proper hang. Smooth
interaction needs far less: under **100 ms** for a discrete action, under one refresh
interval per frame (8.3 ms at 120 Hz, 16.7 ms at 60 Hz) and ideally **< 5 ms** per
update while scrolling or animating.

## Find it

1. Reproduce on a Release build (Product › Profile) — see `instruments-xctrace.md`.
2. Record **Time Profiler** (or **CPU Profiler**) with the **Hangs** instrument; for
   SwiftUI screens use the **SwiftUI** template.
3. Select the hang interval, then decide which kind it is:
   - **Busy main thread** — high CPU on the main thread during the hang. The call tree
     or **Top Functions** (Xcode 27; merges a function's scattered call-tree nodes and
     ranks by self time) shows the expensive work. Fix: do less, cache, or move it off
     the main actor.
   - **Blocked main thread** — low CPU, the thread is waiting. Add **System Trace** and
     look at thread states, syscalls and VM faults for the interval: synchronous file
     I/O, locks, semaphores, XPC/IPC, `DispatchQueue.main.sync` from elsewhere.
4. With async code, add **Swift Concurrency** and (Xcode 27) **Swift Executors** to see
   which work ran on the main actor versus the cooperative pool.
5. Before you change anything, write down the hang duration so the after-run can be
   compared (Run Comparisons, same signpost interval).

## Common causes and fixes

- **`Task {}` inherits the caller's actor.** A `Task { heavyWork() }` started from a
  SwiftUI `body`, action or `@MainActor` model still runs on the main actor. Move the
  work into a `nonisolated` function marked `@concurrent` (Swift 6.2+), or into an actor
  that owns the state. `Task.detached` also works but drops priority and task-locals
  (default `.medium`); use it only when you mean it.

  ```swift
  struct ReportBuilder {
      @concurrent
      func build(from rows: [Row]) async -> Report {
          // CPU-heavy work, runs on the cooperative pool
          Report(rows: rows.sorted())
      }
  }

  @MainActor @Observable final class ReportModel {
      private(set) var report: Report?
      func refresh(rows: [Row]) async {
          report = await ReportBuilder().build(from: rows)
      }
  }
  ```

- With the `NonisolatedNonsendingByDefault` feature (part of Approachable Concurrency),
  a plain `nonisolated async` function runs on the **caller's** actor — it is *not*
  automatically background work. Only `@concurrent` moves it off.
- **Synchronous I/O on the main actor**: `Data(contentsOf:)`, `Data.write(to:)`,
  `FileManager` enumeration, JSON encoding of large values, Keychain or database calls.
  Do them in `@concurrent` functions and hop back with the result.
- **Heavy `static let shared` initialisers** run on first access — often the main thread
  during launch or the first tap. Make them cheap and load lazily off the main actor.
- **Faking synchronous APIs** with `DispatchSemaphore.wait()` / `DispatchGroup.wait()`
  blocks a thread and causes priority inversions; Thread Performance Checker reports
  these. Use `async` APIs.
- **Too many threads** from ad-hoc `Thread`/queue creation — use Swift concurrency or
  shared queues.
- **Existentials in hot loops** (`any Protocol` arrays processed per frame) — prefer
  generics or concrete types where profiling shows dispatch cost.
- **Eager stacks/grids with hundreds of children** — use `LazyVStack`/`LazyVGrid`/`List`;
  eager stacks are fine (and lighter) for small, fixed content.

## SwiftUI: keep updates cheap

Use the **SwiftUI** instrument (Xcode 26+): the *Long View Body Updates* lane marks
bodies over **500 µs orange** and over **1000 µs red**; *Long Representable Updates*
covers `NSViewRepresentable`/`UIViewRepresentable`. The **Cause & Effect Graph** answers
"what marked this view as outdated?". Xcode 27 adds a *Summary of Updates* action and
records layout passes, including why a layout could not be reused.

Rules:

- `body` only describes views. No formatter creation, sorting, filtering, bundle or file
  lookups, or large string building in `body`, `View.init`, `onAppear` or gesture
  `onChanged` — compute in the model and store the result.
- **Observation granularity**: a view depends on every `@Observable` property it reads,
  directly or through helpers. Reading a whole array makes every element change
  invalidate the view. Give list rows their own small observable objects or pass only
  the values a row shows; mark non-UI storage `@ObservationIgnored`.
- Migrate `ObservableObject` to `@Observable` — the old protocol invalidates on any
  `@Published` change.
- Pass subviews only the data they need and extract subviews so invalidation stays
  local.
- Don't put fast-changing values (geometry, timers, scroll offsets) into the
  environment — every reader updates.
- Avoid storing closures in views; captured state widens dependencies. Call
  `@ViewBuilder` content closures in `init` and store the result.
- `GeometryReader`/`onGeometryChange` that write state on every frame cause update
  loops — compare against a threshold before writing, or use a custom `Layout`.
- `ForEach`: cheap, stable identifiers (never `\.self` on non-unique data), a constant
  number of views per element (no `if` around the whole row, no `AnyView` rows), filter
  in the model, not inside `ForEach`.
- **Lazy stacks (WWDC26)**: one subview per element; don't depend on the total content
  size or absolute offsets; keep transforms inside the row's frame; no layout changes
  after a row appears; keep important state outside leaf `@State` (rows are recycled).
  Prefetching runs `init` but discards work started in `onAppear`, so prepare a row's
  data in `init` (cheaply) or in the model.
- Debug one view's updates with `let _ = Self._printChanges()` inside `body` — Debug
  builds only, never commit it.
- `ImageRenderer` is main-actor bound; render on demand (export, share), never inside
  `body` or per frame.
- Expect a burst of long updates right after launch; judge steady-state interaction.

## Verify

- Same scenario, same build configuration, same device: compare before/after with Run
  Comparisons filtered to the same signpost interval.
- Protect the fix with an `XCTOSSignpostMetric` or `XCTHitchMetric` test
  (`performance-tests.md`).
- Field data: hang rate and hitches in Organizer / MetricKit (`field-data.md`).

## Sources

- Improving app responsiveness — https://developer.apple.com/documentation/xcode/improving-app-responsiveness
- Understanding and improving SwiftUI performance — https://developer.apple.com/documentation/xcode/understanding-and-improving-swiftui-performance
- Diagnosing performance issues early — https://developer.apple.com/documentation/xcode/diagnosing-performance-issues-early
- WWDC26 268 Profile, fix, and verify — https://developer.apple.com/videos/play/wwdc2026/268/
- WWDC26 321 Dive into lazy stacks and scrolling with SwiftUI — https://developer.apple.com/videos/play/wwdc2026/321/
- WWDC25 306 Optimize SwiftUI performance with Instruments — https://developer.apple.com/videos/play/wwdc2025/306/
- WWDC23 10248 Analyze hangs with Instruments — https://developer.apple.com/videos/play/wwdc2023/10248/
- WWDC23 10160 Demystify SwiftUI performance — https://developer.apple.com/videos/play/wwdc2023/10160/
- SE-0461 Async function isolation — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
