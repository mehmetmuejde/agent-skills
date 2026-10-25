---
name: xcode-ios-testing
description: Apply when testing a native iPhone or iPad app or Swift package in Xcode — writing, reviewing or migrating unit and integration tests with Swift Testing or XCTest, UI tests with XCUIAutomation on simulators and devices (launch arguments, rotation, size classes, iPad windows, permission prompts, interruptions, deep links), test design with dependency injection for SwiftUI/@Observable models, async and main-actor tests, flaky tests, test plans and configurations, code coverage, running tests with xcodebuild/simctl/swift test in CI, reading .xcresult bundles, snapshot tests and previews, accessibility audits, Dynamic Type and VoiceOver automation, localization tests, StoreKit and App Intents testing, and release testing on real devices and TestFlight. Also for "Tests schreiben", "UI-Test für die iOS-App", "Tests sind flaky", "Testabdeckung", "auf Swift Testing migrieren", "Release testen", "TestFlight vorbereiten". Performance, memory and load tests live in xcode-ios-performance; macOS apps use xcode-macos-testing.
---

# iOS testing

Rules for testing native iPhone and iPad apps and their Swift packages. This file holds
what always applies; read the matching reference **before** working on that topic.

| Task | Read |
|---|---|
| Writing Swift Testing tests: traits, tags, parameters, known issues, migration from XCTest, interop modes | `references/swift-testing.md` |
| Testable design: dependency injection, async and main actor, observation, clock, files, locale, persistence | `references/test-design.md` |
| UI tests: simulators, launch state, identifiers, rotation, waits, permission prompts, accessibility audits, VoiceOver, simctl | `references/ui-testing.md` |
| Test plans, configurations, destinations, coverage, flaky tests, xcodebuild / xcresulttool / simctl commands, CI | `references/test-plans-ci.md` |
| Previews, snapshot tests, rendering limits, screenshots | `references/snapshots-previews.md` |
| Release build on devices, install/update paths, StoreKit, App Intents, push, TestFlight | `references/release-testing.md` |

## Stack — defaults

State: October 2026. Check the installed versions (`xcodebuild -version`,
`swift --version`, `xcrun simctl list runtimes`) before relying on version-specific
features.

- **Xcode 27.1**, **Swift 6.4**, iOS/iPadOS 27.1 SDK. Swift Testing ships with the
  toolchain; its feature level is the Swift version (table in
  `references/swift-testing.md`).
- **Swift Testing** for every new unit and integration test.
- **XCTest** for UI automation (XCUIAutomation), performance metrics, AppIntentsTesting
  and code that raises Objective-C exceptions.
- Swift 6.5 testing features exist only in toolchain snapshots — don't use them yet.
- Simulator runtimes are installed separately (`xcodebuild -downloadPlatform iOS`) — a
  system change, only with approval.
- Third-party test libraries (swift-snapshot-testing, swift-clocks, swift-dependencies)
  are **new dependencies** and need approval.

**Detect before writing.** Look at the existing test targets and packages, which framework
each uses, the test plans of the scheme (`xcodebuild -scheme <S> -showTestPlans`), the
Swift Testing interoperability mode, the default actor isolation of app and test targets,
existing fakes and fixtures, how UI tests launch the app (launch arguments), and which
simulators and runtimes are available. Follow what is there unless it breaks a rule
below; say so when it does.

## Framework choice — always

- New tests in **Swift Testing**. Both frameworks may live in the same target and file.
- Don't rewrite working XCTests in bulk; migrate the tests that change most, a few at a
  time, in their own change.
- Test plan interoperability mode **complete** (or **strict** to finish a migration) —
  never *limited* or *none* for real runs: they turn failures into warnings.
- UI tests, `measure(metrics:)` and AppIntentsTesting stay on XCTest.

## Writing tests — always

- `#expect` for checks, `try #require` when the rest of the test depends on the value.
- Parameterized tests (`@Test(arguments:)`) instead of loops and copies; `zip` for pairs.
- `struct` suites with fresh state per test; setup in `init`, teardown in `deinit` only
  when a class suite needs it.
- Every disabled test has a reason and a ticket (`.disabled("…")`, `.bug(…)`).
- `withKnownIssue` only around the failing part; remove it when Xcode reports the issue
  is gone.
- **No exit tests on iOS**: test `precondition`/`fatalError` paths of shared packages on
  the macOS host, or refactor them into throwing APIs.

## Isolation and parallelism — always

- Swift Testing runs tests in parallel, in-process, in random order. No shared mutable
  globals, singletons, `UserDefaults.standard`, real files or order dependence.
- Mark tests `@MainActor` when they touch main-actor code; XCTest's implicit main-actor
  execution doesn't carry over.
- `.serialized` is the fallback after the coupling is removed, not the fix.
- UI tests may run in parallel on simulator clones; they must not share accounts or
  server-side state.

## Test design — always

- Logic lives in models and services, not in view bodies; test those directly.
- Inject network, file system, database, clock, randomness and system services through
  initializers; hand-written fakes over mocking libraries.
- Each test uses its own temporary directory and an in-memory store.
- Locale, time zone and calendar are set explicitly in tests of formatting and dates.
- No `sleep`, no polling: `await`, `confirmation`, injected clocks.
- Platform-independent logic lives in Swift packages and runs with `swift test` on the
  host — fast feedback without a simulator.

## UI tests — always

- Few UI tests for critical flows; the bulk of coverage comes from unit tests.
- Deterministic launch through `launchArguments`/`launchEnvironment`: in-memory store,
  fixed date, stubbed network, no onboarding.
- Query by `accessibilityIdentifier` (unique, static, not localized) — never by
  localized titles or `accessibilityLabel`.
- Wait with `waitForExistence`/`waitForNonExistence`/`wait(for:toEqual:timeout:)`;
  never fixed sleeps.
- Layout is tested across size classes: one small iPhone, one large iPhone, one iPad in
  the full plan; rotation via `XCUIDevice.shared.orientation`; resized iPad windows. Apps
  built with the iOS 27 SDK are resizable — orientation locks are only a preference.
- Expected permission prompts are part of the test; `simctl privacy` grants are a CI
  shortcut that must not replace the tests that verify the prompt.
- `xcrun simctl erase` wipes a simulator — destructive, only with approval.

## Accessibility and localization — always

- `performAccessibilityAudit()` on every important screen (audits only see what is on
  screen), also at large accessibility text sizes; false positives filtered explicitly in
  the closure.
- VoiceOver checks for key screens with `XCUIDevice.shared.voiceOverService` (iOS 27+).
- Manual pass on top: VoiceOver, Voice Control, largest Dynamic Type sizes, Bold Text,
  Increase Contrast, Reduce Motion, Reduce Transparency, dark mode.
- Localization configurations in the full plan: a long-text language (German), a
  right-to-left language if supported; pseudolanguages (double length, right-to-left,
  accented, bounded) from the scheme options for layout checks.
- Launch tests with `runsForEachTargetApplicationUIConfiguration` cover orientation ×
  language × appearance.

## Flaky tests — always

- A flaky test is a bug. Reproduce with `-run-tests-until-failure -test-iterations 50`,
  find the cause (shared state, timing, clock, locale, simulator state), fix it.
- Retry on failure only for tests against unreliable external systems, maximum 3.
- Never disable, skip, delete or weaken a test to get green, and never bypass hooks or CI
  checks.
- Execution time allowances on, so hanging tests end with diagnostics.

## iOS release — always

Before a release: archived Release build on real devices, launched from the home screen
without the debugger, fresh install and update from the App Store version, Low Power
Mode, bad networks, StoreKit flows, and the TestFlight build is the one submitted
(`references/release-testing.md`).

## Workflow

1. **Understand** the behaviour to test; name the cases (happy path, edge cases, errors).
2. **Bug fix**: write the failing regression test first and watch it fail.
3. **Pick the level**: pure function or model → unit test (package, `swift test`);
   module boundary → integration test with fakes; user flow → UI test; layout → preview
   or snapshot.
4. **Write** the test in Swift Testing (UI and performance in XCTest), deterministic and
   independent.
5. **Run the narrowest scope first** (`-only-testing:` the test or suite on one
   simulator, or `swift test --filter`), then the PR plan, then the full plan with all
   destinations for larger changes.
6. **Gate**: the whole plan green; for flaky suspects a repetition run; lint as the
   project defines it.
7. **Report**: the commands and destinations run and their results (e.g. "212 tests
   passed on iPhone 17 and iPad"), what was not run (no simulator runtime, no device, no
   release checks), and existing failures found — never claim a pass without running it.

## Related skills

- macOS apps: `../xcode-macos-testing/SKILL.md`
- Building the app (architecture, SwiftUI, concurrency, scenes, privacy): `../xcode-ios-development/SKILL.md`
- Performance tests, memory, launch time, hangs: `../xcode-ios-performance/SKILL.md`

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
  https://github.com/swiftlang/swift-evolution/tree/main/proposals/testing
- UI automation: https://developer.apple.com/documentation/xcuiautomation ·
  https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice ·
  https://developer.apple.com/documentation/xctest/handling-ui-interruptions
- Xcode: https://developer.apple.com/documentation/xcode/testing ·
  https://developer.apple.com/documentation/xcode/organizing-tests-to-improve-feedback ·
  https://developer.apple.com/documentation/xcode/testing-a-release-build ·
  https://developer.apple.com/documentation/xcode/setting-up-storekit-testing-in-xcode ·
  https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- Distribution: https://developer.apple.com/testflight/ ·
  https://developer.apple.com/app-store/review/guidelines/
- WWDC: https://developer.apple.com/videos/play/wwdc2026/267/ (Migrate to Swift Testing) ·
  https://developer.apple.com/videos/play/wwdc2026/295/ (AppIntentsTesting) ·
  https://developer.apple.com/videos/play/wwdc2025/344/ (UI automation) ·
  https://developer.apple.com/videos/play/wwdc2024/10195/ (Go further with Swift Testing) ·
  https://developer.apple.com/videos/play/wwdc2023/10035/ (Accessibility audits)
- Idea sources (MIT): https://github.com/AvdLee/Swift-Testing-Agent-Skill ·
  https://github.com/twostraws/Swift-Testing-Agent-Skill ·
  https://github.com/bradwindy/writing-xcuitests

Caveats: querying system alerts through the Springboard application is common practice,
not current Apple documentation; `simctl ui content_size` category names are not listed
in `simctl help`; the `-only-testing` identifier format of Swift Testing tests is not
documented consistently (use `-enumerate-tests`); Liquid Glass rendering in snapshots is
reported by third parties only.
