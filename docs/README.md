# Persona Training Lab Documentation

This directory is the canonical documentation home for Persona Training Lab.

PTL documentation is organized by **reader intent**, not by source-code package. A new user should not need architecture knowledge to complete a workflow; an auditor should not need to reverse-engineer behavior from a tutorial.

For a maintained coverage/gap/scale view of the documentation corpus, see the [Documentation Coverage Map](DOCUMENTATION_MAP.md). For the frozen clean source-size measurement and counting methodology, see [System scale and measured codebase anatomy](architecture/system-scale.md).

## Start here

### I want to use PTL

Begin with:

- [Getting Started](user-guide/getting-started.md) — source-checkout installation, first launch, workspace, first-run orientation.
- [Interface Tour](user-guide/interface-tour.md) — shell, workspaces, Inspector, Activity, Telemetry, Issues, status bar, language/layout behavior.
- [Profiles](user-guide/profiles.md) — define the personality fields used by downstream Training.
- [Datasets](user-guide/datasets.md) — import/preview/validate/approve JSONL and understand approval SHA-256 semantics.
- [Training](user-guide/training.md) — create a run, understand input pinning, launch local full fine-tuning, inspect logs/artifacts/provenance.
- [Snapshots and model versions](user-guide/snapshots.md) — inspect registered model versions, understand lineage, artifact references, and the exact meaning of “snapshot” in v1.0.
- [Agents lineage](user-guide/agents-lineage.md) — read the integrated research graph, distinguish real persisted entities from local branches/placeholders, use protected history, and understand runtime-blocked deletion.
- [Tests and Analysis](user-guide/tests-and-analysis.md) — build a scored portrait, review actual model responses, understand factor KPI values, and compare protocol-compatible model versions.
- [Automation](user-guide/automation.md) — run trusted recipes/ad-hoc commands, understand authorization, runtime claims, timeout/cancel, bounded output, process containment, and audit/privacy boundaries.
- [Appearance & Language](user-guide/appearance-and-language.md) — themes, accents, custom accent behavior, live UI scale, locale switching, RTL text-direction policy, and persistence.
- [Key Bindings & Mouse Gestures](user-guide/key-bindings.md) — edit application navigation and Agents graph bindings, understand draft conflicts, persistence, reset, and current shortcut coverage.
- [Documentation Workspace](user-guide/documentation.md) — use the in-app five-topic documentation subset, understand plain-Markdown display, locale behavior, bundled/source resolution, and its boundary from the complete canonical docs tree.
- [v1.0 Product Contract](reference/v1-product-contract.md) — stable-release guarantees, trust/integrity boundaries, explicit non-goals.

### I operate or troubleshoot PTL

Start with:

- [Workspace & Storage](operations/workspace-and-storage.md) — platform paths, SQLite/filesystem ownership, external UI/settings stores, local models, Training artifacts, Agents local state, Automation recipes/audit, backup/reset.
- [Local Models](operations/local-models.md) — model path resolution, readiness checks, inference-stack health, smoke generation, Training integration, trust and reproducibility boundaries.
- [Troubleshooting & Diagnostic Evidence](operations/troubleshooting.md) — evidence-first triage, Issues/Activity/logs, runtime blockers, crash/orphan handling, subsystem failures, dirty/merged source trees, and release-gate diagnostics.
- [Backup, Reset & Recovery](operations/backup-reset-recovery.md) — whole-workspace backup/restore, external dependency/presentation-state preservation, crash/orphan recovery, partial reset/cleanup risks, and restore validation.
- [Security, Trust & Privacy Boundaries](operations/security-boundaries.md) — OS/workspace authority, storage privacy, model/Dataset trust, Automation consent/audit/process boundaries, logging/redaction limits, and source-integrity guarantees.
- [Key Bindings & Mouse Gestures](user-guide/key-bindings.md) — user-home binding storage, conflict recovery, direct capture, reset semantics, and live shell shortcut synchronization.
- [Documentation Workspace](user-guide/documentation.md) — distinguish a missing registered runtime topic from the normal absence of unregistered canonical documents in the in-app subset.
- [Statuses, Result Codes & Identifiers](reference/statuses-and-identifiers.md) — canonical states, action/diagnostic codes, event families, schema markers, ID shapes, and compatibility aliases.
- [Event and diagnostic schema](reference/event-and-diagnostic-schema.md) — event/error identity, payload and redaction boundaries, duplicate windows, rotating logs and Operations Center projection.
- [Agents lineage](user-guide/agents-lineage.md) — deletion blockers, protected undo/redo, stable identity, last-good projection behavior.
- [Automation](user-guide/automation.md) — recipe discovery/import, host-effect authorization, runtime blockers, output truncation, cancellation/timeout, audit failures, and safe operating rules.
- [Training pipeline specification](training_pipeline.md) — exact Training input transformation, hashes, backend, artifacts, failure/reproducibility boundaries.
- [Snapshots and model versions](user-guide/snapshots.md) — distinguish persisted model-version metadata from the referenced artifact and trace provenance back to a Training run.
- [Tests and Analysis](user-guide/tests-and-analysis.md) — evaluation prerequisites, result states, case review, exact lineage comparison, and operational error meanings.
- [Evaluation contract](reference/evaluation-contract.md) — exact battery, generation, persistence, scoring, comparability, and reproducibility semantics.
- [v1.0 Product Contract](reference/v1-product-contract.md) — security/runtime/integrity boundaries before operational changes.

The dedicated v1.0 operator guides cover workspace/storage, local models, troubleshooting, backup/reset/recovery, and security/trust/privacy boundaries. Feature-specific operating rules remain in their user/technical guides and are cross-linked rather than duplicated as competing contracts.

### I develop, audit, or extend PTL

Start with:

- [Architecture Overview](architecture/overview.md) — composition root, layers, UI shell, persistence, runtime coordination, models, Automation, telemetry, error boundaries.
- [System scale and measured codebase anatomy](architecture/system-scale.md) — frozen clean size baseline, counting methodology, test/production ratio and limits of LOC as a complexity measure.
- [Persistence architecture](architecture/persistence.md) — SQLite connection/transaction boundaries, repository locking, schema/bootstrap behavior, lineage snapshots, Agents JSON, filesystem artifacts, external state, and cross-store atomicity limits.
- [Workspace concurrency and ownership](architecture/workspace-concurrency.md) — single-writer workspace lease, in-process vs SQLite vs file-atomicity guarantees and preference-store boundary.
- [Background work lifecycle](architecture/background-work-lifecycle.md) — screen-owned QThreads, runtime-operation distinction, nonblocking close retry, final bootstrap drain and workspace-lease handoff.
- [SQLite persistence schema reference](reference/persistence-schema.md) — exact current tables, columns, indexes, foreign-key boundaries, additive compatibility bootstrap and schema-change audit rules.
- [UI shell architecture](architecture/ui-shell.md) — workspace ownership/guards, background shutdown, docks/panels, Operations Center integration, application shortcuts, QSettings/key-binding persistence, style/localization boundaries.
- [Agents lineage architecture](architecture/agents-lineage.md) — atomic semantic snapshot, projection/local-state split, stable IDs, runtime links, protected deletion history, guarded Redo, background last-good behavior.
- [Automation architecture](architecture/automation.md) — recipe schema/discovery, trusted-host command contract, runtime leases, audit fail-closed behavior, bounded process execution, process-tree containment, and explicit trust limitations.
- [Automation recipe schema](reference/automation-recipe-schema.md) — exact manifest fields, validation, placeholders, discovery/import collision behavior and resource-claim semantics.
- [Runtime resource safety](architecture/runtime-resource-safety.md) — shared-resource/operation safety contracts.
- [Localization architecture](architecture/localization.md) — catalog, RTL, font, and localization contracts.
- [Training pipeline specification](training_pipeline.md) — detailed Profile/Dataset fingerprints, Training parser/backend, artifact metadata, limitations.
- [Training Dynamics mathematics](architecture/training-dynamics-mathematics.md) — proposed mathematical language for parameter/function/representation/behavior trajectories, evidence levels and interpretation limits; not a claim of current v1.0 instrumentation.
- [Training Dynamics instrumentation](architecture/training-dynamics-instrumentation.md) — proposed sampling/artifact/structural-identity contract for turning that mathematical framework into future PTL evidence.
- [Statuses, Result Codes & Identifiers](reference/statuses-and-identifiers.md) — machine-semantic taxonomy, canonical domain/runtime states, result/diagnostic/event contracts, generated-ID formats and compatibility rules.
- [Event and diagnostic schema](reference/event-and-diagnostic-schema.md) — machine-level event/error payload, identity, persistence/projection and privacy boundaries.
- [Workspace layout reference](reference/workspace-layout.md) — exact persistence/path ownership including workspace, QSettings, user-home bindings and external inputs.
- [Keyboard & mouse bindings reference](reference/keyboard-mouse-bindings.md) — exact binding IDs/defaults and gesture semantics.
- [Snapshots and model versions](user-guide/snapshots.md) — current `model_versions` persistence semantics, derived lifecycle presentation, and provenance limits.
- [Evaluation contract](reference/evaluation-contract.md) — machine-level Tests/Analysis protocol, score parsing, persistence grammar, factor math, protocol-comparison guard.
- [Development setup](development/setup.md) — locked source environment, optional model stacks, launch/headless rules, clean-worktree release precondition.
- [Testing and engineering audits](development/testing.md) — pytest, compile, Ruff, mypy, typing/i18n audits, codebase statistics and quick/full release profiles.
- [Developer tooling](development/tooling.md) — exact `tools/` inventory, PTL-local release ownership, reusable extraction boundaries, and current `quendoris/snippets` relationship.
- [Runtime documentation architecture](development/documentation-runtime.md) — canonical-vs-runtime docs boundary, bundled root resolution, runtime topic registry, localization and plain-text rendering semantics.
- [Visual audit](development/visual-audit.md) — real-application automatic/interactive Qt capture, manifests, geometry, privacy and publication boundaries.
- [Packaging](development/packaging.md) — Hatchling/uv build contract, optional extras, bundled docs and current native-packaging non-goals.
- [Release process](development/release-process.md) — candidate identity, locked dependencies, release-gate evidence, visual review, package inspection and final-tag discipline.

## Current v1.0 documentation map

| Document | Audience | Purpose |
|---|---|---|
| [Documentation Coverage Map](DOCUMENTATION_MAP.md) | Developer / auditor / maintainer | Coverage status, known gaps, research/current separation and corpus scale |
| [Getting Started](user-guide/getting-started.md) | User | Install, launch, workspace, first-run orientation |
| [Interface Tour](user-guide/interface-tour.md) | User | Shell/workspace map and supporting panels |
| [Profiles](user-guide/profiles.md) | User | Create/edit personality definitions |
| [Datasets](user-guide/datasets.md) | User / operator | JSONL structure, validation, approval fingerprints, Training eligibility |
| [Training](user-guide/training.md) | User / operator | End-to-end Training workflow and safe operating rules |
| [Snapshots and model versions](user-guide/snapshots.md) | User / operator / auditor | Model-version registry, lineage, artifact references, lifecycle projection, reproducibility boundary |
| [Agents lineage](user-guide/agents-lineage.md) | User / operator / researcher | Integrated lineage workflow, custom branches, protected history, runtime deletion safety, screenshot plan |
| [Tests and Analysis](user-guide/tests-and-analysis.md) | User / operator / researcher | Portrait execution, case review, KPI interpretation, exact version comparison, screenshot plan |
| [Automation](user-guide/automation.md) | User / operator / auditor | Trusted-host recipes/ad-hoc commands, authorization, claims, process/output containment, audit/privacy, screenshot plan |
| [Appearance & Language](user-guide/appearance-and-language.md) | User / operator / developer | Theme/accent, live scale, language switching, RTL leaf direction/font policy, SQLite preference persistence |
| [Key Bindings & Mouse Gestures](user-guide/key-bindings.md) | User / operator / developer | Editable keyboard/mouse bindings, direct capture, draft conflicts, user-home persistence, shell synchronization |
| [Documentation Workspace](user-guide/documentation.md) | User / operator / developer | In-app topic registry, three-column workflow, plain-Markdown rendering boundary, locale/body behavior, packaged/source docs resolution |
| [Training pipeline specification](training_pipeline.md) | Advanced user / developer / auditor | Exact Training persistence, hashing, parsing, execution, artifact/provenance contract |
| [Evaluation contract](reference/evaluation-contract.md) | Developer / auditor / researcher | Battery identity, inference settings, score parser, serialized result grammar, factor/delta math, comparability and methodology boundaries |
| [SQLite persistence schema reference](reference/persistence-schema.md) | Developer / operator / auditor | Exact current tables/columns/indexes/FKs, compatibility bootstrap and schema audit boundary |
| [Event and diagnostic schema](reference/event-and-diagnostic-schema.md) | Developer / operator / auditor | Event/error IDs, payload/redaction, duplicate handling, logs and Operations Center projection |
| [Automation recipe schema](reference/automation-recipe-schema.md) | Developer / operator / auditor | Exact recipe-manifest grammar, validation, placeholders, import/discovery and resource semantics |
| [Workspace layout reference](reference/workspace-layout.md) | Operator / developer / auditor | Exact workspace/external persistence surfaces, path ownership and backup/reset meaning |
| [Statuses, Result Codes & Identifiers](reference/statuses-and-identifiers.md) | Developer / operator / auditor | Canonical statuses, compatibility aliases, action/diagnostic/event codes, schemas and generated identifiers |
| [Keyboard & mouse bindings reference](reference/keyboard-mouse-bindings.md) | User / developer / auditor | Exact binding IDs/defaults, categories, targets, trigger/conflict semantics |
| [Workspace & Storage](operations/workspace-and-storage.md) | User / operator / developer | Research/workflow data roots, SQLite/filesystem ownership, external UI settings stores, local models, artifacts, backup/reset |
| [Local Models](operations/local-models.md) | User / operator / developer | Model paths, readiness probe, inference health, Training integration, trust/reproducibility limits |
| [Troubleshooting & Diagnostic Evidence](operations/troubleshooting.md) | User / operator / developer | Evidence-first triage, error/operation identities, runtime blockers, subsystem diagnosis, source/release-audit troubleshooting |
| [Backup, Reset & Recovery](operations/backup-reset-recovery.md) | User / operator / developer | Offline whole-workspace backup/restore, external presentation/dependency preservation, crash recovery, partial reset risks |
| [Security, Trust & Privacy Boundaries](operations/security-boundaries.md) | User / operator / developer / auditor | OS authority, unencrypted local state, model/data trust, Automation execution/audit, diagnostic privacy, source integrity |
| [Architecture Overview](architecture/overview.md) | Developer / auditor | System layers/composition/trust boundaries |
| [System scale and measured codebase anatomy](architecture/system-scale.md) | Developer / auditor / maintainer | Clean source-size baseline, counting methodology, scale ratios and interpretation limits |
| [Persistence architecture](architecture/persistence.md) | Developer / auditor | SQLite/filesystem/settings ownership, transaction/locking boundaries, schema bootstrap, cross-store consistency |
| [Workspace concurrency and ownership](architecture/workspace-concurrency.md) | Developer / auditor | Process writer lease, SQLite/thread/file atomicity boundaries and external preference-store concurrency |
| [Background work lifecycle](architecture/background-work-lifecycle.md) | Developer / auditor | QThread owners, shutdown aggregation, runtime-operation distinction and lease-release ordering |
| [UI shell architecture](architecture/ui-shell.md) | Developer / auditor | Workspace/navigation lifecycle, background ownership, docks, Operations Center, shortcuts, shell persistence |
| [Agents lineage architecture](architecture/agents-lineage.md) | Developer / auditor | Semantic snapshot/projection, local state, runtime links, history transactions, failure containment |
| [Automation architecture](architecture/automation.md) | Developer / auditor | Recipe/provider/service/process/audit architecture, trusted-host boundary, runtime claims, containment, failure semantics |
| [Training Dynamics mathematics](architecture/training-dynamics-mathematics.md) | Researcher / developer / auditor | Proposed multi-space mathematical framework; explicitly non-current instrumentation |
| [Training Dynamics instrumentation](architecture/training-dynamics-instrumentation.md) | Researcher / developer / auditor | Proposed evidence/sampling/structural-identity contract; explicitly non-current instrumentation |
| [v1.0 Product Contract](reference/v1-product-contract.md) | Everyone | Stable-release guarantees/boundaries/non-goals |
| [Localization architecture](architecture/localization.md) | Developer / auditor | i18n/RTL architecture |
| [Runtime resource safety](architecture/runtime-resource-safety.md) | Developer / auditor | Runtime resource safety |
| [Development setup](development/setup.md) | Developer / contributor | Locked environment, source launch, headless Qt, repository layout and release preconditions |
| [Testing and engineering audits](development/testing.md) | Developer / auditor | Behavioral/static/audit layers and exact quick/full release-gate scope |
| [Developer tooling](development/tooling.md) | Developer / auditor | Repository-local tool contracts, release coupling and reusable-snippet extraction boundaries |
| [Runtime documentation architecture](development/documentation-runtime.md) | Developer / auditor / documentation author | Canonical/bundled/runtime docs boundaries, topic registration, localization and plain-text rendering |
| [Visual audit](development/visual-audit.md) | Developer / auditor / documentation author | Reproducible Qt captures, manifest evidence, interactive mode and sensitive-data boundaries |
| [Packaging](development/packaging.md) | Developer / release operator | Python build metadata, docs inclusion, extras and distribution verification |
| [Release process](development/release-process.md) | Developer / release operator / auditor | Candidate-to-tag validation/evidence sequence and limits of automated proof |

## Research/methodology references

Existing documents retained as research inputs include:

- [Experiment protocol](experiment_protocol.md)
- [Methodology limits](methodology_limits.md)
- [Personality portrait](personality_portrait.md)
- [Training Dynamics mathematics](architecture/training-dynamics-mathematics.md) — proposed research architecture, not current v1.0 instrumentation.
- [Training Dynamics instrumentation](architecture/training-dynamics-instrumentation.md) — proposed implementation/evidence contract, not current v1.0 instrumentation.

For current implementation truth, read these together with [Tests and Analysis](user-guide/tests-and-analysis.md), the [Evaluation contract](reference/evaluation-contract.md), and the [Training pipeline specification](training_pipeline.md). The canonical v1.0 docs explicitly distinguish protocol measurements from clinical/human-psychology claims and document current provenance limits such as bounded `RAW_RESPONSE` storage and incomplete generation-environment persistence.

## Historical/internal project records

`docs/context/` and `docs/releases/v0.*` are **project-history inputs**, not the public v1.0 source of truth.

They remain while current documentation is reconstructed so useful rationale is not lost. Once a topic is migrated and verified against v1.0 code, historical instructions must not override the current docs silently.

## Documentation quality rules

The v1.0 documentation set follows these rules:

1. **Describe observed behavior, not intended behavior.** Reconstruct docs from audited code/tests/UI.
2. **Separate tutorials from specifications.** User workflow remains readable; technical contracts remain precise.
3. **Show the interface when spatial understanding matters.** Screenshots/diagrams support comprehension rather than decorate.
4. **State destructive effects before actions.** Deletion, replacement, Training, and Automation need persistence/recovery implications first.
5. **Use machine terms exactly.** IDs, paths, status/error codes, environment variables, schemas, protocol identifiers, and commands keep product spelling.
6. **Distinguish guarantees from assumptions.** In particular, Training content-pins Profile/Dataset inputs but v1.0 does not content-address the complete base-model directory or treat the Snapshots UI as an independent immutable artifact store. Evaluation protocol identity is version-string based rather than a persisted battery-content hash.
7. **Keep screenshots reproducible.** Capture from a clean known commit and documented locale/theme/scale/state.
8. **Prefer a clean novice path.** Do not require repository history or unwritten project context.
9. **Cross-link instead of duplicating contracts.** One authoritative storage/trust/integrity contract per concept.
10. **Mark historical material as historical.** Old audit/release notes must not silently override current behavior.
11. **Separate measurement from interpretation.** A scored model response is an observed protocol result; it is not silently upgraded into a clinical diagnosis or claim about inaccessible internal mental state.
12. **Expose evidence quality.** Partial runs, missing provenance, protocol mismatch, bounded diagnostic text, and other limitations must remain visible where they affect interpretation.
13. **Distinguish semantic identity from presentation identity.** In Agents, stable persisted IDs and runtime claims outrank visible titles, aliases, placeholders, and graph labels.
14. **Call executable trust boundaries what they are.** Automation `trusted_host` commands are host code; runtime claims and audit metadata do not transform them into sandboxed/untrusted-safe execution.
15. **Distinguish a command snapshot from transitive executable provenance.** Automation command hashes identify what PTL launched, not the content hashes of every executable/script/data file that command can consume.
16. **Preserve evidence before recovery.** Troubleshooting/reset guidance must not destroy the state needed to classify an incident before the failure is understood.
17. **Do not overclaim privacy/security from partial controls.** Context-key redaction, process containment, hashing, runtime claims, and local-first storage each have narrow meanings and must not be renamed into encryption/sandboxing/authorization guarantees they do not implement.
18. **Document every persistence surface that materially affects reproducibility or operator behavior.** Workspace state, Qt shell settings, key-binding JSON, and external model/Dataset/Automation inputs must not be collapsed into one fictional store.
19. **Do not invent rationale from placement.** A path/shortcut/state split can be documented as current behavior without asserting why it was chosen when code/history does not prove the reason.
20. **Classify machine strings before documenting them.** Canonical status, compatibility alias, action/result code, diagnostic, event type, schema marker, message key and identifier are separate contracts even when their spelling looks similar.
21. **Do not invent universal ID formats.** Current feature IDs use multiple prefix/hex widths; document the generator actually used by each feature.
22. **Do not silently replace project-local release contracts with shared utilities.** A generalized snippet may descend from PTL tooling, but PTL keeps its committed/tested local behavior until dependency migration is an explicit reviewed change.
23. **Distinguish canonical, bundled and runtime-exposed documentation.** A Markdown file can be part of the canonical/bundled docs tree without being registered as a selectable in-application Docs topic; runtime rendering/localization behavior must be documented from `DocsService`/`DocsViewModel`/`DocsScreen` rather than inferred from repository layout.
24. **Separate implemented contracts from proposed research architecture.** Mathematical/instrumentation designs may be precise and implementation-ready while remaining explicitly non-current until code, persistence, tests and release evidence exist.
25. **Separate execution-carrier lifetime from semantic/runtime ownership.** A screen `QThread`, a persisted runtime-operation lease and the outer workspace writer lease solve different problems; documentation must not collapse them into one fictional “workflow supervisor”.
26. **Freeze quantitative claims to an exact measured commit.** Source-size/test-ratio statements must record the counter definition, clean/dirty state and commit instead of silently following a moving branch.

## Current documentation structure

The maintained structure is:

```text
docs/
├── README.md
├── DOCUMENTATION_MAP.md
├── user-guide/
│   ├── getting-started.md
│   ├── interface-tour.md
│   ├── profiles.md
│   ├── datasets.md
│   ├── training.md
│   ├── agents-lineage.md
│   ├── snapshots.md
│   ├── tests-and-analysis.md
│   ├── automation.md
│   ├── appearance-and-language.md
│   ├── key-bindings.md
│   └── documentation.md
├── operations/
│   ├── workspace-and-storage.md
│   ├── local-models.md
│   ├── troubleshooting.md
│   ├── backup-reset-recovery.md
│   └── security-boundaries.md
├── architecture/
│   ├── overview.md
│   ├── system-scale.md
│   ├── persistence.md
│   ├── workspace-concurrency.md
│   ├── background-work-lifecycle.md
│   ├── runtime-resource-safety.md
│   ├── agents-lineage.md
│   ├── automation.md
│   ├── localization.md
│   ├── ui-shell.md
│   ├── training-dynamics-mathematics.md
│   └── training-dynamics-instrumentation.md
├── reference/
│   ├── v1-product-contract.md
│   ├── evaluation-contract.md
│   ├── persistence-schema.md
│   ├── event-and-diagnostic-schema.md
│   ├── automation-recipe-schema.md
│   ├── workspace-layout.md
│   ├── statuses-and-identifiers.md
│   └── keyboard-mouse-bindings.md
├── development/
│   ├── setup.md
│   ├── testing.md
│   ├── tooling.md
│   ├── documentation-runtime.md
│   ├── visual-audit.md
│   ├── packaging.md
│   └── release-process.md
└── assets/
    ├── screenshots/
    └── diagrams/
```

The development subtree and current architecture/reference set now exist. Final screenshot/diagram asset population remains ongoing. Existing links in the sections above point only to created/reviewed documents.

## Screenshot and diagram strategy

The final v1.0 documentation will use:

- full-window screenshots for spatial orientation;
- cropped/annotated screenshots when a control must be located precisely;
- Mermaid/architecture diagrams for lifecycle/relationship concepts;
- clean demo-workspace captures rather than accidental development state;
- explicit error/empty-state screenshots where understanding recovery matters;
- recorded commit/locale/theme/scale/state metadata for reproducibility.

The Agents guide defines a concrete capture inventory for healthy lineage, placeholders, local branches, archive/delete/history, runtime blockers, protocol-compatible/incompatible Delta, contextual navigation, and last-good refresh behavior. The Tests/Analysis guide similarly defines the evaluation capture inventory. The Automation guide defines a capture inventory for recipe discovery/import, trusted-host authorization, exec/shell modes, runtime conflicts, cancellation/timeout, bounded output, and audit/privacy behavior. The Key Bindings guide defines captures for direct input capture, dialogs, conflicts, and persisted-location diagnostics. The Documentation guide defines captures for the three-column runtime workspace, plain-Markdown body display, locale/body separation, and a controlled missing-content state.

The repository includes `tools/visual_audit.py` for reproducible automatic route/locale capture and interactive top-level-window capture. Scenario-specific demo-state preparation and final curated documentation assets remain separate review work; the capture harness does not make captured content automatically publication-safe.

Images support the written contract; they do not replace exact paths, status/error semantics, integrity boundaries, methodology limits, executable trust boundaries, destructive-action warnings, settings ownership, or security/privacy boundaries.