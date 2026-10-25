# Test plans, coverage and CI (macOS)

## Test plans

- Use test plans (`.xctestplan`), several per scheme, one of them the default:
  - **PR** — unit tests plus a few smoke UI tests; fast, runs on every change.
  - **Full** — everything incl. all UI tests and localization configurations; nightly.
  - **Accessibility** / **Localization** — audits and language configurations.
  - **Performance** — Release build, no coverage, no sanitizers (see the
    `xcode-macos-performance` skill).
- Select tests by **tags** (include/exclude, any/all) rather than by name lists.
- **Configurations** are runtime variations of one plan: language and region,
  environment variables, launch arguments, sanitizers, screenshot/video capture,
  repetition, timeouts. The plan runs once per configuration.
- Set the Swift Testing **interoperability mode** in the plan to *complete* (or *strict*
  while finishing a migration). *limited* turns XCTest failures inside Swift Testing tests
  into warnings — tests pass that shouldn't.
- UI tests: set **target-app crash severity** (Xcode 27: off / warning / failure /
  fatal) — keep *failure*, so a crash of the app under test fails the run.
- Launch tests with `override class var runsForEachTargetApplicationUIConfiguration: Bool
  { true }` run once per appearance × localization combination of the plan.

## Coverage

- Enable code coverage per configuration and pick the targets that count (app modules,
  not test helpers).
- Coverage includes tests inside `withKnownIssue`, excludes skipped ones.
- Coverage slows the code down — keep it off in performance plans.
- Coverage is a floor, not a goal. A line run without an assertion proves nothing; set a
  threshold per project and check that new code is covered.

## Flaky tests

- A flaky test is a bug in the test or in the app. Reproduce first:
  `-run-tests-until-failure -test-iterations 50` on the single test.
- Typical causes: shared state between parallel tests, main-actor assumptions from
  XCTest, fixed sleeps, wall clock, locale/time zone of the machine, reset in teardown
  instead of setup, real network, leftover files, window restoration.
- **Retry on failure** only for tests against genuinely unreliable external systems, with
  a low maximum (≤ 3). Never as a blanket CI setting — it hides real bugs and slows CI.
- Never disable, skip or delete a failing test to get green. Mark it with
  `withKnownIssue` plus a ticket, or fix it.
- Set an **execution time allowance** (`-test-timeouts-enabled YES`) so hanging tests end
  with a spindump instead of blocking CI.

## Commands

All flags checked with `xcodebuild -help`, `xcresulttool --help`, `xccov help` and
`swift test --help` on Xcode 27.1. Replace `App`, `AppTests`, `AppUITests`.

```sh
# Discover schemes, destinations, test plans and exact test identifiers
xcodebuild -list -project App.xcodeproj
xcodebuild -scheme App -showdestinations
xcodebuild -scheme App -showTestPlans
xcodebuild test -scheme App -destination 'platform=macOS' \
  -enumerate-tests -test-enumeration-format json -test-enumeration-output-path -

# Default plan with result bundle and coverage
xcodebuild test -scheme App -destination 'platform=macOS' \
  -resultBundlePath build/macos.xcresult -enableCodeCoverage YES
# universal apps: -destination 'platform=macOS,arch=arm64'

# Narrow first: target, suite, single test; skip UI tests
xcodebuild test -scheme App -destination 'platform=macOS' -only-testing:AppTests
xcodebuild test -scheme App -destination 'platform=macOS' -only-testing:AppTests/CartTests
xcodebuild test -scheme App -destination 'platform=macOS' -skip-testing:AppUITests

# Test plans and configurations
xcodebuild test -scheme App -destination 'platform=macOS' -testPlan Full
xcodebuild test -scheme App -destination 'platform=macOS' -testPlan Full \
  -only-test-configuration German
xcodebuild test -scheme App -destination 'platform=macOS' -testLanguage de -testRegion DE

# Flakiness
xcodebuild test -scheme App -destination 'platform=macOS' \
  -only-testing:AppTests/CartTests -run-tests-until-failure -test-iterations 50
xcodebuild test -scheme App -destination 'platform=macOS' -retry-tests-on-failure -test-iterations 3
#   -test-repetition-relaunch-enabled YES relaunches the runner per repetition

# Parallelism, timeouts, diagnostics
xcodebuild test -scheme App -destination 'platform=macOS' -parallel-testing-enabled NO
xcodebuild test -scheme App -destination 'platform=macOS' -test-timeouts-enabled YES \
  -default-test-execution-time-allowance 120 -maximum-test-execution-time-allowance 600
xcodebuild test -scheme App -destination 'platform=macOS' -collect-test-diagnostics on-failure

# CI split: build once, test several times
xcodebuild build-for-testing -scheme App -destination 'platform=macOS' -derivedDataPath build/dd
xcodebuild test-without-building -scheme App -destination 'platform=macOS' \
  -derivedDataPath build/dd -resultBundlePath build/run1.xcresult

# Result bundles (JSON output)
xcrun xcresulttool get test-results summary --path build/macos.xcresult
xcrun xcresulttool get test-results tests --path build/macos.xcresult
xcrun xcresulttool get test-results test-details --path build/macos.xcresult --test-id '<id>'
xcrun xcresulttool get test-results insights --path build/macos.xcresult
xcrun xcresulttool export attachments --path build/macos.xcresult --output-path build/att --only-failures
xcrun xcresulttool merge --output-path merged.xcresult run1.xcresult run2.xcresult
xcrun xcresulttool compare new.xcresult --baseline-path old.xcresult --test-failures
#   `get object`, `graph` and `formatDescription` are deprecated

# Coverage report
xcrun xccov view --report --only-targets build/macos.xcresult
xcrun xccov view --report --json build/macos.xcresult

# Swift packages
swift test
swift test --filter CartTests
swift test --maximum-repetitions 50 --repeat-until fail
SWIFT_TESTING_XCTEST_INTEROP_MODE=strict swift test
```

- The exact identifier syntax of Swift Testing tests for `-only-testing` (with or without
  `()`) is not documented consistently — copy identifiers from `-enumerate-tests`.
- Parallel testing: console output from several test processes can arrive late (Xcode 27
  known issue). Read the result bundle, not the console.

## CI

- One script (`scripts/test.sh` or a Makefile target) runs the same commands locally and
  in CI; CI only calls it.
- Pin the Xcode version: `DEVELOPER_DIR=/Applications/Xcode_27.1.app/Contents/Developer`
  or `xcode-select` on the runner.
- GitHub Actions: the `xcode-27` macOS runner image ships Xcode 27.0 as default plus 27.1
  and a 27.2 beta — select the version explicitly.
- UI tests on CI Macs need Automation Mode without authentication (administrator setup,
  see `ui-testing.md`).
- Upload the `.xcresult` as a CI artifact; summarise with `xcresulttool get test-results
  summary` in the job log.
- **Xcode Cloud**: environment variables reach the test runner only with the
  `TEST_RUNNER_` prefix (stripped at runtime); a variable set both in the test plan and in
  Xcode Cloud takes the Xcode Cloud value. Split a PR workflow (PR plan) from a
  scheduled workflow (Full plan).
- Xcode 27.2 adds a `GetCodeCoverage` tool to Xcode's MCP server (`xcrun mcp-server`);
  agents can read coverage without parsing result bundles.

## Sources

- https://developer.apple.com/documentation/xcode/organizing-tests-to-improve-feedback
- https://developer.apple.com/documentation/xcode/running-tests-and-interpreting-results
- https://developer.apple.com/documentation/xcode/determining-how-much-code-your-tests-cover
- https://developer.apple.com/documentation/xcode/environment-variable-reference
- https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes
- https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes
- https://developer.apple.com/videos/play/wwdc2022/110361/ — Author fast and reliable tests for Xcode Cloud
- https://developer.apple.com/videos/play/wwdc2020/10221/ — Get your test results faster
- https://github.com/actions/runner-images/blob/main/images/macos/xcode-27-arm64-Readme.md
- Local tool help on Xcode 27.1: `xcodebuild -help`, `man xcodebuild`, `xcrun xcresulttool help`, `xcrun xccov help`, `swift test --help`
