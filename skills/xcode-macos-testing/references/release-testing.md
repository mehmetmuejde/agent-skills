# Release testing on macOS

Debug builds attached to the debugger behave differently from what users install. Before
every release, test the archived Release build the way a user gets it.

## Release build in general

- Archive with the **Release** configuration and test that archive, not a Debug run.
- Launch it from Finder, not from Xcode: no debugger, no Xcode environment variables, no
  `DYLD_*` settings.
- Test a **fresh install** (no container, no preferences) and an **update** from the last
  shipped version: data migration, preferences, security-scoped bookmarks, login items.
- Test as a **standard (non-admin) user** — file-system privileges differ.
- On a MacBook: run on battery; with little free memory (open memory-heavy apps); with a
  nearly full disk if the app writes much data.
- Large, damaged or unexpected user files (huge folders, symlinks, packages, files without
  read permission, iCloud placeholders) where the app reads user data.
- Each supported macOS version and each architecture you ship (Apple silicon only from a
  macOS 27 deployment target; x86_64 only if deliberately supported on older macOS).
- Localizations: every shipped language once, plus a right-to-left language if supported.
- Menu bar, keyboard shortcuts, Services, Dock menu, state restoration after a restart.

## Developer ID distribution (outside the Mac App Store)

Requirements for the build:

- Signed with a **Developer ID Application** certificate (installers: Developer ID
  Installer), with a secure timestamp.
- **Hardened Runtime** enabled; exceptions only where strictly needed. Plug-ins and
  hosted code run with the host's entitlements — test plug-in hosting under the hardened
  runtime.
- No `com.apple.security.get-task-allow` entitlement.
- **Notarized** (`xcrun notarytool submit … --wait`, or the Organizer) and the ticket
  **stapled** (`xcrun stapler staple` on the app, DMG or pkg). Read the notary log even
  when notarization succeeds — warnings become errors later.
- Mac App Store builds are not notarized; they go through App Review instead, and must not
  carry `com.apple.quarantine` extended attributes on any file.

### Gatekeeper test — the reliable way

Gatekeeper caches results on the machine that built or already opened the app, so tests
on the build Mac prove little.

1. Use a fresh Mac or a macOS VM that has never seen the app; snapshot it and restore the
   snapshot before every run.
2. Upload the release artifact (DMG/zip/pkg) where users get it and **download it with
   Safari**, so it carries the quarantine attribute.
3. **Disconnect the network** before the first launch — this proves the ticket is stapled.
4. Install and use the app like a user: first launch, permission prompts, login item,
   helper tools, update mechanism.

### Quick checks (less accurate, useful in CI)

```sh
syspolicy_check distribution App.app          # macOS 14+: checks against notarization rules
spctl -a -t exec -vvv App.app                 # Gatekeeper assessment of the app
spctl -a -t open -vvv --context context:primary-signature App.dmg
spctl -a -t install -vvv App.pkg
xcrun stapler validate App.app
codesign -vvvv -R="notarized" --check-notarization App.app
codesign -d --entitlements - App.app          # no get-task-allow, only intended entitlements
```

`xcodebuild -exportNotarizedApp -archivePath … -exportPath …` exports a notarized app from
an archive in CI. Notarization uploads the build to Apple — run it only when the release
is approved.

## Permissions and privacy on a clean machine

- Every TCC prompt appears in context with a clear purpose string (camera, microphone,
  files and folders, automation, accessibility).
- Denying a permission leaves the app usable and explains how to grant it later.
- Features that need Full Disk Access: there is no API to request or reliably query it.
  Verify that the app attempts the operation, handles the error, explains the situation
  and opens the right pane in System Settings (check the deep link on the current macOS).
- Login items and agents registered with `SMAppService` appear in System Settings > General
  > Login Items only after the user opted in; `.requiresApproval` is handled.
- Uninstalling (moving the app to the Trash) leaves no running agents behind.

## TestFlight for Mac

TestFlight works for macOS apps too: up to 100 internal testers, up to 10,000 external
testers (the first external build needs beta review). Use it for Mac App Store builds and
for localization review by native speakers.

## Release checklist (macOS)

- [ ] Full test plan green on the release commit; result bundle stored
- [ ] Archive (Release) launched outside Xcode: fresh install and update path
- [ ] Standard user, battery, low memory, large/odd user data
- [ ] Developer ID: hardened runtime, no `get-task-allow`, notarized, stapled
- [ ] Gatekeeper test on a clean VM, downloaded via Safari, offline first launch
- [ ] Permissions denied/granted paths; login items opt-in
- [ ] Every shipped language opened once

## Sources

- https://developer.apple.com/documentation/xcode/testing-a-release-build
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://developer.apple.com/documentation/security/hardened-runtime
- https://developer.apple.com/forums/thread/130560 — Apple DTS: Testing a Notarised Product
- https://developer.apple.com/news/upcoming-requirements/
- https://developer.apple.com/documentation/servicemanagement/smappservice
- https://developer.apple.com/testflight/
- Local tool help on Xcode 27.1: `man syspolicy_check`, `man spctl`, `xcrun stapler --help`, `xcodebuild -help`
