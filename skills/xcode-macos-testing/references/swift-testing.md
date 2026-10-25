# Swift Testing

Swift Testing is the default framework for new unit and integration tests. It ships with
the toolchain; its feature level follows the Swift version of the Xcode in use
(Xcode 27.1 → Swift 6.4). API names below were checked against the Testing module
interface of Xcode 27.1.

## Feature level by Swift version

| Swift | Added |
|---|---|
| 6.0 | `@Test`, `@Suite`, `#expect`/`#require`, traits, tags, `.serialized`, `.bug`, `.timeLimit` (minutes) |
| 6.1 | range-based `confirmation(expectedCount:)`, `#expect(throws:)` returns the error, `TestScoping` traits |
| 6.2 | exit tests, attachments, `ConditionTrait.evaluate()`, issue handling traits |
| 6.3 | exit-test value capture, `Issue.record(_:severity:)` with `.warning`, image attachments, `Test.cancel()` |
| 6.4 | XCTest ↔ Swift Testing interoperability, `CustomTestReflectable`, `Transferable` attachments, per-case repetition |

Swift 6.5 features (tag filtering in `swift test`, a task-local trait, `#sourceLocation`)
exist only in toolchain snapshots — don't use them until an Xcode release ships them.
Check the project's Xcode/Swift version before using anything from 6.3 or 6.4.

## Basics

```swift
import Testing
@testable import Store

struct CartTests {
    let cart = Cart()          // fresh instance per test: the suite is re-initialised

    @Test func `empty cart has zero total`() {
        #expect(cart.total == .zero)
    }

    @Test func addingItemUpdatesTotal() throws {
        var cart = cart
        cart.add(.apple, quantity: 2)
        let line = try #require(cart.lines.first)   // stop here if nil
        #expect(line.quantity == 2)
    }
}
```

- `#expect` for checks; it records a failure and continues. `#require` when the following
  lines depend on the value (unwrapping an optional, a precondition of the test) — it
  throws and ends the test.
- Raw-identifier names (`` func `empty cart has zero total`() ``) or
  `@Test("Empty cart has zero total")` give readable names. Pick one style per project.
- Prefer `struct` suites. A suite instance is created for every test, so stored
  properties give each test fresh state. Use `final class` or `actor` only when `deinit`
  must tear something down.
- Setup that throws or awaits goes into `init() async throws`.
- `#expect(throws: CartError.outOfStock) { try cart.add(.apple, quantity: 99) }`; the
  returned error can be inspected further.
- `#expect(throws: Never.self) { … }` asserts that nothing is thrown.

## Parameterized tests

```swift
@Test(arguments: [Currency.eur, .usd, .jpy])
func formatsZero(currency: Currency) {
    #expect(Price.zero(currency).formatted().isEmpty == false)
}

@Test(arguments: zip(["1", "1.5", "abc"], [1.0, 1.5, nil]))
func parsesAmount(input: String, expected: Double?) {
    #expect(Amount(input)?.value == expected)
}
```

- Use arguments instead of loops or copy-pasted tests. Each argument is its own test case:
  it is reported, re-run and parallelised on its own.
- Two collections produce **all combinations**; use `zip` for pairs.
- Argument types should be `Sendable`; `CustomTestStringConvertible` makes case names
  readable.

## Traits

| Trait | Use |
|---|---|
| `.enabled(if: condition)` / `.disabled("reason")` | conditional or parked tests — always with a reason |
| `.timeLimit(.minutes(1))` | upper bound for hanging tests (minute granularity only) |
| `.serialized` | run cases of a parameterized test, or the tests of a suite, one after another |
| `.bug("https://…", "title")` / `.bug(id: "PROJ-123")` | link to the ticket |
| `.tags(.networking)` | cross-cutting grouping for test plans |
| `.compactMapIssues { … }` / `.filterIssues { … }` | adjust or drop recorded issues |
| custom `TestScoping` trait | shared setup/teardown around a test or suite |

- `@available` on the test function for OS-gated APIs rather than runtime checks inside the
  body.
- A disabled test needs a reason and a ticket (`.bug`). Never disable a test to get CI
  green — fix it or mark the failing part as a known issue.

## Tags

```swift
extension Tag {
    @Tag static var networking: Self
    @Tag static var persistence: Self
}

@Suite(.tags(.persistence))
struct StoreMigrationTests { … }
```

Suites are structure, tags are cross-cutting concerns. Test plans include or exclude
tags (any/all) — prefer tags over name patterns.

## Known issues, warnings, cancellation

```swift
@Test func syncsAllRecords() async throws {
    let result = try await sync.run()
    #expect(result.uploaded == 10)
    withKnownIssue("Server drops deletions", isIntermittent: true) {
        #expect(result.deleted == 2)
    }
}
```

- Wrap **only the failing part** in `withKnownIssue`, so the rest keeps validating. Xcode
  reports when the known issue no longer occurs — then remove the wrapper.
- `Issue.record("Retried once", severity: .warning)` (Swift 6.3+) reports a finding
  without failing the test.
- `try Test.cancel("Fixture not available")` (Swift 6.3+) cancels the current test — or
  only the current case of a parameterized test. Use it for conditions discovered at
  runtime; use `.enabled(if:)` when the condition is known up front.

## Async and callbacks

- Make the test `async` and `await` the API. No sleeps, no polling.
- Completion handlers: wrap with `withCheckedContinuation` / `withCheckedThrowingContinuation`.
- Callbacks that must fire n times:
  `await confirmation(expectedCount: 2) { confirm in … confirm() … }`.
  `expectedCount: 0` asserts that something never happens; ranges are allowed (6.1+).

## Exit tests

`#expect(processExitsWith: .failure) { … }` runs the closure in a child process and checks
how it exits — the way to cover `precondition`/`fatalError` paths. **Exit tests run on
macOS (and Linux, Windows, FreeBSD, OpenBSD) only, not on iOS.** For iOS code, test the
logic in a shared package on the macOS host, or refactor to a throwing API.

## Attachments and failure output

- `Attachment.record(value, named: "response.json")` for `Encodable`, `NSSecureCoding`,
  `String` or `Data`; images (`CGImage`, `NSImage`, `UIImage`, `CIImage`) from Swift 6.3;
  `Transferable` values from 6.4.
- `CustomTestStringConvertible` shortens how values appear in failure messages;
  `CustomTestReflectable` (6.4) controls how a value is broken down in diffs.

## Isolation and parallelism

- Swift Testing runs all tests **in parallel, in-process and in random order**. Tests must
  not share mutable globals, singletons, files or `UserDefaults` suites.
- XCTest ran synchronous tests on the main actor; Swift Testing does not. Mark the suite or
  test `@MainActor` when it touches main-actor-isolated code (typical for `@Observable`
  view models), or check the test target's default actor isolation build setting.
- `.serialized` is a fallback after removing the coupling — it does not stop other suites
  from running in parallel with the serialized one.

## Migrating from XCTest

| XCTest | Swift Testing |
|---|---|
| `XCTestCase` subclass | `struct` suite (or `final class`/`actor` for `deinit`) |
| `setUp()` / `tearDown()` | `init()` (may be `async throws`) / `deinit` |
| `XCTAssertEqual(a, b)` etc. | `#expect(a == b)` |
| `XCTUnwrap(x)` | `try #require(x)` |
| `continueAfterFailure = false` | `try #require(…)` at the decisive points |
| `XCTFail("…")` | `Issue.record("…")` |
| `XCTSkip` | `.enabled(if:)` / `.disabled(_:)` traits or `try Test.cancel()` |
| `XCTExpectFailure` | `withKnownIssue` (`isIntermittent:` for non-strict) |
| `XCTestExpectation` + `wait` | `async`/`await` or `confirmation(expectedCount:)` |
| `XCTAttachment` | `Attachment.record` |

- **Stay on XCTest** for UI automation (XCUIAutomation), performance metrics
  (`measure(metrics:)`) and tests of code that raises Objective-C exceptions.
- Both frameworks can live in the same target and the same file; Swift Testing tests
  cannot be declared inside an `XCTestCase` class.
- Don't rewrite working XCTests in bulk. New tests in Swift Testing; migrate the tests
  that are edited most, a few at a time, each migration in its own change.

### Interoperability mode (Swift 6.4 / Xcode 27)

Swift 6.4 lets XCTest assertions run inside Swift Testing tests and `#expect` inside
XCTests. The test plan setting (SwiftPM: `swift-tools-version: 6.4`, or the environment
variable `SWIFT_TESTING_XCTEST_INTEROP_MODE`) decides what happens:

| Mode | Effect | Use |
|---|---|---|
| `none` | cross-framework failures are not reported | never, except briefly while bisecting |
| `limited` | XCTest failures in Swift Testing tests become **warnings** — the test passes | default for old test plans; switch away |
| `complete` | cross-framework failures are errors | default for new projects; recommended |
| `strict` | using XCTest API inside Swift Testing tests is a fatal error | to finish a migration |

The advice in WWDC24 "Meet Swift Testing" to never mix assertions is superseded by the
6.4 interoperability.

Apple ships a test-migration agent skill with Xcode 27. It has no open license — don't
copy it; export it locally with `xcrun agent skills export --output-dir <absolute path>`
and read it as a reference.

## Sources

- https://developer.apple.com/documentation/testing
- https://developer.apple.com/documentation/testing/migratingfromxctest
- https://developer.apple.com/documentation/testing/parallelization
- https://developer.apple.com/documentation/testing/traits
- https://developer.apple.com/documentation/testing/known-issues
- https://developer.apple.com/documentation/testing/attachments
- https://developer.apple.com/documentation/testing/exit-testing
- https://github.com/swiftlang/swift-evolution/tree/main/proposals/testing (ST-0013 severity, ST-0016 cancellation, ST-0021 interoperability, ST-0024 repetition)
- https://developer.apple.com/videos/play/wwdc2026/267/ — Migrate to Swift Testing
- https://developer.apple.com/videos/play/wwdc2026/262/ — What's new in Swift
- https://developer.apple.com/videos/play/wwdc2024/10195/ — Go further with Swift Testing
