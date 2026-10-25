# Energy, idle cost and background work on macOS

A Mac app that is idle should use **~0 % CPU** and wake the CPU **at most about once per
second**. Menu bar apps, agents and apps that stay open all day are judged by their idle
cost more than by their peak speed.

Caveat: Apple's only Mac-specific energy guide is the archived *Energy Efficiency Guide
for Mac Apps* (last updated 2016). Its concepts (App Nap, timer coalescing, idle
wakeups) still apply; UI details may differ. **Power Profiler is iPhone/iPad only** — on
the Mac use the tools below.

## Measure

| Tool | What it shows |
|---|---|
| Xcode Energy Impact gauge (Debug navigator) | CPU, wakeups/s, overhead while running from Xcode |
| Activity Monitor › Energy | Energy Impact, 12-hour average, **App Nap**, **Preventing Sleep**, **Idle Wake Ups** |
| Instruments: Activity Monitor template, Time Profiler | per-process CPU over time, where the CPU goes |
| `top` | CPU, memory, power score, idle wakeups per sample |
| `powermetrics` | per-process energy, CPU/GPU power, thermal — **needs sudo, ask first** |
| `timerfires` | which timers fire, with call stacks |
| `pmset -g assertions` | who prevents sleep |

```sh
top -l 30 -s 2 -pid <pid> -stats pid,command,cpu,mem,power,idlew
sudo powermetrics --samplers tasks,cpu_power,thermal -i 1000 -n 60 --show-process-energy -o pm.txt
timerfires -n App -s -t 60            # may need sudo; -s shows stacks for sleep-type timers
pmset -g assertions
```

Measure idle explicitly: run the scenario, then leave the app alone for 5 minutes with its
windows in the state users leave them (menu closed, window in background, window
minimised) and record CPU and IDLEW. Repeat on battery for laptops.

## App Nap

The system naps an app that is not frontmost, has no visible drawing, plays no audio and
holds no power assertion. Napped apps get lower CPU priority, coalesced timers and
throttled I/O.

- Don't rely on App Nap to make your app idle — stop work yourself when it is not
  visible (window occlusion, menu closed, app hidden).
- Work the user started and waits for (export, import, scan) may opt out while it runs:

  ```swift
  let activity = ProcessInfo.processInfo.beginActivity(
      options: .userInitiated, reason: "Exporting library")
  defer { ProcessInfo.processInfo.endActivity(activity) }
  try await exporter.run()
  ```

  End the activity as soon as the work finishes; a forgotten activity keeps the app out
  of App Nap forever. Use `.idleSystemSleepDisabled` only when the work must finish
  before sleep.

## Timers and polling

- Prefer **events** over polling: FSEvents / `DispatchSource` file-system sources,
  notifications (`NSWorkspace`, distributed), KVO/observation, XPC.
- Every repeating timer gets a **tolerance of at least 10 %** of its interval so the
  system can coalesce wakeups (`timer.tolerance = interval * 0.1`; dispatch timers:
  `leeway`). Invalidate timers you no longer need.
- Deferrable periodic work (cleanup, refresh, indexing): `NSBackgroundActivityScheduler`
  — the system picks a good moment:

  ```swift
  let scheduler = NSBackgroundActivityScheduler(identifier: "com.example.app.refresh")
  scheduler.repeats = true
  scheduler.interval = 60 * 60
  scheduler.tolerance = 10 * 60
  scheduler.qualityOfService = .utility
  scheduler.schedule { completion in
      Task {
          await refresher.refresh()
          completion(.finished)
      }
  }
  ```

- SwiftUI `TimelineView` schedules are hints; the system may update less often. Use
  coarse schedules (`.everyMinute`, `.periodic(from:by:)` with seconds, not
  milliseconds) and keep the content cheap. `.animation` schedules redraw every frame —
  only while something actually animates.

## Menu bar extras and always-running apps

- **Sample only while someone looks.** Process lists, `sysctl`/`proc_pidinfo`/IOKit
  queries, disk scans: start them when the menu or window opens and stop when it closes.
  Tie the work to the content's `.task {}` (cancelled on disappear) or to window
  occlusion, and verify with a signpost or log that it really stops.
- If the menu bar **label** shows live values, the sampling can't stop: use the coarsest
  interval that is still useful (seconds, not sub-second), add timer tolerance, sample
  the cheapest API, and update the label only when the displayed value changes.
- Cache expensive, slowly changing data (app icons, bundle metadata, volume info)
  instead of re-reading it per tick.
- Don't redraw the label with a fresh image per tick when the value is the same.
- Measure the polling cost on a 10–30 minute soak with the menu closed and open
  (`soak-testing.md`, plus `top … -stats cpu,power,idlew`). Budget it like any other
  feature: e.g. "menu closed: CPU < 0.5 %, IDLEW ≤ 1/s".

## Disk writes

- Write less and less often: batch saves, avoid rewriting whole files for small changes,
  don't log verbosely in Release. The Organizer flags apps writing **> 1 GB per 24 h**
  (on platforms where it reports).
- `XCTStorageMetric` in a performance test catches regressions in bytes written.

## Thermal state

`ProcessInfo.processInfo.thermalState` with `ProcessInfo.thermalStateDidChangeNotification`
— at `.serious`/`.critical` pause optional work (thumbnails, indexing, prefetching). The
policy is yours; Apple defines only the states.

## Sources

- Energy Efficiency Guide for Mac Apps (archive, 2016) — https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/
- ProcessInfo (beginActivity, thermalState) — https://developer.apple.com/documentation/foundation/processinfo
- NSBackgroundActivityScheduler — https://developer.apple.com/documentation/foundation/nsbackgroundactivityscheduler
- Timer.tolerance — https://developer.apple.com/documentation/foundation/timer/tolerance
- TimelineView — https://developer.apple.com/documentation/swiftui/timelineview
- MenuBarExtra — https://developer.apple.com/documentation/swiftui/menubarextra
- WWDC21 10181 Ultimate application performance survival guide — https://developer.apple.com/videos/play/wwdc2021/10181/
- `man top`, `powermetrics -h`, `man timerfires`, `man pmset` (macOS 27)
