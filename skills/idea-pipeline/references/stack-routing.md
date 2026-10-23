# Stack and tool routing

Pick **one default stack** per idea and say why. Deviate only for a reason that comes
from the intake (platform, existing assets, client stack, the riskiest question).
Prefer stacks the user already works with — check the installed skills and recent
projects before recommending something new.

## 1. Check the environment first

Facts, not questions — look them up during the intake:

- **Skills** — the available skill list in the session. A matching skill sets the
  conventions; a missing one is a gap to record.
- **MCP servers** — tool names in the session (`mcp__<server>__*`, including deferred
  tools). Some servers are configured per project only; if a needed server is missing
  here, check whether it exists for another project and offer to add it (needs approval).
- **CLIs** — `command -v <tool>` for the stack's tools (e.g. `godot`, `blender`, `uv`,
  `node`, `cargo`, `xcodebuild`, `gh`, `docker`). Note versions where they matter.
- **Accounts** — e.g. Apple developer account, GitHub login (`gh auth status`), a
  self-hosted Git server, cloud accounts. Ask only for what can't be checked.

## 2. Default stacks

| Kind of idea | Default | Skills | Tools | Choose something else when |
|---|---|---|---|---|
| Web app | FastAPI backend + React/TypeScript SPA (Vite) | `fastapi-backend`, `react-frontend`, `frontend-accessibility` | uv, node | Pure static content → static site; SSR/SEO needed → React Router framework mode |
| Native iOS / macOS app | SwiftUI, Xcode project | `figma:figma-swiftui` if there is a design | Xcode MCP / `xcodebuild`, simulator; developer account for device builds and TestFlight | Cross-platform is a hard requirement → Tauri or a web app |
| Desktop app / tray tool | Rust + Tauri (web UI) or egui (pure Rust UI) | `rust`, `react-frontend` for a Tauri UI | cargo | The UI is trivial → CLI |
| CLI / developer tool | Rust + clap; Python + uv for quick scripting | `rust` or `fastapi-backend` tooling rules | cargo / uv | — |
| Editor extension | TypeScript + esbuild (VS Code extension API) | `react-frontend` (TypeScript rules) | node, `vsce` | — |
| Game, 2D or 3D, desktop | Godot 4 (GDScript) | — (gap: no game skill yet) | `godot` CLI (headless runs for tests), Blender MCP for assets, CC0 asset packs | Browser is the target → Babylon.js; see engine choice below |
| Game or 3D scene in the browser | Babylon.js + TypeScript + Vite | `react-frontend` (TypeScript rules) | node, Blender MCP for assets (glTF export) | Simple 3D viewer without game logic → Three.js |
| 3D model, asset or scene | Blender, driven via Blender MCP | — | Blender MCP, `blender` CLI for batch export | — |
| Agent / LLM / MCP server | Python + uv (or TypeScript) with the provider's SDK | the LLM provider's SDK skill if installed, `appsec-review` (LLM and MCP sections) | uv / node | — |
| Data or ML experiment | Python + uv, notebooks, results as CSV | — | uv, Jupyter, local model runtime if needed | — |
| Containerised deployment (Stage 2) | Docker + Helm/GitOps as the user already runs it | `docker-kubernetes` | docker, helm | — |

The table is a starting point and grows with use: when a pipeline run picks a stack that
isn't listed, or a default turns out wrong, propose an update to this table.

## 3. Game engine choice

| Engine | Pick it when | Watch out for |
|---|---|---|
| **Godot 4** (default) | 2D or 3D indie scope, fast iteration, open source, scriptable and testable from the CLI | Fewer ready-made assets; C# needs the .NET build |
| **Babylon.js** | The game must run in the browser without install, or embed in a web app | Performance budget of the browser; asset sizes |
| **Unity** | Mobile or console reach, large asset store, team already knows C#/Unity | Licence and runtime terms; editor-centric, hard to drive from the CLI |
| **Unreal Engine** | High-end 3D graphics is the core of the idea | Heavy toolchain, C++/Blueprints, royalty terms; slow for POCs |

For a POC, the engine must be drivable by the agent: headless runs, scriptable scene
setup, readable text formats. Prefer Godot or Babylon.js unless the riskiest question
is specifically about what Unity or Unreal offer.

## 4. Assets

- Placeholder first: primitives and CC0 packs (e.g. Kenney, Quaternius, Poly Haven).
  Record sources and licences in an `assets/CREDITS.md`.
- Custom models via Blender MCP only when the asset itself is part of the riskiest
  question (look, style, animation). Export glTF for web and engines.
- Generated or synthesized sounds and textures: record the generator and settings.

## 5. Record the result

Write the chosen stack, the skills, the tools and anything **missing** into the brief's
Stack section. Then load the stack skills before writing code.
