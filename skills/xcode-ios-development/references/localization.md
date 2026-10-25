# Localization

Every user-facing string is localizable from the first commit — adding it later means
touching every view again.

## String Catalogs

- One `Localizable.xcstrings` per target or package module. Xcode extracts strings when
  it builds (`SWIFT_EMIT_LOC_STRINGS = YES`, `LOCALIZATION_PREFERS_STRING_CATALOGS = YES`
  are template defaults).
- String literals passed to `Text`, `Button`, `Label`, `Toggle`, `navigationTitle` etc. are
  localized automatically.
- Non-view code (models, errors, notifications) carries `LocalizedStringResource`, not
  `String`. Convert to `String` only at the edge with `String(localized:)`.
- In Swift packages and frameworks pass the bundle: `Text("Delete", bundle: #bundle)`,
  `String(localized: "…", bundle: #bundle)`. Without it the lookup goes to the main bundle.
- Generated symbols (`STRING_CATALOG_GENERATE_SYMBOLS = YES`) give compile-time-checked
  keys for manually managed entries.

```swift
struct ExportError: LocalizedError {
    var errorDescription: String? {
        String(localized: "The file could not be written.", bundle: #bundle,
               comment: "Shown when an export fails")
    }
}
```

## Comments for translators

- Add a `comment:` to every string whose meaning is not obvious out of context (button
  vs. title, noun vs. verb).
- Xcode 27: a "do not translate" comment marks the entry *Don't Translate*.

## Plurals

- Interpolate the number into **one** string, then use *Vary by Plural* in the catalog.
  Xcode adds the categories each language needs (for example one/few/many/other).
- Never build plurals with `if count == 1`.

```swift
Text("\(count) files selected")   // vary by plural in the catalog
```

## Grammar agreement

- Automatic agreement: `^[\(count) \(item)](inflect: true)` in a localized string.
- Disambiguate the part of speech with `^[…](morphology: { partOfSpeech: "noun" })`.
- Support is **language-specific** and Apple doesn't publish a complete list — check
  `InflectionRule.canInflect(language:)` at runtime and keep a correct fallback text.

## Formatting

- Numbers, dates, durations, measurements, byte counts and lists through `FormatStyle`:
  `value.formatted(…)`, `Text(value, format: …)`, `.formatted(.list(type: .and))`.
- No `String(format:)` for numbers, no hand-built date strings, no fixed decimal
  separators.
- Layout with `.leading` / `.trailing`, never `.left` / `.right`, so right-to-left
  languages mirror correctly.
- Don't concatenate translated fragments into a sentence — word order differs per
  language. Use one string with interpolation.

## Assets and other resources

- Localize images only when they contain text or culture-specific content; prefer
  SF Symbols, which localize and mirror automatically.
- `InfoPlist.xcstrings` for usage descriptions and the display name.

## Machine translation

Xcode 27 can generate translations (agent translation, MCP tools). They are marked as
machine translation (`state-qualifier="leveraged-mt"` in exported XLIFF). Have a native
speaker review them before shipping.

## Testing localizations

- Scheme → Run → Options → App Language: pseudolanguages (double length, right-to-left,
  accented, bounded) and *Show non-localized strings*.
- Previews: `.environment(\.locale, …)` and `.environment(\.layoutDirection, .rightToLeft)`;
  Xcode 27 previews also offer a localization override.
- Include a long-string language (German) and an RTL language (Arabic or Hebrew) in test
  plans — details in the testing skills.

## Sources

- Localizing and varying text with a string catalog — https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog
- Building a localized food-ordering app (inflection, FormatStyle) — https://developer.apple.com/documentation/foundation/building-a-localized-food-ordering-app
- InflectionRule — https://developer.apple.com/documentation/foundation/inflectionrule
- Preparing your interface for localization — https://developer.apple.com/documentation/xcode/preparing-your-interface-for-localization
- Xcode 27 release notes — https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
