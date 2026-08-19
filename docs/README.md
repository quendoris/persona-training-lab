# Persona Training Lab Documentation

This directory is the canonical documentation home for Persona Training Lab.

PTL documentation is organized by **reader intent**, not by source-code package. A new user should not need to understand the architecture to complete a workflow; an auditor should not need to reverse-engineer behavior from a user tutorial.

## Start here

### I want to use PTL

Begin with:

- [Getting Started](user-guide/getting-started.md) — install from a source checkout, launch PTL, understand the workspace, and complete first-run orientation.
- [Interface Tour](user-guide/interface-tour.md) — understand the shell, twelve workspaces, Inspector, Activity, Telemetry, Issues, and status bar before starting a workflow.
- [v1.0 Product Contract](reference/v1-product-contract.md) — what the stable release guarantees, what it deliberately does not claim, and where its trust boundaries are.

The next user-guide layer expands this into task-oriented walkthroughs for profiles, datasets, training, Agents lineage, snapshots, tests/analysis, Automation, appearance/language, and key bindings.

### I operate or troubleshoot PTL

Start with:

- [Workspace & Storage](operations/workspace-and-storage.md) — platform data paths, SQLite/filesystem ownership, backup, reset, and source-tree separation.
- [v1.0 Product Contract](reference/v1-product-contract.md) — security/runtime boundaries that matter before operational changes.

The operator/reference layer will continue with local-model handling, Automation operations, recovery/troubleshooting, language/RTL behavior, and security boundaries.

### I develop, audit, or extend PTL

Start with:

- [Architecture Overview](architecture/overview.md) — composition root, layers, UI shell, persistence, runtime-operation coordination, models, Automation, telemetry, and error boundaries.
- [Runtime resource safety](architecture/runtime-resource-safety.md) — detailed runtime-resource safety notes.
- [Localization architecture](architecture/localization.md) — detailed catalog/RTL/localization notes.

The architecture/development layer will continue with persistence, Agents lineage, Automation internals, UI-shell contracts, testing, visual audit, packaging, and release methodology.

## Documentation map

### Current v1.0 foundation

| Document | Audience | Purpose |
|---|---|---|
| [Getting Started](user-guide/getting-started.md) | User | Source installation, first launch, workspace, initial orientation |
| [Interface Tour](user-guide/interface-tour.md) | User | Full shell map, workspaces, docks, language/layout behavior |
| [Workspace & Storage](operations/workspace-and-storage.md) | User / operator / developer | Data roots, `app.db`, artifacts, backup/reset, storage integrity |
| [Architecture Overview](architecture/overview.md) | Developer / auditor / advanced user | System layers, composition, persistence, runtime and trust boundaries |
| [v1.0 Product Contract](reference/v1-product-contract.md) | Everyone | Stable-release scope, guarantees, boundaries, non-goals |

### Existing detailed references being migrated into v1.0

| Document | Audience | Status |
|---|---|---|
| [Localization architecture](architecture/localization.md) | Developer / auditor | Detailed existing architecture reference; will be reconciled with final v1.0 terminology |
| [Runtime resource safety](architecture/runtime-resource-safety.md) | Developer / auditor | Detailed existing safety reference; will be reconciled with final v1.0 terminology |
| [Experiment protocol](experiment_protocol.md) | Research / advanced user | Existing research methodology source |
| [Methodology limits](methodology_limits.md) | Research / advanced user | Existing methodology/limits source |
| [Personality portrait](personality_portrait.md) | Research / advanced user | Existing portrait methodology source |
| [Training pipeline](training_pipeline.md) | Advanced user / developer | Existing training-flow source |

### Historical and internal project records

`docs/context/` and the existing `docs/releases/v0.*` documents are **project-history inputs**, not the public v1.0 source of truth. They remain in the repository while the current documentation is reconstructed so useful decisions and rationale are not lost during migration.

Once a topic has been fully migrated and verified against the v1.0 codebase, obsolete historical instructions may be archived or replaced. They should not be treated as authoritative over the v1.0 documentation.

## Documentation quality rules

The v1.0 documentation set follows these rules:

1. **Describe observed product behavior, not intended behavior.** Documentation is reconstructed from the audited code, tests, and accepted UI.
2. **Separate tutorials from specifications.** A step-by-step workflow should remain readable without architecture detail; the specification should remain precise without tutorial prose.
3. **Show the interface when spatial understanding matters.** Screenshots and diagrams are part of the instructional layer, not decoration.
4. **State destructive effects before the action.** Deletion, replacement, training, and Automation actions must explain persistence and recovery implications before telling the reader to click or run them.
5. **Use machine terms exactly.** IDs, paths, status codes, environment variables, schema names, and CLI commands are written exactly as the product uses them.
6. **Distinguish guarantees from operating assumptions.** In particular, the v1.0 release is not presented as having completed the post-release stress campaign.
7. **Keep screenshots reproducible.** Final user-facing screenshots will be captured from a clean, known commit and documented UI state rather than taken ad hoc from development sessions.
8. **Prefer a clean novice path over compressed expert prose.** A reader should not need repository history or unwritten project context to perform a documented task safely.
9. **Cross-link concepts instead of duplicating contracts.** Storage rules, trust boundaries, identifiers, and destructive-action semantics should have one authoritative reference and task guides should link to it.
10. **Mark historical material as historical.** Old release/audit notes must not silently override current v1.0 behavior.

## Planned v1.0 documentation structure

The completed documentation set will use this shape:

```text
docs/
├── README.md
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
│   └── key-bindings.md
├── operations/
│   ├── workspace-and-storage.md
│   ├── local-models.md
│   ├── troubleshooting.md
│   ├── backup-reset-recovery.md
│   └── security-boundaries.md
├── architecture/
│   ├── overview.md
│   ├── persistence.md
│   ├── runtime-safety.md
│   ├── agents-lineage.md
│   ├── automation.md
│   ├── localization.md
│   └── ui-shell.md
├── reference/
│   ├── v1-product-contract.md
│   ├── workspace-layout.md
│   ├── statuses-and-identifiers.md
│   └── keyboard-mouse-bindings.md
├── development/
│   ├── setup.md
│   ├── testing.md
│   ├── visual-audit.md
│   ├── packaging.md
│   └── release-process.md
└── assets/
    ├── screenshots/
    └── diagrams/
```

The tree above is a documentation plan, not a claim that every listed file already exists. Broken placeholder links are intentionally avoided until a document is created and reviewed.

## Screenshot and diagram strategy

The final v1.0 documentation will use visuals deliberately:

- **full-window screenshots** for spatial orientation;
- **cropped/annotated screenshots** for task steps where a control must be located precisely;
- **Mermaid/architecture diagrams** for relationships and lifecycle concepts that a screenshot cannot explain;
- **clean demo-workspace captures** rather than screenshots containing accidental development state;
- **recorded commit/locale/theme/scale metadata** for reproducibility.

The documentation should remain understandable without an image when exact behavior or paths matter. Images support comprehension; they do not replace the written contract.
