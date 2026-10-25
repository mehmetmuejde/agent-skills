# Security, privacy and App Review (iOS / iPadOS)

Most App Store rejections and data leaks come from the same few places: secrets in the
bundle, missing privacy declarations, vague purpose strings and missing account deletion.

## Secrets and credentials

- No API keys or secrets in the app bundle, `Info.plist`, asset catalogs or the repo — the
  bundle is readable by anyone. Provider secrets stay on a server; the app talks to your
  backend.
- User tokens, passwords and keys go into the **Keychain** — never `UserDefaults`, files or
  logs.
- Choose the most restrictive `kSecAttrAccessible` that works:
  - `…WhenUnlocked` (default) for most items;
  - `…WhenUnlockedThisDeviceOnly` / `…ThisDeviceOnly` variants to prevent migration to a
    new device or backup restore;
  - `…AfterFirstUnlock` only for items needed by background work.
- High-value items: `SecAccessControl` with `.userPresence` (Face ID / Touch ID / passcode).
- Keychain items survive app deletion — clear them on first launch after reinstall if the
  app's data model requires it.
- Logs: `Logger` with privacy annotations (`\(value, privacy: .private)`); dynamic values
  are private by default — keep it that way for personal data.

## Data protection

- User data files: `.completeFileProtection` (write with `.completeFileProtection` /
  `FileProtectionType.complete`).
- Weaker classes (`completeUntilFirstUserAuthentication`) only for files background work
  must read while the device is locked.
- Don't store sensitive data in caches or `tmp` without protection; exclude re-creatable
  data from backups (`isExcludedFromBackup`).

## Network

- App Transport Security stays on (HTTPS only). Fix the server instead of adding
  `NSExceptionDomains`; never `NSAllowsArbitraryLoads` in production.
- Validate server data like any untrusted input.

## Privacy manifest (`PrivacyInfo.xcprivacy`)

- Required in the app and in every SDK bundle you ship; SDKs on Apple's list need their own
  signed manifest.
- Declare:
  - collected data types and their purposes (`NSPrivacyCollectedDataTypes`);
  - tracking (`NSPrivacyTracking`) and tracking domains (`NSPrivacyTrackingDomains`);
  - **required-reason APIs** (`NSPrivacyAccessedAPITypes`) with an approved reason for
    each: file timestamps, system boot time, disk space, active keyboards, `UserDefaults`.
- Uploads with missing required-reason declarations are rejected (enforced since May
  2024). `UserDefaults` counts — almost every app needs that entry.
- Keep the manifest in sync with the App Store privacy "nutrition label".

## Permissions

- Request access in context, right before the feature needs it — not all at first launch.
- Purpose strings (`NS…UsageDescription`) state clearly and completely what the data is
  used for; vague strings are rejected (5.1.1).
- Tracking across apps or websites only after App Tracking Transparency consent.
- Personal data shared with third parties — **including third-party AI services** — needs
  disclosure and explicit permission (5.1.2).

## App Review essentials

| Guideline | Requirement |
|---|---|
| 1.2 | apps with user-generated or AI-generated content need filtering, reporting and blocking |
| 2.1 | complete builds; a demo account for review if login is required |
| 2.3 | accurate metadata and screenshots |
| 2.5.1 / 2.5.2 | public APIs only; no downloaded executable code |
| 2.5.4 | background modes only for their purpose |
| 2.5.14 | recording only with consent and a visible indicator |
| 3.1.1 | in-app purchase for digital content and unlocks |
| 4.2 | more than a repackaged website |
| 4.7 | rules for mini apps, chatbots and streamed games |
| 4.8 | a privacy-friendly login option next to third-party logins |
| 5.1.1(v) | account creation in the app ⇒ account deletion in the app |

Also: the launch screen must meet App Store requirements (TN3208); test the release build
on real devices before submission (`xcode-ios-testing`).

## Hardening (optional)

- Enhanced Security capability for high-risk apps (memory tagging on A19 and later) — test
  thoroughly.
- Jailbreak detection and obfuscation don't replace server-side checks; never trust the
  client for authorization.

## Sources

- Restricting keychain item accessibility — https://developer.apple.com/documentation/security/restricting-keychain-item-accessibility
- Encrypting your app's files — https://developer.apple.com/documentation/uikit/encrypting-your-app-s-files
- NSAppTransportSecurity — https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity
- Privacy manifest files — https://developer.apple.com/documentation/bundleresources/privacy-manifest-files
- Describing use of required reason API — https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api
- App Store Review Guidelines — https://developer.apple.com/app-store/review/guidelines/
- Upcoming requirements — https://developer.apple.com/news/upcoming-requirements/
- Enabling enhanced security — https://developer.apple.com/documentation/xcode/enabling-enhanced-security-for-your-app
- OWASP MASVS — https://mas.owasp.org/MASVS/
