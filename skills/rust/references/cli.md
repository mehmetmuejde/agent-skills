# Command-line tools

## Dependencies

```toml
[dependencies]
clap = { version = "4", features = ["derive", "env"] }
anyhow = "1"
serde = { version = "1", features = ["derive"] }
toml = "1"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

[dev-dependencies]
assert_cmd = "2"
predicates = "3"
```

Add tokio only if the tool really does concurrent I/O; a synchronous CLI is simpler.

## clap 4 — derive

```rust
// cli.rs — argument types only, no logic
use std::path::PathBuf;

use clap::{Args, Parser, Subcommand, ValueEnum};

/// Resize and convert images.
#[derive(Debug, Parser)]
#[command(version, about)]
pub struct Cli {
    /// Increase log output (-v, -vv)
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    pub verbose: u8,

    /// Config file (default: the user config directory)
    #[arg(long, env = "IMGTOOL_CONFIG", global = true)]
    pub config: Option<PathBuf>,

    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Resize images to a maximum width
    Resize(ResizeArgs),
    /// Convert images to another format
    Convert(ConvertArgs),
}

#[derive(Debug, Args)]
pub struct ResizeArgs {
    /// Input files
    #[arg(required = true)]
    pub inputs: Vec<PathBuf>,

    /// Maximum width in pixels
    #[arg(long, value_parser = clap::value_parser!(u32).range(1..=20_000))]
    pub width: u32,

    /// Output format
    #[arg(long, value_enum, default_value_t = Format::Png)]
    pub format: Format,

    /// Show what would happen without writing files
    #[arg(long)]
    pub dry_run: bool,
}

#[derive(Debug, Args)]
pub struct ConvertArgs {
    /// Input files
    #[arg(required = true)]
    pub inputs: Vec<PathBuf>,
}

#[derive(Debug, Clone, Copy, ValueEnum)]
pub enum Format {
    Png,
    Jpeg,
    Webp,
}
```

- Doc comments become help texts — every argument has one.
- Validate in clap where possible (`value_parser!(u32).range(…)`, `ValueEnum`), so bad
  input fails with a usage error before any work starts.
- `#[command(version)]` reads the version from `Cargo.toml`.
- Subcommands as an enum; each variant's args struct maps to one command handler.
- `bool` flags are fine **at the CLI surface**; inside the program convert them into enums
  or options structs.
- Test the definition once: `Cli::command().debug_assert()` in a unit test.

## main — thin, maps errors to exit codes

```rust
use std::process::ExitCode;

use clap::Parser;

fn main() -> ExitCode {
    let cli = imgtool::cli::Cli::parse();     // exits with code 2 on usage errors
    imgtool::telemetry::init(cli.verbose);
    match imgtool::run(cli) {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            eprintln!("error: {err:#}");
            imgtool::exit_code(&err)
        }
    }
}
```

- `run` lives in the library (testable) and returns `anyhow::Result<()>`; command handlers
  add `.context(…)` that names the file/URL/step in user terms.
- Print the error chain **once**, on stderr, with `{err:#}` (one line:
  `error: reading input photo.jpg: No such file or directory (os error 2)`).
- Exit codes: `0` success, `1` general failure, `2` usage error (clap does this). Add
  specific codes only when scripts need to branch on them (e.g. from `sysexits`: `65`
  bad input data, `74` I/O error) and document them in `--help`. Map them in one function
  that downcasts to your typed errors.
- No `std::process::exit` deep in the code — it skips destructors (flushing, temp file
  cleanup). Return to `main`.
- Ctrl-C: default behavior (terminate) is fine for short tools; long-running tools install
  a handler and stop cleanly (`ctrlc` crate or tokio `signal`).

## stdout vs stderr

| Stream | Content |
|---|---|
| **stdout** | the result: data, reports, JSON — what a pipe consumes |
| **stderr** | logs, progress, warnings, errors, prompts |

- Machine-readable output behind `--format json` (serde); stable field names, no log lines
  mixed in.
- CLIs of multi-frontend applications expose the whole command core as a JSON interface
  (`commands --schema`, `exec '<json>'`, `{"ok", "result" | "error"}` envelope, stable
  exit codes, destructive guard) — see `agent-interfaces.md`.
- Lock and buffer stdout for large outputs (`let mut out = std::io::stdout().lock();`
  + `writeln!(out, …)?`), and handle `BrokenPipe` (e.g. `| head`) as a normal end, not a
  crash.
- Colors only when the stream is a terminal and `NO_COLOR` is unset (`anstream` handles
  this; clap already does for help text).
- Progress bars (`indicatif`) on stderr, hidden when not a TTY.
- Logging via `tracing-subscriber` writing to **stderr**; `-v`/`-vv` raise the level,
  `RUST_LOG` overrides.

## Configuration layering

Precedence, lowest to highest: **built-in defaults → config file → environment →
command-line flags**.

- Flags and env vars: clap's `env` feature (`#[arg(long, env = "IMGTOOL_WIDTH")]`) covers
  both layers with one declaration and shows the variable in `--help`.
- Config file: TOML deserialized with serde into a struct whose fields are all optional
  (`#[serde(default, deny_unknown_fields)]`); merge explicitly: `cli.width.or(file.width)
  .unwrap_or(DEFAULT_WIDTH)`.
- Default location from the platform's config dir (`etcetera` or `directories`); an
  explicit `--config` path that doesn't exist is an error, a missing default file is not.
- For many settings or several sources, `figment` or `config` instead of manual merging —
  one per project.
- Secrets never as flags (visible in `ps` and shell history): environment, a file path, or
  a prompt (`rpassword`). Keep them in `SecretString`.

## Files and safety

- Writing output: write to a temp file in the target directory, then rename
  (`tempfile::NamedTempFile::persist`) — no half-written files on failure.
- Don't overwrite existing files without `--force`.
- Paths from arguments are used as given; don't resolve `~` yourself.

## Tests

- Library functions: unit tests.
- Whole binary: `assert_cmd` (`assert_cmd::cargo::cargo_bin_cmd!("imgtool")`) with `predicates` for
  stdout/stderr/exit code, or `trycmd` for many CLI cases as snapshot files.
- `insta` for larger outputs (`--help`, JSON reports).
- See `testing.md`.

## Distribution

- `cargo install --locked` for Rust users; release binaries per target from CI
  (`cargo-dist` if the project wants installers).
- Static binaries for Linux: `x86_64-unknown-linux-musl`, rustls instead of OpenSSL.
