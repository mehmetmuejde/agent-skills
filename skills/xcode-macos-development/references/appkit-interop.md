# SwiftUI and AppKit together

New screens are SwiftUI. AppKit stays where it is better (complex text, large tables with
special behaviour, existing code) — there is no need to rewrite a working AppKit app in one
go.

## Embedding

| Direction | API |
|---|---|
| SwiftUI view inside AppKit | `NSHostingView`, `NSHostingController` |
| AppKit view inside SwiftUI | `NSViewRepresentable` (`makeNSView`, `updateNSView`, `Coordinator`) |
| AppKit view controller inside SwiftUI | `NSViewControllerRepresentable` |
| Reuse an AppKit gesture recognizer in SwiftUI | `NSGestureRecognizerRepresentable` |
| SwiftUI menu content in AppKit | `NSHostingMenu` |
| SwiftUI scenes (`Settings`, `MenuBarExtra`) in an AppKit app | `NSHostingSceneRepresentation`, added with `addSceneRepresentation` in `applicationWillFinishLaunching` |

Rules for representables:
- `make…` creates the view once; `update…` applies the current SwiftUI state and must be
  cheap and idempotent.
- Delegates and target/action go through the `Coordinator`; it holds the parent struct's
  values, not the AppKit view strongly in a cycle.
- Don't store SwiftUI state inside the AppKit view; let SwiftUI own it and push it in
  `update…`.

## Observation drives AppKit too

With `@Observable` models, AppKit views update automatically: properties read in
`draw(_:)`, `layout()`, `updateConstraints()` and `updateLayer()` are tracked, and the view
is invalidated when they change. This is on by default with the 2026 SDKs and back-deploys
to macOS 15 with the `NSObservationTrackingEnabled` Info.plist key. One model type can
therefore serve SwiftUI and AppKit views — start migrations with the models.

## Modern AppKit

- Gesture recognizers and `NSControl` events instead of hand-written `mouseDown` tracking
  loops.
- Drag and drop: `beginDraggingSession(items:gesture:source:)`.
- Keyboard navigation: `autorecalculatesKeyViewLoop` on windows so Tab order follows the
  layout.
- State restoration: encode UI state only and always call the restoration completion
  handler.
- Sheets that are not critical: `preventsApplicationTerminationWhenModal = false`.
- Concentric corners: `NSViewCornerConfiguration` instead of hard-coded radii.
- Sidecar / touch input on iPad as display: handle via gesture recognizers (TN3212).

## Threading

- AppKit is main-thread only. All `NS…` view work happens on the main actor; with
  MainActor default isolation this is automatic in UI modules.
- Background results come back via `await` on a main-actor function, never via
  `DispatchQueue.main.async` in new code.

## App delegate in a SwiftUI app

Use `@NSApplicationDelegateAdaptor` only for what SwiftUI scenes don't cover (Dock menu,
`applicationShouldTerminate`, Apple Events, services). Keep it thin and forward to models.

```swift
@main
struct MyApp: App {
    @NSApplicationDelegateAdaptor private var appDelegate: AppDelegate
    var body: some Scene { WindowGroup { ContentView() } }
}
```

## Common mistakes

- Creating the AppKit view again in `update…` instead of updating it.
- Rendering SwiftUI views to images (`ImageRenderer`) inside AppKit draw or update paths —
  render on demand; menu bar icons and other images drawn per update belong in AppKit
  drawing code or asset catalogs.
- Keeping a strong reference from the coordinator to the hosting view and back (cycle).
- Replacing a working AppKit screen with SwiftUI without a reason — migrate when the screen
  changes anyway.
- Calling `NSApp` / `NSWorkspace` from model code — keep platform calls in a small adapter
  so models stay testable.

## Sources

- WWDC26 Use SwiftUI with AppKit and UIKit — https://developer.apple.com/videos/play/wwdc2026/272/
- WWDC26 Modernize your AppKit app — https://developer.apple.com/videos/play/wwdc2026/289/
- AppKit updates — https://developer.apple.com/documentation/updates/appkit
- NSViewRepresentable — https://developer.apple.com/documentation/swiftui/nsviewrepresentable
- NSHostingView — https://developer.apple.com/documentation/swiftui/nshostingview
