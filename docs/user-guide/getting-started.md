# Getting Started

This guide gets a new Persona Training Lab user from a source checkout to a running desktop application and explains where PTL stores its data.

It intentionally does **not** require knowledge of PTL internals.

## Requirements

- Python **3.12 or newer**
- `uv`
- a desktop environment capable of running PySide6 / Qt

Local inference and training have additional optional dependencies and model requirements; the core desktop application does not require them to launch.

## 1. Install the desktop core

From the repository root:

```bash
uv sync --locked
```

`--locked` makes the environment follow the committed lock file instead of silently resolving a different dependency set.

### Optional: inference dependencies

```bash
uv sync --locked --extra inference
```

### Optional: training dependencies

```bash
uv sync --locked --extra training
```

The `training` extra is intended for workflows that need the training stack in addition to the desktop UI.

## 2. Launch PTL

Run:

```bash
uv run --locked python -m persona_training_lab.bootstrap.app
```

The current source distribution uses the Python module entry point. Installer/package launchers are finalized during the v1.0 packaging phase.

## 3. Understand the workspace

PTL creates a persistent workspace outside the source tree. The location does **not** depend on the directory from which you launch the application.

### Linux / other Unix

If `XDG_DATA_HOME` is set:

```text
$XDG_DATA_HOME/persona-training-lab
```

Otherwise:

```text
~/.local/share/persona-training-lab
```

### Windows

Normally:

```text
%LOCALAPPDATA%\Persona Training Lab
```

If `LOCALAPPDATA` is unavailable, PTL falls back to `APPDATA`, then to the conventional local AppData path in the user's home directory.

### macOS

```text
~/Library/Application Support/Persona Training Lab
```

## 4. Know what lives in the workspace

A fresh workspace is created on demand and contains persistent/runtime locations such as:

```text
<workspace>/
├── app.db
├── artifacts/
├── exports/
├── temp/
├── cache/
└── logs/
```

`app.db` is PTL's SQLite workspace database. Do not place a second `app.db` inside the source tree; PTL's release policy treats hidden runtime inputs under `src/`, `tests/`, or `tools/` as a release-blocking condition.

If you do not need an old development workspace, starting with a clean workspace is the simplest way to reproduce first-run behavior.

## 5. Orient yourself in the interface

The left sidebar is the primary workspace navigator. PTL currently exposes these application areas:

| Workspace | Use it for |
|---|---|
| Dashboard | Overview of the current workspace and operational state |
| Profiles | Create and manage personality profiles |
| Agents | Inspect lineage/version relationships and use history/branch interactions |
| Datasets | Import, validate, inspect, and version datasets |
| Training | Check local-model readiness and work with training runs/model versions |
| Snapshots | Work with persisted snapshots |
| Tests | Run and inspect test/evaluation workflows |
| Analysis | Inspect analysis results and related stored data |
| Style | Change theme, accent, UI scale, and interface language |
| Automation | Configure and run controlled automation commands/recipes |
| Documentation | Read documentation from inside PTL |
| Key bindings | Inspect and customize keyboard/mouse bindings |

The shell also provides supporting panels including Inspector, Activity, Issues, and Telemetry. Their exact visibility can be controlled from the shell's panel controls.

## 6. Choose a language and appearance

Open **Style** to configure the interface.

PTL currently includes complete UI catalogs for:

- Arabic (`ar`)
- English (`en-US`)
- Spanish (`es-ES`)
- Russian (`ru-RU`)

Arabic is a real RTL interface mode, not merely a translated string catalog. PTL keeps shell geometry stable while applying RTL direction to text where appropriate. A bundled Noto Sans Arabic UI font is registered for Arabic so rendering does not depend on the host machine's fallback font selection.

Theme, accent palette, UI scale, and language preferences are persisted by the application.

## 7. Optional local-model support

PTL's core UI can run without the inference/training extras. Model-related features expect a local model path when those workflows are used.

Production model loading does **not** enable Hugging Face `trust_remote_code=True`. A model directory therefore cannot silently expand PTL's Python trust boundary by supplying arbitrary repository code through that mechanism.

The v1.0 operations guide will document supported model expectations, readiness checks, training behavior, and troubleshooting in detail.

## 8. Verify a development checkout

For contributors or anyone validating a checkout, the fast release gate is:

```bash
set -o pipefail
uv run --locked python tools/release_gate.py --quick --runs 3
```

The complete test and type-check commands are:

```bash
uv run --locked python -m pytest -q
uv run --locked python -m mypy src
```

The release gate requires a clean Git worktree and also checks for ignored runtime inputs that could change local execution without appearing in the recorded commit.

## Next steps

Return to the [Documentation Hub](../README.md) for the evolving v1.0 guide and reference set.

Before relying on PTL for an advanced workflow, read the [v1.0 Product Contract](../reference/v1-product-contract.md) so the release guarantees and deliberate non-goals are clear.
