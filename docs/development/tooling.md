# Developer Tooling

Persona Training Lab keeps a small set of repository-local developer tools under `tools/`. These files are part of the PTL development/release contract, not a generic utility library.

This document describes the tools that exist in the current repository, what they actually own, and which parts are reasonable candidates for later extraction into reusable engineering snippets.

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

A generalized descendant belongs in the independent `quendoris/snippets` repository as `codebase-anatomy`. PTL keeps `tools/codebase_stats.py` until an explicit migration changes the release contract and its tests.

## `i18n_audit.py`

`tools/i18n_audit.py` is a thin PTL command-line boundary over production localization audit code in `persona_training_lab.i18n`.

It fixes PTL-specific inputs including:

- `src/persona_training_lab` as the source root;
- `src/persona_training_lab/i18n/catalogs` as the catalog directory;
- `ru-RU` as the base locale;
- PTL deep-literal augmentation.

The command returns non-zero when the resulting localization report does not pass, and `--json` exposes the audit payload.

### Reuse boundary

The wrapper itself should not be copied as a generic snippet: its meaning depends on PTL localization architecture and catalog semantics.

Reusable lower-level ideas, if extracted later, would need their own independent catalog/source contracts rather than hard-coded PTL paths or locale assumptions.

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

The scanner/classifier split is a strong candidate for a future reusable snippet, but PTL's exact blocking policy is product/release policy. A reusable version must parameterize policy instead of silently exporting PTL's rule as a universal typing standard.

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

The current commands, environment variables, quick-test manifest and release policy are PTL-specific. A future generic `repro-gate` snippet must receive those policies as configuration rather than inheriting PTL names and commands.

## `visual_audit.py`

The visual-audit harness launches the real PTL application composition, navigates registered workspaces/locales, captures Qt widgets, and writes PNG evidence plus manifest/summary/archive artifacts.

This is intentionally stronger than constructing isolated mock widgets: captures exercise the application shell that users actually see.

That strength is also a privacy/trust boundary. A visual audit can capture real workspace contents, paths, identifiers and current application state. Public documentation captures should therefore use a known clean/demo workspace and declared locale/theme/scale/state.

See [Visual Audit](visual-audit.md) for the exact harness contract.

### Reuse boundary

Reusable primitives include:

- capture naming;
- widget/window image acquisition;
- metadata/manifests;
- archive assembly;
- deterministic scenario result recording.

PTL navigation registry, dependency container, LocalizationManager, workspace preparation and scenario definitions remain PTL-specific.

A generic `app-screenshotter` should be extracted from those primitives rather than by copying the current harness wholesale.

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

The integrity-vendoring pattern may be reusable, but the current script owns PTL-specific asset paths, manifest schema, upstream URL construction, user-agent string and font provenance. It therefore remains project-local.

## Project-local tools vs reusable snippets

The extraction rule for PTL is:

```text
working PTL-local tool
    ↓
audit what is PTL-specific
    ↓
extract only the reusable mechanism
    ↓
specify and test it independently
    ↓
keep PTL local behavior unchanged
    ↓
consider migration only as a separate reviewed change
```

This prevents a new shared repository from silently becoming a release dependency during v1.0 stabilization.

The independent reusable repository is:

```text
quendoris/snippets
```

Its current first extraction is `codebase-anatomy`, descended conceptually from `tools/codebase_stats.py` but designed to separate automatic language/line facts from repository-declared semantic groups such as `core`, `architecture`, or `critical`.

## Candidate extraction matrix

| PTL source | Reusable candidate | Current action |
|---|---|---|
| `codebase_stats.py` | `codebase-anatomy` | extract/generalize independently; keep PTL tool |
| `visual_audit.py` | `app-screenshotter` primitives | candidate after capture contracts stabilize |
| release audit orchestration | `repro-gate` | candidate; PTL policy must remain configuration, not default truth |
| `typing_audit.py` scanner | typing-suppression audit | candidate after policy/scanner separation is explicit |
| font vendoring integrity flow | pinned-asset vendor | possible later extraction; current script strongly PTL-specific |
| `i18n_audit.py` | generic catalog/source audit | do not extract until a non-PTL contract is defined |

## Development invariant

A successful extraction into `snippets` is **not** proof that PTL should depend on it immediately.

During release stabilization, source-of-truth behavior remains the code and tests committed in this repository. Replacing a release-critical local tool with a shared snippet is an architectural/dependency change and must receive the same audit, tests and reproducibility evidence as any other release-critical modification.
