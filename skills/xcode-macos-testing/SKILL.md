---
name: xcode-macos-testing
description: Apply when testing a native macOS app or Swift package in Xcode — writing, reviewing or migrating unit and integration tests with Swift Testing or XCTest, UI tests with XCUIAutomation (menus, menu bar extras, windows, sheets, keyboard shortcuts, Automation Mode), test design with dependency injection for SwiftUI/@Observable models, async and main-actor tests, exit tests, flaky tests, test plans and configurations, code coverage, running tests with xcodebuild/swift test in CI, reading .xcresult bundles, snapshot tests and previews, accessibility audits and VoiceOver automation, localization tests, and release testing of Developer ID builds (notarization, Gatekeeper, clean-machine install). Also for "Tests schreiben", "UI-Test für die Mac-App", "Tests sind flaky", "Testabdeckung", "auf Swift Testing migrieren", "Release testen". Performance, memory and load tests live in xcode-macos-performance; iOS apps use xcode-ios-testing.
---

# macOS testing

Rules for testing native macOS apps and their Swift packages. This file holds what always
applies; read the matching reference **before** working on that topic.

| Task | Read |
|---|---|
| Writing Swift Testing tests: traits, tags, parameters, known issues, exit tests, migration from XCTest, interop modes | `references/swift-testing.md` |
| Testable design: dependency injection, async and main actor, observation, clock, files, locale, persistence | `references/test-design.md` |
| UI tests: launch state, identifiers, Mac element types, menus, windows, sheets, waits, permissions, accessibility audits, VoiceOver | `references/ui-testing.md` |
| Test plans, configurations, coverage, flaky tests, xcodebuild / xcresulttool / swift test commands, CI | `references/test-plans-ci.md` |
| Previews, snapshot tests, rendering limits, screenshots | `references/snapshots-previews.md` |
| Release build, Developer ID, notarization, Gatekeeper test, clean-machine checks | `references/release-testing.md` |

## Stack — defaults

State: October 2026. Check the installed versions (`xcodebuild -version`,
`swift --version`) before relying on version-specific features.

- **Xcode 27.1**, **Swift 6.4**, macOS 27 SDK. Swift Testing ships with the toolchain;
  its feature level is the Swift version (`references/swift-testing.md` has the table).
- **Swift Testing** for every new unit and integration test.
- **XCTest** for UI automation (XCUIAutomation), performance metrics and code that raises
  Objective-C exceptions.
- Swift 6.5 testing features exist only in toolchain snapshots — don't use them yet.
- Test plans (`.xctestplan`) per scheme; result bundles (`.xcresult`) as the record of a
  run.
- Third-party test libraries (swift-snapshot-testing, swift-clocks, swift-dependencies)
  are **new dependencies** and need approval.

**Detect before writing.** Look at the existing test targets and packages, which framework
each uses, the test plans of the scheme (`xcodebuild -scheme <S> -showTestPlans`), the
Swift Testing interoperability mode, the default actor isolation of app and test targets,
existing fakes and fixtures, and how UI tests launch the app (launch arguments). Follow
what is there unless it breaks a rule below; say so when it does.

## Framework choice — always

- New tests in **Swift Testing**. Both frameworks may live in the same target and file.
- Don't rewrite working XCTests in bulk; migrate the tests that change most, a few at a
  time, in their own change.
- Test plan interoperability mode **complete** (or **strict** to finish a migration) —
  never *limited* or *none* for real runs: they turn failures into warnings.
- UI tests and `measure(metrics:)` stay on XCTest.

## Writing tests — always

- `#expect` for checks, `try #require` when the rest of the test depends on the value.
- Parameterized tests (`@Test(arguments:)`) instead of loops and copies; `zip` for pairs.
- `struct` suites with fresh state per test; setup in `init`, teardown in `deinit` only
  when a class suite needs it.
- Every disabled test has a reason and a ticket (`.disabled("…")`, `.bug(…)`).
- `withKnownIssue` only around the failing part; remove it when Xcode reports the issue
  is gone.
- Exit tests (`#expect(processExitsWith:)`) cover `precondition`/`fatalError` paths —
  available on macOS.

## Isolation and parallelism — always

- Swift Testing runs tests in parallel, in-process, in random order. No shared mutable
  globals, singletons, `UserDefaults.standard`, real files or order dependence.
- Mark tests `@MainActor` when they touch main-actor code; XCTest's implicit main-actor
  execution doesn't carry over.
- `.serialized` is the fallback after the coupling is removed, not the fix.
- Mac UI tests run serially.

## Test design — always

- Logic lives in models and services, not in view bodies; test those directly.
- Inject network, file system, database, clock, randomness and system services through
  initializers; hand-written fakes over mocking libraries.
- Each test uses its own temporary directory; never real user folders. In a sandboxed
  app, tests hosted by the app run inside the container.
- Locale, time zone and calendar are set explicitly in tests of formatting and dates.
- No `sleep`, no polling: `await`, `confirmation`, injected clocks.

## UI tests — always

- Few UI tests for critical flows; the bulk of coverage comes from unit tests.
- Deterministic launch through `launchArguments`/`launchEnvironment`: in-memory store,
  fixed date, stubbed network, no onboarding, no state restoration.
- Query by `accessibilityIdentifier` (unique, static, not localized) — never by
  localized titles or `accessibilityLabel`.
- Wait with `waitForExistence`/`waitForNonExistence`/`wait(for:toEqual:timeout:)`;
  never fixed sleeps.
- Test menu commands through the menu bar **and** their keyboard shortcuts
  (`typeKey(_:modifierFlags:)`); test sheets, dialogs and menu bar extras where the app
  has them.
- Automation Mode must be enabled on the test Mac; enabling it without authentication on
  CI Macs is an administrator system change — only with approval.
- XCTest answers unexpected permission dialogs with "Don't Allow" on macOS — expect the
  dialog explicitly or prepare the test Mac.

## Accessibility and localization — always

- `performAccessibilityAudit()` on every important screen (audits only see what is on
  screen), with false positives filtered explicitly in the closure.
- VoiceOver checks for key screens with `XCUIDevice.shared.voiceOverService` (macOS 27+).
- Manual pass on top: keyboard-only navigation, VoiceOver, Increase Contrast, Reduce
  Motion, Reduce Transparency, Show Borders, light and dark appearance.
- Localization configurations in the full plan: a long-text language (German), a
  right-to-left language if supported; pseudolanguages (double length, right-to-left,
  accented, bounded) from the scheme options for layout checks.

## Flaky tests — always

- A flaky test is a bug. Reproduce with `-run-tests-until-failure -test-iterations 50`,
  find the cause (shared state, timing, clock, locale, restoration), fix it.
- Retry on failure only for tests against unreliable external systems, maximum 3.
- Never disable, skip, delete or weaken a test to get green, and never bypass hooks or CI
  checks.
- Execution time allowances on, so hanging tests end with diagnostics.

## macOS release — always

Before a release: archived Release build launched outside Xcode, fresh install and update
path, standard user, Developer ID builds notarized and stapled and checked on a clean
machine (`references/release-testing.md`). Notarization uploads the build to Apple — only
when the release is approved.

## Workflow

1. **Understand** the behaviour to test; name the cases (happy path, edge cases, errors).
2. **Bug fix**: write the failing regression test first and watch it fail.
3. **Pick the level**: pure function or model → unit test; module boundary → integration
   test with fakes; user flow → UI test; layout → preview or snapshot.
4. **Write** the test in Swift Testing (UI and performance in XCTest), deterministic and
   independent.
5. **Run the narrowest scope first** (`-only-testing:` the test or suite, or
   `swift test --filter`), then the test plan of the change (PR plan), then the full plan
   for larger changes.
6. **Gate**: the whole plan green; for flaky suspects a repetition run; lint as the
   project defines it.
7. **Report**: the commands run and their results (e.g. "184 tests passed, 0 failed"),
   what was not run (UI tests without Automation Mode, release checks), and existing
   failures found — never claim a pass without running it.

## Related skills

- iOS apps: `../xcode-ios-testing/SKILL.md`
- Building the app (architecture, SwiftUI, concurrency, sandbox): `../xcode-macos-development/SKILL.md`
- Performance tests, memory leaks, soak tests: `../xcode-macos-performance/SKILL.md`

Apple ships agent skills with Xcode 27 (for example for test modernization and device
interaction). They carry no open license — don't copy them; export them locally with
`xcrun agent skills export --output-dir <absolute path>` and use them as a reference.

## Sources

State: October 2026 (Xcode 27.1 / Swift 6.4).

Written in our own words (no text or code copied) from Apple's Swift Testing, XCTest and
XCUIAutomation documentation, Xcode documentation, WWDC26/25/24/23 sessions, Swift
Evolution testing proposals and local tool help of Xcode 27.1; structure ideas from the
MIT-licensed AvdLee/Swift-Testing-Agent-Skill and twostraws/Swift-Testing-Agent-Skill;
page-object idea from bradwindy/writing-xcuitests (MIT).

- Swift Testing: https://developer.apple.com/documentation/testing ·
  https://developer.apple.com/documentation/testing/migratingfromxctest ·
  https://developer.apple.com/documentation/testing/parallelization ·
  https://developer.apple.com/documentation/testing/exit-testing ·
  https://github.com/swiftlang/swift-evolution/tree/main/proposals/testing
- UI automation: https://developer.apple.com/documentation/xcuiautomation ·
  https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice ·
  https://developer.apple.com/documentation/xctest/handling-ui-interruptions
- Xcode: https://developer.apple.com/documentation/xcode/testing ·
  https://developer.apple.com/documentation/xcode/organizing-tests-to-improve-feedback ·
  https://developer.apple.com/documentation/xcode/testing-a-release-build ·
  https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- Distribution: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution ·
  https://developer.apple.com/forums/thread/130560
- WWDC: https://developer.apple.com/videos/play/wwdc2026/267/ (Migrate to Swift Testing) ·
  https://developer.apple.com/videos/play/wwdc2026/262/ (What's new in Swift) ·
  https://developer.apple.com/videos/play/wwdc2025/344/ (UI automation) ·
  https://developer.apple.com/videos/play/wwdc2024/10195/ (Go further with Swift Testing) ·
  https://developer.apple.com/videos/play/wwdc2023/10035/ (Accessibility audits)
- Idea sources (MIT): https://github.com/AvdLee/Swift-Testing-Agent-Skill ·
  https://github.com/twostraws/Swift-Testing-Agent-Skill ·
  https://github.com/bradwindy/writing-xcuitests

Caveats: whether Xcode 27 runs Mac UI tests in parallel is only covered by a 2020 source;
the `-only-testing` identifier format of Swift Testing tests is not documented
consistently (use `-enumerate-tests`); Liquid Glass rendering in snapshots is reported by
third parties only.
