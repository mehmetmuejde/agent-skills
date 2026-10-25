# Test design for Swift and SwiftUI apps

Most coverage comes from fast unit tests of models and services. UI tests only cover the
critical flows on top (`ui-testing.md`).

## Where the logic lives

- Keep logic out of `View` bodies: views render model state and forward user actions.
  Test the `@Observable` model, the service or the pure function directly.
- Arrange – Act – Assert, one behaviour per test. The test name states the behaviour, not
  the method ("rejects an expired token", not "testValidate2").
- Pure functions and value types first: they need no fakes and run anywhere.
- Code in local Swift packages can be tested with `swift test` without launching the app
  and without a simulator — another reason to keep features in packages.

## Dependency injection

Replace everything the test cannot control — network, file system, database, clock,
randomness, `UserDefaults`, system services — with an injected dependency.

```swift
protocol PriceService: Sendable {
    func price(for id: Product.ID) async throws -> Decimal
}

@MainActor @Observable
final class ProductModel {
    private let prices: any PriceService
    private(set) var price: Decimal?

    init(prices: any PriceService) { self.prices = prices }

    func load(_ id: Product.ID) async {
        price = try? await prices.price(for: id)
    }
}

struct FixedPrices: PriceService {
    var value: Decimal
    func price(for id: Product.ID) async throws -> Decimal { value }
}

@MainActor
struct ProductModelTests {
    @Test func loadsPrice() async {
        let model = ProductModel(prices: FixedPrices(value: 9.99))
        await model.load("apple")
        #expect(model.price == 9.99)
    }
}
```

- Protocol plus a small hand-written fake beats a mocking library. A fake that records
  calls is enough for interaction checks.
- When the code creates objects itself, inject a factory closure or a metatype.
- Inject through the initializer. Defaults (`init(prices: any PriceService = LivePrices())`)
  keep call sites short; the test passes its fake explicitly.
- Fake external services instead of retrying flaky real ones. Real network calls belong
  in a separate, tagged integration suite that is excluded from the PR test plan.
- A DI library (for example Point-Free `swift-dependencies`, MIT) is a new dependency and
  needs approval; plain initializer injection covers most apps.
- `@testable import App` needs *Enable Testability*, which is on for Debug only. Prefer
  testing through the public or `package` API of a module.

## Concurrency and actors

- Make tests `async` and `await` the API under test. Never `sleep` or poll for a result.
- Mark suites `@MainActor` when they touch main-actor-isolated types. Under Swift 6.2+
  modules can default to `MainActor` isolation (SE-0466); when isolation errors appear in
  tests, compare the default actor isolation setting of the app module and the test target.
- Unstructured `Task {}` inside the model makes tests racy: the test can't await it. Give
  the model an `async` method the view calls from `.task {}`, and test that method.
- Callbacks fired n times: `confirmation(expectedCount:)`; completion handlers:
  `withCheckedContinuation`.

## Observation

- Assert state **after** awaiting the action; no observation plumbing needed for that.
- To check a sequence of changes, use `Observations` (SE-0475, Swift 6.2+) or
  `withObservationTracking` and collect the values the test expects.

## Time

- Never depend on the wall clock. Inject a `Clock` (`any Clock<Duration>`) or a
  `now: () -> Date` provider.
- Point-Free `swift-clocks` (MIT) provides `TestClock` and `ImmediateClock` — a new
  dependency, needs approval. A tiny hand-written test clock is often enough.
- Debounce, timeout and retry logic is tested by advancing the injected clock, not by
  waiting.

## File system

- Inject the base directory. Every test creates its own unique temporary directory
  (`FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)`), so
  parallel tests never collide.
- Create fixtures in `init`, not in teardown; clean up in `deinit` of a class suite or
  leave it to the temporary directory.
- Never read or write real user folders (Documents, Desktop, Downloads) in tests.
- In a sandboxed macOS app, tests hosted by the app run inside the app's container — use
  injected temporary directories there too.

## Locale, time zone, calendar

- Set `Locale`, `TimeZone` and `Calendar` explicitly in tests of formatting and date
  logic. CI machines and fresh simulators use different defaults.
- Cover at least: a long-text language (German), a right-to-left language, a region with
  24-hour time and one with 12-hour time, a non-Gregorian calendar where dates matter.
- Formatting via `FormatStyle` takes a locale (`.formatted(.number.locale(locale))`) —
  inject it instead of using `.current`.

## Persistence

- SwiftData: build the `ModelContainer` with
  `ModelConfiguration(isStoredInMemoryOnly: true)` per test.
- Core Data: an in-memory store (`/dev/null` URL) per test.
- Migration tests use real store files from earlier versions, copied into the test's
  temporary directory.

## Test doubles — naming

| Double | Does |
|---|---|
| Stub | returns canned values |
| Fake | working lightweight implementation (in-memory store) |
| Spy | records calls for later assertions |
| Mock | verifies expected calls itself — rarely needed in Swift |

## What not to test

- SwiftUI layout through unit tests — use previews, snapshots (`snapshots-previews.md`)
  or a UI test.
- Apple frameworks themselves.
- Private helpers in isolation — test them through the behaviour that uses them.

## Sources

- https://developer.apple.com/documentation/xcode/adding-tests-to-your-xcode-project
- https://developer.apple.com/documentation/xcode/updating-your-existing-codebase-to-accommodate-unit-tests
- https://developer.apple.com/documentation/testing/migratingfromxctest
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0475-observed.md
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0466-control-default-actor-isolation.md
- https://developer.apple.com/videos/play/wwdc2022/110361/ — Author fast and reliable tests for Xcode Cloud
- https://github.com/pointfreeco/swift-clocks (MIT, third party)
