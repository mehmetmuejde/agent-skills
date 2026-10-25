---
name: xcode-macos-development
description: Apply for any native macOS app work in Swift and SwiftUI with Xcode — writing, reviewing or refactoring `.swift` files, SwiftUI views and `@Observable` models, Xcode projects, local Swift packages and `Package.swift`; project structure with feature modules, layer rules and agent-friendly repositories (`AGENTS.md`, "Projektstruktur", "Feature-Module", "Repo für KI-Agenten optimieren"); setting up a new Mac app ("macOS-App bauen", "neues Xcode-Projekt", "SwiftUI-View", "Menüleisten-App"); scenes and windows (`WindowGroup`, `Window`, `Settings`, `MenuBarExtra`, `DocumentGroup`), the menu bar and keyboard shortcuts, Liquid Glass, Mac typography and accessibility, AppKit interop (`NSViewRepresentable`, `NSHostingView`), Swift 6 concurrency (MainActor default isolation, `@concurrent`, Sendable), SwiftData/Core Data, String Catalogs, App Sandbox, Hardened Runtime, notarization, Developer ID vs Mac App Store, `SMAppService` login items, TCC/Full Disk Access, Keychain and privacy manifests. Holds the rules that always apply — Swift 6 strict concurrency, `@Observable` data flow, system components over custom chrome, a complete menu bar, localization from the start, least-privilege sandbox — and points to references per topic. iOS/iPadOS apps use `xcode-ios-development`; tests use `xcode-macos-testing`; profiling, leaks and hangs use `xcode-macos-performance`.
---

# macOS development (Swift, SwiftUI, Xcode)

Rules for native Mac apps. This file holds what always applies; read the matching
reference **before** working on that topic.

| Task | Read |
|---|---|
| New project, build settings, deployment target, packages, formatting, CI build | `references/project-setup.md` |
| Project structure: modules, layers, feature boundaries, `AGENTS.md`, agent-friendly repo | `references/project-structure.md` |
| async/await, actors, MainActor default isolation, `@concurrent`, Sendable, migration | `references/concurrency.md` |
| `@Observable`, `@State`/`@Bindable`/`@Environment`, navigation, SwiftData/Core Data | `references/swiftui-data-flow.md` |
| Scenes, windows, menu bar, `MenuBarExtra`, Liquid Glass, typography, accessibility | `references/ui-design-accessibility.md` |
| AppKit in SwiftUI and back, observation in AppKit, app delegate | `references/appkit-interop.md` |
| String Catalogs, plurals, grammar agreement, formatting | `references/localization.md` |
| Mac App Store vs Developer ID, sandbox, notarization, login items, TCC, Keychain | `references/distribution-security.md` |

## Stack — defaults

State October 2026 — verify with `xcodebuild -version` and `swift --version` before
relying on a version:

- **Xcode 27.1** (27.2 at release candidate), **Swift 6.4**, **macOS 27 SDK**. Xcode 27
  runs on Apple silicon only.
- **Swift 6 language mode** for new targets, **Approachable Concurrency** on, **MainActor
  default isolation** for the app and UI modules, `nonisolated` default for non-UI packages.
- **SwiftUI** first; AppKit where SwiftUI falls short. `@Observable` models.
- **Persistence**: SwiftData for new apps unless the project already uses Core Data or
  plain files — one persistence layer per app.
- **Tests**: Swift Testing (XCTest for UI automation and performance) — see
  `xcode-macos-testing`.
- **Formatting**: `swift format` from the toolchain with a committed `.swift-format`.
- **Deployment target**: the oldest macOS you really support; gate newer APIs with
  `#available`. Targets ≥ macOS 27 build arm64 only.

**Detect before writing.** Read the project first: `SWIFT_VERSION`,
`SWIFT_DEFAULT_ACTOR_ISOLATION`, `SWIFT_APPROACHABLE_CONCURRENCY`, deployment target,
entitlements, `Package.swift` (`swift-tools-version`, `swiftSettings`), the existing
architecture, persistence and design-system types. Never introduce a second architecture
pattern, persistence layer or design system next to the existing one. If the existing code
deviates from these rules, say so and ask whether to adapt the surrounding code or only do
the task.

## Project setup — always

- New Xcode 27 projects start in **Swift 5 mode** with approachable concurrency and
  MainActor default isolation. Set `SWIFT_VERSION = 6` deliberately — our recommendation,
  not an Apple default.
- App target thin; features and core logic in **local Swift packages**.
- Keep `ENABLE_USER_SCRIPT_SANDBOXING`, App Sandbox and Hardened Runtime on.
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
- Isolated conformances (`extension T: @MainActor P`) for main-actor types.
- No force unwraps or `try!` outside tests and true invariants; errors are typed and
  surfaced to the user where they matter.

Details: `references/concurrency.md`.

## SwiftUI data flow — always

- `@Observable` models (no `ObservableObject` in new code); `@State private` owns,
  `@Bindable` for bindings, `@Environment(Model.self)` for subtrees.
- Logic in models and services, not in `body`; `body` stays cheap.
- `@State` is a macro since Xcode 27 — fix init-order errors per TN3211, not by reordering.
- `NavigationStack` / `NavigationSplitView`; `#Preview` instead of `PreviewProvider`.
- Check the new system components (reordering, swipe containers, item alerts, document
  APIs) before writing custom ones.

Details: `references/swiftui-data-flow.md`.

## Mac UI and accessibility — always

- Every command is in the **menu bar**, with standard shortcuts; settings live in a
  `Settings` scene (⌘,).
- Windows are resizable; less modality than on iPhone; `NavigationSplitView` and inspectors
  for large screens.
- `MenuBarExtra`: a menu by default, user-controlled via `isInserted:`, never the only
  entry point.
- System components get Liquid Glass automatically — no custom bar backgrounds; custom
  glass only on key controls, grouped in a `GlassEffectContainer`. The opt-out
  (`UIDesignRequiresCompatibility`) is ignored with the 27 SDKs.
- No Dynamic Type on macOS: body 13 pt, **10 pt minimum** — `.caption`/`.footnote` are
  10 pt, so not for essential information.
- Semantic colors and Color Sets; SF Symbols for standard actions.
- Every icon-only control has an accessibility label; full keyboard navigation; respect
  Reduce Motion, Reduce Transparency, Increase Contrast and Show Borders; contrast ≥ 4.5:1.

Details: `references/ui-design-accessibility.md`, `references/appkit-interop.md`.

## Localization — always

- String Catalogs from the first commit; `LocalizedStringResource` in non-view code;
  `bundle: #bundle` in packages.
- Plurals via *Vary by Plural*, never `if count == 1`; `FormatStyle` for numbers, dates,
  sizes and lists; `.leading`/`.trailing`.
- Review machine translations before shipping.

Details: `references/localization.md`.

## Distribution and security — always

- Channel decided up front: **Mac App Store** (sandbox mandatory) or **Developer ID**
  (Hardened Runtime + notarization + stapling).
- Least-privilege entitlements; security-scoped bookmarks for persistent file access.
- Login items only through `SMAppService` and only after the user opts in.
- Full Disk Access: attempt, handle the error, guide the user to System Settings — no
  TCC database tricks.
- Secrets never in the bundle or repo; credentials in the Keychain; ATS defaults on;
  `PrivacyInfo.xcprivacy` present.

Details: `references/distribution-security.md`.

## Tooling — always

- `xcodebuild build`/`test` and `swift build`/`swift test` must pass;
  `swift format lint --strict` clean.
- New dependencies (Swift packages, SwiftLint, snapshot libraries) need approval before
  they are added.
- Binding decisions (architecture, persistence, distribution channel, minimum macOS) go
  into an ADR.
- TODOs use the project's TODO marker.
- Apple ships its own agent skills with Xcode 27 (`swiftui-specialist`,
  `swiftui-whats-new-27`, `modernize-tests`, `audit-xcode-security-settings`,
  `building-document-based-swiftui-applications`, …). They are not openly licensed — read
  them locally after `xcrun agent skills export --output-dir <absolute path>`, don't copy
  them into a repository.

## Workflow

1. **Understand** the requirement; restate it and name the screens, models and system
   APIs involved.
2. **Detect** the project's settings and existing patterns (see above).
3. **Plan** briefly: files, models, scenes, entitlements, tests. Ask before binding
   decisions — new dependency, architecture or data-model change, new entitlement or
   permission, minimum OS change, distribution channel.
4. **Implement** model/service first, then views, then menu commands and settings.
5. **Verify**: build, `swift format lint --strict`, tests (Swift Testing; UI tests for
   critical flows).
6. **Run the app** and look at it: light and dark, a narrow and a wide window, keyboard
   only, VoiceOver on the changed screen, German or another long language.
7. **Summary**: what changed, what was verified and how, what was **not** verified, open
   questions. Never claim a build or test passed without running it.

## Related skills

- `../xcode-ios-development/SKILL.md` — iPhone and iPad apps
- `../xcode-macos-testing/SKILL.md` — Swift Testing, XCUITest on the Mac, release checks
- `../xcode-macos-performance/SKILL.md` — Instruments, leaks, hangs, energy, soak tests

## Sources

State: October 2026 (Xcode 27.1 / Swift 6.4). Written in our own words (no text or code
copied) from Apple's documentation, the Human Interface Guidelines, WWDC26/WWDC25
sessions, swift.org and Swift Evolution; structure ideas from these MIT-licensed skills:
twostraws/SwiftUI-Agent-Skill, AvdLee/SwiftUI-Agent-Skill,
AvdLee/Swift-Concurrency-Agent-Skill, twostraws/SwiftData-Agent-Skill and Dimillian/Skills
(macOS packaging). Apple's Xcode-bundled agent skills were used as a reference only.

Caveats: the Swift 6 language-mode rule is a recommendation (Xcode 27 templates still use
Swift 5 mode); the Full Disk Access guidance comes from Apple DTS forum posts; the API for
showing icons in macOS 27 menus is new — verify it in the SDK.

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

**SwiftUI, AppKit and design**
- WWDC26 What's new in SwiftUI — https://developer.apple.com/videos/play/wwdc2026/269/
- WWDC26 Modernize your AppKit app — https://developer.apple.com/videos/play/wwdc2026/289/
- WWDC26 Use SwiftUI with AppKit and UIKit — https://developer.apple.com/videos/play/wwdc2026/272/
- WWDC26 Platforms State of the Union — https://developer.apple.com/videos/play/wwdc2026/102/
- TN3211 — https://developer.apple.com/documentation/technotes/tn3211-resolving-swiftui-source-incompatibilities-for-state-and-contentbuilder
- Migrating to @Observable — https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro
- Adopting Liquid Glass — https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass
- HIG Designing for macOS — https://developer.apple.com/design/human-interface-guidelines/designing-for-macos
- HIG The menu bar — https://developer.apple.com/design/human-interface-guidelines/the-menu-bar
- HIG Typography — https://developer.apple.com/design/human-interface-guidelines/typography
- HIG Accessibility — https://developer.apple.com/design/human-interface-guidelines/accessibility
- WWDC26 What's new in SwiftData — https://developer.apple.com/videos/play/wwdc2026/274/
- Localizing with a string catalog — https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog

**Distribution and security**
- App Sandbox — https://developer.apple.com/documentation/security/app-sandbox
- Hardened Runtime — https://developer.apple.com/documentation/security/hardened-runtime
- Notarizing macOS software — https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- SMAppService — https://developer.apple.com/documentation/servicemanagement/smappservice
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
- https://github.com/Dimillian/Skills
