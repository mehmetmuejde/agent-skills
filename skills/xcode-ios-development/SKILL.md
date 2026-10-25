---
name: xcode-ios-development
description: Apply for any native iPhone or iPad app work in Swift and SwiftUI with Xcode — writing, reviewing or refactoring `.swift` files, SwiftUI views and `@Observable` models, UIKit interop, Xcode projects, local Swift packages and `Package.swift`; project structure with feature modules, layer rules and agent-friendly repositories (`AGENTS.md`, "Projektstruktur", "Feature-Module", "Repo für KI-Agenten optimieren"); setting up a new iOS app ("iOS-App bauen", "iPhone-App", "iPad-App", "neues Xcode-Projekt", "SwiftUI-View"); the UIScene lifecycle, resizable layouts with size classes, iPad windows, iPhone Mirroring and the foldable iPhone Duo (`ArrangementView`), safe areas, Liquid Glass, Dynamic Type, touch targets and accessibility, Swift 6 concurrency (MainActor default isolation, `@concurrent`, Sendable), SwiftData/Core Data, String Catalogs, background tasks, push notifications, App Intents, widgets and extensions, Keychain, data protection, ATS, privacy manifests with required-reason APIs, App Tracking Transparency and App Review rules. Holds the rules that always apply — Swift 6 strict concurrency, `@Observable` data flow, layout by size class never by device idiom, system containers over custom bars, localization from the start, no secrets in the bundle — and points to references per topic. macOS apps use `xcode-macos-development`; tests use `xcode-ios-testing`; profiling, memory, hangs and energy use `xcode-ios-performance`.
---

# iOS and iPadOS development (Swift, SwiftUI, Xcode)

Rules for native iPhone and iPad apps. This file holds what always applies; read the
matching reference **before** working on that topic.

| Task | Read |
|---|---|
| New project, build settings, deployment target, packages, formatting, CI build | `references/project-setup.md` |
| Project structure: modules, layers, feature boundaries, `AGENTS.md`, agent-friendly repo | `references/project-structure.md` |
| async/await, actors, MainActor default isolation, `@concurrent`, Sendable, migration | `references/concurrency.md` |
| `@Observable`, `@State`/`@Bindable`/`@Environment`, navigation, SwiftData/Core Data | `references/swiftui-data-flow.md` |
| UIScene, resizability, size classes, iPhone Duo, safe areas, Liquid Glass, Dynamic Type, accessibility, UIKit interop | `references/layout-resizability.md` |
| String Catalogs, plurals, grammar agreement, formatting | `references/localization.md` |
| Background tasks, push, App Intents, widgets, extensions | `references/background-push-intents.md` |
| Keychain, data protection, ATS, privacy manifest, permissions, App Review | `references/security-privacy-review.md` |

## Stack — defaults

State October 2026 — verify with `xcodebuild -version` and `swift --version` before
relying on a version:

- **Xcode 27.1** (27.2 at release candidate), **Swift 6.4**, **iOS/iPadOS 27.1 SDK**.
- **Swift 6 language mode** for new targets, **Approachable Concurrency** on, **MainActor
  default isolation** for the app and UI modules, `nonisolated` default for non-UI packages.
- **SwiftUI** first; UIKit where SwiftUI falls short. `@Observable` models.
- **Persistence**: SwiftData for new apps unless the project already uses Core Data or
  plain files — one persistence layer per app.
- **Tests**: Swift Testing (XCTest for UI automation and performance) — see
  `xcode-ios-testing`.
- **Formatting**: `swift format` from the toolchain with a committed `.swift-format`.
- **Deployment target**: the oldest iOS you really support; gate newer APIs with
  `#available`. App Store uploads must target iOS 13+ and be built with the 26 SDK or
  newer.

**Detect before writing.** Read the project first: `SWIFT_VERSION`,
`SWIFT_DEFAULT_ACTOR_ISOLATION`, `SWIFT_APPROACHABLE_CONCURRENCY`, deployment target, SDK,
Info.plist (scene manifest, background modes, usage descriptions), entitlements,
`Package.swift`, the existing architecture, persistence and design-system types. Never
introduce a second architecture pattern, persistence layer or design system next to the
existing one. If the existing code deviates from these rules, say so and ask whether to
adapt the surrounding code or only do the task.

## Project setup — always

- New Xcode 27 projects start in **Swift 5 mode** with approachable concurrency and
  MainActor default isolation. Set `SWIFT_VERSION = 6` deliberately — our recommendation,
  not an Apple default.
- App target thin; features, core logic and code shared with extensions in **local Swift
  packages**.
- Building with the iOS 27 SDK makes the scene lifecycle mandatory, the app resizable and
  Liquid Glass unavoidable — plan the SDK bump as its own change.
- Promote chosen warning groups to errors instead of a blanket warnings-as-errors.

Details: `references/project-setup.md`.

## Structure — always

- **Layers** App → Features → Shared; a module imports only lower layers. **Features never
  import features** — the App layer composes them; shared types move down to Shared.
- One local package with **one target per module** (default); group code by feature
  inside a module, not by type; minimal `public` API per module.
- Domain code without UI framework imports; adapters (files, network, storage, system
  APIs) behind protocols, injected by the App layer.
- Boundaries checked by the compiler (`MemberImportVisibility`) and in CI with
  `scripts/check_module_graph.py`.
- **`AGENTS.md`** at the root with the exact build/test/lint commands and the module map;
  `docs/architecture.md` updated in the same change as the code.

Details: `references/project-structure.md`.

## Swift and concurrency — always

- Follow the Swift API Design Guidelines: clarity at the point of use, names by role.
- Start on the main actor; move work off it only when measured, with `@concurrent`.
  `nonisolated async` runs on the **caller's** actor.
- Structured concurrency (`async let`, task groups, `.task {}`) over `Task {}`; store and
  cancel long-lived tasks; check cancellation in long loops.
- No `@unchecked Sendable`, `nonisolated(unsafe)`, `MainActor.assumeIsolated` or
  `DispatchQueue.main.async` to silence diagnostics — restructure.
- No force unwraps or `try!` outside tests and true invariants.

Details: `references/concurrency.md`.

## SwiftUI data flow — always

- `@Observable` models (no `ObservableObject` in new code); `@State private` owns,
  `@Bindable` for bindings, `@Environment(Model.self)` for subtrees.
- Logic in models and services, not in `body`; `body` stays cheap.
- `@State` is a macro since Xcode 27 — fix init-order errors per TN3211, not by reordering.
- `NavigationStack` / `NavigationSplitView`; `TabView` with `Tab` and `.sidebarAdaptable`;
  `#Preview` instead of `PreviewProvider`.

Details: `references/swiftui-data-flow.md`.

## Layout and UI — always

- Lay out by **size class and available space**, never by `userInterfaceIdiom`; never
  `UIScreen.main`. Every screen works from a narrow iPhone to a wide iPad window.
- UIKit apps adopt the **UIScene** lifecycle.
- System containers (tab views, split views, toolbars, sheets) before custom layouts —
  they handle Liquid Glass, resizing and the iPhone Duo hinge. Custom two-pane layouts on
  iPhone Duo use `ArrangementView`.
- Safe areas through `safeAreaInset`/`safeAreaBar`; `ignoresSafeArea` only for decoration.
- No custom bar backgrounds; custom glass only on key controls, in a
  `GlassEffectContainer`. `UIDesignRequiresCompatibility` is ignored with the 27 SDK.
- **Dynamic Type** with text styles, accessibility sizes supported; touch targets 44×44 pt.
- Every icon-only control has an accessibility label; respect Reduce Motion, Reduce
  Transparency and Increase Contrast; contrast ≥ 4.5:1.

Details: `references/layout-resizability.md`.

## Localization — always

- String Catalogs from the first commit; `LocalizedStringResource` in non-view code;
  `bundle: #bundle` in packages; `InfoPlist.xcstrings` for usage descriptions.
- Plurals via *Vary by Plural*, never `if count == 1`; `FormatStyle` for numbers, dates
  and lists; `.leading`/`.trailing`.
- Review machine translations before shipping.

Details: `references/localization.md`.

## Background, push and intents — always

- The mechanism matches the job (background task, background `URLSession`, refresh,
  processing, continued processing, background push); always end tasks and handle
  expiration.
- Background modes only for their purpose; push token sent at every launch.
- Main actions exposed as App Intents; writes run in the app, extensions stay read-only.

Details: `references/background-push-intents.md`.

## Security and privacy — always

- No secrets in the bundle or repo; credentials in the Keychain with the most restrictive
  accessibility; user files with complete data protection; ATS defaults on.
- `PrivacyInfo.xcprivacy` with collected data, tracking domains and **required-reason
  APIs** (including `UserDefaults`).
- Permissions requested in context with precise purpose strings; tracking only with ATT
  consent; data sent to third-party AI services disclosed and consented.
- Account creation in the app ⇒ account deletion in the app.

Details: `references/security-privacy-review.md`.

## Tooling — always

- `xcodebuild build`/`test` against a simulator that exists on the machine and
  `swift test` for packages must pass; `swift format lint --strict` clean.
- New dependencies (Swift packages, SwiftLint, SDKs) need approval; every SDK brings its
  own privacy manifest.
- Binding decisions (architecture, persistence, minimum iOS, SDK bump) go into an ADR.
- TODOs use the project's TODO marker.
- Apple ships its own agent skills with Xcode 27 (`swiftui-specialist`,
  `swiftui-whats-new-27`, `app-resizability`, `app-intents-specialist`,
  `app-intents-whats-new-27`, `modernize-tests`, `audit-xcode-security-settings`, …). They
  are not openly licensed — read them locally after
  `xcrun agent skills export --output-dir <absolute path>`, don't copy them into a
  repository.

## Workflow

1. **Understand** the requirement; restate it and name the screens, models, extensions
   and system APIs involved.
2. **Detect** the project's settings and existing patterns (see above).
3. **Plan** briefly: files, models, scenes, capabilities, permissions, tests. Ask before
   binding decisions — new dependency, architecture or data-model change, new capability,
   entitlement or permission, background mode, minimum iOS or SDK change.
4. **Implement** model/service first, then views, then intents, widgets and extensions.
5. **Verify**: build, `swift format lint --strict`, tests (Swift Testing; UI tests for
   critical flows).
6. **Run the app** and look at it: a small and a large iPhone, an iPad window resized,
   light and dark, the largest accessibility text size, VoiceOver on the changed screen, a
   long language such as German.
7. **Summary**: what changed, what was verified and how, what was **not** verified (for
   example: no device test, no iPhone Duo simulator), open questions. Never claim a build
   or test passed without running it.

## Related skills

- `../xcode-macos-development/SKILL.md` — Mac apps
- `../xcode-ios-testing/SKILL.md` — Swift Testing, XCUITest, simulators, release testing
- `../xcode-ios-performance/SKILL.md` — Instruments, memory limits, hangs, launch, energy

## Sources

State: October 2026 (Xcode 27.1 / Swift 6.4). Written in our own words (no text or code
copied) from Apple's documentation, the Human Interface Guidelines, WWDC26/WWDC25
sessions, swift.org and Swift Evolution; structure ideas from these MIT-licensed skills:
twostraws/SwiftUI-Agent-Skill, AvdLee/SwiftUI-Agent-Skill,
AvdLee/Swift-Concurrency-Agent-Skill and twostraws/SwiftData-Agent-Skill. Apple's
Xcode-bundled agent skills were used as a reference only.

Caveats: the Swift 6 language-mode rule is a recommendation (Xcode 27 templates still use
Swift 5 mode); WWDC26 names the UIKit bar-minimisation APIs inconsistently — check the SDK
headers; grammar agreement (`inflect:`) works only for some languages.

**Releases and tools**
- Xcode 27 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- Xcode 27.1 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27_1-release-notes
- Apple Developer releases — https://developer.apple.com/news/releases/
- Upcoming requirements — https://developer.apple.com/news/upcoming-requirements/
- Build settings reference — https://developer.apple.com/documentation/xcode/build-settings-reference
- Organizing your code with local packages — https://developer.apple.com/documentation/xcode/organizing-your-code-with-local-packages
- swift-format — https://github.com/swiftlang/swift-format

**Swift and concurrency**
- Swift 6.4 released — https://www.swift.org/blog/swift-6.4-released/
- Swift API Design Guidelines — https://www.swift.org/documentation/api-design-guidelines/
- Adopting strict concurrency in Swift 6 apps — https://developer.apple.com/documentation/swift/adoptingswift6
- WWDC25 Embracing Swift concurrency — https://developer.apple.com/videos/play/wwdc2025/268/
- WWDC26 What's new in Swift — https://developer.apple.com/videos/play/wwdc2026/262/
- Swift Evolution SE-0461, SE-0466, SE-0470, SE-0472, SE-0475, SE-0481, SE-0504, SE-0518 — https://github.com/swiftlang/swift-evolution/tree/main/proposals

**SwiftUI, UIKit and design**
- WWDC26 What's new in SwiftUI — https://developer.apple.com/videos/play/wwdc2026/269/
- WWDC26 Modernize your UIKit app — https://developer.apple.com/videos/play/wwdc2026/278/
- WWDC26 Use SwiftUI with AppKit and UIKit — https://developer.apple.com/videos/play/wwdc2026/272/
- WWDC26 Platforms State of the Union — https://developer.apple.com/videos/play/wwdc2026/102/
- TN3211 — https://developer.apple.com/documentation/technotes/tn3211-resolving-swiftui-source-incompatibilities-for-state-and-contentbuilder
- Transitioning to the UIKit scene-based life cycle — https://developer.apple.com/documentation/uikit/transitioning-to-the-uikit-scene-based-life-cycle
- ArrangementView — https://developer.apple.com/documentation/swiftui/arrangementview
- Adopting Liquid Glass — https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass
- HIG Designing for iOS — https://developer.apple.com/design/human-interface-guidelines/designing-for-ios
- HIG Typography — https://developer.apple.com/design/human-interface-guidelines/typography
- HIG Accessibility — https://developer.apple.com/design/human-interface-guidelines/accessibility
- WWDC26 What's new in SwiftData — https://developer.apple.com/videos/play/wwdc2026/274/
- Localizing with a string catalog — https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog

**Background, intents, security and review**
- Choosing background strategies — https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app
- WWDC26 Discover new capabilities in App Intents — https://developer.apple.com/videos/play/wwdc2026/345/
- Restricting keychain item accessibility — https://developer.apple.com/documentation/security/restricting-keychain-item-accessibility
- Privacy manifest files — https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
- App Store Review Guidelines — https://developer.apple.com/app-store/review/guidelines/

**Project structure and agents**
- Tuist: The Modular Architecture (TMA) — https://tuist.dev/en/docs/guides/features/projects/tma-architecture
- Feature-Sliced Design (layer idea) — https://feature-sliced.design/
- SE-0444 Member import visibility — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0444-member-import-visibility.md
- Extending and customizing agents (Xcode) — https://developer.apple.com/documentation/xcode/extending-and-customizing-agents
- WWDC26 session 259 (agentic coding in Xcode) — https://developer.apple.com/videos/play/wwdc2026/259/
- AGENTS.md in Xcode 27 (Apple developer forums) — https://developer.apple.com/forums/thread/833246

**Idea sources (MIT)**
- https://github.com/twostraws/SwiftUI-Agent-Skill
- https://github.com/AvdLee/SwiftUI-Agent-Skill
- https://github.com/AvdLee/Swift-Concurrency-Agent-Skill
- https://github.com/twostraws/SwiftData-Agent-Skill
