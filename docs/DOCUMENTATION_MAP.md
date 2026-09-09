# Persona Training Lab — Documentation Coverage Map

> **Branch audited:** `agent/history-keyguard-poller`
>
> **Frozen clean scale baseline:** `69ef4d28013d1ae666a73bcbe2470ae257bcf3ee`
>
> This file is a maintenance map, not a second source of product truth. Feature behavior remains authoritative in the linked user/operations/architecture/reference documents and ultimately in audited code/tests.

## 1. Why this map exists

Persona Training Lab has crossed the point where documentation can be maintained as an informal README plus a few feature notes. The repository now contains a desktop application, persistence layer, runtime-operation safety system, local-model and full-training paths, lineage/history machinery, evaluation/analysis, Automation, localization, telemetry, developer tooling, release evidence, and a growing research-methodology layer.

The documentation therefore has four separate jobs:

1. teach a user how to operate PTL without source-code knowledge;
2. let an operator recover or diagnose a real workspace safely;
3. state implementation contracts precisely enough for engineering/audit work;
4. preserve the distinction between **implemented v1.0 behavior** and **proposed research architecture**.

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

The current branch already contains documentation commits after that frozen baseline, including `architecture/system-scale.md`, `architecture/background-work-lifecycle.md`, and `architecture/preference-persistence.md`. Therefore the table above is intentionally **not relabelled as the live HEAD size**. Exact final-candidate counts must be regenerated after the documentation/code audit stabilizes.

For methodology, interpretation limits and regeneration commands, use [System scale and measured codebase anatomy](architecture/system-scale.md).

The useful scale statement is now evidence-backed rather than approximate:

> **At the frozen clean baseline, PTL already exceeded 103 thousand tracked physical text lines and contained about 61.8 thousand measured Python code lines, while its tracked documentation alone exceeded 25 thousand physical lines.**

## 3. Status legend

- **A — audited/current:** behavior has a dedicated current document and has already received code/test consistency review.
- **B — covered/current:** behavior is documented, but final cross-document consistency, screenshots, or edge-case review remains.
- **C — distributed coverage:** behavior exists in several cross-cutting documents but lacks one dedicated authoritative page.
- **R — research/proposed:** mathematically or architecturally specified future research capability; not claimed as current v1.0 instrumentation.
- **H — historical:** retained as project history; must not override current docs.
- **G — gap:** dedicated documentation is still needed or current coverage is too indirect for a project of this size.

## 4. User-facing workflow coverage

| Surface | Status | Current authority | Remaining work |
|---|---|---|---|
| Getting started / first launch | B | `user-guide/getting-started.md`, `quickstart.md` | final screenshots; re-check commands against final release candidate |
| Interface shell / navigation | B | `user-guide/interface-tour.md`, `architecture/ui-shell.md` | screenshot population and final navigation consistency pass |
| Profiles | B | `user-guide/profiles.md` | add dedicated field/schema reference only if field set continues growing |
| Datasets | A | `user-guide/datasets.md`, `training_pipeline.md` | final import/validation examples and screenshots |
| Training | A | `user-guide/training.md`, `training_pipeline.md` | reconcile future dynamics instrumentation with current v1.0 boundaries |
| Model versions / Snapshots | B | `user-guide/snapshots.md` | stronger artifact/provenance examples; final lifecycle consistency review |
| Agents lineage | A | `user-guide/agents-lineage.md`, `architecture/agents-lineage.md` | continue auditing protected history and cross-store race/failure semantics |
| Tests / Analysis | A | `user-guide/tests-and-analysis.md`, `reference/evaluation-contract.md` | screenshots; future bridge to richer training-dynamics evidence |
| Automation | A | `user-guide/automation.md`, `architecture/automation.md`, `reference/automation-recipe-schema.md` | final consistency/visual pass; import collision behavior is fail-closed rather than overwrite |
| Appearance / language | A | `user-guide/appearance-and-language.md`, `architecture/localization.md`, `architecture/preference-persistence.md` | custom accent validation remains a known code seam; re-check if fixed |
| Key bindings / gestures | A | `user-guide/key-bindings.md`, `reference/keyboard-mouse-bindings.md`, `architecture/preference-persistence.md` | current user-global persistence/concurrency boundary is now explicit; revisit only if multi-workspace processes become supported |
| In-app Docs workspace | A | `user-guide/documentation.md`, `development/documentation-runtime.md` | visual examples; rendered-Markdown remains explicitly non-current |
| Dashboard / Projects overview | C | `user-guide/interface-tour.md`, service/viewmodel docs indirectly | **G:** dedicated user workflow if Projects/Dashboard becomes more than orientation |
| Telemetry | C | `interface-tour.md`, `ui-shell.md`, troubleshooting | **G:** dedicated telemetry semantics/limitations if used as research evidence |
| Operations Center / Issues / Activity | B | `interface-tour.md`, `troubleshooting.md`, `ui-shell.md`, `reference/event-and-diagnostic-schema.md` | operator workflow is mechanically specified; dedicated page remains optional if navigation proves unclear |

## 5. Operations coverage

| Topic | Status | Authority | Remaining work |
|---|---|---|---|
| Workspace and path ownership | A | `operations/workspace-and-storage.md`, `reference/workspace-layout.md`, `architecture/workspace-concurrency.md` | keep single-writer ownership synchronized with bootstrap/recovery changes |
| Local models | A | `operations/local-models.md` | record stronger base-model content provenance if implementation gains it |
| Troubleshooting / evidence preservation | A | `operations/troubleshooting.md`, `reference/event-and-diagnostic-schema.md` | continue adding concrete recovery classes discovered during architecture audit |
| Backup / reset / recovery | A | `operations/backup-reset-recovery.md` | keep Agents JSON ↔ SQLite same-snapshot and offline-owner rules synchronized with lineage changes |
| Security / trust / privacy | A | `operations/security-boundaries.md`, `reference/event-and-diagnostic-schema.md` | re-audit every new diagnostics/research artifact before release |
| Runtime-operation leases | A | `architecture/runtime-resource-safety.md`, `architecture/workspace-concurrency.md`, troubleshooting | preserve distinction between SQLite claims and the outer desktop writer lease; document new resource kinds introduced by future instrumentation |
| Background shutdown / ownership handoff | A | `architecture/background-work-lifecycle.md`, `architecture/workspace-concurrency.md` | keep every new long-running workspace integrated with shell final-drain ownership |
| UI/input preference restore scope | A | `architecture/preference-persistence.md`, backup/storage docs | QSettings and user-home bindings remain intentionally outside whole-workspace backup semantics |
| Export / portability | C | storage + backup docs | **G:** dedicated export/portability contract if PTL adds supported workspace migration/export rather than raw backup |

## 6. Architecture coverage

| Subsystem | Status | Authority | Remaining work |
|---|---|---|---|
| System composition / layers | A | `architecture/overview.md` | final top-down consistency pass against composition root |
| System scale / anatomy | A | `architecture/system-scale.md` | regenerate exact metrics for final clean release candidate; compare history only with compatible counting rules |
| Persistence | A | `architecture/persistence.md`, `reference/persistence-schema.md` | continue transaction/race audit; schema mechanics have a dedicated reference |
| Workspace concurrency / writer ownership | A | `architecture/workspace-concurrency.md`, `architecture/preference-persistence.md` | workspace writer model and external preference-store boundary are now separated; keep synchronized if process model changes |
| Preference persistence / scope | A | `architecture/preference-persistence.md` | SQLite Style, QSettings shell state and user-home bindings have explicit scope/write/backup limits; no rationale invented for current placement |
| Background work / shutdown ownership | A | `architecture/background-work-lifecycle.md` | current QThread/runtime-operation/workspace-lease roles are separated; re-audit every new long-running feature |
| UI shell / lifecycle | A | `architecture/ui-shell.md`, `architecture/background-work-lifecycle.md`, `architecture/preference-persistence.md` | final screenshot-independent diagrams and cross-document consistency pass |
| Agents lineage | A | `architecture/agents-lineage.md` | current highest-priority cross-store audit area |
| Runtime resource safety | A | `architecture/runtime-resource-safety.md`, `architecture/workspace-concurrency.md` | immediate SQLite claims remain atomic; standard desktop multi-writer workspace access is fail-closed at bootstrap |
| Automation | A | `architecture/automation.md`, `reference/automation-recipe-schema.md` | manifest contract is mechanical; continue trust/review-to-run audit |
| Localization | A | `architecture/localization.md` | no major gap currently |
| Evaluation / Analysis | B | `reference/evaluation-contract.md`, methodology docs | optional dedicated architecture page only if orchestration becomes more complex |
| Training implementation | A | `training_pipeline.md` | current backend is full-parameter training; avoid projecting proposed dynamics math onto current v1.0 behavior |
| Training Dynamics mathematics | R | `architecture/training-dynamics-mathematics.md` | sources/derivations and implementation design can continue to grow without claiming runtime support |
| Training Dynamics instrumentation | R | `architecture/training-dynamics-instrumentation.md` | define artifact schema, sampling tiers, structural signatures, probe battery, storage cost budget |
| Telemetry architecture | C | shell/troubleshooting + telemetry code | **G:** dedicated page before telemetry becomes research evidence |
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

`tools/codebase_stats.py` makes measurement provenance explicit: human and JSON output identify repository root, branch, full/short commit, upstream and dirty state; untracked files remain outside `git ls-files` statistics but are reported in provenance. The clean `69ef4d28...` run now provides a real frozen scale baseline instead of an estimate.

Remaining work is predominantly **final-candidate evidence population**, not missing prose:

- run release gate on a clean current candidate after the architecture/doc audit stabilizes;
- regenerate codebase statistics for that final candidate and compare them to the frozen `69ef4d28...` baseline;
- run visual audit on controlled/demo state;
- inspect packaged wheel contents;
- verify links and bundled docs after final documentation changes;
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

## 10. Historical material

`docs/context/` and `docs/releases/v0.*` are status **H**.

They are useful for rationale recovery, chronology, and forensic reconstruction. They are not allowed to silently define current behavior when they disagree with current code/tests/canonical docs.

Current historical corpus includes context/handoff/working-rule documents and old release/audit records. Before final documentation freeze, every cross-link from canonical docs into historical material should be intentional and visibly labelled historical.

## 11. Highest-priority remaining documentation work

### P0 — continue code-as-documentation architecture audit

1. Continue the Agents runtime-link/history transaction audit under the explicit single-writer workspace contract.
2. Synchronize `agents-lineage`, `runtime-resource-safety`, `persistence`, troubleshooting and backup docs after every safety correction.
3. Re-run full current-only language search for stale `planned`, `future`, old statuses, old paths, and obsolete migration wording.
4. Continue applying the same fail-closed review to mutable trusted execution/configuration surfaces such as Automation manifests.
5. Re-check known smaller seams (for example custom accent validation) rather than allowing documentation to normalize implementation drift.

Two previous P0 concurrency gaps are now explicitly closed at the documentation-contract level:

```text
child/background lifetime
    -> architecture/background-work-lifecycle.md

state outside workspace lease
    -> architecture/preference-persistence.md
```

The preference audit found no reason to invent a v1.0 migration: ordinary default-workspace desktop launches are already serialized by `WorkspaceOwnership`. It does establish a hard constraint for any future simultaneous different-workspace process model because QSettings and the home-relative binding file are user-level stores without a PTL interprocess CAS/transaction contract.

### P1 — close distributed coverage only where it improves use

1. operator-facing Operations Center page only if user testing shows the current interface-tour/troubleshooting/reference split is hard to navigate;
2. dedicated Telemetry architecture/semantics before telemetry is used as research evidence;
3. dedicated Dashboard/Projects workflow only if those surfaces become more than orientation/projection.

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

Documentation is ready for a v1.0 freeze only when all of the following are true:

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