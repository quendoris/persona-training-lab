# Development setup

This guide describes the current source-checkout development environment for Persona Training Lab (PTL). It is intentionally tied to the repository's audited Python/`uv` configuration rather than to historical setup notes.

## Requirements

PTL currently requires:

- Python **3.12 or newer**;
- [`uv`](https://docs.astral.sh/uv/) for dependency/environment management;
- a desktop environment capable of running Qt/PySide6 for interactive UI work.

The project uses a `src/` layout and Hatchling as its build backend. Runtime dependencies and optional local-model stacks are declared in `pyproject.toml`; exact resolved dependency versions are pinned by `uv.lock`.

## Clone and synchronize

From the repository root:

```bash
uv sync --locked
```

For development commands that require pytest, Ruff or mypy, ensure the development dependency group is installed:

```bash
uv sync --locked --group dev
```

Use `--locked` for validation and release work. It makes dependency resolution fail instead of silently changing the lockfile.

## Optional local-model stacks

The desktop core does not require the full inference/training stack.

Install inference support when model probing or generation is needed:

```bash
uv sync --locked --extra inference
```

Install Training support when local full fine-tuning is needed:

```bash
uv sync --locked --extra training
```

The `training` extra includes the inference dependencies plus the dataset stack declared by the project. These extras install Python dependencies; they do not make arbitrary model repositories trusted and do not bypass PTL's local-model safety checks.

## Launch the application

Run PTL from the repository root with:

```bash
uv run --locked python -m persona_training_lab.bootstrap.app
```

Runtime workspace data is deliberately stored outside the source checkout. Starting PTL from a different current working directory must not turn the repository into the application's data directory.

See [Workspace & Storage](../operations/workspace-and-storage.md) and [Workspace layout reference](../reference/workspace-layout.md) for the exact platform-specific persistence roots and external settings stores.

## Headless Qt work

Many automated UI tests and audit tools can run through Qt's offscreen platform plugin:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked python -m pytest -q
```

On Windows, set the environment variable using the shell's native syntax before running the command.

Offscreen execution is useful for repeatable tests and automated visual captures, but it is not a substitute for an interactive native-platform visual check. Window-manager behavior, font rendering, DPI handling and platform integration can differ from the offscreen environment.

## Repository layout for developers

The high-level source layout is:

```text
src/persona_training_lab/   production package
tests/                      automated test suite
tools/                      repository-local engineering/audit tools
docs/                       user, operator, architecture and developer docs
pyproject.toml               package/dependency/tool configuration
uv.lock                      locked dependency graph
```

`tools/` currently contains project-specific audit/build-support programs such as the release gate, typing audit, i18n audit, codebase statistics and visual audit harness. These are part of PTL's engineering process, not runtime application workspaces.

## Before editing behavior

When changing a subsystem, first locate its current contract in the documentation and tests. In particular:

- persistence changes should be checked against [Persistence architecture](../architecture/persistence.md);
- shell/navigation changes against [UI shell architecture](../architecture/ui-shell.md);
- Agents changes against [Agents lineage architecture](../architecture/agents-lineage.md);
- Automation changes against [Automation architecture](../architecture/automation.md);
- machine states/identifiers against [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md).

The project treats tests and current implementation as evidence. Documentation should not preserve an older behavior merely because it appeared in a historical note.

## Clean-worktree rule for release evidence

Ordinary development and test runs may be performed with local changes. The release gate is different: it refuses to start when Git reports a dirty worktree because its report is designed to be tied reproducibly to one recorded commit.

Before running the release gate, commit or stash local changes and verify:

```bash
git status --short
```

A clean result is a precondition for release-gate evidence, not a general rule for day-to-day development.

## Next steps

Continue with:

- [Testing](testing.md) for pytest/static/audit layers;
- [Visual audit](visual-audit.md) for automatic and interactive Qt captures;
- [Packaging](packaging.md) for wheel/sdist behavior;
- [Release process](release-process.md) for the final evidence sequence.
