# Release process

This document defines the current engineering evidence sequence for preparing a PTL release candidate. It describes the release machinery that exists in the repository today and separates automated proof from manual review.

## Release principle

A release result should be attributable to one known Git commit and one known dependency state.

The release gate therefore refuses to start from a dirty worktree and records Git, Python, platform, seed and per-step evidence into an isolated audit directory.

A release should not be declared from memory, an old successful run, or a test result produced before the candidate commit changed.

## 1. Resolve the candidate commit

Before final validation:

```bash
git status --short
git rev-parse HEAD
git branch --show-current
```

The worktree must be clean for `tools/release_gate.py`.

If generated, ignored or external files under `src/`, `tests/` or `tools/` can alter execution without being represented by the recorded commit, the release-policy tests are expected to detect that class of source-integrity problem.

## 2. Synchronize the locked development environment

Use the tracked lockfile:

```bash
uv sync --locked --group dev
```

Install optional model extras only when the validation activity requires them:

```bash
uv sync --locked --extra inference
uv sync --locked --extra training
```

Do not regenerate `uv.lock` as a side effect of release validation.

## 3. Run the quick gate during final iteration

The curated quick gate is useful while closing the last candidate defects:

```bash
uv run --locked python tools/release_gate.py --quick
```

For repeated stability evidence:

```bash
uv run --locked python tools/release_gate.py --quick --runs 3
```

The quick profile currently runs compileall, Ruff, typing-suppression audit, the curated pytest manifest, i18n audit and codebase statistics.

It intentionally does **not** run full mypy or package build. A quick PASS is therefore an iteration gate, not the final release proof.

## 4. Run the full release gate

From the clean candidate commit:

```bash
uv run --locked python tools/release_gate.py
```

For repeated pytest execution:

```bash
uv run --locked python tools/release_gate.py --runs 3
```

The full profile currently blocks on this sequence:

1. compile all Python under `src`, `tests`, `tools`;
2. Ruff over the same roots;
3. typing-suppression audit;
4. mypy over `src`;
5. complete pytest suite, repeated according to `--runs`;
6. i18n audit;
7. codebase statistics;
8. `uv build`.

No current step is informational-only in the full profile.

## 5. Preserve the release-gate evidence

The gate writes to:

```text
artifacts/release-audit/<timestamp>-<commit>-seed-<seed>/
```

The session includes:

- `metadata.json`;
- one log per executed step;
- `summary.json`;
- `summary.md`.

The metadata records the exact commit, branch, dirty-worktree state, Python executable/version, platform, seed, run count and quick/full mode.

Do not copy only the final “PASS” line into release notes and discard the report directory when reproducible evidence is required.

## 6. Run visual audit separately

Visual audit is currently **not** a release-gate step.

For a controlled automatic pass:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked python tools/visual_audit.py \
  --width 1440 \
  --height 900
```

For native/manual inspection:

```bash
uv run --locked python tools/visual_audit.py --interactive
```

Use a clean/demo workspace for captures intended to leave the development machine. Review screenshots and metadata for sensitive workspace information before publication.

Preserve the visual-audit manifest/bundle together with the commit it records when screenshots are part of the release evidence.

See [Visual audit](visual-audit.md) for the capture contract and limitations.

## 7. Inspect package output

The full gate proves that `uv build` returned success. Before distribution, inspect the generated artifacts under `dist/` and verify at least:

- expected wheel and source-distribution files exist;
- package/version metadata is intended;
- license/notice material is correct;
- bundled documentation is present where PTL expects it;
- no repository-only files unexpectedly became runtime requirements.

Until package-content inspection is fully automated, this remains an explicit release-review step rather than something inferred from build success.

## 8. Verify exposed version surfaces

PTL currently has more than one place where release/version identity can appear. Before tagging a stable release, explicitly verify:

- `pyproject.toml` project version;
- runtime `persona_training_lab.__version__`;
- release notes/documentation version references;
- intended Git tag/release name.

Do not assume these values are synchronized automatically.

## 9. Review product-contract-sensitive changes

Before final release, compare candidate behavior against the current documentation contracts, especially:

- [v1.0 Product Contract](../reference/v1-product-contract.md);
- [Persistence architecture](../architecture/persistence.md);
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md);
- [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md);
- [Training pipeline specification](../training_pipeline.md);
- [Evaluation contract](../reference/evaluation-contract.md).

If code and documentation disagree, do not silently choose whichever is more convenient. Determine the intended release behavior, then update implementation/tests/docs so one contract remains.

## 10. Review documentation navigation and bundled docs

The documentation tree is part of the application package. Check that:

- `docs/README.md` links to every current public/developer document;
- renamed files have no stale links;
- historical `docs/context/` and `docs/releases/v0.*` material is not presented as current v1 truth;
- in-application documentation resolves after packaging.

## 11. Tag only after evidence is tied to the final commit

The final validation reports must refer to the same commit that will be tagged/released.

If any code, test, dependency, packaging metadata or contract documentation changes after the last full gate, the previous full-gate result is historical evidence for the old commit, not proof for the new candidate.

Run the full validation again.

## Release-gate exit meanings

`tools/release_gate.py` currently uses:

- exit `0` — gate completed with no blocking failures;
- exit `1` — a blocking validation step failed;
- exit `2` — release-audit configuration/precondition error, such as dirty worktree or unresolved Git HEAD;
- exit `130` — interrupted by the operator; partial logs are preserved.

A configuration error is not equivalent to a tested-and-failed product candidate; it means valid release evidence was not produced.

## Failure handling

When the gate stops on a blocking step:

1. preserve the generated report/log directory;
2. diagnose the first failing layer;
3. fix the candidate;
4. commit the fix;
5. rerun validation from the new clean commit.

Do not edit files while a report is running and then present that report as evidence for the modified tree. The clean-worktree precondition protects the start state; release discipline must preserve the identity of the candidate throughout the run.

## What a full gate does not prove

Even a complete PASS does not by itself prove:

- pixel-perfect native rendering on every supported desktop environment;
- correctness of arbitrary external/local model contents;
- absence of sensitive information in screenshots/logs;
- native installer/signing/update behavior that is not implemented by this Python build;
- performance on every hardware configuration;
- semantic quality of every AI output.

Those are separate evidence domains and should remain separate in release claims.
