# Soak and load tests on iPhone and iPad

A soak test runs a realistic scenario for a long time and checks that memory and CPU
reach a **plateau**. On iOS a slow leak ends in jetsam — often only after an hour of
real use, in the background, or on the device with the least memory. A load test is the
same procedure with a scaled-up data set (10× what a heavy user has).

**Status of this procedure:** assembled from Apple's documentation and the tools' help
output; it was **not run end-to-end on a device** while writing this guide. Check each
command against your Xcode version (`xcrun xctrace help record`) the first time.

## Procedure

1. **Fixture** — Release configuration, development-signed (tools can attach), fixed
   data set seeded via launch arguments or a test fixture, the lowest-memory device you
   support, battery level and Low Power Mode noted, debugger not attached.
2. **Driver** — an XCUITest that repeats the workflow N times (open, scroll, edit, close,
   background/foreground), or an internal soak mode behind a launch argument (internal
   builds only).
3. **Warm-up** — one iteration before measuring.
4. **Mark iterations** with `OSSignposter` events so traces line up with the workload.
5. **Record** on the device:

   ```sh
   xcrun xctrace list devices
   # memory over time, only the last 10 minutes of allocation events kept
   xcrun xctrace record --device '<device name or UDID>' --template 'Allocations' \
     --window 10m --time-limit 1h --output soak.trace --attach App
   # lighter: process-level CPU and memory over time
   xcrun xctrace record --device '<device name or UDID>' --template 'Activity Monitor' \
     --time-limit 1h --output soak-am.trace --attach App
   xcrun xctrace export --input soak-am.trace --toc     # discover the table schemas
   ```

   Alternatively use the Xcode memory gauge / memory report while the UI test runs.
6. **Snapshot diff** — export a memory graph after warm-up and at the end (Xcode Debug
   Memory Graph › File › Export, or `-enablePerformanceTestsDiagnostics YES` for memory
   metrics in performance tests), then on the Mac:

   ```sh
   leaks post.memgraph                         # exit 0 none, 1 leaks
   leaks post.memgraph -diffFrom=pre.memgraph
   heap post.memgraph -diffFrom=pre.memgraph -sortBySize
   vmmap -summary post.memgraph                # % FRAG ≤ ~25 %
   ```

7. **Evaluate** — footprint after warm-up should be flat. A steady slope or a staircase
   (each iteration leaves a step) is persistent growth; transient peaks are fine if they
   stay far from the device limit. Compare the peak with what the lowest-memory device
   allows (jetsam reports show the limit in practice).
8. **Gate** — new leaks or growth above the budget (e.g. MB per hour, or MB per
   iteration) fail the run; keep traces, memgraphs and numbers as artifacts.
9. **Background check** — send the app to the background mid-run, wait, return: memory
   at suspension should drop; the app should resume, not relaunch.

## In a performance test

A bounded variant runs in CI as a UI-test performance test: loop the workflow inside
`measure(metrics: [XCTMemoryMetric(application: app)])`. Xcode reports the peak and the
growth from start to end of each iteration — growth that doesn't return to ~0 across
iterations is the same staircase. See `performance-tests.md`.

## Simulator as a quick pre-check

Simulator apps are Mac processes, so `footprint` can sample them:

```sh
footprint -p App --sample 10 --sample-duration 1800 -f bytes -j soak.json
```

The JSON has `samples[]` with `start_time.wall_time_s` and `processes[].footprint` in
bytes; fit a line through it to get MB/hour with this skill's `scripts/analyze_soak.py`
(`python3 -I scripts/analyze_soak.py soak.json --max-mb-per-hour 5`). Simulator numbers differ from devices
(Mac memory, no limit, no jetsam) — use them to spot growth, never to judge headroom.

## Load scenarios worth having

- Largest realistic data set × the most expensive workflow (import, sync, search,
  photo grid).
- Repeated push/pop of screens and open/close of sheets (leaked view models and
  observers).
- Long scrolling of the biggest list with images (decode/cache growth).
- Background/foreground cycles, low-memory situations (another heavy app; Device Hub
  *Simulate Memory Pressure* in Xcode 27.2 for simulators).
- Extensions (widgets, share, notification service) with their much lower limits.

## Sources

- Reducing your app's memory use — https://developer.apple.com/documentation/xcode/reducing-your-app-s-memory-use
- Writing and running performance tests — https://developer.apple.com/documentation/xcode/writing-and-running-performance-tests
- WWDC24 10173 Analyze heap memory — https://developer.apple.com/videos/play/wwdc2024/10173/
- WWDC21 10180 Detect and diagnose memory issues — https://developer.apple.com/videos/play/wwdc2021/10180/
- Xcode 27 / 27.2 Release Notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- `man xctrace`, `man leaks`, `man heap`, `man vmmap`, `footprint --help` (Xcode 27.1)
