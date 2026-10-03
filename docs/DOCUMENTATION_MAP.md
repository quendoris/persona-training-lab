# Persona Training Lab — Documentation Coverage Map

> **Branch audited:** `agent/history-keyguard-poller`
>
> **Frozen clean scale baseline:** `69ef4d28013d1ae666a73bcbe2470ae257bcf3ee`
>
> **Latest clean quick-gate evidence:** `39d25de13568571a019992fe84ec8a616b6e7048` — `603 passed ×3`
>
> This file is a maintenance map, not a second source of product truth. Feature behavior remains authoritative in the linked user/operations/architecture/reference documents and ultimately in audited code/tests.

## 1. Why this map exists

Persona Training Lab has crossed the point where documentation can be maintained as an informal README plus a few feature notes. The repository now contains a desktop application, persistence layer, runtime-operation safety system, local-model and full-training paths, lineage/history machinery, evaluation/analysis, Automation, localization, telemetry, developer tooling, release evidence, and a growing research-methodology layer.

The documentation therefore has four separate jobs:

1. teach a user how to operate PTL without source-code knowledge;
2. let an operator recover or diagnose a real workspace safely;
3. state implementation contracts precisely enough for engineering/audit work;
4. preserve the distinction between **implemented v0.1.0 behavior** and **proposed research architecture**.

This map records coverage, remaining gaps, and documentation scale so that new work does not silently create undocumented subsystems.

## 2. Measured documentation and repository scale

The clean detached worktree at commit `69ef4d28013d1ae666a73bcbe2470ae257bcf3ee` reported:

| Category | Files | Physical lines | Nonblank lines | Python code lines |
|---|---:|---:|---:|---:|
| Production Python | 323 | 44,726 | 39,976 | 39,737 |
| Tests Python | 135 | 24,033 | 20,074 | 20,145 |
| Tools Python | 6 | 2,123 | 1,897 | 1,897 |
| Documentation | 60 | 25,681 | 17,196 | — |
| SVG assets | 13 | 41 | 41 | — |
| Configuration | 82 | 7,004 | 6,963 | — |
| Other text | 2 | 213 | 195 | — |
| **Tracked text total** | **621** | **103,821** | **86,342** | — |
| **All Python** | **464** | **70,882** | **61,947** | **61,779** |

The test-to-production ratio under the token-aware Python-code definition is approximately:

```text
20,145 / 39,737 ≈ 0.507
```

The baseline was measured from a clean detached worktree with `Dirty: no`, so those numbers are reproducibly tied to that exact commit.

The frozen table above remains the historical scale comparison point. A later clean detached quick-gate run at `39d25de13568571a019992fe84ec8a616b6e7048` measured **639 tracked text files**, **110,810 physical lines**, **63,182 Python code lines**, **40,006 Production Python code lines**, **21,034 Tests Python code lines**, and **71 documentation files / 30,979 documentation physical lines**. Those current-candidate numbers are evidence for that exact commit only; final release statistics must be regenerated after the documentation/code audit stabilizes.

For methodology, interpretation limits and regeneration commands, use [System scale and measured codebase anatomy](architecture/system-scale.md).

The useful scale statement is now evidence-backed rather than approximate:

> **At the frozen clean baseline, PTL already exceeded 103 thousand tracked physical text lines and contained about 61.8 thousand measured Python code lines, while its tracked documentation alone exceeded 25 thousand physical lines.**

## 3. Status legend

- **A — audited/current:** behavior has a dedicated current document and has already received code/test consistency review.
- **B — covered/current:** behavior is documented, but final cross-document consistency, screenshots, or edge-case review remains.
- **C — distributed coverage:** behavior exists in several cross-cutting documents but lacks one dedicated authoritative page.
- **R — research/proposed:** mathematically or architecturally specified future research capability; not claimed as current v0.1.0 instrumentation.
- **H — historical:** retained as project history; must not override current docs.
- **G — gap:** dedicated documentation is still needed or current coverage is too indirect for a project of this size.

### Current coverage snapshot

Across the explicit coverage-table rows in this map, the current state is:

| Status | Rows | Share of implemented/current rows |
|---|---:|---:|
| **A — audited/current** | **40** | **100.0%** |
| **B — covered/current** | **0** | **0.0%** |
| **C — distributed coverage** | **0** | **0.0%** |
| **R — research/proposed** | **2** | separate from the implemented/current denominator |

There are **40 implemented/current rows** (`A+B+C`) and two intentionally proposed research rows. Therefore:

```text
strictly audited/closed now:      40 / 40 = 100.0%
current coverage at least B:      40 / 40 = 100.0%
still distributed current scope:   0 / 40 =   0.0%
research/proposed:                  2 rows, not counted as v0.1.0 closure debt
```

The 100.0% implementation/documentation coverage figure must not be reported as “100% release complete”. Research/proposed rows are tracked separately, and final full-gate, visual, package-install and release-artifact evidence remain outstanding. For this map, **A is the strict code/test/document consistency closure count**, not the release tag.

## 3.1 Current closure mind map

The coverage tables reduce to this current implementation/documentation state:

```text
PTL v0.1.0 documentation/code audit
├── strictly audited/current (A): 40 / 40 implemented rows = 100.0%
├── covered/current but not strictly closed (B): 0 / 40 = 0.0%
├── distributed current coverage (C): 0 / 40 = 0.0%
└── proposed research architecture (R): 2 rows, outside v0.1.0 closure denominator
    ├── Training Dynamics mathematics
    └── Training Dynamics instrumentation
```

All **40 implemented/current rows are now A** at the code/test/document-consistency level. The previously pending Agents projection-publication, Telemetry background-lifecycle, and staged Training-artifact publication regressions were executed locally and are also present in the quick manifest. The clean `39d25de...` quick gate then exercised the curated inventory three times with **603 passed in each run**.

There is therefore no remaining P0 item whose only missing step is “execute the already-written regression”. The remaining work is a final **crack audit + freeze-evidence pass**: continue looking for code/document contract mismatches, repair only concrete findings, then produce fresh quick/full-gate, visual, packaging/install and final release evidence. The release gate now checks candidate identity at both start and completion so evidence cannot silently follow a moving HEAD/worktree.

## 4. User-facing workflow coverage

| Surface | Status | Current authority | Remaining work |
|---|---|---|---|
| Getting started / first launch | A | `user-guide/getting-started.md`, `quickstart.md`, `development/setup.md` | source launch/dependency/workspace/UI-scale instructions audited against `pyproject.toml`, bootstrap and path code; final screenshots remain P2 evidence |
| Interface shell / navigation | A | `user-guide/interface-tour.md`, `architecture/ui-shell.md` | twelve-workspace registry, sidebar navigation, dock topology, leave guards, stable RTL geometry and status synchronization audited against current shell code; screenshots remain P2 evidence |
| Profiles | A | `user-guide/profiles.md`, profile service/repository/viewmodel tests | required fields, normalization limits, IDs, `ready` persistence and Training handoff audited against current code/tests; dedicated schema page remains optional |
| Datasets | A | `user-guide/datasets.md`, `training_pipeline.md` | final import/validation examples and screenshots |
| Training | A | `user-guide/training.md`, `training_pipeline.md` | reconcile future dynamics instrumentation with current v0.1.0 boundaries |
| Model versions / Snapshots | A | `user-guide/snapshots.md`, `architecture/provenance-and-external-state.md` | registry/artifact/base-model provenance boundaries audited against current service/tests; final screenshot pass remains |
| Agents lineage | A | `user-guide/agents-lineage.md`, `architecture/agents-lineage.md`, `architecture/agents-protected-history.md` | safety-first projection/resource-link publication and protected history are implemented, documented and executed in the quick-gate inventory; continue only concrete remaining race/provenance findings |
| Tests / Analysis | A | `user-guide/tests-and-analysis.md`, `reference/evaluation-contract.md` | screenshots; future bridge to richer training-dynamics evidence |
| Automation | A | `user-guide/automation.md`, `architecture/automation.md`, `reference/automation-recipe-schema.md` | review-to-run semantic identity now fails closed with `recipe_stale`; targeted pytest/Ruff/i18n evidence exists; final clean-gate/visual pass remains |
| Appearance / language | A | `user-guide/appearance-and-language.md`, `architecture/localization.md`, `architecture/preference-persistence.md` | strict `#RRGGBB` custom-accent write validation is implemented and targeted-tested; final visual/release pass remains |
| Key bindings / gestures | A | `user-guide/key-bindings.md`, `reference/keyboard-mouse-bindings.md`, `architecture/preference-persistence.md` | current user-global persistence/concurrency boundary is explicit; revisit only if multi-workspace processes become supported |
| In-app Docs workspace | A | `user-guide/documentation.md`, `development/documentation-runtime.md` | visual examples; rendered-Markdown remains explicitly non-current |
| Dashboard / Projects overview | A | `user-guide/dashboard.md`, `user-guide/interface-tour.md`, Dashboard service/viewmodel tests | Dashboard is documented as read-only workflow aggregation/routing; `projects` is explicitly a read-only compatibility/fallback source, not a current CRUD workspace |
| Telemetry | A | `user-guide/telemetry.md`, `architecture/telemetry.md`, troubleshooting | owned background collection, service/provider failure isolation and shell-shutdown participation are documented and exercised by the current quick-gate inventory; final native visual/release evidence remains |
| Operations Center / Issues / Activity | A | `user-guide/operations-center.md`, `interface-tour.md`, `troubleshooting.md`, `ui-shell.md`, `reference/event-and-diagnostic-schema.md` | dedicated operator contract now covers source projection, refresh cadence, filtering/deduplication, routing, correlation identity and failure/privacy boundaries |

## 5. Operations coverage

| Topic | Status | Authority | Remaining work |
|---|---|---|---|
| Workspace and path ownership | A | `operations/workspace-and-storage.md`, `reference/workspace-layout.md`, `architecture/workspace-concurrency.md` | keep single-writer ownership synchronized with bootstrap/recovery changes |
| Local models | A | `operations/local-models.md` | record stronger base-model content provenance if implementation gains it |
| Troubleshooting / evidence preservation | A | `operations/troubleshooting.md`, `reference/event-and-diagnostic-schema.md`, `architecture/agents-protected-history.md` | protected-history blocker/subtree/identity outcomes synchronized; continue adding concrete recovery classes discovered during audit |
| Backup / reset / recovery | A | `operations/backup-reset-recovery.md`, `architecture/agents-protected-history.md` | same-snapshot Agents pair and fail-closed mixed-generation behavior synchronized; keep aligned with future lineage changes |
| Security / trust / privacy | A | `operations/security-boundaries.md`, `reference/event-and-diagnostic-schema.md` | re-audit every new diagnostics/research artifact before release |
| Runtime-operation leases | A | `architecture/runtime-resource-safety.md`, `architecture/workspace-concurrency.md`, troubleshooting | protected-history exact identity now distinguishes lease ownership from historical identity; document new resource kinds introduced by future instrumentation |
| Background shutdown / ownership handoff | A | `architecture/background-work-lifecycle.md`, `architecture/workspace-concurrency.md` | keep every new long-running workspace integrated with shell final-drain ownership |
| UI/input preference restore scope | A | `architecture/preference-persistence.md`, backup/storage docs | QSettings and user-home bindings remain intentionally outside whole-workspace backup semantics |
| Export / portability | A | `operations/export-portability.md`, `operations/backup-reset-recovery.md`, `reference/workspace-layout.md`, `architecture/provenance-and-external-state.md` | current negative contract is explicit: `exports/` is user-facing workspace output, whole-workspace copy is backup rather than normalized export, and no general import/migration bundle is claimed |

## 6. Architecture coverage

| Subsystem | Status | Authority | Remaining work |
|---|---|---|---|
| System composition / layers | A | `architecture/overview.md` | final top-down consistency pass against composition root |
| System scale / anatomy | A | `architecture/system-scale.md` | regenerate exact metrics for final clean release candidate; compare history only with compatible counting rules |
| Persistence | A | `architecture/persistence.md`, `reference/persistence-schema.md`, `architecture/provenance-and-external-state.md` | protected-history/projection-link boundaries and cross-cutting provenance strengths are synchronized; continue remaining transaction/race audit |
| Workspace concurrency / writer ownership | A | `architecture/workspace-concurrency.md`, `architecture/preference-persistence.md` | workspace writer model and external preference-store boundary are separated; keep synchronized if process model changes |
| Preference persistence / scope | A | `architecture/preference-persistence.md` | SQLite Style, QSettings shell state and user-home bindings have explicit scope/write/backup limits; no rationale invented for current placement |
| Background work / shutdown ownership | A | `architecture/background-work-lifecycle.md` | current QThread/runtime-operation/workspace-lease roles are separated; re-audit every new long-running feature |
| UI shell / lifecycle | A | `architecture/ui-shell.md`, `architecture/background-work-lifecycle.md`, `architecture/preference-persistence.md` | final screenshot-independent diagrams and cross-document consistency pass |
| Agents lineage | A | `architecture/agents-lineage.md`, `architecture/agents-protected-history.md` | exact protected-history identity/TOCTOU is complete; new semantic projections now reconcile safety links before publication and local redraws use only the accepted projection; execute the new regression tranche and continue remaining cross-store race review |
| Runtime resource safety | A | `architecture/runtime-resource-safety.md`, `architecture/workspace-concurrency.md`, `architecture/agents-protected-history.md` | primary delete/create-Undo/delete-Redo pre/post-lease identity rules synchronized; continue audit of any other destructive resource paths |
| Automation | A | `architecture/automation.md`, `reference/automation-recipe-schema.md` | mutable manifest review-to-run identity is now bound by a semantic SHA-256 expectation and fails closed before lease/process launch; transitive executable provenance remains explicitly outside this guarantee |
| Localization | A | `architecture/localization.md` | no major gap currently |
| Evaluation / Analysis | A | `architecture/evaluation-analysis.md`, `reference/evaluation-contract.md`, `user-guide/tests-and-analysis.md` | execution ownership, QThread/runtime separation, exact model-version scoping, persisted portrait evidence, protocol guard and compatibility `analysis_results` boundary are now consolidated; future richer evidence remains in Training Dynamics R docs |
| Training implementation | A | `training_pipeline.md`, `architecture/provenance-and-external-state.md` | current backend is full-parameter training; staged artifact publication is implemented, documented and exercised by the current quick-gate inventory; avoid projecting proposed dynamics math onto current v0.1.0 behavior |
| Training Dynamics mathematics | R | `architecture/training-dynamics-mathematics.md` | sources/derivations and implementation design can continue to grow without claiming runtime support |
| Training Dynamics instrumentation | R | `architecture/training-dynamics-instrumentation.md` | define artifact schema, sampling tiers, structural signatures, probe battery, storage cost budget |
| Telemetry architecture | A | `architecture/telemetry.md`, `architecture/background-work-lifecycle.md`, troubleshooting, telemetry code/tests | provider/service/snapshot/panel contract includes off-GUI-thread collection and dock-owner shutdown integration and is exercised by the current quick-gate inventory |
| `WorkflowSupervisor` abstraction | A | `architecture/background-work-lifecycle.md`, audited `application/workflows/*` | current role is only a small in-memory state registry; do not describe it as worker/runtime authority; decide later whether naming/scaffolding should remain |
| Error reporting/event log | A | `reference/event-and-diagnostic-schema.md`, troubleshooting/security/persistence | payload, dedup, rotation, Operations Center projection and privacy limits have one authority |

## 7. Machine/reference coverage

Already strong:

- `reference/v1-product-contract.md` — release-level guarantees and non-goals;
- `reference/evaluation-contract.md` — evaluation battery, scoring, serialized results, protocol comparability;
- `reference/statuses-and-identifiers.md` — states, codes, identifiers, compatibility aliases;
- `reference/workspace-layout.md` — persistence surfaces and path ownership;
- `reference/keyboard-mouse-bindings.md` — binding IDs/defaults/semantics;
- `reference/persistence-schema.md` — exact current SQLite tables, columns, indexes, foreign-key boundaries and additive bootstrap rules;
- `reference/event-and-diagnostic-schema.md` — reporter/event payloads, IDs, duplicate windows, rotating-log contract, Operations Center projection and evidence/privacy limits;
- `reference/automation-recipe-schema.md` — exact manifest fields, validation, placeholders, resource semantics, discovery/import and review-to-run boundaries.

The remaining high-value machine-reference addition is a **Training Dynamics artifact/schema reference**, but only once instrumentation leaves proposed status and real artifacts exist. Until then, the proposed instrumentation document remains the correct home.

## 8. Development/release coverage

The developer layer is largely complete:

- setup;
- testing and audit layers;
- tooling inventory;
- runtime documentation architecture;
- visual audit;
- packaging;
- release process.

`tools/codebase_stats.py` makes measurement provenance explicit: human and JSON output identify repository root, branch, full/short commit, upstream and dirty state; untracked files remain outside `git ls-files` statistics but are reported in provenance. The clean `69ef4d28...` run provides the frozen scale baseline instead of an estimate.

The current branch has fresh **quick-gate** evidence at `39d25de13568571a019992fe84ec8a616b6e7048`: compileall PASS, Ruff PASS, typing audit PASS with zero blocking findings, **603 pytest passes ×3**, i18n audit PASS with zero UI literals/missing references, docs audit PASS, and clean codebase statistics. This is still not the final release proof because full mypy/build/package-audit, native visual review, installed-package acceptance and final-SHA evidence remain outstanding.

Targeted local evidence supplied for commit `015952d669802fe8234432b78edd7149f8c5b2bb` established a narrower checkpoint for the Automation review-identity + strict custom-accent tranche:

```text
targeted pytest: 74 passed
targeted Ruff:    All checks passed
i18n audit:       PASS
catalog keys:     1518
referenced keys:  1449
hard-coded UI literals: 0
```

The supplied typing-audit output showed the known informational suppression inventory, but the captured image did not expose its final summary line; this map therefore does not promote that screenshot into a fresh full typing/release claim. Later Telemetry documentation/test commits also move HEAD beyond `015952d...`, so the targeted checkpoint is evidence for those two tranches, **not** current-HEAD release evidence.

Remaining work is predominantly **final-candidate audit/evidence population**, not missing broad feature prose:

- continue the code-vs-document crack audit and repair only concrete mismatches;
- run the **full** release gate on the clean final candidate after documentation stabilizes;
- regenerate final codebase statistics and compare them with the frozen `69ef4d28...` baseline and the intermediate `39d25de...` candidate;
- run automatic and native/manual visual audit on controlled/demo state;
- execute the full-gate built-package audit and install the resulting wheel into a clean environment;
- verify links and bundled in-application docs after final documentation changes;
- replace screenshot plans with reproducible captures where spatial understanding matters.

## 9. Research/methodology coverage

Current research documents:

- `experiment_protocol.md`;
- `methodology_limits.md`;
- `personality_portrait.md`;
- `reference/evaluation-contract.md`;
- `architecture/training-dynamics-mathematics.md`;
- `architecture/training-dynamics-instrumentation.md`.

This layer separates three epistemic levels:

```text
implemented measurement contract
        ≠
mathematical interpretation framework
        ≠
causal/mechanistic explanation
```

The next major research-documentation tasks are:

- formal checkpoint structural identity and cross-version correspondence;
- variable-dimensional model comparison rules;
- probe-set/versioning contract;
- intervention/replay design for causal claims;
- uncertainty/coverage reporting for every derived explanation;
- data-volume and compute-budget tiers for instrumentation.

## 10. Working context and historical material

`docs/context/` is **maintained working/handoff context**, not an authoritative architecture layer and no longer treated as wholly historical. It must summarize current canonical truth and stay subordinate to current code/tests plus the user/operations/architecture/reference/development contracts.

`docs/releases/` is mixed-purpose:

- `releases/v0.1.0-checklist.md` is a **live release-closure checklist** for the current candidate;
- older shell/architecture audit records are **H — historical** evidence.

Historical records remain useful for rationale recovery, chronology and forensic reconstruction, but they must not silently define current behavior. Before final documentation freeze, every cross-link into a historical record should be intentional and visibly historical.

## 11. Highest-priority remaining documentation work

### P0 — continue code-as-documentation crack audit

The three previously pending execution-only tranches are closed: Agents projection publication, Telemetry service/provider/background lifecycle, and staged Training artifact publication all have executed local evidence and are covered by the current quick inventory.

The remaining P0 rule is therefore narrower and stronger:

1. continue top-to-bottom code/document review for ownership, lifecycle, transactions, cross-store identity, error boundaries, persistence/provenance and packaging assumptions;
2. treat a discrepancy as a release blocker only when it is a concrete code/document/test contract conflict, not an aesthetic refactor opportunity;
3. turn every repaired crack into a regression or audit invariant before moving on;
4. keep proposed Training Dynamics mathematics/instrumentation at `R` until runtime code exists;
5. synchronize architecture, operator/recovery, machine-reference and hub/map surfaces after each correction.

The user-facing Telemetry gap is now closed to A. The guide is audited against the current panel/view-model/service/provider path and documents the 30-second visible timer, owned background refresh thread, shell shutdown participation, first-row NVIDIA-SMI limitation, process-sample scope, privacy boundary and non-research-evidence status; the corresponding service/provider/background-lifecycle regression tranche has now been executed.

The targeted current-only language pass across canonical root/user-guide/operations/architecture/reference/development docs is also closed. It found one stale current claim — the old unbound Automation review-to-run wording in `operations/workspace-and-storage.md` — which was corrected. Remaining `future` wording in the scanned hits is deliberate research/migration/constraint language, and the historical Agents home path is explicitly labelled non-v1. A broader final terminology/link/package audit remains P2 freeze work rather than an open P0 architecture seam.

The provenance pass then found a concrete Training publication seam rather than merely an overclaim: `LocalFullFineTuneBackend` previously wrote the final `<run_id>/model/` namespace before `training_metadata.json` was guaranteed to succeed. That allowed ordinary metadata-save failure to leave apparently final model bytes without an authoritative completed Training artifact. The backend now stages model, tokenizer, and metadata under a hidden same-parent directory and publishes the final run directory only after staging succeeds; ordinary exceptions best-effort clean the staging directory, existing final run directories are not overwritten, and abrupt process/host termination is still documented as capable of leaving **unpublished** staging debris. `tests/test_training_artifact_publication.py` is in the quick-test inventory and has now been executed successfully, including through the clean three-run quick gate.

The same pass re-read the current Training, Snapshots, Local Models, Workspace/Storage, Backup/Recovery, Security, Export/Portability, Automation and v1 product-contract claims for stronger-than-code provenance language. One user-facing Training sentence that said provenance “binds the artifact” was narrowed: PTL records the accepted Profile/Dataset identity alongside the artifact, but does not hash the complete trained artifact after publication. No additional current provenance claim in that audited set required a product-code change. Base-model bytes, post-publication artifact bytes and Automation transitive dependencies therefore remain deliberate path/external-provenance boundaries, not hidden P0 items.

This pass also closed the cross-cutting provenance documentation gap. `architecture/provenance-and-external-state.md` now separates content-pinned Profile/Dataset identity from path-only base-model/trained-artifact identity, transient Automation recipe review identity, and external transitive dependencies. During that audit, `operations/workspace-and-storage.md` was corrected so it no longer describes the already-fixed Automation review-to-run seam as unbound. Model versions / Snapshots are therefore promoted from B to A at the documentation/code-test-consistency level; this does not create complete artifact/base-model hashing that v0.1.0 does not implement.

Two P0 items that were still open in the previous revision are now **closed at targeted code/test/documentation level**:

```text
Automation recipe review-to-run identity
    reviewed semantic snapshot
        -> expected SHA-256 identity
        -> re-resolve current recipe
        -> mismatch => recipe_stale
        -> no runtime lease
        -> no process launch

Custom accent write validation
    exact #RRGGBB only
        -> canonical lowercase persisted custom value
    otherwise
        -> selected named accent
    legacy/external invalid persisted value
        -> renderer keeps defensive cyan fallback
```

The targeted `015952d...` local run reported 74 pytest passes, targeted Ruff success, and a passing i18n audit for the Automation/Style tranche. This is intentionally narrower than a current clean quick/full release gate.

The newer Agents projection-publication tranche is implemented, documented **and promoted to executed evidence**:

```text
worker builds coherent projection
        ↓
transactionally reconcile projection resource links
        │
        ├─ failure -> keep previous accepted UI generation
        │
        └─ success -> publish full/content projection
                       -> commit accepted revision

local branch/history redraw
        -> use screen accepted _real_projection
        -> never consume a newer unaccepted worker last_good directly
```

The dedicated regression file is `tests/test_lineage_projection_publish_safety.py`, is included in the quick-test inventory, and has been executed successfully as part of the current local evidence.

The most recent P0 protected-history tranche established and synchronized this rule:

```text
historical node ID alone
        ≠
proof of current safety identity

recorded/captured links
        ↓ exact check
fresh destructive lease
        ↓ exact check again
state/history mutation
```

It now applies to modern primary branch deletion, protected `branch_create_v1` Undo, and protected `branch_delete_v1` Redo. Protected deletion Undo separately requires empty current link slots before restoring the recorded identity. Mixed-generation `app.db` + `agents_lineage_state.json` recovery therefore fails closed rather than being silently merged.

The synchronized canonical set for that tranche is:

```text
architecture/agents-lineage.md
architecture/agents-protected-history.md
architecture/runtime-resource-safety.md
architecture/persistence.md
operations/troubleshooting.md
operations/backup-reset-recovery.md
docs/README.md
```

Two earlier P0 concurrency gaps are also closed at the documentation-contract level:

```text
child/background lifetime
    -> architecture/background-work-lifecycle.md

state outside workspace lease
    -> architecture/preference-persistence.md
```

The preference audit found no reason to invent a v0.1.0 migration: ordinary default-workspace desktop launches are already serialized by `WorkspaceOwnership`. It does establish a hard constraint for any future simultaneous different-workspace process model because QSettings and the home-relative binding file are user-level stores without a PTL interprocess CAS/transaction contract.

### P1 — consolidate current coverage without inventing product surface

There are no remaining status-C rows in the implemented/current map.

The two formerly distributed areas were closed deliberately:

```text
Operations Center
    -> dedicated user/operator contract

Dashboard / Projects
    -> dedicated Dashboard contract
    -> Projects explicitly documented as read-only compatibility/fallback state

Export / portability
    -> dedicated negative operating contract
    -> reserved exports path != implemented exporter/importer
```

Telemetry already has dedicated user + architecture semantics. Keep current operator telemetry separate from Training Dynamics until a versioned/persisted research-measurement contract actually exists.

Do not create additional standalone pages merely to increase a coverage percentage; add one only when a real user, operator, machine-reference, or architecture boundary would otherwise remain ambiguous.

### P2 — usability and evidence

1. reproducible screenshots;
2. diagrams where temporal/transaction order matters;
3. full Markdown-link validation;
4. runtime bundled-docs validation;
5. final terminology/status/path consistency pass;
6. final clean-candidate release-gate and codebase-statistics evidence.

### P3 — research architecture expansion

Continue the Training Dynamics research layer, but preserve `R` status until code exists. The next useful documents/specifications should describe:

- structural model manifests;
- correspondence/coverage between checkpoints with changing tensor sets or shapes;
- probe/evidence artifact schemas;
- mathematical uncertainty and epistemic labels;
- causal intervention experiment design.

## 12. Documentation freeze criterion

Documentation is ready for a v0.1.0 freeze only when all of the following are true:

1. every user-visible workspace has a discoverable operating path;
2. every destructive operation states its storage/runtime implications;
3. every persistent state surface appears in the storage/reference map;
4. every machine status/identifier used in user-visible evidence is defined;
5. architecture documents describe current code, not historical intent;
6. proposed research architecture is visibly separated from implemented behavior;
7. all internal links resolve;
8. screenshot plans have either been populated or explicitly removed as nonessential;
9. a clean current candidate has fresh release-gate and codebase-statistics evidence;
10. no known architecture problem is being hidden by documentation wording.

## 13. Scale in one sentence

PTL has reached the scale where its documentation has to be treated as an **engineered subsystem with its own architecture, consistency rules, provenance and release evidence**, not as prose appended after implementation.