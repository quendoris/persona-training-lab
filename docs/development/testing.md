# Testing and engineering audits

PTL uses several validation layers because no single test runner proves the properties needed for a desktop research workstation. This document describes what each current layer checks and, just as importantly, what it does not prove.

## Test suite

Run the complete pytest suite from the repository root:

```bash
uv run --locked python -m pytest -q
```

For a single file or focused test while developing:

```bash
uv run --locked python -m pytest -q tests/test_training_runner.py
uv run --locked python -m pytest -q tests/test_training_runner.py::test_name
```

The repository's pytest configuration points `testpaths` at `tests/`.

The test suite includes unit, integration and Qt-facing contract tests. Many UI tests use an offscreen Qt platform so they can execute without a visible desktop. Passing those tests does not replace a native interactive visual check.

## Compile check

The release workflow compiles Python sources under production code, tests and tools:

```bash
uv run --locked python -m compileall -q src tests tools
```

This catches syntax/import-compilation failures. It does not execute application behavior.

## Ruff

Run the repository lint check with:

```bash
uv run --locked python -m ruff check src tests tools
```

Ruff is blocking in both quick and full release-gate profiles.

## Typing

### mypy

The full release profile runs:

```bash
uv run --locked python -m mypy src
```

mypy is a blocking full-release step. It is intentionally absent from the smaller quick profile; therefore a successful quick gate must not be reported as proof that the full typing gate passed.

### Typing-suppression audit

PTL also has a dedicated audit for suppressions that could hide typing failures:

```bash
uv run --locked python tools/typing_audit.py
```

Machine-readable output:

```bash
uv run --locked python tools/typing_audit.py --json
```

The audit scans Python under `src/`, `tests/` and `tools/`, plus supported mypy configuration files. Production/release-tool/config suppressions are blocking. Narrow, error-code-qualified `# type: ignore[...]` seams in tests are inventoried as informational rather than silently treated as production-safe suppressions.

This audit complements mypy; it does not replace mypy.

## Localization audit

Run the localization/catalog audit with:

```bash
uv run --locked python tools/i18n_audit.py
```

For JSON output:

```bash
uv run --locked python tools/i18n_audit.py --json
```

The audit validates the complete locale catalogs against the Russian base locale and augments the report with deeper source-literal inspection.

A stricter UI-literal mode is also available for targeted work:

```bash
uv run --locked python tools/i18n_audit.py --strict-ui-literals
```

The current release gate invokes the JSON audit without the `--strict-ui-literals` flag. Do not describe the stricter flag as part of the release gate unless the implementation is changed accordingly.

## Codebase statistics

The repository-local statistics tool is:

```bash
uv run --locked python tools/codebase_stats.py
```

Machine-readable form:

```bash
uv run --locked python tools/codebase_stats.py --json
```

It counts tracked UTF-8 text files and separates categories including production Python, tests, tools, documentation, styles, SVG assets and configuration. For Python, it additionally derives a code-line count that excludes comments, blank lines and recognized docstrings.

The result is an engineering inventory, not a complexity or quality metric. A larger number of lines does not imply more functionality or better architecture.

## Release-policy tests

`tests/test_release_gate_policy.py` protects several release assumptions, including:

- full-profile mypy/build are blocking;
- the quick profile is explicitly smaller;
- removed bypass flags such as `--skip-mypy` and `--skip-build` stay rejected;
- release reports require a resolvable Git HEAD;
- a dirty worktree is rejected before report creation;
- ignored runtime-affecting files under `src/tests/tools` are not allowed beyond known generated/platform noise;
- production model loaders must not opt into `trust_remote_code=True`.

These tests are important because they verify the release mechanism itself rather than merely application features.

## Visual-audit tests

`tests/test_visual_audit_tool.py` launches the real PTL composition through `tools/visual_audit.py` in offscreen mode and verifies, among other things:

- complete-locale default capture behavior;
- route coverage through the navigation registry;
- PNG capture creation;
- manifest and ZIP bundle creation;
- interactive capture metadata for visible top-level windows.

Read [Visual audit](visual-audit.md) before using those captures as release or documentation evidence.

## Quick release profile

The curated quick profile is run with:

```bash
uv run --locked python tools/release_gate.py --quick
```

Its current validation sequence is:

1. `compileall`;
2. Ruff;
3. typing-suppression audit;
4. pytest using the explicit paths in `tools/release_quick_tests.txt`;
5. i18n audit;
6. codebase statistics.

The quick profile deliberately omits full mypy and package build. It is useful for repeated high-confidence development checks, but it is not the final release proof.

## Full release profile

Run the full profile with:

```bash
uv run --locked python tools/release_gate.py
```

Its current validation sequence is:

1. `compileall`;
2. Ruff;
3. typing-suppression audit;
4. mypy over `src`;
5. complete pytest suite;
6. i18n audit;
7. codebase statistics;
8. `uv build`.

Every current step is blocking.

The gate can repeat pytest multiple times:

```bash
uv run --locked python tools/release_gate.py --runs 3
```

A random 32-bit seed is generated when `--seed` is not supplied. The seed, run count, Git commit, branch, Python/platform metadata and per-step logs are written into the audit directory. `PYTHONHASHSEED`, `PTL_RELEASE_AUDIT=1` and `PTL_RELEASE_AUDIT_DIR` are propagated to child steps.

## Evidence directories

The release gate writes isolated reports under:

```text
artifacts/release-audit/
```

Each session directory is timestamped and includes the commit prefix and seed. It contains step logs, metadata JSON and Markdown/JSON summaries.

This `artifacts/` directory belongs to the repository's engineering evidence flow. It is different from the end-user runtime workspace's own `artifacts/` directory.

## Failure interpretation

A failed command should be diagnosed at the failing layer instead of being flattened into “tests failed”. For example:

- compile failure → syntax/import-compilation problem;
- Ruff failure → lint/static rule problem;
- typing-audit failure → potentially hidden type errors;
- mypy failure → type-checking contract problem;
- pytest failure → behavioral/contract regression;
- i18n failure → catalog/literal/localization contract problem;
- build failure → packaging/build-system problem;
- visual-audit failure → Qt composition/navigation/capture problem.

Preserve the corresponding logs before modifying the failing state when the evidence may matter for release diagnosis.
