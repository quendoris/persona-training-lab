# Persona Training Lab

Persona Training Lab (PTL) is a desktop-first workstation for building, training, evaluating, inspecting, and operating personality-oriented local AI workflows.

The application combines a PySide6 desktop interface, SQLite-backed workspace state, local-model tooling, personality profiles and datasets, training and evaluation flows, version lineage, automation, telemetry, configurable key bindings, and multilingual UI support in one local workstation.

> **Documentation status:** PTL is in the v1.0 documentation and packaging phase. The audited runtime baseline is complete; public documentation is being rebuilt against the current architecture before the v1.0 release.

## Project evolution

Persona Training Lab started as an MVP prototype for experimenting with AI personas and local AI workflows.

During development, the project evolved through several architectural stages:

### Stage 1 — MVP foundation

Initial implementation of AI persona experiments, local workflows, and basic application structure.

### Stage 2 — Architecture redesign

The project was reorganized into clearer application boundaries with separated interface, application, infrastructure, and runtime responsibilities.

### Stage 3 — Internationalization

Added multilingual support and interface adaptation for different writing systems, including RTL language support.

### Stage 4 — Research infrastructure

Introduced the foundation for reproducible AI experimentation:

- experiment workflows;
- model and dataset management;
- version lineage;
- evaluation flows;
- analysis tooling;
- workspace state tracking.

### Stage 5 — Engineering refactoring

The codebase underwent a large-scale refactoring focused on maintainability and reliability:

- stronger module boundaries;
- expanded automated testing;
- safer runtime operations;
- improved error handling;
- release validation workflows.

### Stage 6 — Release preparation

Current development stage:

- complete technical documentation;
- architecture review;
- release audit pipeline;
- packaging preparation;
- final v1.0 quality validation.

## What PTL contains

The desktop application exposes dedicated workspaces for:

- **Dashboard** — current workspace state and operational overview.
- **Profiles** — personality-profile creation and management.
- **Agents** — model/persona lineage, version relationships, history navigation, and branch operations.
- **Datasets** — dataset import, validation, versions, and records.
- **Training** — local-model checks, training runs, progress, artifacts, and model-version publication.
- **Snapshots** — persisted snapshots of workspace/persona state.
- **Tests** — personality and evaluation test workflows.
- **Analysis** — analysis views over stored experiment and lineage data.
- **Automation** — controlled command recipes, execution, cancellation, timeout handling, and audit metadata.
- **Style** — theme, accent, UI scale, and interface language.
- **Documentation** — documentation available from inside the application.
- **Key bindings** — configurable keyboard and mouse interaction bindings.

The shell also includes Inspector, Activity, Issues, and Telemetry surfaces for operational context.

## Start from a source checkout

PTL requires **Python 3.12+**. The repository uses `uv` for dependency and environment management.

Install the desktop core:

```bash
uv sync --locked
```

Run the application:

```bash
uv run --locked python -m persona_training_lab.bootstrap.app
```

Optional local-model capabilities are installed with extras:

```bash
# Inference support
uv sync --locked --extra inference

# Training support
uv sync --locked --extra training
```

See the [Getting Started guide](docs/user-guide/getting-started.md) for workspace locations, first-launch behavior, optional model support, and the interface map.

## Where PTL stores data

Runtime data is intentionally kept outside the source tree and does not depend on the directory from which PTL is launched.

| Platform | Default workspace |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\\Persona Training Lab` |
| macOS | `~/Library/Application Support/Persona Training Lab` |

The workspace contains `app.db` plus runtime directories such as `artifacts/`, `exports/`, `temp/`, `cache/`, and `logs/`.

## Languages and interface direction

PTL currently ships complete UI catalogs for:

- Arabic (`ar`, RTL)
- English (`en-US`)
- Spanish (`es-ES`)
- Russian (`ru-RU`)

Arabic UI text uses a bundled Noto Sans Arabic UI font so rendering does not depend on host-system Arabic fallback fonts.

## Validation baseline

The current audited runtime baseline is guarded by:

- a curated quick release gate;
- the complete pytest suite;
- Ruff and mypy;
- a typing-suppression audit;
- an i18n catalog/UI-literal audit;
- visual audit tooling across application routes and locales;
- release-policy checks for clean source inputs and local-model trust boundaries.

The detailed release methodology is being consolidated into the v1.0 documentation set.

## Documentation

Start at the **[Documentation Hub](docs/README.md)**.

The documentation is organized for three different readers:

1. **Users** — installation, first run, concepts, and task-oriented walkthroughs.
2. **Operators / advanced users** — workspace behavior, automation, model handling, recovery, and troubleshooting.
3. **Developers / auditors** — architecture, persistence, runtime safety, localization, testing, packaging, and release contracts.

The [v1.0 Product Contract](docs/reference/v1-product-contract.md) defines what the first stable release promises and, equally importantly, what is intentionally outside that promise.

## Independent development

◆ Solo developer · No donations · No sponsors

## License

Persona Training Lab is licensed under **AGPL-3.0-only**. See [LICENSE](LICENSE), [NOTICE](NOTICE), and [AUTHORS](AUTHORS).
