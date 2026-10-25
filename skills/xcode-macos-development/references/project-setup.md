# Project setup, build settings and tooling (macOS)

State: Xcode 27.1, Swift 6.4, macOS 27 SDK. Check the installed versions first:

```sh
xcodebuild -version
swift --version
xcrun --sdk macosx --show-sdk-version
```

## What a new Xcode 27 project gives you

Template defaults (read from Xcode 27.1's project templates):

| Setting | Template value | Our rule |
|---|---|---|
| `SWIFT_VERSION` | `5.0` | set `6` (recommendation, not an Apple default) |
| `SWIFT_APPROACHABLE_CONCURRENCY` | `YES` | keep on every target |
| `SWIFT_DEFAULT_ACTOR_ISOLATION` | `MainActor` (app target) | keep for app/UI modules only |
| `SWIFT_UPCOMING_FEATURE_MEMBER_IMPORT_VISIBILITY` | `YES` | keep |
| `ENABLE_USER_SCRIPT_SANDBOXING` | `YES` | keep; declare script inputs/outputs |
| `LOCALIZATION_PREFERS_STRING_CATALOGS`, `SWIFT_EMIT_LOC_STRINGS`, `STRING_CATALOG_GENERATE_SYMBOLS` | `YES` | keep |
| `ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS` | `YES` | keep; use generated color/image symbols |
| `ENABLE_APP_SANDBOX` | `YES` | keep, also for Developer ID apps |
| `ENABLE_HARDENED_RUNTIME` | `YES` | keep (required for notarization) |
| `ENABLE_USER_SELECTED_FILES` | `readonly` | widen only when the app writes user files |
| Deployment target | latest macOS | lower it deliberately, see below |

## Deployment target and architectures

- Pick the oldest macOS you really support and gate newer APIs with `#available` /
  `@available`. Every API newer than the deployment target needs a gate.
- Xcode 27 runs on Apple silicon only. With `MACOSX_DEPLOYMENT_TARGET >= 27.0`,
  `ARCHS_STANDARD` drops `x86_64` — macOS 26 was the last release for Intel Macs.
- Add `x86_64` only when you deliberately support Intel Macs on older macOS; the 27 SDK can
  still build Universal apps that back-deploy to macOS 12.
- The Mac App Store accepts Apple-silicon-only binaries.

## Modules

- Keep the app target thin: `App` struct, scenes, composition. Features and core logic
  live in **local Swift packages** (File › New › Package, add the library product to the
  app target).
- One package target per feature or core area; UI packages use MainActor default
  isolation, non-UI packages stay `nonisolated` (see `concurrency.md`).
- `// swift-tools-version: 6.2` or newer so `swiftSettings` like `.defaultIsolation` are
  available.
- Explicit modules are the default build mode since Xcode 26; turn them off
  (`SWIFT_ENABLE_EXPLICIT_MODULES = NO`) only for a blocking issue, with an ADR.
- Every Clang module name visible in one dependency scan must be unique (Xcode 27) —
  watch vendored `module.modulemap` files.

## Warnings

- Promote selected warning groups to errors (`SWIFT_WARNINGS_AS_ERRORS_GROUPS`, Swift
  6.4 `@diagnose`) rather than a blanket "treat warnings as errors" that breaks on every
  new compiler.
- Fix deprecation warnings when you touch the code; don't silence them.

## Project file format

Xcode 27.2 introduces a JSON project file (`.xcproj`), readable only by Xcode 27+. Adopt it
for merge-friendly diffs only once everyone and CI use Xcode 27.2 or newer — it is a
binding decision (ADR).

## Optional hardening

- **Enhanced Security** capability (pointer authentication, typed allocators, memory
  tagging on M5 and later): driven by the threat model, test thoroughly — it can affect
  stability.
- `SWIFT_STRICT_MEMORY_SAFETY` (Swift 6.2+): opt-in for the strictest projects.
- Apple's bundled `audit-xcode-security-settings` skill reviews these settings (export
  with `xcrun agent skills export --output-dir <absolute path>`).

## Formatting and linting

- `swift format` ships with the toolchain (swift-format 604). Commit a `.swift-format`
  JSON config; run `swift format lint --strict --recursive Sources Tests` in CI and
  `swift format --in-place --recursive …` locally.
- SwiftLint (MIT, third-party) is optional — a new dependency, needs approval.

## Documentation

- `///` doc comments on public API of packages; DocC catalogs for packages that others
  consume (`swift package generate-documentation` needs the swift-docc-plugin — a
  dependency; Xcode's *Build Documentation* works without it).

## Build and CI

```sh
xcodebuild -list -project App.xcodeproj
xcodebuild build -scheme App -destination 'platform=macOS'
xcodebuild test  -scheme App -destination 'platform=macOS' \
  -testPlan Default -resultBundlePath build/test.xcresult
xcodebuild archive -scheme App -destination 'generic/platform=macOS' \
  -archivePath build/App.xcarchive
xcodebuild -exportArchive -archivePath build/App.xcarchive \
  -exportOptionsPlist ExportOptions.plist -exportPath build/export
swift build && swift test          # inside a package
```

- Automatic signing for development. Distribution certificates only in the CI keychain;
  never commit certificates, provisioning profiles or `.p8` keys.
- Xcode Cloud is an option for Apple-hosted CI; GitHub runners provide an `xcode-27` image.
- Signing, notarization and distribution: `distribution-security.md`.

## Sources

- Xcode 27 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- Xcode 27.2 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes
- Xcode 26 release notes (explicit modules) — https://developer.apple.com/documentation/xcode-release-notes/xcode-26-release-notes
- Build settings reference — https://developer.apple.com/documentation/xcode/build-settings-reference
- Organizing your code with local packages — https://developer.apple.com/documentation/xcode/organizing-your-code-with-local-packages
- Updating your project configuration file format — https://developer.apple.com/documentation/xcode/updating-your-xcode-project-configuration-file-format
- Enabling enhanced security — https://developer.apple.com/documentation/xcode/enabling-enhanced-security-for-your-app
- swift-format — https://github.com/swiftlang/swift-format
- Swift-DocC — https://www.swift.org/documentation/docc/
- WWDC26 Platforms State of the Union — https://developer.apple.com/videos/play/wwdc2026/102/
