---
name: xcode-macos-performance
description: Apply for performance work on native macOS apps in Swift/SwiftUI with Xcode — profiling with Instruments and xctrace (Time Profiler, CPU Profiler, SwiftUI, Hangs, Allocations, Leaks, System Trace, Swift Concurrency/Executors, Top Functions, Run Comparisons), memory leaks, retain cycles and growing memory, footprint and swap, hangs and spinning cursor, slow SwiftUI updates, high CPU, energy and idle wakeups, App Nap, menu bar and background apps that poll, launch time, performance tests with XCTest metrics and baselines, soak and load tests, performance budgets in CI, MetricKit and Organizer field data. Also for "App ist langsam", "hängt", "Speicherleck", "Arbeitsspeicher steigt", "CPU-Last zu hoch", "Lasttest", "Performance optimieren", "Energieverbrauch". Holds the rules that always apply — measure before changing, Release builds, one change at a time with before/after numbers, Apple's budgets, no work on the main actor that blocks, idle means idle — and points to references per topic. iOS/iPadOS apps use xcode-ios-performance; general Mac development uses xcode-macos-development; functional tests use xcode-macos-testing.
---

# macOS performance

Rules for finding and fixing performance problems in Mac apps. This file holds what
always applies; read the matching reference **before** working on that topic.

| Task | Read |
|---|---|
| Choose a template, record and export traces, Top Functions, Run Comparisons | `references/instruments-xctrace.md` |
| Leaks, retain cycles, growing footprint, memgraph tools (`leaks`, `heap`, `vmmap`, `footprint`) | `references/memory-leaks.md` |
| Hangs, spinning cursor, main-actor work, SwiftUI update cost, lazy stacks | `references/hangs-swiftui.md` |
| XCTest performance tests, metrics, signposts, baselines, CI numbers | `references/performance-tests.md` |
| Idle CPU, wakeups, App Nap, timers, menu bar polling, `top`/`powermetrics` | `references/energy-background.md` |
| Long-running soak and load tests, `scripts/soak.sh`, `scripts/analyze_soak.py` | `references/soak-testing.md` |
| MetricKit (`MetricManager`), StateReporting, Organizer | `references/field-data.md` |

## Tools — defaults

State: October 2026 — Xcode 27.1, Swift 6.4, macOS 27 SDK. Check with
`xcodebuild -version` and `xcrun xctrace list templates` before relying on a name.

- **Instruments 27**: Time Profiler, **CPU Profiler**, **SwiftUI** (long body updates,
  Cause & Effect Graph), Hangs, Animation Hitches, Allocations, Leaks, VM Tracker,
  System Trace, Swift Concurrency + **Swift Executors**, File Activity, App Launch,
  Activity Monitor. Analysis: **Top Functions**, **Run Comparisons** (Xcode 27).
  Processor Trace needs an M4 or later Mac.
- **xctrace** for scripted recording/export; **`leaks`, `heap`, `vmmap`,
  `malloc_history`, `footprint`** work directly on Mac processes and `.memgraph` files.
- **XCTest** for performance tests (`measure(metrics:)`, `XCTClockMetric`, `XCTCPUMetric`,
  `XCTMemoryMetric`, `XCTStorageMetric`, `XCTApplicationLaunchMetric`,
  `XCTOSSignpostMetric`, `XCTHitchMetric`). **Swift Testing has no performance API.**
- **Signposts**: `OSSignposter` with the `.pointsOfInterest` category.
- **Field data**: MetricKit `MetricManager` (macOS 27+); legacy `MXMetricManager` only
  for older deployment targets. No memory metrics on macOS.
- Energy: Xcode Energy gauge, Activity Monitor, `top`, `powermetrics` (sudo).
  **Power Profiler is iPhone/iPad only.**

**Detect before measuring.** Read the scheme (Profile and Test actions, build
configuration), existing test plans, signposts and performance tests. Ask which
scenario is slow and on which Mac (chip, memory, macOS version, data size).

## Method — always

- **Measure first.** No optimisation without a recording that shows the cause. Write
  down the number (duration, CPU %, footprint, wakeups) before changing code.
- **Release build** (Product › Profile, development-signed so tools can attach). Debug
  builds, the debugger, sanitizers and coverage distort every number.
- **Representative Mac and data**: the slowest supported chip and a heavy user's data
  set; note power state and other running apps.
- **One change at a time**, then record again under the same conditions. Compare with
  **Run Comparisons**, filtered to the same **signpost interval**.
- Check structural causes first (blocking, main-actor work, repeated work, missing
  caching, eager loading) before micro-optimising.
- **Protect every fix** with a performance test or a soak-test budget, and record the
  before/after numbers in the change description or the docs.
- Report exactly what was measured and how; say what was not measured.

## Budgets

| What | Budget | Source |
|---|---|---|
| Discrete interaction (click → result) | < 100 ms total, main thread well below | Apple, responsiveness |
| Per frame while scrolling/animating | < 1 refresh interval (8.3 ms @120 Hz), aim < 5 ms | Apple, responsiveness |
| Hang | reported from 250 ms; > 500 ms is a proper hang | Apple, WWDC23 |
| SwiftUI view body | orange > 500 µs, red > 1000 µs | SwiftUI instrument |
| Heap fragmentation | `% FRAG` ≤ ~25 % | WWDC21 |
| Idle app | ~0 % CPU, ≤ ~1 wakeup/s | Mac energy guide (2016) |
| Disk writes | far below 1 GB / 24 h | Organizer threshold |
| Soak growth | project budget, e.g. ≤ 5 MB/hour after warm-up | own budget |

Keep the project's budgets in the repository and as performance-test baselines.

## Leaks & memory — always

- macOS has **swap and no jetsam**: growth doesn't crash, it slows the whole Mac. The
  app must bound its own memory — there are no memory warnings.
- Strong capture of `self` in stored closures → `[weak self]`; `unowned` only with a
  guaranteed lifetime. Back references `weak`.
- Long-lived tasks (`for await` over notifications/streams) are stored and cancelled, or
  run in `.task {}`. Timers are invalidated.
- Caches are bounded and evicted; images are downsampled to display size.
- Distinguish leaks (Leaks), abandoned memory (Mark Generation, `heap -diffFrom`) and
  transient peaks (Allocations).

Details: `references/memory-leaks.md`.

## Hangs & responsiveness — always

- Nothing blocking on the main actor: no synchronous file, network, database or Keychain
  work, no semaphores or `DispatchGroup.wait()`.
- `Task {}` inherits the caller's actor; `nonisolated async` runs on the caller's actor
  with Approachable Concurrency. CPU-heavy work goes into `@concurrent` functions.
- Busy main thread → reduce or move work; blocked main thread → System Trace for the
  wait.

Details: `references/hangs-swiftui.md`.

## SwiftUI — always

- `body` is cheap: no formatting, sorting, filtering or I/O; derived values live in the
  model.
- `@Observable` (not `ObservableObject`); views read only what they show; per-row
  observable objects for large lists; fast-changing values not in the environment.
- Stable, cheap `ForEach` identities, a constant number of views per element, lazy
  containers for long content.
- `Self._printChanges()` only temporarily in Debug.

Details: `references/hangs-swiftui.md`.

## macOS specifics — always

- **Idle means idle**: no polling while nothing is visible; events over timers; timer
  tolerance ≥ 10 %; `NSBackgroundActivityScheduler` for deferrable work.
- **Menu bar extras and background apps** sample only while their UI is open; if the
  label shows live values, use the coarsest useful interval and measure the cost on a
  soak run.
- App Nap: don't depend on it; opt out only for user-initiated work with
  `beginActivity(options: .userInitiated, …)` and end it promptly.
- Launch time has no watchdog on macOS — still measure it (`XCTApplicationLaunchMetric`,
  App Launch template) and keep work out of launch.
- Thread Sanitizer and Address Sanitizer run on macOS — use them in separate runs.
- Commands that need root (`powermetrics`, `footprint`/`timerfires` on other users'
  processes) need approval first.

Details: `references/energy-background.md`, `references/soak-testing.md`.

## Workflow

1. **Symptom** — what is slow, how often, on which Mac and data; reproduce reliably.
2. **Template** — pick it from the table in `references/instruments-xctrace.md`.
3. **Measure** — Release build, record, note the numbers; add signposts around the
   scenario if missing.
4. **Hypothesis** — name the cause the trace shows (function, allocation site, wait).
5. **One fix**, smallest change that removes the cause.
6. **Verify** — same scenario, Run Comparisons; numbers before/after.
7. **Regression guard** — performance test (`references/performance-tests.md`) or soak
   budget (`references/soak-testing.md`).
8. **Report** — what changed, numbers before/after, how measured, what was not checked.

Stuck after two or three attempts on the same problem: stop, report what was measured,
what was tried and what is known, and ask before trying further variations.

## Related skills

- `xcode-macos-development` — architecture, concurrency and SwiftUI rules that prevent
  most problems.
- `xcode-macos-testing` — functional tests, test plans, CI and result bundles.
- `xcode-ios-performance` — the same work for iPhone and iPad (jetsam, Power Profiler).

## Sources

Written in our own words (no text or code copied) from Apple's Xcode, Instruments,
XCTest and MetricKit documentation, WWDC26/25/24/23/22/21 sessions, the (archived) Energy
Efficiency Guide for Mac Apps and the local man pages of the Xcode 27.1 tools; ideas
cross-checked against the MIT-licensed steipete/agent-scripts (instruments-profiling,
native-app-performance), CharlesWiltgen/Axiom (axiom-performance) and
AvdLee/SwiftUI-Agent-Skill (performance patterns). No material from PolyForm-licensed
skills. State: October 2026 (Xcode 27.1 / Swift 6.4).

Apple documentation:
- Improving your app's performance — https://developer.apple.com/documentation/xcode/improving-your-app-s-performance
- Improving app responsiveness — https://developer.apple.com/documentation/xcode/improving-app-responsiveness
- Understanding and improving SwiftUI performance — https://developer.apple.com/documentation/xcode/understanding-and-improving-swiftui-performance
- Reducing your app's memory use — https://developer.apple.com/documentation/xcode/reducing-your-app-s-memory-use
- Reducing your app's launch time — https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time
- Writing and running performance tests — https://developer.apple.com/documentation/xcode/writing-and-running-performance-tests
- XCTest performance tests — https://developer.apple.com/documentation/xctest/performance-tests
- Diagnosing memory, thread, and crash issues early — https://developer.apple.com/documentation/xcode/diagnosing-memory-thread-and-crash-issues-early
- Diagnosing performance issues early — https://developer.apple.com/documentation/xcode/diagnosing-performance-issues-early
- Analyzing the performance of your shipping app — https://developer.apple.com/documentation/xcode/analyzing-the-performance-of-your-shipping-app
- MetricKit — https://developer.apple.com/documentation/metrickit
- OSSignposter — https://developer.apple.com/documentation/os/ossignposter
- ProcessInfo — https://developer.apple.com/documentation/foundation/processinfo
- Energy Efficiency Guide for Mac Apps (archive, 2016) — https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/
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

Idea sources (MIT):
- steipete/agent-scripts — https://github.com/steipete/agent-scripts
- CharlesWiltgen/Axiom — https://github.com/CharlesWiltgen/Axiom
- AvdLee/SwiftUI-Agent-Skill — https://github.com/AvdLee/SwiftUI-Agent-Skill

Caveats: the Mac energy guide is a 2016 archive (concepts valid, UI may differ); older
Apple docs still name the removed "Energy Log" template; the `xcbaselines` format is
undocumented (never generate baselines by script); WWDC talks spell some memory-tool
flags with two dashes where the man pages use one; `xctrace help` shows `--device-name`
in an example but the option is `--device`; whether the Organizer shows metrics for a
Mac app depends on the distribution channel and is not confirmed in the docs; the
`time-profile` export schema comes from a secondary source — discover schemas with
`--toc`.
