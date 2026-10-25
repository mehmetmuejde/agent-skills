# Field data: MetricKit, StateReporting and the Organizer

Lab profiling shows what happens on your machine; field data shows what happens on
users' machines. Use field data to pick what to profile and to confirm a fix shipped.

## MetricKit — new API (iOS 27+/macOS 27+)

- `MetricManager` with async sequences `metricReports` and `diagnosticReports`;
  reports are `Codable` value types (`MetricReport`, `DiagnosticReport`).
- Create **one long-lived instance** early at launch and keep it (it is not a
  singleton; several instances split the reports between them non-deterministically).
- Metric reports arrive at most once per 24 h; diagnostics as they occur.

```swift
import MetricKit

@MainActor final class FieldMetrics {
    private let manager = MetricManager()
    private var tasks: [Task<Void, Never>] = []

    func start(upload: @escaping @Sendable (Data) async -> Void) {
        let manager = self.manager
        tasks.append(Task {
            for await report in manager.metricReports {
                if let data = try? JSONEncoder().encode(report) { await upload(data) }
            }
        })
        tasks.append(Task {
            for await diagnostic in manager.diagnosticReports {
                if let data = try? JSONEncoder().encode(diagnostic) { await upload(data) }
            }
        })
    }
}
```

- Custom intervals: `MetricManager.logHandle(category:)` plus `mxSignpost(…)` produce
  `SignpostIntervalMetric` values in the daily report.
- Launch work after the first frame: `trackLaunchTask(id:)` (main actor) reports it as
  `ExtendedLaunchMetric`.

Availability (from the 27 SDK interfaces):

| Type | iOS 27 | macOS 27 |
|---|---|---|
| `HangTimeMetric`, `HitchTimeMetric`, `CPUTimeMetric`, `TimeToFirstDrawMetric`, `ApplicationResumeTimeMetric`, `ExtendedLaunchMetric`, `LogicalDiskWritesMetric` | yes | yes |
| `HangDiagnostic` (call stack tree, duration), `CPUExceptionDiagnostic`, `DiskWriteExceptionDiagnostic`, `CrashDiagnostic`, `AppLaunchDiagnostic` | yes | yes |
| **`PeakMemoryMetric`, `SuspendedMemoryMetric`, `MemoryExceptionDiagnostic`** | yes | **no** |

On macOS there is no field metric for memory — memory regressions on the Mac must be
caught with performance tests and soak tests (`soak-testing.md`).

## MetricKit — legacy API

`MXMetricManager` with an `MXMetricManagerSubscriber` (iOS 13+, macOS 12+) delivers
`MXMetricPayload` / `MXDiagnosticPayload`. Keep it only for deployment targets below 27;
Apple recommends migrating. Never run both for the same data without a reason —
decide per deployment target (`if #available(iOS 27, macOS 27, *)`).

## StateReporting (27+)

Attaches app state to metrics so reports can be split by phase ("importing",
"syncing", "idle"). Create the `MetricManager` with
`init(enabledStateReportingDomains:)`. Rules: narrow domains, **stable phases** (not
transient UI events), few states per domain; check in Instruments' Points of Interest
track that the states change where you expect before shipping. Reports flag
`hasExceededStateLimit` when you report too many.

## Organizer (Xcode 27)

Window › Organizer › your app:

- **Insights overview** and metrics: launch time, hang rate, **Hitches** (replaces
  Scrolling), memory, battery/energy, disk writes, **Storage**.
- **Hang rate** = seconds per hour the app was unresponsive for > 250 ms; look at median
  and 90th percentile, filter by device class.
- **Metric Goals**: targets per metric (battery, disk writes, hang rate, hitches, memory,
  storage), optionally compared with similar apps.
- Regression notifications fire when the latest version is ≥ 75 % worse than the average
  of the previous four.
- Diagnostics reports (hangs, disk writes, energy, launch) include call stacks;
  "Generate Recommendations" proposes fixes — treat them as hypotheses to verify with a
  profile.
- Data needs users who share analytics; TestFlight builds count.
- **Caveat (macOS):** whether the Organizer shows metrics for a Mac app depends on the
  distribution channel — this is not stated clearly in the docs reviewed; check the
  Organizer for your app instead of assuming. MetricKit works regardless.

## Using field data

1. Pick the worst metric for the most common device class / percentile.
2. Read the diagnostics call stacks; form a hypothesis.
3. Reproduce locally under similar conditions (older device, large data set, low
   memory), then profile — field stacks alone don't prove a fix.
4. After shipping, watch the metric for the new version; keep the before/after numbers.

## Privacy

Reports can contain paths, region format and device type. Upload only what you need,
over HTTPS, and declare collection in the privacy manifest and the App Store privacy
details.

## Sources

- MetricKit — https://developer.apple.com/documentation/metrickit
- WWDC26 222 Meet the new MetricKit — https://developer.apple.com/videos/play/wwdc2026/222/
- WWDC26 258 What's new in Xcode 27 — https://developer.apple.com/videos/play/wwdc2026/258/
- Analyzing the performance of your shipping app — https://developer.apple.com/documentation/xcode/analyzing-the-performance-of-your-shipping-app
- Analyzing responsiveness issues in your shipping app — https://developer.apple.com/documentation/xcode/analyzing-responsiveness-issues-in-your-shipping-app
- WWDC21 10181 Ultimate application performance survival guide — https://developer.apple.com/videos/play/wwdc2021/10181/
- Xcode 27 Release Notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
