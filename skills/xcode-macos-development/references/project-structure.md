# Project structure for agent-friendly apps

A structure that works for people and coding agents alike: small modules with one job,
boundaries the compiler enforces, commands that give the same answer every time and
documentation that says where things go. Swift has no Feature-Sliced Design standard;
the rules below take its ideas (layers, slices, public API per slice, an automated
boundary check) and map them onto Swift packages.

Why this helps agents: an agent working inside one module needs only that module and the
public API of its dependencies in context; an undeclared dependency fails the build
instead of slipping through review; `swift build` / `swift test` on a package give fast,
simulator-free feedback; and a written module map replaces guessing.

## Layout

```text
<repo>/
├── AGENTS.md                     # how to build, test, where things go (see below)
├── App/                          # thin app target(s): @main App, scenes, composition root
│   └── App.xcodeproj             # (or .xcproj with Xcode 27.2+)
├── Packages/
│   └── AppModules/               # one local package, one target per module
│       ├── Package.swift
│       ├── Sources/
│       │   ├── AppFeature/       # app layer: root navigation, wires features together
│       │   ├── Search/           # feature
│       │   ├── Settings/         # feature
│       │   ├── DesignSystem/     # shared: tokens, components, styles
│       │   ├── Persistence/      # shared: storage adapter
│       │   └── APIClient/        # shared: network adapter (+ APIClientInterface if needed)
│       └── Tests/
│           ├── SearchTests/
│           └── SettingsTests/
└── docs/
    ├── architecture.md           # module map, layer rules, data flow
    └── adr/                      # binding decisions
```

**One package with many targets** is the default: a single `Package.swift` shows the whole
graph, and every module is still a separate compile unit with its own access control.
Split into **one package per feature** only with a reason (separate team ownership,
separate CI jobs, reuse in another app) — decide once and record it in an ADR.

The app target stays almost empty: the `@main` type, scene declarations, entitlements,
Info.plist, asset catalog for the app icon, and the composition root that creates the live
dependencies. Extensions (widgets, intents, share extensions) are thin targets as well and
import the same modules.

## Layers

From top to bottom; a module may only import modules of **lower** layers.

| Layer | Contains | May import |
|---|---|---|
| **App** | `@main`, scenes, root navigation, composition root | everything below |
| **Features** | one module per user-facing feature: views, `@Observable` model, feature-local services | Shared only — **never another feature** |
| **Shared** | design system, domain types used by several features, adapters (persistence, network, system APIs) and their interfaces | other Shared modules, no feature |

- **Features never import features.** When feature A needs to show feature B, the App
  layer composes them (navigation destination, closure, or a route value passed up).
  When two features need the same type, it moves down to Shared.
- **Domain code has no UI framework imports** (no SwiftUI, AppKit, UIKit) — keep it in
  its own Shared module so it builds and tests on any platform.
- **Adapters behind protocols** at real I/O boundaries (file system, network, database,
  clock, system services). Put the protocol and its value types in a small interface
  module (`APIClientInterface`) when several modules use it or the implementation is
  heavy; the live implementation lives in its own module and is injected by the App
  layer. Don't create interface modules speculatively — only for a second implementation
  (the fake the tests use counts), build-time isolation or a dependency cycle.
- **Shared stays small.** No `Common`/`Utils` catch-all module; a helper used by one
  feature stays in that feature.

This mirrors the Modular Architecture of Tuist (formerly µFeatures), which splits each
feature into `Feature`, `FeatureInterface`, `FeatureTesting`, `FeatureTests` and
`FeatureExample` targets. Use that full split only for large apps where build time or
team boundaries demand it; the layer rules above are enough for most apps.

## Inside a module

- **Group by feature, not by type**: `Search/SearchView.swift`, `Search/SearchModel.swift`,
  `Search/Components/ResultRow.swift` — no app-wide `Views/`, `ViewModels/`, `Models/`
  folders.
- **Public API is the slice's contract**: mark only what the App layer or other modules
  use as `public`; everything else stays `internal`. A feature usually exports one entry
  view and its model's initializer.
- **One primary type per file**, file named after it; split files that pass a few hundred
  lines — smaller files are cheaper to read and safer to edit.
- **Resources live with the module**: its own String Catalog and assets
  (`resources: [.process("Resources")]`), accessed with `bundle: .module` / `#bundle`.
- **Previews with fixtures** for every screen and important component (`#Preview` with
  sample data from a `Fixtures` file or the testing target) — agents and reviewers check
  UI through them.
- **Tests next to the module**: `Tests/<Module>Tests/`, fakes for the module's
  dependencies in the test target or a `<Module>Testing` target.

## Let the compiler enforce the boundaries

- Every import must be declared in `Package.swift`; SwiftPM rejects imports of targets the
  module doesn't depend on.
- Turn on `MemberImportVisibility` (SE-0444) so members of a module are only visible
  where that module is imported, not leaked through another import. New Xcode 27 projects
  enable it already (`SWIFT_UPCOMING_FEATURE_MEMBER_IMPORT_VISIBILITY`).
- Consider `InternalImportsByDefault` (SE-0409) for packages: imports become `internal`
  unless written `public import`, so a module's dependencies don't leak into its clients.
- **Check the layer rules in CI.** `scripts/check_module_graph.py` reads
  `swift package describe --type json` and a small `module-layers.json` (layers top to
  bottom, `"isolated": true` for the feature layer, documented exceptions in `"allow"`).
  It fails on upward imports, feature-to-feature imports and modules that belong to no
  layer:

  ```sh
  python3 -I scripts/check_module_graph.py module-layers.json --package-path Packages/AppModules
  ```

  Exit codes: 0 = clean, 1 = violations, 2 = input error. Copy the script into the
  project's `scripts/` folder; it only needs Python 3 and the Swift toolchain.

## Keep the Xcode project small

- Code lives in packages; the agent edits `Package.swift` and Swift files, which are
  plain text and merge well. Avoid hand-editing `project.pbxproj`.
- Use **folder-synchronized groups** (Xcode 16+) for the app target so new files need no
  project-file change; consider the JSON `.xcproj` format (Xcode 27.2+) once the whole
  team and CI are on Xcode 27.
- Add third-party packages through `Package.swift` with pinned versions, not through
  Xcode's package UI — and only after approval.

## Agent harness

- **`AGENTS.md` at the repository root**, short and factual: required Xcode version, the
  exact build / test / lint / format commands, the module map and layer rules (or a link
  to `docs/architecture.md`), where new code goes, conventions, and what must not be
  touched. Agents launched from Xcode 27 read `AGENTS.md` when the agent itself supports
  it (Apple developer forums answer). Tool-specific files (`CLAUDE.md` and others) point
  to it instead of repeating it — follow the project's rule on whether such files are
  committed.
- **Deterministic commands** that agents and CI share — for example a `scripts/` folder
  or Makefile with `build`, `test`, `lint`, `check-modules`. Each prints a clear result
  and exits non-zero on failure.
- **Architecture notes in the repo** (`docs/architecture.md`), updated in the same change
  as the code — Apple's WWDC26 agent session shows exactly this practice.
- **Fast feedback per module**: `swift build` / `swift test` inside the package for
  modules that build on macOS; `xcodebuild … -only-testing:` for the rest.
- **Xcode tools for agents**: `xcrun mcpbridge` bridges an MCP client to Xcode's tools
  (build, tests, preview rendering, documentation search) while Xcode is running;
  `xcrun mcp-server` manages the headless server (its `enable`/`approve` commands need
  sudo — ask first). Per-agent configuration for agents launched inside Xcode lives in
  `~/Library/Developer/Xcode/CodingAssistant/<agent>/` (user level, not in the repo).
- Third-party agent tooling such as XcodeBuildMCP (MIT) is optional and a new dependency
  — only with approval.

## Sources

- Organizing your code with local packages — https://developer.apple.com/documentation/xcode/organizing-your-code-with-local-packages
- Swift Package Manager — https://www.swift.org/documentation/package-manager/
- SE-0444 Member import visibility — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0444-member-import-visibility.md
- SE-0409 Access-level modifiers on import declarations — https://github.com/swiftlang/swift-evolution/blob/main/proposals/0409-access-level-on-imports.md
- Extending and customizing agents (Xcode) — https://developer.apple.com/documentation/xcode/extending-and-customizing-agents
- WWDC26 session 259 (agentic coding in Xcode, architecture notes in the project) — https://developer.apple.com/videos/play/wwdc2026/259/
- Apple developer forums: AGENTS.md support in Xcode 27 — https://developer.apple.com/forums/thread/833246
- Tuist: The Modular Architecture (TMA) — https://tuist.dev/en/docs/guides/features/projects/tma-architecture
- Feature-Sliced Design (layers and slices, ideas only) — https://feature-sliced.design/
- SPM modular architecture for agentic coding (secondary) — https://dev.to/fraser-scott-morrison/spm-modular-programming-architecture-2a98 ,
  example repo https://github.com/fraserscottmorrison/spm-modular-programming
- pointfreeco/isowords (one package, many modules; secondary example) — https://github.com/pointfreeco/isowords
- XcodeBuildMCP (MIT, optional) — https://github.com/getsentry/XcodeBuildMCP
