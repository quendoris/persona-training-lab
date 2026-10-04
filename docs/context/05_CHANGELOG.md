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

- Built-package inspection is now automated and blocking in the full release gate. `tools/package_audit.py` verifies current-version wheel/sdist identity, wheel metadata, the full bundled docs tree, localization catalogs, UI assets/fonts, legal files and absence of repository-only runtime roots; its unit tests are included in the quick pytest inventory.

- Evaluation crack audit closed a protocol-integrity seam: a JSONL battery could previously mix `battery_version`, `instrument` or `scoring_version` between cases while the persisted run summary advertised only the first case's identity. Battery loading now rejects mixed protocol identity before inference, with parameterized regression coverage.

- Tests/Analysis now consume an explicit personality-portrait projection instead of assuming every generic `experiments` row is a portrait. Current semantic-title rows and structured legacy portrait payloads remain compatible; unrelated experiment records cannot become the latest/previous portrait pair. Regression coverage includes a newer unrelated row ahead of two valid portraits.

- Training/backend boundary now fails closed on an internally inconsistent backend result: `status=completed` without a published artifact path becomes terminal `artifact_not_created`, with no artifact/checkpoint persisted and regression coverage in the quick suite.

- Dataset import now canonicalizes external JSONL paths with `expanduser().resolve()` before persistence. This closes a provenance seam where a relative stored path could resolve to different bytes after restart from another working directory; regression coverage verifies the persisted path is absolute/canonical.

- Model-version publication no longer reselects the newest Training row after a run finishes. The exact started `run_id` is carried through completion and published only if that same run is completed with an artifact; a regression injects a newer distractor row during backend execution and proves it is not published.

- Telemetry lifetime audit closed a queued-signal race: the GUI previously cleared `_refresh_thread` as soon as a snapshot signal was applied, even though the Python worker could still be alive for a short unwind window. The panel now retains/reaps the concrete thread by `is_alive()`, blocks overlap in that window, and shutdown cannot mistake signal delivery for worker termination.

- Bootstrap failure ownership is now explicit: if `build_container()` raises after opening the primary SQLite connection but before publishing an `AppContainer`, it closes the connection and drops the connection-lock registry entry before re-raising. A regression forces a mid-composition repository-construction failure and proves the connection is closed.

- Release evidence now closes candidate identity at both ends of a run. Quick and full gates finish with a blocking `candidate_identity_audit.py` step that requires HEAD to still match the recorded start commit and the worktree to remain clean; tests cover both worktree mutation and HEAD movement.

- The first post-audit quick gate exposed a compatibility seam in Agents screen construction: standalone/test view-models without an injected `lineage_state_path` must continue using `AtomicLineageStateStore()` with its default/fake factory contract, while production composition passes the explicit workspace path. The constructor now branches on path presence instead of always passing `None`.

- Real-model release acceptance exposed that the documented Qwen3.5-0.8B default declares `Qwen3_5ForConditionalGeneration` while PTL forced inference and Training through `AutoModelForCausalLM`. Both paths now share an architecture-aware Transformers runtime selector, keep `trust_remote_code=False`, distinguish missing ML extras/runtime incompatibility/OOM, and the UI model check requires runtime compatibility in addition to file presence.
- Automation is no longer only a host-process launcher. Production composition now exposes reserved `ptl_internal` built-in actions over the same live application services for model probe/generation, Profile/Dataset lifecycle, Training, ModelVersion, Big Five, state snapshots and clean-workspace full acceptance; workspace manifests cannot opt into this internal capability.
- ModelVersion publication moved from `TrainingViewModel` into `TrainingService`, so successful Training has the same artifact/version lifecycle when launched from UI, Automation or another application caller.
