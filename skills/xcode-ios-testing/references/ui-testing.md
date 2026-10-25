# UI tests on iPhone and iPad (XCUIAutomation)

UI tests drive the real app out of process through the accessibility layer. They are slow
and more fragile than unit tests — write few of them, for the critical flows: onboarding,
sign-in, the main task end to end, purchase, destructive actions with confirmation,
permission prompts, deep links.

The automation APIs (`XCUIApplication`, `XCUIElement`, `XCUIDevice`, …) live in the
**XCUIAutomation** framework, imported automatically with XCTest. UI tests stay on XCTest.

## Simulators and devices

- Install the iOS simulator runtime first (`xcodebuild -downloadPlatform iOS`) — a system
  change, only with approval.
- Pick destinations from `xcrun simctl list devices available` (name + OS, or UDID).
- The full plan covers **one small iPhone, one large iPhone and one iPad** (size classes);
  the PR plan one iPhone.
- Simulators clone for parallel UI testing; Device Hub may not show the clones (Xcode 27
  known issue). Cloning 27.2 simulators can fail on permissions — see the 27.2 release
  notes for the workaround.
- Keyboard and mouse input in Device Hub only works with iOS 18+ simulators. Device Hub
  clicks are synthesized touches — test pointer behaviour with "Simulate Trackpad or Mouse"
  or a real iPad.

## Deterministic launch

```swift
@MainActor
final class CheckoutUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments += ["-uiTesting"]
        app.launchEnvironment["UITEST_FIXTURE"] = "cart-with-two-items"
        XCUIDevice.shared.orientation = .portrait
        XCUIDevice.shared.appearance = .light
        app.launch()
    }
}
```

- The app checks the launch argument once at startup and switches to test doubles:
  in-memory store, fixed date, stubbed network, no onboarding, no analytics, animations
  shortened if the app supports it.
- Deep links into a screen: `app.open(url)` (iOS 16.4+) or
  `xcrun simctl openurl <device> 'myapp://item/42'`.
- Reset state in `setUp`, never rely on teardown having run. For a truly clean device,
  `xcrun simctl erase <device>` wipes that simulator — destructive, only with approval.

## Finding elements

- Query by **`accessibilityIdentifier`**: unique app-wide, descriptive, static, never
  localized. Use model ids for repeated views (`"product-\(product.id)"`).
- Never use `accessibilityLabel` as a test id — it is spoken by VoiceOver, localized, and
  audits flag labels that look like ids.
- Prefer the identifier; otherwise the shortest unique query; `firstMatch` for dynamic
  content.
- UI recording generates queries — review the alternatives and pick the identifier-based
  one.
- Hiding decorative views from accessibility also hides them from UI tests (UIKit:
  `automationElements` can expose elements to automation only).

## Interacting and device state

- Touch: `tap()`, `doubleTap()`, `press(forDuration:)`, `swipeUp()`, `pinch(withScale:velocity:)`,
  `typeText(_:)`.
- **Rotation**: `XCUIDevice.shared.orientation = .landscapeLeft` (iOS only). Supported
  orientations are only a preference on iOS 27 — resizable scenes, iPad windows and iPhone
  Mirroring ignore them, so layouts must work in all sizes.
- **Appearance**: `XCUIDevice.shared.appearance = .dark`.
- **Location**: `XCUIDevice.shared.location`, a GPX file in the scheme, or
  `xcrun simctl location <device> set <lat>,<lon>`.
- iPad: test resized windows and Stage Manager sizes, not only full screen; iPhone apps
  are resizable when built with the iOS 27 SDK (iPhone Duo, iPhone Mirroring on macOS 27).
- Launch tests with `override class var runsForEachTargetApplicationUIConfiguration: Bool
  { true }` run once per orientation × localization × appearance of the plan.

## Waiting

- `waitForExistence(timeout:)`, `waitForNonExistence(timeout:)`,
  `wait(for: \.isHittable, toEqual: true, timeout:)`.
- App state: `app.wait(for: .runningForeground, timeout:)`; background/foreground with
  `XCUIDevice.shared.press(.home)` and `app.activate()`.
- Custom conditions: `XCTNSPredicateExpectation` with `XCTWaiter`.
- **Never fixed sleeps.**

## Permission prompts and interruptions

- An **expected** prompt is part of the test: wait for it and tap the button. To trigger
  it again, call `app.resetAuthorizationStatus(for: .photos)` (it may terminate the app —
  launch afterwards).
- System alerts are rendered outside the app process. Querying them through
  `XCUIApplication(bundleIdentifier: "com.apple.springboard")` is common practice but not
  described in Apple's current documentation — verify on the iOS version you test.
- `addUIInterruptionMonitor(withDescription:handler:)` only for **unexpected** UI that
  blocks an element. Monitors run last-registered first and only when an element is
  blocked; return `true` when handled. On iOS the implicit handler taps the cancel or
  default button of unexpected alerts; banners are handled automatically.
- CI shortcut: `xcrun simctl privacy <device> grant|revoke|reset <service> <bundle-id>`.
  Apple warns this can hide bugs such as a missing usage description — never use it in
  tests that verify the prompt itself.

## Accessibility in UI tests

```swift
func testCheckoutIsAccessible() throws {
    try app.performAccessibilityAudit(for: [.dynamicType, .contrast, .textClipped]) { issue in
        issue.element?.identifier == "decorative-banner"   // true = ignore
    }
}
```

- `performAccessibilityAudit()` (iOS 17+) fails the test on its own. Categories:
  `.contrast`, `.elementDetection`, `.hitRegion`, `.sufficientElementDescription`,
  `.dynamicType`, `.textClipped`, `.trait`, `.action`, `.parentChild`.
- Audits only see **what is on screen** — navigate to each screen and audit it; set
  `continueAfterFailure = true` in audit tests to see every issue.
- Run audits at large accessibility text sizes too (`simctl ui <device> content_size …`;
  the accepted category names are not listed in `simctl help` — try `increment` or check
  Apple's docs).
- **VoiceOver automation** (iOS 27+): `XCUIDevice.shared.voiceOverService` — `enable()`,
  `moveForward()`, `moveBackward()`, `currentSpeech()`, `disable()`. Check reading order
  and spoken labels of key screens.
- The iPhone Duo simulator can't convey its content to VoiceOver or Accessibility
  Inspector in Device Hub (27.1) — test accessibility of Duo layouts on a device.
- Audits don't replace manual checks with VoiceOver, Voice Control, Switch Control,
  largest text sizes, Bold Text, Increase Contrast, Reduce Motion and Reduce Transparency.

## Screens as helpers

Wrapping the queries of one screen in a small type ("screen object" / page object) keeps
tests readable and each identifier in one place. Not an Apple pattern, but widely used:

```swift
struct CartScreen {
    let app: XCUIApplication
    var checkoutButton: XCUIElement { app.buttons["cart-checkout"] }
    func row(_ id: String) -> XCUIElement { app.cells["cart-row-\(id)"] }
}
```

## Simulator control for tests and screenshots

```sh
xcrun simctl ui <UDID> appearance dark
xcrun simctl ui <UDID> increase_contrast enabled
xcrun simctl status_bar <UDID> override --time 9:41 --batteryLevel 100 --batteryState charged
xcrun simctl push <UDID> com.example.App payload.json      # simulated push notification
xcrun simctl io <UDID> screenshot shot.png
xcrun simctl io <UDID> recordVideo run.mov
```

## Sources

- https://developer.apple.com/documentation/xcuiautomation
- https://developer.apple.com/documentation/xcuiautomation/xcuiapplication
- https://developer.apple.com/documentation/xcuiautomation/xcuielement
- https://developer.apple.com/documentation/xcuiautomation/xcuidevice
- https://developer.apple.com/documentation/xcuiautomation/xcuiaccessibilityaudittype
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice
- https://developer.apple.com/documentation/xctest/handling-ui-interruptions
- https://developer.apple.com/documentation/xcode/simulating-location-in-tests
- https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- https://developer.apple.com/videos/play/wwdc2025/344/ — Record, replay, and review: UI automation with Xcode
- https://developer.apple.com/videos/play/wwdc2023/10035/ — Perform accessibility audits for your app
- https://developer.apple.com/videos/play/wwdc2020/10220/ — Handle interruptions and alerts in UI tests
- https://github.com/bradwindy/writing-xcuitests (MIT, secondary: page objects)
- Local tool help on Xcode 27.1: `xcrun simctl help`
