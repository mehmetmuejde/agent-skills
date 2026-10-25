# Snapshots and previews

Apple has no snapshot-testing API. Visual checks come from three places: `#Preview` while
building, snapshot tests for regressions, and UI-test screenshots for flows.

## Previews

- Use `#Preview`. `PreviewProvider` and its modifiers are deprecated in Xcode 27.
- `#Preview(arguments:)` (Xcode 27) renders a grid of variants from one preview — use it
  for states (empty, loading, error, long text).
- Check the canvas variants for color scheme, orientation, Dynamic Type size,
  localization and increased contrast before calling a view done.
- Set `\.locale` and `\.layoutDirection` in a preview to see a translation or right-to-left
  layout without switching the scheme language.
- Previews are not tests: nothing fails when a preview looks wrong. Xcode's MCP server
  offers a preview-rendering tool, so an agent can render and inspect a preview image.
- Previews run on the main actor and must not touch real data or the network — feed them
  sample models.

## Snapshot tests

The de-facto standard is **pointfreeco/swift-snapshot-testing** (MIT; 1.19.x in October
2026). It is a **new dependency** — add it only with approval, and only to the test
target.

- Works with Swift Testing (a `.snapshots(record: .failed)` suite trait) and XCTest.
- Reference images must be recorded and compared on the **exact same simulator model and
  OS version**. Pin both in CI; record references on the CI configuration.
- Prefer text strategies (`.dump`, `.json`, `.recursiveDescription`) for logic and
  structure; image snapshots only for layout that matters.
- Review every re-recorded reference in the diff like code. A test that re-records on
  failure by default is not a test.
- Small pixel drift between machines: decide on a precision threshold once per project;
  Swift Testing's `.warning` severity can report drift without failing.

## Rendering limits

- `ImageRenderer` only draws what SwiftUI renders itself (text, images, shapes, simple
  stacks). Views composited by Core Animation — complex system controls and containers,
  web views, media players, most UIKit/AppKit-backed views — come out as a placeholder.
- Liquid Glass materials are not reproduced in snapshots taken through hosting controllers
  (reported by third parties, not by Apple). Treat such snapshots as **layout-only** and
  check glass on a real device, in Device Hub or in previews.
- Snapshots don't see animations, focus rings or hover states; cover those in UI tests or
  manual checks.

## UI-test screenshots

- Test plan configurations capture screenshots and video of UI tests; keep them for
  failures by default, "keep all" for a review run.
- Explicit captures: `XCUIScreen.main.screenshot()` or `element.screenshot()`, then attach
  with `XCTAttachment` (`.lifetime = .keepAlways` to keep it on success).
- Screenshots for the store are a separate concern; generate them from a UI test with
  fixed data, a fixed date and (iOS) an overridden status bar.

## Sources

- https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- https://developer.apple.com/documentation/swiftui/imagerenderer
- https://developer.apple.com/documentation/xcode/previewing-localizations
- https://developer.apple.com/documentation/xcuiautomation
- https://github.com/pointfreeco/swift-snapshot-testing (MIT, third party)
- https://dev.classmethod.jp/en/articles/swift-snapshot-testing/ (secondary: Liquid Glass not reproduced)
