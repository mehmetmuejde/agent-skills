# Instruments and xctrace

Instruments in Xcode 27.1 needs target devices on iOS 17+ (watchOS 10+, tvOS 17+). Check
what your Xcode ships before relying on a template name:

```sh
xcrun xctrace version
xcrun xctrace list templates      # templates
xcrun xctrace list instruments    # single instruments to add with --instrument
xcrun xctrace list devices
```

## Template per symptom

| Symptom | Start with | Add |
|---|---|---|
| UI freezes, spinning cursor, "hängt" | Time Profiler | Hangs, Points of Interest; System Trace if CPU is low |
| High CPU, slow computation | CPU Profiler (clock-frequency sampling) | Top Functions view; Processor Trace / CPU Counters for micro-level work |
| SwiftUI screen slow, too many updates | SwiftUI | Time Profiler (included), Hitches |
| Stutter while scrolling/animating | Animation Hitches | SwiftUI, Time Profiler |
| Async code slow or stuck | Swift Concurrency | Swift Executors (Xcode 27), Time/CPU Profiler for the *Profile* detail |
| Memory grows, leaks | Allocations | Leaks, VM Tracker |
| Slow launch | App Launch | Points of Interest |
| Disk or file I/O | File Activity | System Trace |
| Network | Network | Points of Interest |
| Energy (iPhone/iPad, iOS 26+) | Power Profiler | Thermal State |
| Energy (Mac) | Activity Monitor template + command-line tools (see the platform reference) | |
| Core Data / SwiftData | Data Persistence | Time Profiler |

Notes:

- **Processor Trace** records every branch with ~1 % overhead but needs an **M4 or later
  Mac, M4 iPad Pro or A18+ iPhone**, enabled under Privacy & Security › Developer Tools
  (Mac) or Developer settings (device).
- Older Apple docs mention an "Energy Log" template — it no longer exists.
- "View Body (Legacy)" / "View Properties (Legacy)" are superseded by the SwiftUI
  instrument.

## Xcode 27 analysis features

- **Top Functions**: merges all call-tree nodes of a function and ranks by self weight —
  the fastest way to find the real hotspot when it is called from many places.
- **Run Comparisons**: record the baseline run and the optimised run in one document
  (`--append-run`), then compare; regressions red, improvements green, in call tree and
  flame graph. Filter both runs to the **same signpost interval** and the same track,
  otherwise you compare different amounts of work.
- **Swift Executors** instrument: main actor, cooperative pool and custom executors.
- **System Trace**: unified plot of syscalls, VM faults and thread states, thread
  priority graph, inspector with syscall arguments.
- **SwiftUI** instrument: *Summary of Updates*, layout passes and why a layout was not
  cached.
- Points of Interest also shows **StateReporting** states.

## Build and launch

- Profile a **Release** build: Product › Profile (⌘I) uses the Profile action, which
  builds Release by default.
- Thread Performance Checker and other diagnostics add overhead to call stacks — keep
  them off for profiles (they are off when you use Profile or launch from Instruments).
- Attaching needs a debuggable process: development-signed builds carry
  `get-task-allow`. A Developer ID / App Store build with the Hardened Runtime cannot be
  attached without it — profile a development-signed Release build instead.
- System binaries protected by SIP can't be recorded.

## xctrace command line

```sh
# macOS: launch the executable by path so LaunchServices can't pick another installed copy
xcrun xctrace record --template 'Time Profiler' --time-limit 60s --no-prompt \
  --output run.trace --launch -- /path/App.app/Contents/MacOS/App

# attach to a running process (pid or name)
xcrun xctrace record --template 'Allocations' --time-limit 10m --output alloc.trace --attach App
xcrun xctrace record --template 'Leaks' --time-limit 5m --output leaks.trace --attach <pid>

# combine instruments
xcrun xctrace record --template 'Time Profiler' --instrument 'Hangs' \
  --instrument 'Points of Interest' --time-limit 2m --output hangs.trace --attach App

# device (iOS/iPadOS): --device <name|UDID>
xcrun xctrace record --device '<device name>' --template 'Time Profiler' \
  --time-limit 60s --output device.trace --attach App

# second run into the same document for Run Comparisons
xcrun xctrace record --template 'Time Profiler' --output run.trace --append-run \
  --run-name after-fix --time-limit 60s --attach App

# long recordings: keep only the last 5 minutes of events
xcrun xctrace record --template 'Allocations' --window 5m --time-limit 2h --output soak.trace --attach App

# recording options (Xcode 27): print as JSON, edit, pass back
xcrun xctrace record --template 'Time Profiler' --instrument 'Processor Trace' \
  --show-recording-options > options.json
xcrun xctrace record --template 'Time Profiler' --recording-options options.json --attach App
```

- `xctrace help record` still shows `--device-name` in an example; the option list (and
  this guide) use **`--device`**.
- `--env VAR=value` sets environment variables for `--launch` (e.g.
  `MallocStackLogging=lite`).

### Export

```sh
xcrun xctrace export --input run.trace --toc                 # discover runs and table schemas
xcrun xctrace export --input run.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="<schema>"]' --output table.xml
xcrun xctrace export --input run.trace --toc --time-start 10s --duration 30s
xcrun xctrace export --input capture.atrc --toc               # .atrc / .logarchive import directly
```

- Always discover schema names with `--toc` first. `time-profile` for Time Profiler
  samples comes from community scripts, not Apple docs.
- Exports of large traces can take long; restrict with `--time-start` / `--duration`
  (a unit suffix is required).
- Allocations exports include a backtrace per row (Xcode 27).

## Reading a trace — checklist

1. Select the interval of the problem (signpost, hang, or the time range you reproduced).
2. Call tree: *Invert Call Tree* and *Hide System Libraries* to find your code; or Top
   Functions.
3. Note the numbers (duration, CPU time, allocations) before changing code.
4. One change, new recording, Run Comparisons on the same interval.

## Sources

- Xcode 27 Release Notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- Improving your app's performance — https://developer.apple.com/documentation/xcode/improving-your-app-s-performance
- WWDC26 268 Profile, fix, and verify — https://developer.apple.com/videos/play/wwdc2026/268/
- WWDC25 308 Optimize CPU performance with Instruments — https://developer.apple.com/videos/play/wwdc2025/308/
- WWDC25 306 Optimize SwiftUI performance with Instruments — https://developer.apple.com/videos/play/wwdc2025/306/
- Diagnosing performance issues early — https://developer.apple.com/documentation/xcode/diagnosing-performance-issues-early
- `man xctrace`, `xcrun xctrace help record|export` (Xcode 27.1)
- steipete/agent-scripts `instruments-profiling` (MIT; binary-path launch, export schema) — https://github.com/steipete/agent-scripts
