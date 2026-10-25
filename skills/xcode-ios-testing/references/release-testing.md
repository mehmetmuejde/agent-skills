# Release testing on iPhone and iPad

Simulator runs and Debug builds under the debugger behave differently from what users
install. Before every release, test the archived Release build on real devices.

## Real devices, no debugger

- Archive with the **Release** configuration; install the archive build (TestFlight or an
  ad-hoc/development export) on **real devices** — the simulator is not a user device
  (memory limits, thermal state, cameras, performance, push, background execution).
- Launch from the **home screen**, not from Xcode. The debugger disables watchdog
  terminations and keeps the app from being suspended — background `URLSession`
  transfers, background tasks and suspension bugs never show up under it.
- Cover the oldest supported device and OS, a current iPhone, an iPad (windowed and full
  screen), and an iPhone Duo or its simulator if the app supports the form factor.

## Install paths

- **Fresh install** (no data) and **update** from the version currently in the App Store:
  data migration, SwiftData/Core Data schema migration, keychain items, preferences.
- Deleting the app does not delete everything: **App Group containers and keychain
  items survive** — test a reinstall with leftover keychain data.
- Restore from backup / new device migration where the app stores device-bound data
  (`…ThisDeviceOnly` keychain items don't migrate).

## Conditions

- **Low Power Mode** on; low battery.
- Poor networks: Network Link Conditioner (Settings > Developer), airplane mode during a
  request, captive portal, **IPv6-only / NAT64** network.
- Low memory: many apps open, large photos/videos; watch for termination in the
  background and state restoration afterwards.
- Large, damaged or unexpected user data (huge libraries, corrupt files, full disk).
- Interruptions: incoming call, notification, Siri, app switcher, Control Center,
  rotation during an animation, split view and Stage Manager resizing on iPad.
- Accessibility: largest text sizes, VoiceOver, Voice Control, Bold Text, Reduce Motion,
  Increase Contrast, dark mode.
- Every shipped language once; right-to-left if supported.

## Permissions and privacy

- Every permission prompt appears in context with a clear purpose string; denying it
  leaves the app usable and explains how to change it in Settings.
- `app.resetAuthorizationStatus(for:)` in UI tests re-triggers prompts; on devices, reset
  via Settings or a reinstall.
- Tracking only after the App Tracking Transparency prompt; the privacy manifest matches
  what the build actually collects (Xcode's privacy report from the archive).

## In-app purchases

- Local testing with a **StoreKit configuration file** in the scheme and the StoreKit
  Transaction Manager: purchases, renewals, refunds, interrupted purchases, Ask to Buy,
  offer codes and subscription bundles (Xcode 27).
- Then the sandbox environment with a sandbox account on a device, then TestFlight.
- Restore purchases on a second device; expired and grace-period subscriptions.

## App Intents, widgets, extensions

- **AppIntentsTesting** (Xcode 27) runs intents across process boundaries; it lives in a
  UI-testing bundle on XCTest, signed with the same team as the app.
- Widgets and Live Activities: placeholder, snapshot and timeline states; data shared
  through the App Group stays consistent when app and widget write at the same time.
- Extensions have much lower memory limits than the app — test them with real data.

## Push notifications

- Simulator: `xcrun simctl push <UDID> <bundle-id> payload.json` for presentation and
  handling.
- Device: real APNs (sandbox environment for development builds, production for
  TestFlight/App Store), including notification service extensions and background pushes.
  Background pushes are rate-limited — test the app's behaviour when they don't arrive.

## TestFlight

- Up to **100 internal** testers and up to **10,000 external** testers; the first build
  for external testers needs beta review.
- Native speakers review localizations through TestFlight feedback.
- Ship the release candidate through TestFlight before App Review; use the same build.

## App Review readiness

- Complete build: no placeholder content, no broken links; a **demo account** in the
  review notes if the app needs sign-in.
- Account creation in the app ⇒ account deletion in the app.
- Screenshots show the real app.
- Purpose strings, privacy manifest and App Privacy answers agree.

## Release checklist (iOS)

- [ ] Full test plan green on the release commit (small iPhone, large iPhone, iPad);
      result bundle stored
- [ ] Archive build on real devices, launched from the home screen
- [ ] Fresh install and update from the App Store version; leftover keychain data
- [ ] Low Power Mode, bad networks, IPv6-only, low memory, interruptions
- [ ] Permissions: granted and denied paths
- [ ] StoreKit: local configuration, sandbox, restore
- [ ] Widgets, intents, extensions, push
- [ ] Accessibility pass at the largest text size; every language opened once
- [ ] TestFlight build is the build submitted for review

## Sources

- https://developer.apple.com/documentation/xcode/testing-a-release-build
- https://developer.apple.com/documentation/xcode/setting-up-storekit-testing-in-xcode
- https://developer.apple.com/videos/play/wwdc2026/295/ — Validate your App Intents adoption with AppIntentsTesting
- https://developer.apple.com/testflight/
- https://developer.apple.com/app-store/review/guidelines/
- https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
- https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns
- https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
