# Background work, push notifications, App Intents and extensions

iOS suspends apps quickly. Pick the mechanism that matches the job instead of trying to
keep the app alive.

## Choosing a background mechanism

| Job | Mechanism |
|---|---|
| Finish a short task after the user leaves the app | `beginBackgroundTask(withName:expirationHandler:)` … `endBackgroundTask` |
| Upload or download that may outlive the app | background `URLSession` configuration |
| Refresh content regularly (about 30 s of runtime) | `BGAppRefreshTask` |
| Deferrable heavy work (maintenance, indexing, ML) | `BGProcessingTask` (can require power/network) |
| A long task the user started and watches | `BGContinuedProcessingTask` — must report progress; shown with system UI |
| Server tells the app new data exists | background push (`content-available: 1`, priority 5) — rate-limited, a few per hour |

Rules:
- In SwiftUI, handle scheduled tasks with the `.backgroundTask(…)` scene modifier
  (e.g. `.appRefresh("id")`).
- Register task identifiers in `BGTaskSchedulerPermittedIdentifiers` (Info.plist) and
  submit requests with `BGTaskScheduler.shared.submit(_:)`; the system decides when they
  run.
- Always end background tasks and handle expiration: save state, cancel work, call the
  completion. Missing `endBackgroundTask` leads to termination.
- After entering the background the app has only a few seconds; start
  `beginBackgroundTask` before long work, not after.
- Enable background modes only for their intended purpose (App Review 2.5.4).
- Under the debugger the app is not suspended and background `URLSession` work behaves
  differently — verify background behaviour on a device launched from the home screen.

## Push notifications

- Push Notifications capability (`aps-environment` entitlement).
- Request authorization in context (`UNUserNotificationCenter.requestAuthorization`), not
  at first launch without reason.
- Register for remote notifications at **every** launch and send the device token to your
  server — tokens change.
- Notification Service Extension for mutable content (decrypting, attaching media);
  Notification Content Extension for custom UI.
- Never put secrets or personal data into push payloads in clear text.
- Background pushes are not guaranteed — design the server so a missed push only delays
  data.

## App Intents

- Expose the app's main actions as `AppIntent`s and its content as `AppEntity`s; they
  power Shortcuts, Siri, Spotlight, widgets, controls and Apple Intelligence features.
- Index entities in Spotlight so they are searchable.
- iOS 27 additions:
  - `LongRunningIntent` and `CancellableIntent` for work beyond 30 seconds;
  - `ExecutionTargets` — run writes in the main app (`.main`), keep extensions read-only;
  - `EntityCollection` and `SyncableEntity` for larger and synced entity sets.
- Validate intents with AppIntentsTesting (UI-testing bundle, same team as the app) — see
  the `xcode-ios-testing` skill.
- Apple ships `app-intents-specialist` and `app-intents-whats-new-27` skills with Xcode 27
  (reference only; export with `xcrun agent skills export --output-dir <absolute path>`).

## Widgets, Live Activities and controls

- WidgetKit with App Intents configuration; timelines as cheap as possible; refresh via
  `WidgetCenter` when data changes, not on a fast timer.
- App and extensions share data through an App Group container. Avoid two processes
  writing the same store at the same time — let the app write and the extension read, or
  coordinate (SwiftData `HistoryObserver`, file coordination).
- Extensions have much lower memory limits than the app — keep them small.
- Live Activities for ongoing tasks the user follows; end them when the task ends.

## Sharing code with extensions

- Shared logic in local Swift packages linked into app and extensions.
- Extension-safe APIs only in shared code (no `UIApplication.shared`); gate app-only code.

## Sources

- Choosing background strategies for your app — https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app
- BGContinuedProcessingTask — https://developer.apple.com/documentation/backgroundtasks/bgcontinuedprocessingtask
- Extending your app's background execution time — https://developer.apple.com/documentation/uikit/extending-your-app-s-background-execution-time
- Registering your app with APNs — https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns
- WWDC26 Discover new capabilities in App Intents — https://developer.apple.com/videos/play/wwdc2026/345/
- WWDC26 Validate your App Intents adoption with AppIntentsTesting — https://developer.apple.com/videos/play/wwdc2026/295/
- WidgetKit — https://developer.apple.com/documentation/widgetkit
- App Store Review Guidelines — https://developer.apple.com/app-store/review/guidelines/
