# Developer Tooling

Persona Training Lab keeps a small set of repository-local developer tools under `tools/`. These files are part of the PTL development/release contract, not a generic utility library.

This document describes the tools that exist in the current repository, what they actually own, and which reusable mechanisms already have independent descendants outside PTL.

The distinction matters because a reusable implementation elsewhere does **not** automatically replace the version that a release gate, test, or audit in this repository depends on.

## Current tool inventory

```text
tools/
├── codebase_stats.py
├── i18n_audit.py
├── release_gate.py
├── release_quick_tests.txt
├── typing_audit.py
├── vendor_noto_arabic_fonts.py
└── visual_audit.py
```

Each file has a different coupling level.

## `codebase_stats.py`

Purpose:

- count recognized tracked text files;
- report physical/nonblank lines;
- calculate Python code lines using `tokenize` while excluding AST-recognized docstrings;
- split PTL files into project-shaped categories such as Production Python, Tests Python, Tools Python and Documentation;
- emit human or JSON output;
- report branch/commit and largest tracked text files.

Source selection is deliberately Git-based:

```text
git ls-files -z
```

`uv.lock` is explicitly excluded from the tracked-text accounting.

### Reuse boundary

The generic ideas are reusable:

- tracked-file inventory;
- language/code-line accounting;
- machine-readable reporting;
- repository-size ratios.

The current category rules are PTL-specific. For example, every `src/*.py` file is called Production Python and every `tests/*.py` file Tests Python. A generic tool must not pretend these directory names encode universal architecture.

An independent generalized descendant exists in `quendoris/snippets` as `codebase-anatomy`. It adds multi-language accounting and explicit repository-declared semantic groups instead of exporting PTL's path taxonomy as universal truth.

PTL still keeps and uses `tools/codebase_stats.py`. The existence of `codebase-anatomy` is not a dependency migration and does not alter PTL release evidence.

## `i18n_audit.py`

`tools/i18n_audit.py` is a thin PTL command-line boundary over production localization audit code in `persona_training_lab.i18n`.

It fixes PTL-specific inputs including:

- `src/persona_training_lab` as the source root;
- `src/persona_training_lab/i18n/catalogs` as the catalog directory;
- `ru-RU` as the base locale;
- PTL deep-literal augmentation.

The command returns non-zero when the resulting localization report does not pass, and `--json` exposes the audit payload.

### Reuse boundary

The wrapper itself is PTL-specific: its meaning depends on PTL localization architecture and catalog semantics.

No independent generic catalog/source-audit package is part of the current PTL toolchain. Any reusable implementation would need an explicit contract for catalog roots, base locale, literal policy and failure semantics rather than inheriting PTL paths or assumptions implicitly.

## `typing_audit.py`

The typing audit searches Python comments and selected type-checker configuration files for suppressions that can hide typing errors.

Current scanned source roots are:

```text
src/
tests/
tools/
```

Current configuration candidates are:

```text
pyproject.toml
mypy.ini
.mypy.ini
setup.cfg
tox.ini
```

The audit recognizes source/config markers including:

- `# type: ignore[...]`;
- `# mypy: ignore-errors`;
- mypy disabled-error-code directives;
- `ignore_errors = true` in supported configuration files.

The current policy treats narrowly coded `# type: ignore[...]` findings under `tests/` as informational. Other recognized suppressions are blocking.

The JSON form records total, blocking, informational and per-finding details.

### Reuse boundary

The scanner/classifier mechanics are separable from policy in principle, but PTL's exact blocking policy is product/release policy. No independently versioned typing-suppression snippet is part of PTL's current dependency or release contract.

## `release_quick_tests.txt`

This is not executable code. It is the curated test manifest consumed by `release_gate.py` when `--quick` is selected.

`ReleaseGate.load_quick_test_manifest()` requires that the manifest:

- is readable;
- contains at least one non-comment/nonblank path;
- contains no duplicate paths;
- references files that exist in the repository.

The manifest is therefore part of the quick-release policy and must be reviewed when test coverage or critical subsystems change.

## `release_gate.py`

`release_gate.py` orchestrates PTL's reproducible release audit.

Before it creates a report directory, it requires:

- a resolvable Git `HEAD`;
- a clean worktree.

That means a dirty/conflicted checkout produces a **release-audit configuration error**, not a failed pytest/Ruff result.

The quick profile runs blocking:

```text
compileall
ruff
typing-audit
pytest (curated manifest, repeated according to --runs)
i18n-audit
codebase-stats
```

The full profile additionally makes `mypy` and `uv build` blocking release steps.

Child processes receive a recorded seed through `PYTHONHASHSEED` plus the PTL release-audit environment markers. Logs, metadata and JSON/Markdown summaries are written under an isolated audit directory.

See [Release Process](release-process.md) and [Testing](testing.md) for the release workflow rather than duplicating the complete gate contract here.

### Reuse boundary

Useful generic ideas include:

- clean-commit preconditions;
- isolated evidence directories;
- recorded seed/environment;
- ordered blocking steps;
- repeated tests;
- machine-readable summaries.

The current commands, environment variables, quick-test manifest and release policy are PTL-specific. No shared `repro-gate` implementation is part of the current PTL release path; PTL release evidence is produced by this repository's `tools/release_gate.py`.

## `visual_audit.py`

The visual-audit harness launches the real PTL application composition, navigates registered workspaces/locales, captures Qt widgets, and writes PNG evidence plus manifest/summary/archive artifacts.

This is intentionally stronger than constructing isolated mock widgets: captures exercise the application shell that users actually see.

That strength is also a privacy/trust boundary. A visual audit can capture real workspace contents, paths, identifiers and current application state. Public documentation captures should therefore use a known clean/demo workspace and declared locale/theme/scale/state.

See [Visual Audit](visual-audit.md) for the exact harness contract.

### Reuse boundary

The reusable surface has been split deliberately rather than copying PTL's harness wholesale:

- `quendoris/snippets/app-screenshotter` contains small PySide6 in-process widget/top-level capture and PNG-manifest primitives;
- `quendoris/snippets/archive-bundler` contains an independent deterministic file-inventory/ZIP evidence primitive.

PTL's navigation registry, dependency container, LocalizationManager, workspace preparation, route/locale traversal, interactive scenario semantics, PTL manifest schema and release/documentation rules remain PTL-specific.

Neither reusable snippet replaces `tools/visual_audit.py` in PTL. The project-local harness still owns the end-to-end PTL visual-audit contract and its tests.

This separation is also intentional because the generic snippets have different guarantees: `app-screenshotter` does not claim deterministic PNG bytes across Qt/platform/rendering environments, while `archive-bundler` is designed around deterministic archive representation for unchanged selected bytes/metadata.

## `vendor_noto_arabic_fonts.py`

This tool vendors the pinned Arabic UI font assets described by PTL's `noto_arabic_ui.json` manifest.

It verifies:

- manifest schema `1`;
- bundled license presence and expected Git blob SHA-1;
- each font's expected byte size;
- each font's expected Git blob SHA-1.

Normal vendoring downloads from the manifest-pinned GitHub repository/commit over HTTPS, writes through a temporary path, replaces the destination, and then runs the same local verification used by `--check`.

The command also prints SHA-256 values as diagnostic/provenance information, while the manifest contract itself currently pins Git blob SHA-1 and size.

### Reuse boundary

The integrity-vendoring pattern is conceptually reusable, but the current script owns PTL-specific asset paths, manifest schema, upstream URL construction, user-agent string and font provenance. It remains project-local and has no shared-tool dependency in the current PTL release path.

## Project-local tools vs reusable snippets

The extraction rule that preserves PTL release identity is:

```text
working PTL-local tool
    ↓
audit what is PTL-specific
    ↓
extract only a reusable mechanism into an independent project
    ↓
specify and test that project independently
    ↓
keep PTL local behavior/dependencies unchanged
```

An external extraction records engineering provenance. It does not create a PTL dependency edge by itself.

The independent reusable repository relevant to the already-created descendants is:

```text
quendoris/snippets
```

Current extractions relevant to PTL are:

```text
codebase-anatomy
    ← conceptually descended from tools/codebase_stats.py

app-screenshotter
    ← capture/evidence primitives distilled from tools/visual_audit.py

archive-bundler
    ← generic deterministic evidence-packaging primitive applicable to visual/release artifacts
```

These relationships record engineering provenance, not dependency edges. PTL does not import these snippets in the current v1.0 documentation/release contract.

## Current extraction/dependency matrix

| PTL source / need | Independent reusable implementation | Current PTL dependency state |
|---|---|---|
| `codebase_stats.py` | `codebase-anatomy` | independently extracted; PTL still uses local release tool |
| widget/top-level capture ideas from `visual_audit.py` | `app-screenshotter` | independently extracted; PTL harness remains canonical |
| generic evidence ZIP/inventory need | `archive-bundler` | independently extracted; no PTL dependency migration |
| release audit orchestration | none in the PTL dependency graph | local `release_gate.py` is authoritative |
| `typing_audit.py` scanner/policy | none in the PTL dependency graph | local tool/policy is authoritative |
| font vendoring integrity flow | none in the PTL dependency graph | local font-vendoring tool is authoritative |
| `i18n_audit.py` | none in the PTL dependency graph | local localization audit is authoritative |

## Development invariant

A successful extraction into `snippets` is **not** proof that PTL should depend on it.

Source-of-truth release behavior remains the code and tests committed in this repository. Replacing a release-critical local tool with a shared implementation would be an architectural/dependency change and would need its own audit, tests and reproducibility evidence before it could become part of the PTL release contract.

Conversely, PTL documentation must not describe an independently extracted snippet as part of PTL's release guarantee unless PTL actually imports/invokes that version and the relationship is covered by tests. Provenance and dependency are different relationships.
