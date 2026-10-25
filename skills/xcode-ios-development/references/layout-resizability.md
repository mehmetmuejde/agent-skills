# Layout, resizability, Liquid Glass and accessibility (iPhone and iPad)

With the iOS 27 SDK every app is resizable. Layout must work at any scene size, on any
device shape — iPhone, iPad windows, iPhone Mirroring on the Mac and the foldable
iPhone Duo.

## UIScene lifecycle (mandatory with the iOS 27 SDK)

- An app built with the iOS 27 SDK that has no scene lifecycle **fails to launch**.
- SwiftUI `App` apps already comply.
- UIKit apps: `UIApplicationSceneManifest` in the Info.plist plus a `UISceneDelegate`, or
  `application(_:configurationForConnecting:options:)`. Move window setup, URL handling
  and state restoration from the app delegate into the scene delegate.
- Apple's bundled `app-resizability` skill (Xcode 27) walks through this migration —
  export it with `xcrun agent skills export --output-dir <absolute path>`.

## Resizability

- Rebuilding with the iOS 27 SDK opts the app into resizing: iPad windows, iPhone apps on
  iPad, iPhone Mirroring on macOS 27, iPhone Duo.
- Lay out by **size classes and available space**, never by `userInterfaceIdiom`.
  Compare `== .regular` — a size class can be unspecified.
- Never use `UIScreen.main` or screen bounds. Use the view's own size
  (`GeometryReader`/`onGeometryChange` sparingly, or a custom `Layout`),
  `windowScene.effectiveGeometry` and `traitCollection.displayScale`.
- Don't replace `UIScreen.main` with `UIApplication.shared` or `UIDevice.current` globals —
  read what you need from the view or scene.
- Supported orientations are only a preference in resizable environments; iPhone
  Mirroring always runs portrait. `UIRequiresFullscreen` now means discrete resizing, not
  opting out.
- UIKit: traits are tracked automatically; `registerForTraitChanges` only for cache
  invalidation.

## System containers first

`TabView` (with the `Tab` API and `.sidebarAdaptable`), `NavigationSplitView`,
`NavigationStack`, toolbars and sheets adapt to every size, to Liquid Glass and to the
iPhone Duo hinge and cameras. Custom tab bars and hand-made split layouts are where
resizing bugs live.

## iPhone Duo (iOS 27.1 SDK)

- Prefer the system containers above — they handle vertical bars, the fold and the camera
  areas.
- Custom two-pane layouts: `ArrangementView` (SwiftUI) or `UIArrangementViewController`
  (UIKit). Don't nest `ArrangementView` inside scroll views or split views.
- Keep content away from the fold and cameras with `reservedRegions(…)` (kinds
  `.division` and `.occlusion`).
- `toolbarVerticalBehavior(.disabled)` only for UIs whose controls must stay at the bottom.
- `onHingeChange` only for effects that are really tied to the hinge angle.
- In the iPhone Duo simulator VoiceOver and the Accessibility Inspector can't read the
  content — check accessibility on another device.

## Safe areas

- `safeAreaInset(edge:)` / `safeAreaBar(edge:)` for content that sits above or below
  scrolling content — no guessed bottom padding.
- `ignoresSafeArea()` only for decoration (backgrounds), never for controls or text.

## Liquid Glass on iOS 27

- Standard components adopt it automatically; remove custom bar, sheet and popover
  backgrounds. The opt-out `UIDesignRequiresCompatibility` is ignored with the 27 SDK.
- Custom glass: `glassEffect(_:in:)` sparingly, only on key controls, grouped in a
  `GlassEffectContainer`; `.interactive()` for controls; prefer `.buttonStyle(.glass)` /
  `.glassProminent`.
- Bars that shrink on scroll: SwiftUI `toolbarMinimizationBehavior(.onScrollDown, for: …)`
  and `tabBarMinimizeBehavior(…)`. WWDC26 names the UIKit counterparts inconsistently —
  check the SDK headers before using them.
- Re-check custom scroll-edge effect overrides after adopting the 27 SDK.
- Action sheets need a source view/item so they can anchor on iPad and resizable windows.
- Concentric corners (`ConcentricRectangle`) instead of hard-coded radii.
- Use `Tab(role:)` and `.topBarPinnedTrailing` where they fit instead of custom placement.

## Typography — Dynamic Type

- Use text styles (`.body`, `.headline`, …) so Dynamic Type works; default body 17 pt,
  minimum 11 pt. Custom fonts scale with `.font(.custom(_:size:relativeTo:))` /
  `@ScaledMetric`.
- Support the accessibility sizes: allow multi-line text, switch `HStack` to `VStack` when
  `dynamicTypeSize.isAccessibilitySize`, avoid truncation.
- SF Symbols scale with the text automatically; scale meaningful custom icons too.

## Touch targets and ergonomics

- Default touch target 44×44 pt, minimum 28×28 pt.
- Primary actions within reach (middle or bottom of the screen).
- Keep system gestures working: swipe back, row swipe actions, pull to refresh.

## Color and symbols

- Semantic colors and asset-catalog Color Sets with light, dark and increased-contrast
  variants; no hard-coded appearance colors.
- SF Symbols for standard actions; deliberate rendering mode.

## Accessibility — always

- Every icon-only control has a label: `Button("Add", systemImage: "plus") { … }`;
  `.accessibilityLabel` on custom views; `.accessibilityHidden(true)` on decoration.
- Contrast ≥ 4.5:1 for text up to 17 pt, ≥ 3:1 for 18 pt or bold — light and dark.
- Respect Reduce Motion, Reduce Transparency, Increase Contrast, Bold Text, Smart Invert.
- Combine related elements into one VoiceOver element; set the reading order where the
  layout misleads it.
- Check with Xcode Previews overrides, the Device Hub inspector and on a real device with
  VoiceOver; automated audits are in the `xcode-ios-testing` skill.

## UIKit interop

- `UIHostingController` to embed SwiftUI; `UIViewRepresentable` /
  `UIViewControllerRepresentable` for UIKit inside SwiftUI (`make…` once, cheap idempotent
  `update…`, delegates through the `Coordinator`).
- `@Observable` models drive UIKit automatically: properties read in `layoutSubviews`,
  `updateProperties`, cell and button configuration and compositional-layout section
  providers are tracked.
- UIKit is main-thread only — keep it on the main actor.

## Sources

- Transitioning to the UIKit scene-based life cycle — https://developer.apple.com/documentation/uikit/transitioning-to-the-uikit-scene-based-life-cycle
- WWDC26 Modernize your UIKit app — https://developer.apple.com/videos/play/wwdc2026/278/
- WWDC26 Use SwiftUI with AppKit and UIKit — https://developer.apple.com/videos/play/wwdc2026/272/
- WWDC26 What's new in SwiftUI — https://developer.apple.com/videos/play/wwdc2026/269/
- WWDC26 Platforms State of the Union — https://developer.apple.com/videos/play/wwdc2026/102/
- ArrangementView — https://developer.apple.com/documentation/swiftui/arrangementview
- SwiftUI updates — https://developer.apple.com/documentation/updates/swiftui
- UIKit updates — https://developer.apple.com/documentation/updates/uikit
- UIDesignRequiresCompatibility — https://developer.apple.com/documentation/bundleresources/information-property-list/uidesignrequirescompatibility
- Adopting Liquid Glass — https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass
- HIG Designing for iOS — https://developer.apple.com/design/human-interface-guidelines/designing-for-ios
- HIG Typography — https://developer.apple.com/design/human-interface-guidelines/typography
- HIG Accessibility — https://developer.apple.com/design/human-interface-guidelines/accessibility
- twostraws/SwiftUI-Agent-Skill, resizability reference (MIT, idea source) — https://github.com/twostraws/SwiftUI-Agent-Skill
