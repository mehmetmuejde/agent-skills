# UI tests on macOS (XCUIAutomation)

UI tests drive the real app out of process through the accessibility layer. They are slow
and more fragile than unit tests — write few of them, for the critical flows: first
launch, the main task end to end, destructive actions with confirmation, settings that
change behaviour, menu commands and keyboard shortcuts.

The automation APIs (`XCUIApplication`, `XCUIElement`, `XCUIDevice`, …) live in the
**XCUIAutomation** framework, imported automatically with XCTest. UI tests stay on XCTest.

## Prerequisites on the Mac

- **Automation Mode** must be enabled; the first UI-test run asks for authentication.
  On CI or lab Macs an administrator runs
  `automationmodetool enable-automationmode-without-authentication` — a system change,
  only with approval.
- Recording UI tests needs Accessibility permission for *Xcode Helper*.
- Run Mac UI tests **serially**. Parallel UI testing is documented for iOS/tvOS
  simulators; the only Apple statement on macOS UI tests (WWDC20) says they don't run in
  parallel — not re-confirmed for Xcode 27.

## Deterministic launch

The test cannot reach into the app's models. Control state at launch:

```swift
@MainActor
final class LibraryUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments += ["-uiTesting", "-ApplePersistenceIgnoreState", "YES"]
        app.launchEnvironment["UITEST_FIXTURE"] = "library-small"
        XCUIDevice.shared.appearance = .light
        app.launch()
    }
}
```

- The app checks the launch argument once at startup and switches to test doubles:
  in-memory store, fixed date, stubbed network, no onboarding, no analytics.
- Keep tests independent of **window state restoration**: an app-side switch that skips
  restoration under `-uiTesting` is the reliable way. The `-ApplePersistenceIgnoreState
  YES` user default is common practice but not documented in the SDK.
- `app.open(url)` (macOS 13.3+) for deep links into a specific screen.
- Reset in `setUp`, never rely on teardown having run.

## Finding elements

- Query by **`accessibilityIdentifier`**: unique app-wide, descriptive, static, never
  localized. Use model ids for repeated views (`"book-\(book.id)"`).
- Never use `accessibilityLabel` as a test id — it is what VoiceOver speaks, it is
  localized, and accessibility audits flag labels that look like ids.
- Prefer the identifier; otherwise the shortest query that is unique. `firstMatch` for
  dynamic content when any match will do.
- UI recording generates queries — review the alternatives Xcode offers and pick the
  identifier-based one.
- Hiding decorative views from accessibility also hides them from UI tests — that's
  intended; don't expose them just for tests.

### Mac element types

| Query | Element |
|---|---|
| `menuBars`, `menuBarItems`, `menus`, `menuItems` | main menu |
| `statusItems` | menu bar extras (`MenuBarExtra`) |
| `windows`, `sheets`, `dialogs`, `popovers` | window structure |
| `toolbars`, `toolbarButtons` | toolbar |
| `outlines`, `outlineRows`, `tables`, `tableRows` | sidebars, lists, tables |
| `splitGroups`, `popUpButtons`, `checkBoxes`, `dockItems` | other Mac controls |

## Interacting

- Mouse: `click()`, `doubleClick()`, `rightClick()`, `hover()`,
  `click(forDuration:thenDragTo:)`, `scroll(byDeltaX:deltaY:)`.
- Keyboard: `typeText(_:)` for text, `typeKey(_:modifierFlags:)` for shortcuts,
  `XCUIElement.perform(withKeyModifiers:block:)` for modifier-clicks.

```swift
func testNewWindowFromMenuAndShortcut() {
    app.menuBarItems["File"].click()
    app.menuItems["New Window"].click()
    XCTAssertEqual(app.windows.count, 2)

    app.typeKey("n", modifierFlags: .command)
    XCTAssertTrue(app.windows.element(boundBy: 2).waitForExistence(timeout: 5))
}
```

- **Menus**: drive the menu path once and test the keyboard shortcut separately. Menu
  titles are localized — run menu tests in one fixed language, or give menu items
  identifiers.
- **Windows**: assert `app.windows.count`; address windows by identifier; close with
  ⌘W or the close button; don't depend on window position.
- **Sheets and dialogs**: `app.sheets.firstMatch.waitForExistence(timeout:)`, then act on
  its buttons. Test that the destructive button is not the default and that Escape
  cancels.
- **Menu bar extras**: query `statusItems` / `menuBarItems`. How a `MenuBarExtra` is
  exposed depends on its accessibility tree — inspect it with Accessibility Inspector
  before writing the test.
- `XCUIDevice.orientation` doesn't exist on macOS; `XCUIDevice.shared.appearance` does
  (macOS 12+).

## Waiting

- `waitForExistence(timeout:)`, `waitForNonExistence(timeout:)`,
  `wait(for: \.isEnabled, toEqual: true, timeout:)`.
- App state: `app.wait(for: .runningForeground, timeout:)`.
- Custom conditions: `XCTNSPredicateExpectation` with `XCTWaiter`.
- **Never fixed sleeps.** A UI test that needs `sleep` is waiting for the wrong thing.

## Interruptions and permissions

- On macOS XCTest's implicit handler answers permission dialogs with **"Don't Allow"**
  and handles the Bluetooth setup assistant. If a test needs a permission, grant it on
  the test Mac beforehand or expect the dialog explicitly.
- Expected alerts are part of the test: query them and `waitForExistence`.
- `addUIInterruptionMonitor(withDescription:handler:)` only for **unexpected** UI that
  blocks an element. Monitors run last-registered first, only when an element is blocked;
  return `true` when handled.
- `app.resetAuthorizationStatus(for:)` re-triggers first-run prompts; it may terminate the
  app, so launch afterwards.
- Full Disk Access and other TCC grants can't be scripted from a test — document the
  manual setup of the test Mac.

## Accessibility in UI tests

```swift
func testLibraryIsAccessible() throws {
    try app.performAccessibilityAudit(for: [.contrast, .sufficientElementDescription]) { issue in
        // return true to ignore a known false positive
        issue.element?.identifier == "decorative-cover"
    }
}
```

- `performAccessibilityAudit()` (macOS 14+) fails the test on its own; no assertion needed.
  Categories: `.contrast`, `.elementDetection`, `.hitRegion`,
  `.sufficientElementDescription`, `.dynamicType`, `.textClipped`, `.trait`, `.action`,
  `.parentChild`.
- Audits only see **what is on screen**. Navigate to each screen and audit it (a helper
  called at the end of every flow works well). Set `continueAfterFailure = true` in audit
  tests so all issues are reported.
- **VoiceOver automation** (macOS 27+): `XCUIDevice.shared.voiceOverService` —
  `enable()`, `moveForward()`, `moveBackward()`, `currentSpeech()` (returns the
  utterance), `disable()`. Check reading order and spoken labels of key screens.
- Audits don't replace manual checks with VoiceOver, keyboard-only navigation, Increase
  Contrast, Reduce Motion, Reduce Transparency and Show Borders.

## Screens as helpers

Wrapping the queries of one screen in a small type ("screen object" / page object) keeps
tests readable and puts each identifier in one place. Not an Apple pattern, but widely
used:

```swift
struct LibraryScreen {
    let app: XCUIApplication
    var addButton: XCUIElement { app.toolbarButtons["library-add"] }
    func book(_ id: String) -> XCUIElement { app.outlineRows["book-\(id)"] }
}
```

## Screenshots

Test plan configurations capture screenshots and video (keep on failure by default).
Explicit captures: `app.windows.firstMatch.screenshot()` + `XCTAttachment`. See
`snapshots-previews.md`.

## Sources

- https://developer.apple.com/documentation/xcuiautomation
- https://developer.apple.com/documentation/xcuiautomation/xcuiapplication
- https://developer.apple.com/documentation/xcuiautomation/xcuielement
- https://developer.apple.com/documentation/xcuiautomation/xcuidevice
- https://developer.apple.com/documentation/xcuiautomation/xcuielementtypequeryprovider
- https://developer.apple.com/documentation/xcuiautomation/xcuiaccessibilityaudittype
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice
- https://developer.apple.com/documentation/xcuiautomation/recording-ui-automation-for-testing
- https://developer.apple.com/documentation/xctest/handling-ui-interruptions
- https://developer.apple.com/videos/play/wwdc2025/344/ — Record, replay, and review: UI automation with Xcode
- https://developer.apple.com/videos/play/wwdc2023/10035/ — Perform accessibility audits for your app
- https://developer.apple.com/videos/play/wwdc2020/10220/ — Handle interruptions and alerts in UI tests
- https://github.com/bradwindy/writing-xcuitests (MIT, secondary: page objects)
