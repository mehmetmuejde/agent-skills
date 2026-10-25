---
name: xcode-ios-performance
description: Apply for performance work on native iPhone and iPad apps in Swift/SwiftUI with Xcode — profiling with Instruments and xctrace on devices (Time Profiler, CPU Profiler, SwiftUI, Hangs, Animation Hitches, Allocations, Leaks, System Trace, Swift Concurrency/Executors, App Launch, Power Profiler, Top Functions, Run Comparisons), memory leaks, retain cycles, growing memory, memory limits and jetsam terminations, memory warnings, image memory, hangs and hitches, slow SwiftUI updates and scrolling, launch time and watchdog kills, battery drain, thermal state and Low Power Mode, background execution, performance tests with XCTest metrics and baselines, soak and load tests, performance budgets in CI, MetricKit and Organizer field data. Also for "App ist langsam", "ruckelt", "hängt", "Speicherleck", "Arbeitsspeicher steigt", "App wird beendet", "Akku", "Lasttest", "Performance optimieren". Holds the rules that always apply — measure on a real device before changing, Release builds, one change at a time with before/after numbers, Apple's budgets, stay far below the memory limit, no blocking work on the main actor — and points to references per topic. macOS apps use xcode-macos-performance; general iOS development uses xcode-ios-development; functional tests use xcode-ios-testing.
---

# iOS performance

Rules for finding and fixing performance problems in iPhone and iPad apps. This file
holds what always applies; read the matching reference **before** working on that topic.

| Task | Read |
|---|---|
| Choose a template, record on a device, export traces, Top Functions, Run Comparisons | `references/instruments-xctrace.md` |
| Memory limits, jetsam, memory warnings, leaks, images, memgraph analysis | `references/memory-leaks.md` |
| Hangs, main-actor work, SwiftUI update cost, lazy stacks and scrolling | `references/hangs-swiftui.md` |
| XCTest performance tests, metrics, signposts, baselines, CI numbers | `references/performance-tests.md` |
| Launch time, watchdog, hitches, Power Profiler, background time, thermal, Low Power Mode | `references/launch-energy-background.md` |
| Long-running soak and load tests on devices | `references/soak-testing.md` |
| MetricKit (`MetricManager`), StateReporting, Organizer | `references/field-data.md` |

## Tools — defaults

State: October 2026 — Xcode 27.1, Swift 6.4, iOS 27.1 SDK. Instruments 27 needs devices
on iOS 17+. Check with `xcodebuild -version` and `xcrun xctrace list templates`.

- **Instruments 27**: Time Profiler, **CPU Profiler**, **SwiftUI** (long body updates,
  Cause & Effect Graph), Hangs, **Animation Hitches**, Allocations, Leaks, VM Tracker,
  System Trace, Swift Concurrency + **Swift Executors**, App Launch, File Activity,
  Network, **Power Profiler** (iOS 26+). Analysis: **Top Functions**, **Run
  Comparisons**. Processor Trace needs an A18+ iPhone or M4 iPad Pro.
- **xctrace** with `--device` for scripted recordings; memgraph analysis with
  `leaks`/`heap`/`vmmap` on the Mac (they don't attach to device processes).
- **XCTest** performance tests (`measure(metrics:)`, `XCTApplicationLaunchMetric`,
  `XCTMemoryMetric`, `XCTCPUMetric`, `XCTClockMetric`, `XCTStorageMetric`,
  `XCTOSSignpostMetric`, `XCTHitchMetric`). **Swift Testing has no performance API.**
- **Signposts**: `OSSignposter` with the `.pointsOfInterest` category.
- **Field data**: MetricKit `MetricManager` (iOS 27+, incl. peak/suspended memory and
  memory exception diagnostics); legacy `MXMetricManager` for older deployment targets;
  Organizer metrics and goals.
- On device: Settings › Developer › **Hang Detection** and **Performance Trace**.

**Detect before measuring.** Read the scheme (Profile and Test actions), test plans,
existing signposts and performance tests, the deployment target and the extensions.
Ask which scenario is slow and on which device and iOS version.

## Method — always

- **Measure first**, on a **real device** — ideally the slowest and lowest-memory one you
  support. Simulator numbers (CPU, memory, energy) are not representative; the
  Simulator has no memory limit and no jetsam.
- **Release build** via Product › Profile; no debugger for launch, background and
  watchdog behaviour (the debugger disables the watchdog and suspension).
- Write down the numbers before changing code.
- **One change at a time**; record again under the same conditions and compare with
  **Run Comparisons** on the same **signpost interval**.
- Structural causes first (blocking, main-actor work, repeated work, eager loading,
  full-size images) before micro-optimising.
- **Protect every fix** with a performance test or soak budget; record before/after
  numbers in the change description or docs.
- Report exactly what was measured, on which device, and what was not measured.

## Budgets

| What | Budget | Source |
|---|---|---|
| Discrete interaction (tap → result) | < 100 ms total, main thread well below | Apple, responsiveness |
| Per frame while scrolling/animating | < 1 refresh interval (8.3 ms @120 Hz), aim < 5 ms | Apple, responsiveness |
| Hang | reported from 250 ms; > 500 ms is a proper hang | Apple, WWDC23 |
| SwiftUI view body | orange > 500 µs, red > 1000 µs | SwiftUI instrument |
| Launch | first frame as fast as possible; far from the watchdog | Apple, launch time |
| Memory | peak far below the smallest supported device's limit; low at suspension | Apple, memory |
| Heap fragmentation | `% FRAG` ≤ ~25 % | WWDC21 |
| Disk writes | far below 1 GB / 24 h | Organizer threshold |

Keep the project's budgets in the repository and as performance-test baselines.

## Leaks & memory — always

- Every app has a **memory limit**; crossing it kills the app (jetsam), extensions far
  earlier. Footprint = dirty + compressed memory; there is no swap.
- Respond to memory warnings quickly by freeing caches; use `NSCache` with limits;
  release large resources in the background.
- Images are downsampled to display size (`byPreparingThumbnail(ofSize:)` or ImageIO);
  decoded size is width × height × 4 bytes.
- `[weak self]` in stored closures; long-lived tasks stored and cancelled or run in
  `.task {}`; timers and display links invalidated.
- Distinguish leaks, abandoned memory (Mark Generation) and transient peaks.

Details: `references/memory-leaks.md`.

## Hangs & responsiveness — always

- Nothing blocking on the main actor: no synchronous I/O, database, Keychain or network
  calls, no semaphores or `DispatchGroup.wait()`.
- `Task {}` inherits the caller's actor; `nonisolated async` runs on the caller's actor
  with Approachable Concurrency. CPU-heavy work goes into `@concurrent` functions.
- Busy main thread → reduce or move work; blocked main thread → System Trace.

Details: `references/hangs-swiftui.md`.

## SwiftUI — always

- `body` is cheap: no formatting, sorting, filtering or I/O in `body`, `init`,
  `onAppear` or gesture handlers; derived values live in the model.
- `@Observable`; views read only what they show; per-row observable objects for large
  lists; fast-changing values not in the environment.
- Lazy stacks for long content with one subview per element, stable identities and a
  constant number of views per element; prepare row data in `init` or the model, not in
  `onAppear`.

Details: `references/hangs-swiftui.md`.

## iOS specifics — always

- **Launch**: no static initialisers, minimal work before the first frame, fewer
  dynamic frameworks; measure cold and warm launches without the debugger.
- **Hitches**: test scrolling and animations with Animation Hitches on an older device.
- **Energy**: Power Profiler or on-device Performance Trace on battery; compare on the
  same device model only; stop off-screen timers, animations and location updates.
- **Background**: `beginBackgroundTask` always paired with `endBackgroundTask`;
  BackgroundTasks for longer work; no file locks held while suspended.
- **Thermal state and Low Power Mode**: reduce optional work at `.serious`/`.critical`
  and in Low Power Mode.
- **Thread Sanitizer runs only in the Simulator**, not on devices; sanitizer runs are
  separate from performance runs.

Details: `references/launch-energy-background.md`, `references/soak-testing.md`.

## Workflow

1. **Symptom** — what is slow, how often, which device/iOS/data; reproduce reliably.
2. **Template** — from the table in `references/instruments-xctrace.md`.
3. **Measure** on a device with a Release build; note numbers; add signposts if missing.
4. **Hypothesis** — the cause the trace shows (function, allocation site, wait, launch
   phase).
5. **One fix**, the smallest change that removes the cause.
6. **Verify** — same scenario and device, Run Comparisons; numbers before/after.
7. **Regression guard** — performance test (`references/performance-tests.md`) or soak
   budget (`references/soak-testing.md`).
8. **Report** — what changed, numbers before/after, device and build, what was not
   checked.

Stuck after two or three attempts on the same problem: stop, report what was measured,
what was tried and what is known, and ask before trying further variations.

## Related skills

- `xcode-ios-development` — architecture, concurrency and SwiftUI rules that prevent most
  problems.
- `xcode-ios-testing` — functional tests, simulators, test plans, CI and result bundles.
- `xcode-macos-performance` — the same work for Mac apps (swap, App Nap, memory CLI
  tools, soak script).

## Sources

Written in our own words (no text or code copied) from Apple's Xcode, Instruments,
XCTest and MetricKit documentation, WWDC26/25/24/23/22/21 sessions and the local man
pages of the Xcode 27.1 tools; ideas cross-checked against the MIT-licensed
steipete/agent-scripts (instruments-profiling, native-app-performance),
CharlesWiltgen/Axiom (axiom-performance) and AvdLee/SwiftUI-Agent-Skill (performance
patterns). No material from PolyForm-licensed skills. State: October 2026 (Xcode 27.1 /
Swift 6.4).

Apple documentation:
- Improving your app's performance — https://developer.apple.com/documentation/xcode/improving-your-app-s-performance
- Improving app responsiveness — https://developer.apple.com/documentation/xcode/improving-app-responsiveness
- Understanding and improving SwiftUI performance — https://developer.apple.com/documentation/xcode/understanding-and-improving-swiftui-performance
- Reducing your app's memory use — https://developer.apple.com/documentation/xcode/reducing-your-app-s-memory-use
- Reducing your app's launch time — https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time
- Reduce terminations in your app — https://developer.apple.com/documentation/xcode/reduce-terminations-in-your-app
- Measuring your app's power use with Power Profiler — https://developer.apple.com/documentation/xcode/measuring-your-app-s-power-use-with-power-profiler
- Writing and running performance tests — https://developer.apple.com/documentation/xcode/writing-and-running-performance-tests
- XCTest performance tests — https://developer.apple.com/documentation/xctest/performance-tests
- Diagnosing memory, thread, and crash issues early — https://developer.apple.com/documentation/xcode/diagnosing-memory-thread-and-crash-issues-early
- Diagnosing performance issues early — https://developer.apple.com/documentation/xcode/diagnosing-performance-issues-early
- Analyzing the performance of your shipping app — https://developer.apple.com/documentation/xcode/analyzing-the-performance-of-your-shipping-app
- MetricKit — https://developer.apple.com/documentation/metrickit
- OSSignposter — https://developer.apple.com/documentation/os/ossignposter
- ProcessInfo — https://developer.apple.com/documentation/foundation/processinfo
- Xcode 27 Release Notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes

WWDC sessions:
- 2026/268 Profile, fix, and verify — https://developer.apple.com/videos/play/wwdc2026/268/
- 2026/222 Meet the new MetricKit — https://developer.apple.com/videos/play/wwdc2026/222/
- 2026/321 Dive into lazy stacks and scrolling with SwiftUI — https://developer.apple.com/videos/play/wwdc2026/321/
- 2025/306 Optimize SwiftUI performance with Instruments — https://developer.apple.com/videos/play/wwdc2025/306/
- 2025/308 Optimize CPU performance with Instruments — https://developer.apple.com/videos/play/wwdc2025/308/
- 2025/226 Profile and optimize power usage in your app — https://developer.apple.com/videos/play/wwdc2025/226/
- 2024/10173 Analyze heap memory — https://developer.apple.com/videos/play/wwdc2024/10173/
- 2023/10248 Analyze hangs with Instruments — https://developer.apple.com/videos/play/wwdc2023/10248/
- 2023/10160 Demystify SwiftUI performance — https://developer.apple.com/videos/play/wwdc2023/10160/
- 2022/10082 Track down hangs with Xcode and on-device detection — https://developer.apple.com/videos/play/wwdc2022/10082/
- 2021/10180 Detect and diagnose memory issues — https://developer.apple.com/videos/play/wwdc2021/10180/
- 2021/10181 Ultimate application performance survival guide — https://developer.apple.com/videos/play/wwdc2021/10181/
- 2018/416 iOS Memory Deep Dive — https://developer.apple.com/videos/play/wwdc2018/416/

Idea sources (MIT):
- steipete/agent-scripts — https://github.com/steipete/agent-scripts
- CharlesWiltgen/Axiom — https://github.com/CharlesWiltgen/Axiom
- AvdLee/SwiftUI-Agent-Skill — https://github.com/AvdLee/SwiftUI-Agent-Skill

Caveats: older Apple docs still name the removed "Energy Log" template; the
`xcbaselines` format is undocumented (never generate baselines by script); WWDC talks
spell some memory-tool flags with two dashes where the man pages use one; `xctrace help`
shows `--device-name` in an example but the option is `--device`; the `time-profile`
export schema comes from a secondary source — discover schemas with `--toc`; the
device soak procedure was not run end-to-end on a device.
