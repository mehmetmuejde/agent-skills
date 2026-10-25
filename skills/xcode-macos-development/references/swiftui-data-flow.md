# SwiftUI data flow, navigation and persistence

How state, models and navigation fit together in a SwiftUI app. State: SwiftUI with the
27 SDKs (iOS 27 / macOS 27).

## Models

- Models are `@Observable` classes. No `ObservableObject`, `@Published`, `@StateObject`,
  `@ObservedObject` or `@EnvironmentObject` in new code. Old and new can coexist — migrate
  a model when you touch it.
- `@Observable` classes are `@MainActor` (explicitly, or through the module's MainActor
  default isolation). `@Observable` is not supported on actors.
- Business logic lives in models and services, not in view bodies — that is what makes it
  testable.
- Storage the UI never reads gets `@ObservationIgnored`.
- Cache derived values (sorted, filtered, formatted) as stored properties on the model,
  updated when the source changes — not recomputed in `body`.

## Ownership

| Situation | Use |
|---|---|
| View creates and owns the model | `@State private var model = Model()` |
| Child only reads | plain `let model: Model` |
| Child needs bindings into the model | `@Bindable var model: Model` |
| Many views in a subtree need it | `.environment(model)` + `@Environment(Model.self) private var model` |
| Local view state | `@State private var …` — always `private` |
| Custom environment value | `@Entry var …` in an `EnvironmentValues` extension |

- Pass views only the data they read. Value-type inputs are compared field by field; a
  large struct passed whole makes the view update for unrelated changes.
- Bindings come from key paths (`$model.title`), not `Binding(get:set:)` built in `body`.
- `@Entry` defaults must not be closures or new class instances — they are re-created on
  every access and invalidate dependants.

## `@State` is a macro since Xcode 27

`@State` is now a macro with lazy, once-only initialisation of class values (it
back-deploys to iOS 17 / macOS 14). Code that compiled before can break:

- assigning `@State` in `init` before all other stored properties are initialised,
- a default value plus an assignment in `init`,
- property wrappers composed on top of `@State`.

Follow Apple's TN3211 for each case. Apple explicitly warns that merely reordering the
assignments is not the right fix. Result builders are unified under `@ContentBuilder`; new
ambiguity errors in `overlay`/`background` overloads are covered by the same note.

## Views

- Small views with one job; extract a subview when a part has its own inputs.
- `body` is cheap: no formatter creation, sorting, filtering or I/O.
- Stable identity: `ForEach` over `Identifiable` data; never `id: \.self` on values that
  can repeat. No `AnyView` for row types.
- `.task { }` for async loading tied to a view's lifetime (cancelled automatically);
  `.task(id:)` to restart when an input changes.
- `onChange(of:)` with the two-parameter (or zero-parameter) closure; the one-parameter
  form is deprecated.
- Modern modifiers: `foregroundStyle` (not `foregroundColor`), `clipShape(.rect(cornerRadius:))`
  (not `cornerRadius`), `Tab` (not `tabItem`).
- Previews: `#Preview`; `PreviewProvider` is deprecated in Xcode 27. `#Preview` bodies run
  on the main actor; `#Preview(arguments:)` renders variant grids.

## Navigation

- `NavigationStack` with `navigationDestination(for:)` and value-based `NavigationLink`;
  `NavigationSplitView` for sidebar layouts. `NavigationView` and destination-only
  `NavigationLink` are soft-deprecated.
- Keep the navigation path in a model when deep links or state restoration need it.
- Tabs: `TabView` with the `Tab` API and `.tabViewStyle(.sidebarAdaptable)`. Don't build
  custom tab bars — system bars adapt to Liquid Glass, overflow and new form factors.

## Prefer new system components over custom code (27 SDKs)

Before writing a custom solution, check these (verify availability against the
deployment target with `#available`):

- reordering: `reorderable()` / `reorderContainer(for:)`
- swipe actions outside `List`: `swipeActionsContainer()`
- item-driven alerts and dialogs: `alert(_:item:)`, `confirmationDialog(_:item:)`
- image loading with HTTP caching: `AsyncImage` + `asyncImageURLSession`
- toolbars: `ToolbarSpacer`, `ToolbarOverflowMenu`, `visibilityPriority`
- documents: `ReadableDocument` / `WritableDocument` with `DocumentReader` /
  `DocumentWriter` (URL access, partial writes, writing off the main actor);
  `FileDocument` / `ReferenceFileDocument` still work.

## Lifecycle

- SwiftUI `App` with `Scene`s. React to `@Environment(\.scenePhase)` to save and refresh.
- Work that must survive a view belongs in a model owned by the `App` or scene, not in a
  view's `@State`.

## Persistence

Decide once per project (record it in an ADR) and don't add a second persistence layer.

**SwiftData**
- `@Query` in views (27 SDK: `sectionBy:` for sections); `ResultsObserver` outside views;
  `HistoryObserver` for changes made by sync or extensions. Keep observation tokens alive.
- Background work through a `@ModelActor`; pass `PersistentIdentifier`s across actors,
  never model objects.
- `@Attribute(.codable)` only for types you don't own — such values are opaque to
  predicates and sorting and don't migrate when their shape changes.
- CloudKit sync: no `@Attribute(.unique)`, every relationship optional, every property
  optional or with a default.
- Version schemas (`VersionedSchema` + `SchemaMigrationPlan`) before the first release
  that changes a model.

**Core Data** stays valid for existing stores and advanced needs.

**Files / `Codable`** for small settings and documents; `UserDefaults` only for
preferences — never for secrets or large data.

## Sources

- Migrating from ObservableObject to @Observable — https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro
- TN3211 State and ContentBuilder source incompatibilities — https://developer.apple.com/documentation/technotes/tn3211-resolving-swiftui-source-incompatibilities-for-state-and-contentbuilder
- `Entry()` macro — https://developer.apple.com/documentation/swiftui/entry()
- NavigationStack — https://developer.apple.com/documentation/swiftui/navigationstack
- ScenePhase — https://developer.apple.com/documentation/swiftui/scenephase
- SwiftUI updates — https://developer.apple.com/documentation/updates/swiftui
- WWDC26 What's new in SwiftUI — https://developer.apple.com/videos/play/wwdc2026/269/
- WWDC26 What's new in SwiftData — https://developer.apple.com/videos/play/wwdc2026/274/
- ModelActor — https://developer.apple.com/documentation/swiftdata/modelactor
- Syncing SwiftData across devices — https://developer.apple.com/documentation/swiftdata/syncing-model-data-across-a-persons-devices
