# Memory on iPhone and iPad: limits, jetsam, leaks and growth

iOS has **no swap**. Every app has a per-device memory limit; exceeding it terminates
the app (**jetsam**). In the foreground that looks like a crash to the user; in the
background it means the app cold-launches next time and loses state. App extensions
(widgets, share, keyboard, notification service) have **much lower** limits.

The number that matters is the **footprint**: dirty + compressed memory (pages are
16 KB). Field data reports **peak memory** and **memory at suspension** — lower memory at
suspension means fewer background terminations.

## Three different problems

| Problem | What you see | Tool |
|---|---|---|
| **Leak** — unreachable memory (retain cycles) | Leaks instrument, memory graph | Memory Graph Debugger |
| **Abandoned memory** — reachable but never used again (unbounded caches) | footprint grows, Leaks shows nothing | Allocations **Mark Generation** |
| **Transient spike** — peak during one operation | high peak, jetsam during the peak | Allocations, `XCTMemoryMetric` peak |

A staircase (each repetition leaves footprint higher) is persistent growth.

## Workflow

1. Reproduce on a **real device**, ideally the one with the least memory you support.
   The Simulator runs on the Mac's memory: no limit, no jetsam, no memory warnings
   (Xcode 27.2 adds *Simulate Memory Pressure* in Device Hub for simulators), and the
   memory gauge is always green.
2. **Allocations** with Mark Generation before each repetition; filter "Created & Still
   Living".
3. **Memory Graph Debugger** for "who keeps this alive"; File › Export Memory Graph
   writes a `.memgraph`.
4. If weak/unowned references are missing from the graph, set **Reflection Metadata
   Level = All** in the debug build.
5. Fix, then measure footprint and generations again.

## Command-line analysis

`leaks`, `heap`, `vmmap` and `malloc_history` can't attach to processes on a device.
Run them on the Mac against an exported `.memgraph` (from Xcode or from
`-enablePerformanceTestsDiagnostics YES` result bundles). Simulator apps are Mac
processes, so the tools also attach to them directly — but simulator numbers are not
representative.

```sh
leaks app.memgraph                           # exit 0 none, 1 leaks, >1 error
leaks post.memgraph -diffFrom=pre.memgraph   # only leaks new since pre
heap post.memgraph -diffFrom=pre.memgraph    # objects new since pre
heap app.memgraph -sortBySize -H
vmmap -summary app.memgraph                  # regions, % FRAG
leaks app.memgraph -traceTree <address>
```

Man pages use single-dash options (`-summary`, `-sortBySize`); some WWDC talks write
two dashes — follow the man page.

## Jetsam and memory reports

- Jetsam event reports (JSON, no backtraces): Xcode › Devices and Simulators › device
  logs, or Settings › Privacy & Security › Analytics & Improvements › Analytics Data
  (`JetsamEvent-…`). Check `largestProcess`, the `reason` of your process (e.g. per-process
  limit) and `pageSize`.
- Exceeding the limit while debugging shows `EXC_RESOURCE` (MEMORY).
- MetricKit (iOS 27): `PeakMemoryMetric`, `SuspendedMemoryMetric` and
  `MemoryExceptionDiagnostic` (`field-data.md`).

## Respond to memory pressure

- Listen for `UIApplication.didReceiveMemoryWarningNotification` (or
  `didReceiveMemoryWarning` in view controllers) and free caches **quickly** — don't walk
  the whole object graph.
- `NSCache` with `countLimit`/`totalCostLimit` evicts automatically; `NSPurgeableData`
  for data you can recreate (don't put it inside an `NSCache`).
- Allocate large amounts gradually instead of in one burst.
- `os_proc_available_memory()` (iOS 13+) returns limit − footprint: advisory only, read it
  when needed, don't cache it, and don't use it to grow up to the limit.
- Release large resources when entering the background (images, decoded media, caches).
- The `com.apple.developer.kernel.increased-memory-limit` entitlement exists for apps
  that genuinely need more memory; it is not a fix for leaks or unbounded caches.

## Common causes and fixes (Swift/SwiftUI)

- **Closure retain cycles**: stored closures capturing `self` strongly, including
  `self.method` passed as a closure → `[weak self]`; `unowned` only with a guaranteed
  lifetime.
- **Two-way strong references** (parent ↔ child, delegates) → `weak` back reference.
- **Tasks that never finish** (`for await` over notifications or an `AsyncStream`) keep
  captures alive → store and `cancel()` them, or use SwiftUI `.task {}`. Finishing tasks
  release their captures; `[weak self]` is rarely needed there.
- Long loops check `Task.isCancelled` / `try Task.checkCancellation()`.
- Timers and `CADisplayLink`s not invalidated keep their targets alive.
- **Unbounded caches** and wrong cache keys; evict when content scrolls away or the app
  goes to the background.
- **Autoreleased objects in loops** → `autoreleasepool { }` per iteration.
- **Images**: decoded size is width × height × 4 bytes regardless of file size. Show
  thumbnails at display size:

  ```swift
  // UIKit, iOS 15+: decode at the target size off the main actor
  let thumbnail = await image.byPreparingThumbnail(ofSize: CGSize(width: 300, height: 300))
  ```

  or downsample from the file with ImageIO without decoding the full image:

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

- **Core Data / SwiftData**: unsaved changes stay in memory; save in batches and reset
  contexts in long imports, fetch in batches — balance against disk writes.
- Large buffers held by long-lived objects → release after use, allocate lazily.
- Group allocations by lifetime to limit fragmentation (`% FRAG` ≤ ~25 %).

## Sanitizers

Address Sanitizer works on devices and simulators. **Thread Sanitizer does not run on
iOS devices** — run it in the Simulator. Keep sanitizer runs separate from performance
runs.

## Guard against regressions

- `XCTMemoryMetric(application:)` UI test for the heaviest workflow with
  `-enablePerformanceTestsDiagnostics YES` (pre/post memgraphs) — `performance-tests.md`.
- Long-running check on a device — `soak-testing.md`.

## Sources

- Reducing your app's memory use (incl. responding to low-memory warnings, jetsam event reports) — https://developer.apple.com/documentation/xcode/reducing-your-app-s-memory-use
- os_proc_available_memory — https://developer.apple.com/documentation/os/os_proc_available_memory
- Reduce terminations in your app — https://developer.apple.com/documentation/xcode/reduce-terminations-in-your-app
- Diagnosing memory, thread, and crash issues early — https://developer.apple.com/documentation/xcode/diagnosing-memory-thread-and-crash-issues-early
- WWDC24 10173 Analyze heap memory — https://developer.apple.com/videos/play/wwdc2024/10173/
- WWDC21 10180 Detect and diagnose memory issues — https://developer.apple.com/videos/play/wwdc2021/10180/
- WWDC18 416 iOS Memory Deep Dive — https://developer.apple.com/videos/play/wwdc2018/416/
- Xcode 27.2 Release Notes (Simulate Memory Pressure) — https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes
- `man leaks`, `man heap`, `man vmmap` (macOS 27)
