# Persona Training Lab Documentation

This directory is the canonical documentation home for Persona Training Lab.

PTL documentation is organized by **reader intent**, not by source-code package. A new user should not need to understand the architecture to complete a workflow; an auditor should not need to reverse-engineer behavior from a user tutorial.

## Start here

### I want to use PTL

Begin with:

- [Getting Started](user-guide/getting-started.md) — install from a source checkout, launch PTL, understand the workspace, and orient yourself in the interface.
- [v1.0 Product Contract](reference/v1-product-contract.md) — what the stable release guarantees, what it deliberately does not claim, and where its trust boundaries are.

The v1.0 documentation phase will expand the user guide into task-oriented walkthroughs for profiles, datasets, training, Agents lineage, snapshots, tests, analysis, automation, styling/localization, and key bindings.

### I operate or troubleshoot PTL

The operator/reference layer will cover:

- workspace layout and data lifecycle;
- local-model discovery and model-loading boundaries;
- Automation execution, timeout, cancellation, and process containment;
- logs, Issues, Activity, and Telemetry;
- recovery and troubleshooting;
- language/RTL/font behavior;
- backup and clean-reset procedures.

### I develop, audit, or extend PTL

The architecture/reference layer will cover:

- application layering and composition root;
- SQLite schema and repository ownership;
- runtime-operation coordination and destructive-operation safety;
- Agents lineage projection, history, refresh, and branch deletion;
- UI shell, view models, panels, key bindings, and interaction contracts;
- localization catalogs, RTL policy, and bundled font provenance;
- model inference/training integration and security boundaries;
- release gates, test profiles, visual audit, build, and packaging acceptance.

## Documentation map

### Current v1.0 documentation

| Document | Audience | Purpose |
|---|---|---|
| [Getting Started](user-guide/getting-started.md) | User | Source installation, first launch, workspace, UI orientation |
| [v1.0 Product Contract](reference/v1-product-contract.md) | Everyone | Stable-release scope, guarantees, boundaries, non-goals |
| [Localization architecture](architecture/localization.md) | Developer / auditor | Existing detailed localization design notes |
| [Runtime resource safety](architecture/runtime-resource-safety.md) | Developer / auditor | Existing runtime-resource safety design notes |
| [Experiment protocol](experiment_protocol.md) | Research / advanced user | Existing experiment methodology |
| [Methodology limits](methodology_limits.md) | Research / advanced user | Existing methodological limits |
| [Personality portrait](personality_portrait.md) | Research / advanced user | Existing portrait methodology |
| [Training pipeline](training_pipeline.md) | Advanced user / developer | Existing training-flow notes |

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
