# Launch, hitches, energy and background work on iPhone and iPad

## Launch

- **Launch time** in the Organizer = tap on the icon → first frame after the static
  launch screen. Measure **cold** launches (after reboot, after a memory-heavy app
  evicted yours) and **warm** launches (after force-quit) separately; resume from the
  background is a third case.
- Tools: **App Launch** template, `XCTApplicationLaunchMetric(waitUntilResponsive: true)`
  in a UI-test performance test, MetricKit `TimeToFirstDrawMetric`,
  `ApplicationResumeTimeMetric` and `ExtendedLaunchMetric`
  (`MetricManager.trackLaunchTask(id:)` for work after the first frame that the user
  still waits for).
- The **watchdog** kills launches and scene creation that take too long — crash reports
  with `0x8badf00d` and a "scene-create watchdog transgression"; Apple's example shows a
  ~20 s wall-clock allowance. Treat any launch near seconds as a bug long before that.
- The debugger disables the watchdog — measure launches without Xcode attached
  (Profile, TestFlight, or launch from the home screen).

Reduce launch work:

- Fewer dynamic frameworks (merge them; mergeable libraries in Release).
- No static initialisers: Objective-C `+load`, C++ static constructors,
  `__attribute__((constructor))`, heavy Swift globals touched at launch.
- `application(_:didFinishLaunchingWithOptions:)`, the `App` initialiser and the first
  scene do only what the first frame needs; everything else is deferred or runs off the
  main actor afterwards.
- A simple first view; load data asynchronously with placeholders.
- Mark remaining startup phases with Points-of-Interest signposts so App Launch shows
  them.

## Hangs and hitches

- **On-device Hang Detection**: Settings › Developer › Hang Detection (threshold
  ≥ 250 ms) shows hang notifications with logs for development-signed and TestFlight
  builds — useful while testing away from Xcode.
- **Animation Hitches** template on a real, preferably older device for scroll and
  animation stutter; `XCTHitchMetric(application:)` (iOS 26+) or
  `XCTOSSignpostMetric.scrollingAndDecelerationMetric` in performance tests; Organizer
  **Hitches** metric (Xcode 27) for the field.
- Causes and fixes: `hangs-swiftui.md`.

## Power and energy

- **Power Profiler** (iPhone/iPad, iOS/iPadOS 26+) in Instruments shows system power and
  your app's CPU, GPU, display and networking impact; it also records thermal state.
- **On-device Performance Trace** (Settings › Developer › Performance Trace) records up
  to ~10 h without Xcode, for apps installed from Xcode, TestFlight or enterprise
  distribution — ideal for "battery drain during a real day" reports.
- While the device charges, system power reads 0 — profile on battery, using wireless
  debugging if you need Xcode.
- Power numbers are **not comparable across device models**. Compare variants on the
  same device, several runs each, averaged, under the same conditions.
- Typical wins: lazy containers instead of eager ones for long content, caching instead
  of recomputing, batching network requests, discretionary background `URLSession` for
  non-urgent transfers, lower location accuracy, stopping animations and timers that
  are off-screen.

## Background execution

- After `applicationDidEnterBackground` / scene `.background` the app has a few seconds.
  Before starting work that must finish, call
  `UIApplication.shared.beginBackgroundTask(withName:expirationHandler:)` and **always**
  call `endBackgroundTask(_:)` — also from the expiration handler. Forgotten tasks lead
  to "Task Timeout" terminations.
- Longer or periodic work belongs in BackgroundTasks (`BGAppRefreshTask`,
  `BGProcessingTask`, `BGContinuedProcessingTask`) or background `URLSession`.
- Extensions use `ProcessInfo.performExpiringActivity(withReason:using:)`.
- Holding file locks (e.g. a SQLite database in an App Group) while suspended causes
  "File Lock" terminations — finish or release before suspension.
- Release memory when entering the background (`memory-leaks.md`): lower memory at
  suspension means fewer background terminations.
- The debugger keeps the app from suspending — test background behaviour without it.

## Thermal state and Low Power Mode

```swift
let info = ProcessInfo.processInfo
if info.thermalState == .serious || info.thermalState == .critical {
    // pause prefetching, lower frame rate, defer indexing
}
if info.isLowPowerModeEnabled {
    // skip optional background refresh and visual effects
}
// observe: ProcessInfo.thermalStateDidChangeNotification,
//          Notification.Name.NSProcessInfoPowerStateDidChange
```

Apple defines the states; how the app reacts is a product decision — reduce optional
work first, never the user's primary task.

## Network and disk

- Batch requests, avoid polling, use HTTP caching; prefer push or background fetch over
  timers.
- Disk writes: batch saves, avoid rewriting large files for small changes; the Organizer
  flags > 1 GB/24 h. `XCTStorageMetric` catches regressions.

## Sources

- Reducing your app's launch time — https://developer.apple.com/documentation/xcode/reducing-your-app-s-launch-time
- Addressing watchdog terminations — https://developer.apple.com/documentation/xcode/addressing-watchdog-terminations
- Reduce terminations in your app — https://developer.apple.com/documentation/xcode/reduce-terminations-in-your-app
- Extending your app's background execution time — https://developer.apple.com/documentation/uikit/extending-your-app-s-background-execution-time
- Measuring your app's power use with Power Profiler — https://developer.apple.com/documentation/xcode/measuring-your-app-s-power-use-with-power-profiler
- Improving app responsiveness — https://developer.apple.com/documentation/xcode/improving-app-responsiveness
- ProcessInfo (thermalState, isLowPowerModeEnabled) — https://developer.apple.com/documentation/foundation/processinfo
- WWDC25 226 Profile and optimize power usage in your app — https://developer.apple.com/videos/play/wwdc2025/226/
- WWDC22 10082 Track down hangs with Xcode and on-device detection — https://developer.apple.com/videos/play/wwdc2022/10082/
- WWDC26 222 Meet the new MetricKit — https://developer.apple.com/videos/play/wwdc2026/222/
