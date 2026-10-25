# Performance tests (XCTest), signposts and budgets in CI

Performance tests turn a measured budget into a regression gate. **Swift Testing has no
performance API** (its `.timeLimit` trait only accepts minutes and is a hang guard, not a
measurement) — performance tests are XCTest, which may live in the same target as Swift
Testing tests.

## APIs

- `measure { … }` — wall clock with the class's `defaultMetrics`.
- `measure(metrics:block:)`, `measure(metrics:options:block:)`, `measure(options:block:)`.
- `XCTMeasureOptions`: `iterationCount` (default **5**; the block runs
  `iterationCount + 1` times and the **first run is discarded** as warm-up);
  `invocationOptions` `.manuallyStart` / `.manuallyStop` with `startMeasuring()` /
  `stopMeasuring()` to keep setup and reset out of the measured region.
- Override `defaultMetrics` / `defaultMeasureOptions` per test class.

## Metrics

| Metric | Measures | Notes |
|---|---|---|
| `XCTClockMetric()` | monotonic wall time | |
| `XCTCPUMetric()`, `(application:)`, `(limitingToCurrentThread:)` | CPU time, cycles, instructions retired | |
| `XCTMemoryMetric()`, `(application:)` | physical memory: peak during the block and growth start→end | |
| `XCTStorageMetric()`, `(application:)` | logical bytes written | |
| `XCTApplicationLaunchMetric()`, `(waitUntilResponsive:)` | launch to first frame (or until responsive) | macOS 11+/iOS 14+ |
| `XCTOSSignpostMetric(subsystem:category:name:)` | duration of your signpost interval | |
| `XCTOSSignpostMetric.scrollingAndDecelerationMetric` | scroll hitches | macOS 11+/iOS 15+ |
| `XCTOSSignpostMetric.navigationTransitionMetric` | push/pop transitions | **not on macOS** |
| `XCTHitchMetric(application:)` | hitches while the block runs | macOS 26+/iOS 26+ |

`(application:)` initialisers come from XCUIAutomation and need a **UI-test target**
with an `XCUIApplication`. Deprecated: `XCTOSSignpostMetric.applicationLaunch`,
`scrollDecelerationMetric`, `scrollDraggingMetric`.

```swift
import XCTest

final class LaunchPerformanceTests: XCTestCase {
    func testLaunch() {
        measure(metrics: [XCTApplicationLaunchMetric(waitUntilResponsive: true)]) {
            XCUIApplication().launch()
        }
    }

    func testOpenLibrary() {
        let app = XCUIApplication()
        app.launch()
        let options = XCTMeasureOptions()
        options.invocationOptions = [.manuallyStop]
        measure(metrics: [
            XCTOSSignpostMetric(subsystem: "com.example.app", category: "PointsOfInterest",
                                name: "Load library"),
            XCTMemoryMetric(application: app),
        ], options: options) {
            app.buttons["library"].click()      // iOS: .tap()
            stopMeasuring()
            app.buttons["home"].click()         // reset outside the measured region
        }
    }
}
```

## Signposts

Mark the work you want to measure; the same names drive Instruments' Points of Interest
track, Run Comparisons and `XCTOSSignpostMetric`.

```swift
import os

let signposter = OSSignposter(subsystem: "com.example.app", category: .pointsOfInterest)

func loadLibrary() async throws -> Library {
    let state = signposter.beginInterval("Load library", id: signposter.makeSignpostID())
    defer { signposter.endInterval("Load library", state) }
    return try await store.loadLibrary()
}
```

`category: .pointsOfInterest` is the string `"PointsOfInterest"` — use that in
`XCTOSSignpostMetric`. Use `beginAnimationInterval` for animations. Signposts are cheap,
but don't emit them per element in hot loops.

## Test plan and build configuration

- Separate test plan **Performance**, selected with `-testPlan Performance`.
- The scheme's Test action builds **Release** for this plan; **Debug executable off**;
  **code coverage, sanitizers, Main Thread Checker and Thread Performance Checker off** —
  each one distorts timing and memory.
- Release has `ENABLE_TESTABILITY = NO`, so `@testable import` fails. Prefer UI-level
  performance tests (`XCUIApplication` + `(application:)` metrics) or measure public API
  of a package; enabling testability in a dedicated configuration slows the code.
- Run sanitizers (`-enableAddressSanitizer`, `-enableThreadSanitizer`,
  `-enableUndefinedBehaviorSanitizer`) in a **separate** run, never with perf tests.

## Baselines

- Set them in Xcode's performance result (Set Baseline, Edit, Max STDDEV). A test fails
  when the average is worse than the baseline by more than the allowed deviation; a gray
  marker means no baseline for this destination.
- Baselines are stored per **destination (host + device)** in
  `<project>.xcodeproj/xcshareddata/xcbaselines/` (packages:
  `.swiftpm/xcode/xcshareddata/xcbaselines/`). Commit the folder.
- The format is **undocumented** — never write or generate baseline files by script.
  A CI machine needs its own baselines set in Xcode; otherwise gate on numbers you
  extract yourself (below).

## Running and reading results

```sh
xcodebuild -scheme App -showTestPlans
xcodebuild test -scheme App -testPlan Performance -destination 'platform=macOS' \
  -resultBundlePath build/perf.xcresult -enablePerformanceTestsDiagnostics YES
#   iOS device: -destination 'platform=iOS,name=<device name>'
xcodebuild test … -only-testing:AppUITests/LaunchPerformanceTests/testLaunch
xcrun xcresulttool get test-results metrics --path build/perf.xcresult --compact
xcrun xcresulttool get test-results metrics --path build/perf.xcresult --test-id '<id>'
xcrun xcresulttool compare build/new.xcresult --baseline-path build/old.xcresult --tests
```

- `-enablePerformanceTestsDiagnostics YES` stores a ktrace for time/CPU metrics and
  **pre/post memgraphs** for memory metrics in the result bundle (XCTest enables malloc
  stack logging). Analyse the memgraphs as in `memory-leaks.md`.
- A failing perf test: Control-click the test diamond › *Profile "<test>"* opens it in
  Instruments.
- Keep the extracted numbers (JSON) as a CI artifact and compare against budgets you
  keep in the repository, e.g. a small table in the docs or a JSON file next to the
  tests — that works on any machine, unlike Xcode baselines.

## What to test

- Launch (`XCTApplicationLaunchMetric`), the most-used screens (signpost intervals),
  scrolling of the largest lists, memory after the heaviest workflow, bytes written by
  saves/imports. One test per budget; a regression should point at one feature.
- Tests should use fixed, realistic data sets (generated in setup), not the developer's
  real data.

## Sources

- Writing and running performance tests — https://developer.apple.com/documentation/xcode/writing-and-running-performance-tests
- XCTest performance tests and metric classes — https://developer.apple.com/documentation/xctest/performance-tests
- Organizing tests into test plans — https://developer.apple.com/documentation/xcode/organizing-tests-to-improve-feedback
- OSSignposter — https://developer.apple.com/documentation/os/ossignposter
- Build settings reference (ENABLE_TESTABILITY) — https://developer.apple.com/documentation/xcode/build-settings-reference
- WWDC26 267 Migrate to Swift Testing — https://developer.apple.com/videos/play/wwdc2026/267/
- WWDC21 10180 Detect and diagnose memory issues — https://developer.apple.com/videos/play/wwdc2021/10180/
- WWDC19 417 Improving battery life and performance — https://developer.apple.com/videos/play/wwdc2019/417/
- Swift Forums: performance test baselines (xcbaselines location, undocumented format) — https://forums.swift.org/t/performance-test-baselines-not-available-for-swift-packages/45621
