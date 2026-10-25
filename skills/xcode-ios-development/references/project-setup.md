# Project setup, build settings and tooling (iOS / iPadOS)

State: Xcode 27.1, Swift 6.4, iOS 27.1 SDK. Check the installed versions first:

```sh
xcodebuild -version
swift --version
xcrun --sdk iphoneos --show-sdk-version
xcrun simctl list runtimes          # is an iOS simulator runtime installed?
```

Installing a simulator runtime (`xcodebuild -downloadPlatform iOS`) changes the system —
ask before running it.

## What a new Xcode 27 project gives you

| Setting | Template value | Our rule |
|---|---|---|
| `SWIFT_VERSION` | `5.0` | set `6` (recommendation, not an Apple default) |
| `SWIFT_APPROACHABLE_CONCURRENCY` | `YES` | keep on every target |
| `SWIFT_DEFAULT_ACTOR_ISOLATION` | `MainActor` (app target) | keep for app/UI modules only |
| `SWIFT_UPCOMING_FEATURE_MEMBER_IMPORT_VISIBILITY` | `YES` | keep |
| `ENABLE_USER_SCRIPT_SANDBOXING` | `YES` | keep; declare script inputs/outputs |
| `LOCALIZATION_PREFERS_STRING_CATALOGS`, `SWIFT_EMIT_LOC_STRINGS`, `STRING_CATALOG_GENERATE_SYMBOLS` | `YES` | keep |
| `ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS` | `YES` | keep |
| Deployment target | latest iOS | lower it deliberately, see below |

## Deployment target and SDK requirements

- Pick the oldest iOS you really support and gate newer APIs with `#available` /
  `@available`.
- App Store: since April 2026 uploads must be built with Xcode 26 / the 26 SDKs or newer;
  since September 2026 iOS/iPadOS uploads must target iOS 13 or later.
- Building with the **iOS 27 SDK** changes behaviour even without code changes:
  - the **UIScene lifecycle is mandatory** — an app without it fails to launch;
  - the app becomes **resizable** (iPad windows, iPhone Mirroring, iPhone Duo);
  - the Liquid Glass opt-out `UIDesignRequiresCompatibility` is ignored.
  See `layout-resizability.md` before raising the SDK of an existing app.
- On-device debugging needs iOS 17 or later.

## Modules

- Keep the app target thin: `App` struct, scenes, composition. Features and core logic
  live in **local Swift packages** (File › New › Package, add the library product to the
  app target).
- One package target per feature or core area; UI packages use MainActor default
  isolation, non-UI packages stay `nonisolated` (see `concurrency.md`).
- Extensions (widgets, intents, notification service) share code through packages, not by
  adding the same files to several targets.
- `// swift-tools-version: 6.2` or newer so `.defaultIsolation` is available.
- Explicit modules are the default since Xcode 26; turn them off only for a blocking issue,
  with an ADR. Clang module names must be unique per dependency scan (Xcode 27).

## Warnings

- Promote selected warning groups to errors (`SWIFT_WARNINGS_AS_ERRORS_GROUPS`, Swift
  6.4 `@diagnose`) rather than a blanket "treat warnings as errors".
- Fix deprecation warnings when you touch the code; don't silence them.

## Project file format

Xcode 27.2 introduces a JSON project file (`.xcproj`), readable only by Xcode 27+. Adopt it
only once everyone and CI use Xcode 27.2 or newer — a binding decision (ADR).

## Optional hardening

- **Enhanced Security** capability (pointer authentication, typed allocators, memory
  tagging on A19 / M5 and later): threat-model driven, test thoroughly.
- `SWIFT_STRICT_MEMORY_SAFETY` (Swift 6.2+): opt-in for the strictest projects.
- Apple's bundled `audit-xcode-security-settings` skill reviews these settings (export
  with `xcrun agent skills export --output-dir <absolute path>`).

## Formatting and linting

- `swift format` ships with the toolchain. Commit a `.swift-format` JSON config; run
  `swift format lint --strict --recursive Sources Tests` in CI.
- SwiftLint (MIT, third-party) is optional — a new dependency, needs approval.

## Build and CI

```sh
xcrun simctl list devices available
xcodebuild build -scheme App -destination 'platform=iOS Simulator,name=iPhone 17'
xcodebuild test  -scheme App -destination 'platform=iOS Simulator,name=iPhone 17' \
  -resultBundlePath build/test.xcresult
xcodebuild archive -scheme App -destination 'generic/platform=iOS' \
  -archivePath build/App.xcarchive
xcodebuild -exportArchive -archivePath build/App.xcarchive \
  -exportOptionsPlist ExportOptions.plist -exportPath build/export
```

- Device names in `-destination` must exist on the machine — take them from
  `simctl list`.
- Automatic signing for development; distribution certificates and profiles only in the
  CI keychain, never in the repo. App Store Connect API keys (`.p8`) are secrets.
- Interface Builder files compile in `toolchain` mode without a simulator on build servers
  (Xcode 27).
- Xcode Cloud is an option for Apple-hosted CI; GitHub runners provide an `xcode-27` image.

## Sources

- Xcode 27 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- Xcode 27.1 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27_1-release-notes
- Xcode 27.2 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes
- Build settings reference — https://developer.apple.com/documentation/xcode/build-settings-reference
- Upcoming requirements — https://developer.apple.com/news/upcoming-requirements/
- Organizing your code with local packages — https://developer.apple.com/documentation/xcode/organizing-your-code-with-local-packages
- Updating your project configuration file format — https://developer.apple.com/documentation/xcode/updating-your-xcode-project-configuration-file-format
- Enabling enhanced security — https://developer.apple.com/documentation/xcode/enabling-enhanced-security-for-your-app
- Distributing your app for beta testing and releases — https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases
- swift-format — https://github.com/swiftlang/swift-format
