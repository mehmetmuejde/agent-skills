# Mac UI: scenes, menus, Liquid Glass, typography, accessibility

A Mac app should feel like a Mac app: resizable windows, a complete menu bar, keyboard
control and system components. State: macOS 27 with Liquid Glass.

## Scenes and windows

| Scene | Use |
|---|---|
| `WindowGroup` | main content; people can open several windows |
| `Window(id:)` | a unique utility window (opened with `openWindow(id:)`, listed in the Window menu) |
| `Settings` | the only place for app settings — gives "Settings…" with ⌘, |
| `MenuBarExtra` | a menu bar extra |
| `DocumentGroup` (+ `DocumentGroupLaunchScene`) | document-based apps |

- In a multiplatform target wrap `Settings` and `MenuBarExtra` in `#if os(macOS)`.
- Let people resize, move, hide and full-screen windows. Set sensible minimum sizes with
  `.frame(minWidth:minHeight:)`; don't fix the window size without a reason.
- Fewer modal sheets and fewer nesting levels than on iPhone — large displays allow side
  by side layouts (`NavigationSplitView`, inspectors).
- Dim custom-drawn content in inactive windows using `appearsActive` from the environment.
- State restoration: restore UI state only (selection, open windows), never data.

## Menu bar

- Every command is reachable from the menu bar, even when it also has a button.
- Standard menus and shortcuts stay standard (⌘N, ⌘O, ⌘S, ⌘W, ⌘Z, ⌘,). Add commands with
  `.commands { CommandMenu(…) }` and `CommandGroup(after:/before:/replacing:)`.
- Menu titles are one word where possible.
- macOS 27 hides icons in menus by default. Show an icon only on key actions — the exact
  opt-in API is new; verify it in the SDK / WWDC26 "What's new in SwiftUI" before using it.

## Menu bar extras (`MenuBarExtra`)

- Prefer a menu (`.menuBarExtraStyle(.menu)`); use the window style only when the content
  is too rich for a menu.
- Let people decide whether the extra appears: bind `isInserted:` to a setting.
- Don't make it the only entry point — the app may be hidden by the system or the user.
  Offer the same actions in the app's menus or Dock menu.
- The icon is a template image (monochrome, adapts to the menu bar appearance).
- Work behind a menu bar extra runs constantly — sample data only while it is visible
  (see the `xcode-macos-performance` skill).

## Liquid Glass (macOS 27)

- Standard SwiftUI/AppKit components adopt Liquid Glass automatically. Remove custom
  backgrounds from toolbars, sidebars, sheets, popovers and split views.
- macOS 27 refinements: sidebars extend to the window edges, accent-coloured sidebar
  icons, tighter window corners, a uniform toolbar via scroll edge effects, interactive
  glass on controls. Don't fight them with custom chrome.
- `UIDesignRequiresCompatibility` (the old opt-out) is ignored when building with the 27
  SDKs — there is no way out of the new design.
- Custom glass: `glassEffect(_:in:)` sparingly, on key functional elements only — never on
  content, never stacked glass on glass. Group nearby glass elements in a
  `GlassEffectContainer`; `.interactive()` for controls.
- Prefer `.buttonStyle(.glass)` / `.buttonStyle(.glassProminent)` over hand-made glass.
- Concentric corners instead of hard-coded radii: `ConcentricRectangle` in SwiftUI,
  `NSViewCornerConfiguration` in AppKit.
- Toolbars: hide whole items (not their content), group related items, separate groups
  with `ToolbarSpacer`, don't mix text and icon items in one group.
- Section headers in title-style capitalisation; no forced uppercase.

## Typography

macOS has **no Dynamic Type**. Use the system text styles; sizes are fixed:

| Style | Size |
|---|---|
| Large Title | 26 pt |
| Title 1 / 2 / 3 | 22 / 17 / 15 pt |
| Headline | 13 pt bold |
| Body (default) | 13 pt |
| Callout | 12 pt |
| Subheadline | 11 pt |
| Footnote, Caption 1, Caption 2 | **10 pt** |

- 10 pt is the minimum. `.caption`/`.footnote` render at 10 pt on the Mac — too small for
  information people need; use them sparingly.
- If the design needs sizes between the styles, define them once in the design system
  (e.g. a `Font` extension) instead of scattering `.system(size:)` literals.
- `monospacedDigit()` for numbers that change in place.

## Controls and layout

- Default control size 28×28 pt, minimum 20×20 pt.
- Full keyboard navigation: every control reachable with Tab, `.focusable()` and
  `@FocusState` for custom controls, default and cancel buttons on dialogs
  (`.keyboardShortcut(.defaultAction)` / `.cancelAction`). For destructive confirmations
  make Cancel the default.
- Contextual menus (`.contextMenu`) on items that have actions.

## Color and symbols

- Semantic system colors or asset-catalog Color Sets with light, dark and
  increased-contrast variants. Never hard-code appearance-specific colors.
- SF Symbols for standard actions (same icon the system uses for the same action); choose
  the rendering mode deliberately (monochrome, hierarchical, palette, multicolor).

## Accessibility — always

- Every icon-only control has a label: `Button("Add", systemImage: "plus") { … }` instead
  of an image-only button; `.accessibilityLabel` for custom views.
- Decorative images: `.accessibilityHidden(true)`. Headings: `.accessibilityAddTraits(.isHeader)`.
- Contrast: ≥ 4.5:1 for text up to 17 pt, ≥ 3:1 for 18 pt or bold. Check light and dark.
- Respect Reduce Motion (`accessibilityReduceMotion`), Reduce Transparency, Increase
  Contrast and — new on macOS 27 — Show Borders. Check them in Xcode Previews overrides and
  the Device Hub inspector.
- Group related elements (`.accessibilityElement(children: .combine)`) so VoiceOver reads a
  row as one item.
- VoiceOver can be driven from UI tests with `XCUIVoiceOverService` (Xcode 27) — see the
  testing skill.

## Sources

- HIG Designing for macOS — https://developer.apple.com/design/human-interface-guidelines/designing-for-macos
- HIG The menu bar — https://developer.apple.com/design/human-interface-guidelines/the-menu-bar
- HIG Settings — https://developer.apple.com/design/human-interface-guidelines/settings
- HIG Typography — https://developer.apple.com/design/human-interface-guidelines/typography
- HIG Accessibility — https://developer.apple.com/design/human-interface-guidelines/accessibility
- HIG Dark Mode — https://developer.apple.com/design/human-interface-guidelines/dark-mode
- HIG SF Symbols — https://developer.apple.com/design/human-interface-guidelines/sf-symbols
- SwiftUI Window / Settings / MenuBarExtra — https://developer.apple.com/documentation/swiftui/window , https://developer.apple.com/documentation/swiftui/settings , https://developer.apple.com/documentation/swiftui/menubarextra
- Adopting Liquid Glass — https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass
- Applying Liquid Glass to custom views — https://developer.apple.com/documentation/swiftui/applying-liquid-glass-to-custom-views
- UIDesignRequiresCompatibility — https://developer.apple.com/documentation/bundleresources/information-property-list/uidesignrequirescompatibility
- WWDC26 What's new in SwiftUI — https://developer.apple.com/videos/play/wwdc2026/269/
- WWDC26 Modernize your AppKit app — https://developer.apple.com/videos/play/wwdc2026/289/
