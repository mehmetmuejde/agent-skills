# Swift concurrency

Swift 6 concurrency for app code on Apple platforms. The goal is data-race safety checked
by the compiler — not silenced diagnostics. State: Swift 6.4 / Xcode 27.

## Settings that decide how code behaves

Read these **before** writing concurrent code; the same source means different things
under different settings.

| Setting | Where | Effect |
|---|---|---|
| `SWIFT_VERSION = 6` | target build settings | Swift 6 language mode: strict concurrency is complete and an error |
| `SWIFT_APPROACHABLE_CONCURRENCY = YES` | target | turns on `NonisolatedNonsendingByDefault`, `InferIsolatedConformances`, `InferSendableFromCaptures`, `GlobalActorIsolatedTypesUsability`, `DisableOutwardActorInference` |
| `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor` | target | unannotated declarations are `@MainActor` |
| `.defaultIsolation(MainActor.self)` | `Package.swift` `swiftSettings` | same for a package target (tools version 6.2+) |
| `.enableUpcomingFeature("NonisolatedNonsendingByDefault")` | `Package.swift` | mirrors the Xcode approachable-concurrency behaviour in packages |

Xcode 27 templates create app targets in **Swift 5 mode** with approachable concurrency and
MainActor default isolation. Switching to Swift 6 mode is our recommendation, not an Apple
default — do it per module and only when the module builds cleanly with complete checking.

```swift
// Package.swift — UI package
.target(
    name: "FeatureUI",
    swiftSettings: [
        .defaultIsolation(MainActor.self),
        .enableUpcomingFeature("NonisolatedNonsendingByDefault"),
        .enableUpcomingFeature("InferIsolatedConformances"),
    ]
)
```

Libraries, networking, parsing and storage packages keep the `nonisolated` default: they
offer a nonisolated API and let callers decide where to run it. MainActor default in such
a package serialises all of its work on the main thread.

## Start on the main actor

- Write single-threaded code on the main actor first. Add concurrency only when profiling
  shows main-thread work that hurts responsiveness.
- UI types, view models and `@Observable` models stay on the main actor.
- Most classes are **not** actors. Introduce a custom `actor` only for state that must be
  shared by concurrent work and that would otherwise cause too much main-thread work.

## Moving work off the main actor

- Under `NonisolatedNonsendingByDefault` (SE-0461) a `nonisolated async` function runs on
  the **caller's** actor. It does not move work to the background by itself.
- Mark CPU-heavy functions `@concurrent` to run them on the concurrent pool.
- A `Task { }` created from main-actor code inherits the main actor — synchronous heavy
  work inside it still blocks the UI.

```swift
nonisolated struct ThumbnailRenderer {
    @concurrent
    func render(_ data: Data) async throws -> CGImage {
        // decoding and scaling run off the main actor
    }
}
```

## Sendable

- Value types (`struct`, `enum`) with Sendable members are Sendable; make them so
  explicitly when they cross actors in public API.
- Main-actor types are implicitly Sendable.
- Keep model classes non-Sendable; finish mutating a value before sending it.
- Never reach for `@unchecked Sendable`, `nonisolated(unsafe)` or
  `MainActor.assumeIsolated` to silence a diagnostic. Restructure instead:
  - `weak let` (SE-0481, Swift 6.4) makes a class with a weak reference checkable.
  - `~Sendable` (SE-0518, Swift 6.4) states explicitly that a type is not Sendable.
- If an unchecked conformance is truly needed (a lock-protected type), document the
  invariant next to it and keep the type small.

## Protocol conformances of main-actor types

Use an isolated conformance (SE-0470) instead of making members `nonisolated`:

```swift
extension SettingsModel: @MainActor Equatable { … }
```

## Structured concurrency first

- Prefer `async let`, `withTaskGroup` / `withThrowingTaskGroup` and SwiftUI's `.task { }`
  (cancelled when the view disappears) over unstructured `Task { }`.
- `Task.detached` only with a reason (it drops priority, task-locals and isolation).
- `Task.immediate` (SE-0472) when the first part of the work must run synchronously on the
  current actor before the first suspension.
- Keep a reference to every long-lived `Task` you create and cancel it when its owner goes
  away. A task that loops forever (`for await` over a stream) keeps captured objects alive.
- Swift 6.4 warns when a throwing `Task { }` drops its error. Handle the error inside the
  task or keep the task and inspect its result.

## Cancellation

- Cancellation is cooperative: call `try Task.checkCancellation()` or check
  `Task.isCancelled` before each expensive step and inside long loops.
- `withTaskCancellationShield` (SE-0504, Swift 6.4) only around short cleanup that must
  finish (closing a file, rolling back a transaction).

## Actors

- Reentrancy: state can change across every `await` inside an actor. Re-check invariants
  after each suspension; don't hold "in-progress" assumptions across awaits.
- Keep actor methods synchronous where possible and do the awaiting outside.

## Observing `@Observable` outside SwiftUI

Use `Observations` (SE-0475) as an async sequence, or `withContinuousObservation`
(SE-0506) — keep the returned token alive for as long as you want updates. Don't add
Combine just to observe a model.

## Bridging old APIs

- Completion handlers → `withCheckedThrowingContinuation`; resume exactly once.
- No `DispatchQueue.main.async` in new code — use main-actor isolation.
- No `DispatchSemaphore.wait` / `DispatchGroup.wait` to make async code synchronous.

## Migration of an existing module

1. Turn on upcoming features one by one and fix warnings.
2. Raise *Strict Concurrency Checking* to *Complete* in Swift 5 mode.
3. Switch the module to Swift 6 mode — app target first, then its modules.
4. Keep each step a separate, reviewable change.

## Debugging

- LLDB: `language swift task tree` shows the task hierarchy.
- Instruments *Swift Concurrency* template (tasks, actors; *Swift Executors* in Xcode 27).
- Give long-running tasks names (`Task(name:)`) so they show up readably in tools.

## Sources

- WWDC25 Embracing Swift concurrency — https://developer.apple.com/videos/play/wwdc2025/268/
- WWDC26 What's new in Swift — https://developer.apple.com/videos/play/wwdc2026/262/
- Adopting strict concurrency in Swift 6 apps — https://developer.apple.com/documentation/swift/adoptingswift6
- Build settings reference — https://developer.apple.com/documentation/xcode/build-settings-reference
- The Swift Programming Language: Concurrency — https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/
- SE-0461 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
- SE-0466 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0466-control-default-actor-isolation.md
- SE-0470 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0470-isolated-conformances.md
- SE-0472 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0472-task-start-synchronously-on-caller-context.md
- SE-0475 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0475-observed.md
- SE-0481 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0481-weak-let.md
- SE-0504 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0504-task-cancellation-shields.md
- SE-0506 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0506-advanced-observation-tracking.md
- SE-0518 — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0518-tilde-sendable.md
- Swift 6.4 released — https://www.swift.org/blog/swift-6.4-released/
