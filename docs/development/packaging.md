# Packaging

PTL currently uses standard Python packaging metadata in `pyproject.toml`, with Hatchling as the build backend and `uv` as the normal build frontend used by the release gate.

This guide documents the package contract that exists now. It does not imply that native installers, application bundles or signed platform packages already exist.

## Package metadata

The current project metadata declares:

- package name: `persona-training-lab`;
- Python requirement: `>=3.12`;
- license expression: `AGPL-3.0-only`;
- build backend: `hatchling.build`;
- core dependency set centered on PySide6 and psutil;
- optional `inference` and `training` dependency extras;
- development dependencies through the `dev` dependency group.

The repository's `LICENSE`, `NOTICE` and `AUTHORS` files are part of the licensing/documentation contract and should be reviewed whenever distribution metadata changes.

## Build from a clean source checkout

Synchronize the locked environment first:

```bash
uv sync --locked --group dev
```

Then build:

```bash
uv build
```

The current full release gate runs the same `uv build` command and then executes a blocking repository-local package-content audit.

Build output is normally written under:

```text
dist/
```

`/dist/` is repository-ignored generated output. The full release gate is allowed to create distribution artifacts without turning the validated source worktree into a new untracked-source candidate; package files are inspected/checksummed as release artifacts rather than committed source.

A successful build proves that the configured Python distributions can be produced. It does not by itself prove runtime startup, dependency compatibility on every supported host, model-stack availability, or native desktop packaging quality.

## Wheel documentation inclusion

The Hatch configuration explicitly force-includes the repository `docs/` tree into the wheel under:

```text
persona_training_lab/docs
```

This exists because PTL exposes documentation inside the application and therefore the documentation set is not only a GitHub-side artifact.

Changes to documentation paths can consequently be packaging changes. When reorganizing `docs/`, verify that in-application documentation lookup still resolves the intended files from an installed wheel rather than only from a source checkout.

## Optional extras

The core package avoids forcing large local-model dependencies on every installation.

Inference support is declared through the `inference` extra and currently includes the model-runtime stack such as Torch, Transformers, Accelerate, Safetensors, Tokenizers and SentencePiece.

Training support is declared through the `training` extra and includes the same model stack plus the datasets dependency.

Typical source-checkout synchronization:

```bash
uv sync --locked --extra inference
uv sync --locked --extra training
```

Packaging metadata must keep those extras coherent with the code paths that import or probe them. A dependency being optional in packaging must remain optional at application startup unless the product contract is deliberately changed.

## Source layout and import boundary

Production Python lives under:

```text
src/persona_training_lab/
```

Repository-only programs under `tools/` are not application entry points merely because they are Python files. They are engineering utilities for audit, statistics, visual capture and release validation.

Similarly, `tests/` is validation source and must not become an undeclared runtime dependency of the installed application.

## Application launch contract

The documented source-checkout launch path is:

```bash
uv run --locked python -m persona_training_lab.bootstrap.app
```

There is currently no console-script entry point declared in `pyproject.toml`. Do not document a command such as `persona-training-lab` unless an actual project script/entry point is added and tested.

## Versioning

The package metadata currently declares version `0.1.0` in `pyproject.toml` while the project is being prepared for the v0.1.0 documentation/release contract.

Treat version synchronization as a release task. The release gate now enforces equality between package metadata and runtime `__version__` before it creates release evidence.

Release notes, documentation labels and the Git tag remain separate human/public surfaces and still require final review; package/runtime equality does not automatically rewrite or validate them.

## Locked dependencies

`uv.lock` is a tracked release input. Release validation should use `--locked` when synchronizing/running commands so an audit cannot silently mutate dependency resolution while claiming to validate one Git commit.

A changed dependency declaration normally requires the lockfile to be deliberately regenerated and reviewed. Conversely, an unexpected lockfile change during unrelated work should be treated as evidence that dependency state changed.

## Build verification

At minimum, packaging work should verify:

1. `uv build` succeeds from a clean tracked source state;
2. expected wheel/sdist artifacts are produced under `dist/`;
3. package metadata is correct;
4. required license/notice material is present;
5. bundled documentation is present where the application expects it;
6. core installation does not accidentally require optional local-model stacks;
7. installed-package startup/documentation lookup is exercised before calling packaging complete.

The current full release gate directly proves items 1–5 for the built artifacts through `uv build` plus `tools/package_audit.py`, and also verifies that repository-only `tests/` or `tools/` roots did not enter the runtime wheel. Installed-environment startup and clean/existing-profile smoke remain separate acceptance work.

## Native desktop packaging

The current repository metadata builds Python distributions. It does not define a Windows installer, macOS application bundle, Linux AppImage/Flatpak/Snap package, code-signing process or automatic update channel.

Those would be separate packaging layers with their own trust, filesystem, Qt plugin, model-dependency and signing contracts. They should not be implied by the existence of a wheel/sdist build.

## Relationship to release validation

In the full release gate, `uv build` is blocking and occurs after compile, lint, typing, pytest, i18n, documentation-audit and codebase-statistics steps. A blocking package-audit step then inspects the generated wheel/sdist contents and metadata.

The quick release profile intentionally skips build. Therefore a quick-gate PASS is not packaging evidence.

See [Release process](release-process.md) for the complete evidence sequence.
