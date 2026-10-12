# Applications — one core, several frontends

Rust applications whose logic is shared by **several frontends**: a desktop UI (egui/eframe,
Iced, Slint, Dioxus, Tauri), a browser build (WebAssembly), a CLI and automation clients
(`agent-interfaces.md`). The core is UI-independent, synchronous and reachable through one
typed entry point: `App::execute(Command)`.

## When this architecture applies

| Project | Architecture |
|---|---|
| Web backend / API, CLI tool, worker service | feature slices + ports (`architecture.md`) — the default |
| Application with ≥ 2 frontends sharing a domain (desktop + browser + CLI + agents) | layered command core (this file) |
| Library crate | `library.md` |
| Single-binary tool without a domain core, embedded/`no_std` | not this file (`cli.md`, `unsafe-ffi-wasm.md`) |

The two architectures fit together: **features still organize the modules inside L0 and
L1** (`domain/src/items.rs`, `application/src/items.rs`), exactly like the feature slices
of `architecture.md`. What this file adds is the crate layering, the single command entry
point and the rules that keep frontends thin. A server that should offer the same
operations as the desktop app becomes one more host (L4) of the same core.

## Layers

```text
L4 apps/*            composition roots: wire adapters into App, start a frontend — nothing else
L3 ui-*              frontends; depend on the core only
L2 adapters          storage-*, platform; depend on the core only (siblings of the UI)
L1 application       App::execute(Command) -> Result<Output, AppError>, events, ports, jobs
L0 domain            entities, value objects, rules — pure Rust, no I/O
```

| Layer | Contains | Depends on | Must not contain |
|---|---|---|---|
| L0 domain | entities, value objects (validated newtypes), domain errors, pure functions | std, serde, thiserror, uuid, schemars | I/O, clocks, randomness sources other than id generation, async |
| L1 application | `App` service, `Command`/`Output`, `AppError`, `AppEvent`, ports (traits), job model, in-memory test doubles | L0 | UI, drivers, async runtimes, `web-sys`, threads, `cfg(target_arch)` |
| L2 adapters | repository implementations, job runners, platform services (paths, clipboard, notifications) | L0–L1 + their driver | UI crates, other adapters |
| L3 frontends | UI crates (`ui-egui`, `ui-iced`, …) | L0–L1 + the UI framework | storage, platform, threads |
| L4 hosts | `main` functions: choose adapters, build `App`, start the frontend | everything | logic |

```text
crates/
├── domain/            L0
├── application/       L1
├── storage-sqlite/    L2  native
├── storage-browser/   L2  wasm32
├── platform/          L2
└── ui-egui/           L3
apps/
├── desktop/           L4  native host
├── web/               L4  browser host (trunk)
└── cli/               L4  CLI + JSON exec interface
xtask/                     automation, outside the layer model
```

- **Adapters and frontends are siblings.** The UI never imports SQLite, a storage adapter
  never imports the UI. Only the host knows both.
- **No framework dependencies in the core**: no UI framework, async runtime, database
  driver or web API (`web-sys`, `js-sys`) in L0/L1.
- **Enforce the layering with a `cargo metadata` check** (an `xtask layers` command, see
  `tooling.md`): every workspace crate is registered with its layer; a crate may depend
  only on workspace crates of allowed lower layers; framework and driver crates (egui,
  eframe, winit, wgpu, iced, slint, dioxus, tauri, rusqlite, web-sys, tokio, …) are banned
  below the layer that may use them; an unregistered crate fails the check. It runs in CI.
- Shared crates (L0, L1, UIs that also run in the browser) **compile for desktop and
  `wasm32-unknown-unknown`** — checked in CI (`unsafe-ffi-wasm.md`).

## The App service

```rust
pub struct App {
    repo: Box<dyn ItemRepository>,
    jobs: Box<dyn JobRunner>,
    clock: Box<dyn Clock>,
    events: Vec<AppEvent>,
}

impl App {
    /// The only entry point for every frontend, automation client and test.
    pub fn execute(&mut self, command: Command) -> Result<Output, AppError> { /* … */ }
    /// Collects job updates and applies their results (call every frame / on a timer).
    pub fn poll(&mut self) { /* … */ }
    /// What changed since the last call; frontends refresh from this.
    pub fn drain_events(&mut self) -> Vec<AppEvent> { std::mem::take(&mut self.events) }
}
```

- **Single owner, synchronous.** Exactly one thread owns `App`. No `Arc<Mutex<App>>` in
  frontends that run on one thread; multi-threaded hosts (servers, Tauri) wrap it **once,
  at the host** (`async.md` for tokio hosts).
- **Dependency injection by constructor with trait objects.** The implementation is
  chosen per target and at runtime (SQLite on desktop, IndexedDB snapshot in the browser,
  in-memory in tests), which is the `dyn` case of the ports rule in `architecture.md`.
  Generic parameters only where a measured hot path needs monomorphization.
- **Ports only with real implementations**: a trait exists because there are at least two
  implementations you actually use (SQLite + browser + in-memory). No speculative
  interfaces.
- **One path to the logic.** GUI, CLI, agents and tests all go through `App::execute`.
  Never add a second path (a "fast path" for the CLI, an agent-only shortcut).

## Commands

```rust
/// Every operation of the application. Doc comments become the JSON Schema descriptions.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "command", content = "params", rename_all = "snake_case")]
pub enum Command {
    /// Create an item with the given name.
    CreateItem { name: ItemName },
    /// List all items, oldest first.
    ListItems,
    /// Delete an item permanently.
    DeleteItem { id: ItemId },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Effect { Read, Write, Destructive }

pub struct CommandInfo {
    pub name: &'static str,
    pub label: &'static str,
    pub effect: Effect,
    pub description: &'static str,
}

pub const COMMANDS: &[CommandInfo] = &[ /* one entry per variant */ ];
```

- **One serializable enum, adjacently tagged**:
  `{"command": "create_item", "params": {"name": "Milk"}}`; unit variants need no
  `params` (`{"command": "list_items"}`).
- **Doc comment on every variant** — `schemars` turns it into the schema description that
  CLI help, MCP tools and docs reuse.
- **Static metadata table** (`COMMANDS`: name, label, effect, description) plus a **drift
  test** that compares it with the variant names in the enum's JSON Schema in both
  directions, so a new variant without metadata (or stale metadata) fails CI.
- **`Effect::{Read, Write, Destructive}` per command.** A command missing from the table
  is treated as **destructive**.
- `execute` validates through the domain constructors (`ItemName::parse`; deserialization
  uses the same path via `#[serde(try_from = "String")]`, `security.md`), calls ports,
  pushes events and returns a typed `Output`.
- **Reads are commands too** (`ListItems`, `GetItem`), so every frontend and agent has one
  interface.

Adding a command: variant (with doc comment) → `COMMANDS` entry → `execute` arm (+ `Output`
variant) → command tests → frontend wiring → docs (command table).

## Events

`AppEvent` values (`ItemCreated`, `JobChanged`, …) are queued by `App` and pulled by
frontends with `drain_events()`. They are also the hook for:

- **audit logs** (who ran what, when),
- **undo/redo** (record the inverse command for each change),
- **macros** (record and replay a `Vec<Command>`),
- automation (MCP resource updates, `agent-interfaces.md`).

Keep events small (ids, not whole objects) unless a consumer needs the data.

## Errors

- **Domain**: `DomainError` — the caller's fault (invalid name, rule violated).
- **Ports**: `StorageError` — `Duplicate`, `Missing`, `Corrupt`, `Backend`, `NewerSchema`
  (`database.md`).
- **Application**: `AppError { Validation, NotFound, Storage, … }` with
  `fn code(&self) -> &'static str` (stable, snake_case) and `fn is_user_error(&self) -> bool`.
- Frontends map **codes** to messages, dialogs and exit codes — never parse error strings.
- General error rules (thiserror, chaining, no stringly-typed errors across crate
  boundaries): `errors.md`.

## Background jobs

### Pick the right tool

| Need | Use | Not |
|---|---|---|
| Show progress, cancel, keep the UI responsive for long work | background job (`JobTask` + `JobRunner`) | a thread spawned in UI code |
| Speed up one CPU-heavy computation | `rayon` inside a job step (native) | tokio |
| Many concurrent network calls / a server | tokio in the host or a network adapter (`async.md`) | a blocking thread per request |
| Work on other machines/processes | queue + worker binary (`QueueJobRunner`) | in-process threads |
| Periodic work in a GUI | timer → command | busy loops |

### Job model

- `JobRequest` (serde) → `App` builds a `JobTask` with **all inputs copied in** →
  `JobRunner::submit`.
- `JobTask::step()` does a bounded slice of work (**≤ ~10 ms**) and returns
  `Progress { done, total }` or `Finished(result)`.
- A `CancelToken` (`Arc<AtomicBool>`) is checked before each step; runners also check it
  while sleeping.
- Runners per target: thread pool (native), inline-per-frame (browser and tests, ≤ ~8 ms
  per frame), queue (distributed, later). They implement the same `JobRunner` port.
- **Results that change data are applied in `App::poll()` on the owner thread** — tasks
  never write to repositories.
- Shutdown: cancel + join on drop; workers finish their current step only.
- A native runner wakes the UI through a notifier closure passed in by the host (egui:
  a cloned `Context::request_repaint`).

### Distributed jobs (Celery-like) — checklist

- persistent job table,
- idempotency key per request,
- retries with backoff and a maximum number of attempts,
- visibility timeout / heartbeat,
- dead-letter queue,
- progress reporting channel,
- graceful shutdown (stop taking work, finish the current step, requeue the rest),
- the same `JobTask` code in the worker binary.

## UI development

### Principles

- A UI crate depends on the application core and its framework only.
- It holds **view state** (selected tab, form drafts, confirmation flags) and **caches of
  outputs** (the lists it renders). Domain state lives in `App`.
- **No business logic in UI code**: user actions become `Command`s, outputs are rendered.
  Validation rules belong to the domain; the UI only displays errors.
- In immediate-mode UIs, **queue commands while drawing** (`self.pending.push(cmd)`) and
  execute them after layout — avoids borrow conflicts and double execution.
- Refresh caches when `drain_events()` returns something (or after own commands).
- Keep frames coming while jobs run (`ctx.request_repaint_after(16 ms)`), otherwise stop
  repainting.
- Errors from `execute` go to a visible status area **with the error code**; never panic
  in UI code.
- **Destructive commands need an explicit confirmation step** (`security.md`).
- Never block the UI thread for more than a few milliseconds — use a job.

### egui / eframe 0.36

- `eframe::App` splits into `logic(&mut self, ctx, frame)` (no drawing: poll jobs, process
  events) and `ui(&mut self, ui, frame)` (draw).
- Panels: `egui::Panel::{top, bottom, left, right}(id).show(ui, …)`,
  `egui::CentralPanel::default().show(ui, …)`.
- The UI crate depends on **`egui`, not `eframe`**; hosts pick native (`wgpu`) or web
  (`glow`/`wgpu`) rendering.
- Accessibility labels: `ui.add(TextEdit::singleline(…)).labelled_by(label.id)` — also
  makes `egui_kittest` queries by label work.
- Theme switching: `egui::widgets::global_theme_preference_switch(ui)`.
- Background threads wake the UI with a cloned `egui::Context` (`request_repaint()`),
  passed to the job runner as notifier.
- Tests: `egui_kittest::Harness::new_ui_state(|ui, state| …, state)`, `harness.run()`,
  `get_by_label(…).click()`, `.focus()` then `.type_text(…)` (`testing.md`).
- egui 0.36 needs Rust ≥ 1.95 — UI frameworks raise their MSRV quickly; bump the
  toolchain deliberately (`tooling.md`).

### Adding another framework

1. New crate `ui-<framework>` at L3 — never a shared "widget abstraction" across
   frameworks.
2. Map: user action → `Command`; `Output` → view model; `AppEvent` → refresh or
   notification; a timer or subscription calls `App::poll()` while jobs run.
3. Host in `apps/<name>` wires the same adapters as the existing desktop host; register
   both crates in the layer check.

| Framework | Where `App` lives | Notes |
|---|---|---|
| Iced | application state | commands from `update(message)`; `Subscription::run`/timer for polling |
| Slint | Rust side behind `Rc<RefCell<App>>` | callbacks execute commands; models from outputs |
| Dioxus | context provider (`Rc<RefCell<App>>`) | signals updated from events; desktop + web |
| Tauri | Rust state behind `Mutex<App>` | `#[tauri::command] fn execute(cmd: Command)`; JSON from the web frontend; `emit` events |

### Don'ts

- Calling repositories, `std::fs` or `std::thread` from UI code.
- Formatting rules that are really business rules.
- Blocking the UI thread — use a job.

## Anti-patterns

- UI calling a repository, opening a file, spawning a thread.
- A "service" per frontend (`CliItemService`, `GuiItemService`).
- `cfg(target_arch = "wasm32")` in domain/application — it belongs in adapters and hosts.
- Generic `Repository<T>` traits before there is a second entity.
- God-crates (`common`, `utils`) — put code where it is used.
- Agent-only shortcuts into the core (`agent-interfaces.md`).

## Projects based on rust-app-starter

The **rust-app-starter** template implements every rule in this file. Crates carry the
prefix `starter-*` (rename it once for a new project); automation runs through
`cargo xtask ci` (format, clippy native + wasm32, tests, layers, wasm, cargo-deny),
`cargo xtask layers` and `cargo xtask wasm`. The layer table is `LAYERS` in
`xtask/src/layers.rs`; the browser-shared crate list is `WASM_CRATES` in
`xtask/src/main.rs`.

- **New command:** variant in `Command` → entry in `COMMANDS` → arm in `App::execute` →
  test in `app.rs` → frontend wiring. `exec` in the CLI works immediately.
- **New entity field:** domain + migration file + adapter mapping + contract test +
  snapshot version handling in the browser adapter.
- **New job:** `JobRequest` variant → `JobTask` impl with short steps → build it in
  `App::start_job` → apply data-changing results in `App::poll`.
- **New frontend:** `crates/ui-<fw>` at L3 + host in `apps/<name>`; register both in
  `LAYERS`.
- **New crate:** register in `LAYERS`, add to `WASM_CRATES` if shared with the browser,
  inherit the workspace package fields and lints, add the never-crash `#![deny]` block at
  the crate root (the template uses the crate-root variant, `tooling.md`).
