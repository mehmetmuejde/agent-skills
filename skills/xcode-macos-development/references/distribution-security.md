# Distribution, sandbox, permissions and security (macOS)

Decide the distribution channel first — Mac App Store or Developer ID (outside the store).
It drives the sandbox, entitlements, update mechanism and which system access is
possible. Record the decision in an ADR.

## Mac App Store

- App Sandbox is mandatory.
- Packaged by Xcode only — no third-party installers.
- No login items or auto-launch without the user's consent; no downloading of code or apps
  that change the app's functionality; updates only through the store.
- Uploads must not contain `com.apple.quarantine` extended attributes on any file.
- Since April 2026 uploads must be built with Xcode 26 / the 26 SDKs or newer.

## Developer ID (outside the store)

1. Sign with a **Developer ID Application** certificate.
2. **Hardened Runtime** on (`ENABLE_HARDENED_RUNTIME = YES`), secure timestamp, no
   `get-task-allow` entitlement in the release build.
3. **Notarize** and **staple**:

```sh
xcrun notarytool submit build/App.zip --keychain-profile "<profile>" --wait
xcrun stapler staple build/App.app          # also for .dmg / .pkg
xcrun notarytool log <submission-id> --keychain-profile "<profile>"
```

- Read the notary log even when the submission is accepted — warnings become errors later.
- `altool` is no longer accepted for notarization; Xcode Organizer can notarize as well.
- Store notary credentials with `notarytool store-credentials` in the keychain — never in
  scripts or the repo.
- Release checks (Gatekeeper on a clean machine) are in the `xcode-macos-testing` skill.

## App Sandbox

- Keep the sandbox on for Developer ID apps too — the templates enable it.
- Add only the entitlements the app needs: network client/server, user-selected files
  (read-only or read-write), Downloads, camera, microphone, …
- Entitlements declare intent. Privacy prompts (TCC) still appear.
- Persistent access to user-chosen files: security-scoped bookmarks.

```swift
let data = try url.bookmarkData(options: .withSecurityScope,
                                includingResourceValuesForKeys: nil, relativeTo: nil)
// later
var isStale = false
let url = try URL(resolvingBookmarkData: data, options: .withSecurityScope,
                  relativeTo: nil, bookmarkDataIsStale: &isStale)
guard url.startAccessingSecurityScopedResource() else { return }
defer { url.stopAccessingSecurityScopedResource() }
if isStale { /* create and store a fresh bookmark */ }
```

## Hardened Runtime exceptions

`com.apple.security.cs.allow-jit`, `disable-library-validation`,
`allow-unsigned-executable-memory` only when strictly required, each with a written reason.
Plug-ins loaded into the app inherit its entitlements.

## Login items, agents, daemons

- Use `SMAppService`: `.mainApp`, `.loginItem(identifier:)`, `.agent(plistName:)`,
  `.daemon(plistName:)`.
- Register only after the user opts in (a setting, off by default).
- Handle `.requiresApproval`: explain and open
  `SMAppService.openSystemSettingsLoginItems()`.
- `SMLoginItemSetEnabled` and hand-written LaunchAgents plists are legacy.

## Privacy permissions (TCC) and Full Disk Access

- Ask in context, with purpose strings (`NS…UsageDescription`) that state clearly what the
  access is used for.
- **Full Disk Access** has no API to request it and no reliable API to query it. Attempt
  the operation, handle the permission error, then explain and send the user to
  System Settings › Privacy & Security. Never read the TCC database — it is not API.
  Caveat: this guidance comes from Apple DTS forum posts (2018–2022); it is still the only
  Apple statement — verify the System Settings deep link on the current macOS.
- Mac App Store apps should not depend on Full Disk Access.

## Secrets and credentials

- No API keys or secrets in the bundle, the repo or `Info.plist`; provider secrets stay on
  a server.
- User tokens and passwords go into the **Keychain**, never `UserDefaults` or files.
- Use the most restrictive `kSecAttrAccessible` that works (`…WhenUnlocked` is the default;
  `…ThisDeviceOnly` prevents migration to other devices); `SecAccessControl` with
  `.userPresence` for high-value items.

## Network

- App Transport Security defaults stay on (HTTPS only). Fix the server instead of adding
  `NSExceptionDomains`; never `NSAllowsArbitraryLoads` in production.

## Privacy manifest

- `PrivacyInfo.xcprivacy` in the app and in every SDK bundle you ship: collected data
  types, tracking domains.
- Required-reason API declarations are only enforced for iOS, iPadOS, tvOS, visionOS and
  watchOS — add them anyway in shared multiplatform code.
- Data shared with third parties — **including third-party AI services** — needs
  disclosure and explicit permission (App Review 5.1.2).

## Running external tools

- `Process` with an explicit executable URL and an argument array — never a shell string
  built from user input.
- Commands that change or delete user data require explicit confirmation in the UI and
  should prefer moving to the Trash (`FileManager.trashItem`) over deletion.

## Sources

- App Sandbox — https://developer.apple.com/documentation/security/app-sandbox
- Configuring the macOS App Sandbox — https://developer.apple.com/documentation/xcode/configuring-the-macos-app-sandbox
- Accessing files from the macOS App Sandbox — https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox
- Hardened Runtime — https://developer.apple.com/documentation/security/hardened-runtime
- Notarizing macOS software before distribution — https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- Developer ID — https://developer.apple.com/developer-id/
- SMAppService — https://developer.apple.com/documentation/servicemanagement/smappservice
- Apple DTS forum: Full Disk Access — https://developer.apple.com/forums/thread/107546 , https://developer.apple.com/forums/thread/114452
- Restricting keychain item accessibility — https://developer.apple.com/documentation/security/restricting-keychain-item-accessibility
- NSAppTransportSecurity — https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity
- Privacy manifest files — https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
- App Store Review Guidelines — https://developer.apple.com/app-store/review/guidelines/
- Upcoming requirements — https://developer.apple.com/news/upcoming-requirements/
