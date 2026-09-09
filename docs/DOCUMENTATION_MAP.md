# Persona Training Lab — Documentation Coverage Map

> **Branch audited:** `agent/history-keyguard-poller`
>
> **Baseline HEAD when this map was created:** `3037a4587172173e3c904f6c7d95bfc1ee32ef98`
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

## 2. Current documentation scale

At the baseline above, `docs/` contains **54 Markdown documents**.

By role:

| Area | Documents | Approx. source size | Role |
|---|---:|---:|---|
| `docs/user-guide/` | 12 | 188 KB | end-user workflows |
| `docs/operations/` | 5 | 160 KB | storage, recovery, diagnostics, security, models |
| `docs/architecture/` | 9 | 211 KB | current architecture + proposed training-dynamics research architecture |
| `docs/reference/` | 5 | 98 KB | machine-level contracts |
| `docs/development/` | 7 | 57 KB | setup, tests, tooling, packaging, release, docs runtime |
| root methodology / runtime docs | 6 | 95 KB | quickstart, Training pipeline, experiment/methodology material, docs hub |
| `docs/context/` | 7 | 23 KB | historical/internal project context |
| `docs/releases/` | 3 | 21 KB | historical release/audit records |
| **Total** | **54** | **~852 KB** | documentation source only |

The repository itself is now on the order of **10^5 tracked physical text lines**. The last locally observed integration statistics were already near that scale before the newest documentation and lineage-safety work. Exact line counts must be regenerated on a clean checkout with `tools/codebase_stats.py`; this map intentionally does not turn an older dirty-worktree statistic into a false exact current number.

The useful scale statement is therefore:

> PTL is no longer a small application with supporting docs. It is a roughly hundred-thousand-line engineering/research system with a documentation corpus that is itself approaching one megabyte of authored Markdown.

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
| Automation | A | `user-guide/automation.md`, `architecture/automation.md` | dedicated recipe-schema reference would reduce duplication |
| Appearance / language | A | `user-guide/appearance-and-language.md`, `architecture/localization.md` | custom accent validation remains a known code seam; re-check if fixed |
| Key bindings / gestures | A | `user-guide/key-bindings.md`, `reference/keyboard-mouse-bindings.md` | decide whether user-global storage is intentional architecture or migration debt |
| In-app Docs workspace | A | `user-guide/documentation.md`, `development/documentation-runtime.md` | visual examples; rendered-Markdown remains explicitly non-current |
| Dashboard / Projects overview | C | `user-guide/interface-tour.md`, service/viewmodel docs indirectly | **G:** dedicated user workflow if Projects/Dashboard becomes more than orientation |
| Telemetry | C | `interface-tour.md`, `ui-shell.md`, troubleshooting | **G:** dedicated telemetry semantics/limitations if used as research evidence |
| Operations Center / Issues / Activity | C | `interface-tour.md`, `troubleshooting.md`, `ui-shell.md` | **G:** one operator-facing contract for retention, ordering, identities, and failure meanings |

## 5. Operations coverage

| Topic | Status | Authority | Remaining work |
|---|---|---|---|
| Workspace and path ownership | A | `operations/workspace-and-storage.md`, `reference/workspace-layout.md` | final consistency pass after any new research artifact roots are introduced |
| Local models | A | `operations/local-models.md` | record stronger base-model content provenance if implementation gains it |
| Troubleshooting / evidence preservation | A | `operations/troubleshooting.md` | continue adding concrete recovery classes discovered during architecture audit |
| Backup / reset / recovery | A | `operations/backup-reset-recovery.md` | keep Agents JSON ↔ SQLite same-snapshot rules synchronized with lineage changes |
| Security / trust / privacy | A | `operations/security-boundaries.md` | re-audit every new diagnostics/research artifact before release |
| Runtime-operation leases | A | `architecture/runtime-resource-safety.md`, troubleshooting | document any new resource kinds introduced by Training Dynamics instrumentation |
| Export / portability | C | storage + backup docs | **G:** dedicated export/portability contract if PTL adds supported workspace migration/export rather than raw backup |

## 6. Architecture coverage

| Subsystem | Status | Authority | Remaining work |
|---|---|---|---|
| System composition / layers | A | `architecture/overview.md` | final top-down consistency pass against composition root |
| Persistence | A | `architecture/persistence.md` | continue transaction/race audit; add schema-level reference if useful |
| UI shell / lifecycle | A | `architecture/ui-shell.md` | final worker/close-guard audit and screenshot-independent diagrams |
| Agents lineage | A | `architecture/agents-lineage.md` | current highest-priority architecture audit area |
| Runtime resource safety | A | `architecture/runtime-resource-safety.md` | verify cross-connection and multi-process assumptions explicitly |
| Automation | A | `architecture/automation.md` | recipe schema reference; keep trust boundary explicit |
| Localization | A | `architecture/localization.md` | no major gap currently |
| Evaluation / Analysis | B | `reference/evaluation-contract.md`, methodology docs | optional dedicated architecture page only if orchestration becomes more complex |
| Training implementation | A | `training_pipeline.md` | current backend is simple full-parameter SGD; avoid projecting proposed math onto v1.0 behavior |
| Training Dynamics mathematics | R | `architecture/training-dynamics-mathematics.md` | sources/derivations and implementation design can continue to grow without claiming runtime support |
| Training Dynamics instrumentation | R | `architecture/training-dynamics-instrumentation.md` | define artifact schema, sampling tiers, structural signatures, probe battery, storage cost budget |
| Telemetry architecture | C | shell/troubleshooting + telemetry code | **G:** dedicated page if telemetry feeds future research analysis |
| Workflow supervision/background jobs | C | `ui-shell.md`, runtime safety docs | **G:** dedicated lifecycle/state-machine contract may be justified |
| Error reporting/event log | C | troubleshooting/security/persistence | **G:** dedicated event/evidence architecture would improve auditability |

## 7. Machine/reference coverage

Already strong:

- `reference/v1-product-contract.md` — release-level guarantees and non-goals;
- `reference/evaluation-contract.md` — evaluation battery, scoring, serialized results, protocol comparability;
- `reference/statuses-and-identifiers.md` — states, codes, identifiers, compatibility aliases;
- `reference/workspace-layout.md` — persistence surfaces and path ownership;
- `reference/keyboard-mouse-bindings.md` — binding IDs/defaults/semantics.

High-value additions:

1. **`reference/persistence-schema.md`** — tables, primary keys, critical indexes, compatibility columns, ownership and migration/bootstrap rules. `architecture/persistence.md` should remain conceptual; the reference should be mechanical.
2. **`reference/automation-recipe-schema.md`** — exact recipe fields, types, defaults, validation, execution mode, trust implications.
3. **`reference/event-and-diagnostic-schema.md`** — event log fields, error IDs, correlation/causation IDs, redaction boundary, retention/ordering semantics.
4. **Training Dynamics artifact/schema reference** once instrumentation leaves proposed status.

## 8. Development/release coverage

The developer layer is largely complete:

- setup;
- testing and audit layers;
- tooling inventory;
- runtime documentation architecture;
- visual audit;
- packaging;
- release process.

Remaining work is predominantly **evidence population**, not missing prose:

- run release gate on a clean current candidate;
- record exact current codebase statistics;
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

This layer now separates three epistemic levels:

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

Current historical corpus:

- 7 context/handoff/working-rule documents;
- 3 old release/audit documents.

Before final documentation freeze, every cross-link from canonical docs into historical material should be intentional and visibly labelled historical.

## 11. Highest-priority remaining documentation work

### P0 — continue code-as-documentation architecture audit

1. Finish the current Agents runtime-link/history transaction audit.
2. Re-check persistence/race semantics across separate SQLite connections and possible multiple PTL processes.
3. Synchronize `agents-lineage`, `runtime-resource-safety`, `persistence`, troubleshooting and backup docs after every safety correction.
4. Re-run full current-only language search for stale `planned`, `future`, old statuses, old paths, and obsolete migration wording.

### P1 — close dedicated reference gaps

1. persistence schema reference;
2. event/error/diagnostic schema reference;
3. Automation recipe schema reference;
4. operator-facing Operations Center semantics if the current distributed coverage proves too hard to use.

### P2 — usability and evidence

1. reproducible screenshots;
2. diagrams where temporal/transaction order matters;
3. full Markdown-link validation;
4. runtime bundled-docs validation;
5. final terminology/status/path consistency pass;
6. clean-candidate codebase statistics and release evidence.

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

PTL has reached the scale where its documentation has to be treated as an **engineered subsystem with its own architecture, consistency rules, provenance and release gate**, not as prose appended after implementation.
