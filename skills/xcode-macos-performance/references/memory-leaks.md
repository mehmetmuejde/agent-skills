# Memory on macOS: leaks, growth and footprint

macOS has **no jetsam for ordinary apps and has swap**: a growing app is not killed, it
pushes the system into compression and swapping, makes every other app slower and
shows up as "Memory Pressure" in Activity Monitor. The number that matters is the
**footprint** — dirty + compressed + swapped memory. macOS sends no memory warnings to
apps (and neither does the Simulator), so the app must bound its own memory.

## Three different problems

| Problem | What you see | Tool |
|---|---|---|
| **Leak** — unreachable memory (retain cycles, missing `deallocate`) | Leaks instrument, `leaks` | Memory Graph, `leaks -traceTree` |
| **Abandoned memory** — reachable but never used again (unbounded caches, growing arrays) | footprint grows, Leaks shows nothing | Allocations **Mark Generation**, `heap -diffFrom` |
| **Transient spike** — peak during one operation | high peak, returns to baseline | Allocations "Created & Destroyed", `XCTMemoryMetric` peak |

A "step pattern" (each repetition of the same action leaves footprint higher) is the
signature of persistent growth.

## Workflow

1. Reproduce the action several times in a Release build.
2. **Allocations** with Mark Generation before each repetition: memory that is still
   alive in every generation is the growth. Filter by "Created & Still Living".
3. **Memory Graph Debugger** (Debug navigator › Debug Memory Graph) for "who keeps this
   alive"; File › Export Memory Graph to save a `.memgraph`.
4. If weak/unowned references don't show in the graph, set **Reflection Metadata Level =
   All** for the debug build.
5. Fix, then compare footprint and generations again.

## Command-line tools (attach to a process, or read a `.memgraph`)

The man pages use **single-dash** options (`-summary`, `-sortBySize`,
`-fullStackHistory`); some WWDC talks write them with two dashes — follow the man page.

```sh
leaks App                                   # exit 0 = none, 1 = leaks, >1 = error
leaks -quiet -atExit -- /path/App.app/Contents/MacOS/App   # sets MallocStackLogging=lite
leaks App -outputGraph pre.memgraph         # writes a graph only (exit 0), no scan
leaks post.memgraph -diffFrom=pre.memgraph  # leaks that are new since pre
leaks App -traceTree <address>              # why is this block alive?
leaks App -referenceTree='MyClass' -groupByType

heap App -sortBySize -H                     # what is on the heap, by size
heap post.memgraph -diffFrom=pre.memgraph   # objects new since pre
heap App -addresses 'MyClass'

vmmap -summary App                          # regions; MALLOC zones and % FRAG
malloc_history App -callTree -invert        # needs MallocStackLogging
malloc_history App <address>

footprint -p App -f bytes -j fp.json        # footprint per category
footprint -p App --sample 10 --sample-duration 1800 -j soak.json
MallocStackLogging=lite /path/App.app/Contents/MacOS/App   # live allocations with stacks
```

- `leaks` with `-outputGraph` only writes the graph; run `leaks file.memgraph` for the
  scan and its exit code. The exit code makes it usable as a CI gate.
- Fragmentation: keep `% FRAG` in `vmmap -summary` at **≤ ~25 %**; group allocations
  with the same lifetime.
- `footprint` needs root for processes of other users (ask first); your own app works.
- Attaching requires `get-task-allow` (development signing); see `instruments-xctrace.md`.

## Common causes and fixes (Swift/SwiftUI)

- **Closure retain cycles**: an object stores a closure that captures `self` strongly —
  including passing `self.method` as a closure. Use `[weak self]`; `[unowned self]` only
  when the closure can't outlive the object (it crashes otherwise).
- **Two-way strong references** between objects (parent ↔ child, delegate) — make the
  back reference `weak`.
- **Tasks that never finish**: a `Task` keeps its captures until it completes. A loop like
  `for await note in NotificationCenter.default.notifications(named: …)` or over an
  `AsyncStream` never completes, so it keeps `self` alive. Store the task and `cancel()`
  it, or run it in SwiftUI `.task {}` (cancelled when the view disappears). For tasks
  that finish, `[weak self]` is rarely needed.
- Cancellation is cooperative: long loops check `Task.isCancelled` or call
  `try Task.checkCancellation()`.
- **Timers** (`Timer`, dispatch sources, run-loop timers) not invalidated keep their
  targets alive and keep waking the CPU.
- **Unbounded caches**: dictionaries keyed by something that never repeats, or that are
  never evicted. Bound the size (`NSCache` with `countLimit`/`totalCostLimit`), evict
  when content leaves the screen or the window closes.
- **Wrong cache key** (cache never hits, only grows).
- **Autoreleased objects in loops** (Foundation/AppKit APIs in tight loops) — wrap the
  loop body in `autoreleasepool { }`.
- **Images**: decoded size is width × height × 4 bytes, independent of file size.
  Downsample with ImageIO before display and drop large images when not visible:

  ```swift
  import ImageIO

  func thumbnail(at url: URL, maxPixelSize: Int) -> CGImage? {
      let noCache = [kCGImageSourceShouldCache: false] as CFDictionary
      guard let source = CGImageSourceCreateWithURL(url as CFURL, noCache) else { return nil }
      let options = [
          kCGImageSourceCreateThumbnailFromImageAlways: true,
          kCGImageSourceShouldCacheImmediately: true,
          kCGImageSourceCreateThumbnailWithTransform: true,
          kCGImageSourceThumbnailMaxPixelSize: maxPixelSize,
      ] as CFDictionary
      return CGImageSourceCreateThumbnailAtIndex(source, 0, options)
  }
  ```

- **Large buffers kept by long-lived objects** — release (`= nil`) after use, allocate
  lazily.
- **Core Data / SwiftData**: unsaved changes and registered objects stay in memory; save
  and reset contexts in batch jobs, fetch in batches.
- Manual `UnsafeMutablePointer.allocate` without `deallocate`.
- Tooling artefact: locals in functions that never return (`Never`) can look leaked.

## Sanitizers and checkers

- **Address Sanitizer** for memory corruption, **Thread Sanitizer** for data races —
  both work for macOS apps; run them in a separate test run (they distort performance).
- Main Thread Checker can be injected into an existing binary via
  `libMainThreadChecker.dylib`.

## Guard against regressions

- `XCTMemoryMetric(application:)` test for the heaviest workflow with
  `-enablePerformanceTestsDiagnostics YES` → pre/post memgraphs in the result bundle
  (`performance-tests.md`).
- Soak test for long-running apps (`soak-testing.md`).

## Sources

- Reducing your app's memory use — https://developer.apple.com/documentation/xcode/reducing-your-app-s-memory-use
- Diagnosing memory, thread, and crash issues early — https://developer.apple.com/documentation/xcode/diagnosing-memory-thread-and-crash-issues-early
- WWDC24 10173 Analyze heap memory — https://developer.apple.com/videos/play/wwdc2024/10173/
- WWDC21 10180 Detect and diagnose memory issues — https://developer.apple.com/videos/play/wwdc2021/10180/
- WWDC18 416 iOS Memory Deep Dive (image memory, ImageIO) — https://developer.apple.com/videos/play/wwdc2018/416/
- Task (Swift) — https://developer.apple.com/documentation/swift/task
- `man leaks`, `man heap`, `man vmmap`, `man malloc_history`, `footprint --help` (Xcode 27.1 / macOS 27)
