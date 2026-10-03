# Persona Training Lab — Accepted Changes

This is a compact engineering-history summary, not the public release changelog and not a substitute for the canonical architecture/reference docs.

## Current accepted baseline direction

- PTL is a full desktop research workstation rather than the old Phase 2.x scaffold.
- The first public package release is `0.1.0`.
- Pre-release scope is frozen to documentation/code consistency, concrete defect repair, visual acceptance, full automated gate, packaging/install acceptance and release evidence.
- Training Dynamics runtime features and the Mathematical Inspector are post-v0.1.0 work.
- The later adversarial/falsification battery is intentionally separated from ordinary regression testing and comes after the mathematical/instrumentation layer can actually be falsified.

## Major accepted architecture changes

- Workspace ownership is independent from process current working directory.
- SQLite/persistence/runtime operations have explicit ownership and concurrency contracts.
- Long-running UI operations participate in explicit shutdown ownership.
- Agents lineage uses coherent persisted projection data plus separate local graph/history/layout state.
- Destructive Agents history binds to exact safety identity and fails closed on mismatches.
- Projection publication reconciles resource links before a new generation becomes screen-accepted.
- Training pins Profile/Dataset input identity and publishes final artifacts only after staging completes.
- Automation is an explicit trusted-host surface with runtime claims, audit records, process-tree containment and review-to-run semantic identity.
- Telemetry collection moved off the GUI thread and participates in shell shutdown.
- Localization is catalog-driven across `ru-RU`, `en-US`, `es-ES`, and RTL `ar`.
- UI literal inventory reached zero in the current audit.
- Documentation audit is a blocking release-gate step.

## Most recent executed evidence before documentation moved HEAD

Commit:

```text
39d25de13568571a019992fe84ec8a616b6e7048
```

Evidence:

- compileall PASS;
- Ruff PASS;
- typing audit: zero blocking findings;
- quick pytest inventory: **603 passed ×3**;
- i18n audit PASS;
- docs audit PASS;
- clean tracked-tree statistics.

This evidence is not automatically inherited by later commits.

## Current documentation findings

- The old v0.1.0 checklist described a pre-refactor release and has been replaced with a post-refactor release-close checklist.
- Release/testing docs had fallen behind the real gate by omitting the blocking `docs-audit` step; they are synchronized again.
- The Training pipeline contained a duplicated “Artifact layout and publication” section/numbering block; the duplicate was removed.
- Legacy `docs/context/*` files were materially stale and are being rewritten as compact current handoff context rather than competing architecture truth.


## Additional crack-audit corrections

- Corrected the intermediate `67b24d2...` codebase-statistics transcription to the actual measured values: 110,810 physical lines, 63,182 Python code lines and 21,034 Tests Python code lines.
- Corrected the architecture overview startup sequence so workspace writer ownership is acquired before `build_container(settings)`, and the final background drain/lease release ordering is visible.
- Corrected the background-work cancellation matrix: Training inference/full Training, Tests and Automation execute blocking work in owned QThreads rather than on the Qt GUI thread.
- Removed the last stale `v1.0` wording from the current workspace-concurrency contract.

- Corrected documentation taxonomy after refreshing `docs/context/*`: context is now maintained handoff material, while only old release/audit records remain historical; the live v0.1.0 checklist is linked from the Documentation Hub and release process.

- Synchronized developer-tool documentation with the real release gate: `tools/docs_audit.py` is now listed/described as a blocking quick/full gate component, and packaging/setup docs no longer omit it.

- The documentation/version drift found during the v0.1.0 sweep is now guarded in code: `release_gate.py` fails closed when `pyproject.toml` version and runtime `persona_training_lab.__version__` diverge, and records both values in release metadata/summary.

- Crack audit found a real explicit-workspace composition defect: `build_container(AppSettings(workspace_dir=...))` used the custom root for SQLite/artifacts/Automation but constructed `LocalModelService` with its default OS workspace root. Production wiring now injects `paths.root`, and a composition-level regression asserts the default model path follows the explicit workspace.

- Crack audit found a second workspace-path seam: `WorkspaceOwnership` canonicalized explicit roots, while `build_workspace_paths()` previously fanned out the raw `workspace_dir`. Relative or `~` overrides could therefore make the writer lock and actual mutable paths disagree. Workspace path fan-out now canonicalizes with `expanduser().resolve()`, with regression coverage for a relative override.

- The same explicit-workspace audit found Agents local state bypassing composition: the composed screen constructed `AtomicLineageStateStore()` with the default OS workspace even when the application used an explicit workspace override. Wiring now injects `<workspace>/agents_lineage_state.json` through `AgentsViewModel`, and the screen consumes that path.

- Release audit also found that full-gate `uv build` writes `dist/` while the repository did not ignore that directory. `/dist/` is now explicitly ignored and policy-tested so producing release artifacts does not make the source candidate appear newly dirty.

- Visual-audit isolation was corrected after workspace stabilization changed semantics: merely `chdir`-ing into a temporary directory no longer selected the PTL workspace. The harness now injects the temporary directory through `AppSettings`, plus audit-local key bindings and QSettings-backed window state, with a subprocess regression proving Agents/model/key-binding/window-state paths all remain inside the audit workspace.

- Primary SQLite lifetime is now explicit: `AppContainer` owns the writable connection, normal desktop/visual-audit shutdown closes it after worker drain and before workspace release/temp cleanup, and the connection-lock registry entry is removed. This avoids relying on interpreter GC and closes a Windows temporary-workspace cleanup seam.
