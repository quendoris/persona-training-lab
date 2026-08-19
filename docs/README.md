# Persona Training Lab Documentation

This directory is the canonical documentation home for Persona Training Lab.

PTL documentation is organized by **reader intent**, not by source-code package. A new user should not need architecture knowledge to complete a workflow; an auditor should not need to reverse-engineer behavior from a tutorial.

## Start here

### I want to use PTL

Begin with:

- [Getting Started](user-guide/getting-started.md) — source-checkout installation, first launch, workspace, first-run orientation.
- [Interface Tour](user-guide/interface-tour.md) — shell, workspaces, Inspector, Activity, Telemetry, Issues, status bar, language/layout behavior.
- [Profiles](user-guide/profiles.md) — define the personality fields used by downstream Training.
- [Datasets](user-guide/datasets.md) — import/preview/validate/approve JSONL and understand approval SHA-256 semantics.
- [Training](user-guide/training.md) — create a run, understand input pinning, launch local full fine-tuning, inspect logs/artifacts/provenance.
- [Snapshots and model versions](user-guide/snapshots.md) — inspect registered model versions, understand lineage, artifact references, and the exact meaning of “snapshot” in v1.0.
- [v1.0 Product Contract](reference/v1-product-contract.md) — stable-release guarantees, trust/integrity boundaries, explicit non-goals.

### I operate or troubleshoot PTL

Start with:

- [Workspace & Storage](operations/workspace-and-storage.md) — platform paths, SQLite/filesystem ownership, local models, Training artifacts, backup/reset.
- [Training pipeline specification](training_pipeline.md) — exact Training input transformation, hashes, backend, artifacts, failure/reproducibility boundaries.
- [Snapshots and model versions](user-guide/snapshots.md) — distinguish persisted model-version metadata from the referenced artifact and trace provenance back to a Training run.
- [v1.0 Product Contract](reference/v1-product-contract.md) — security/runtime/integrity boundaries before operational changes.

The operator layer will continue with dedicated local-model, recovery/troubleshooting, Automation, and security-boundary guides.

### I develop, audit, or extend PTL

Start with:

- [Architecture Overview](architecture/overview.md) — composition root, layers, UI shell, persistence, runtime coordination, models, Automation, telemetry, error boundaries.
- [Runtime resource safety](architecture/runtime-resource-safety.md) — shared-resource/operation safety contracts.
- [Localization architecture](architecture/localization.md) — catalog, RTL, font, and localization contracts.
- [Training pipeline specification](training_pipeline.md) — detailed Profile/Dataset fingerprints, Training parser/backend, artifact metadata, limitations.
- [Snapshots and model versions](user-guide/snapshots.md) — current `model_versions` persistence semantics, derived lifecycle presentation, and provenance limits.

## Current v1.0 documentation map

| Document | Audience | Purpose |
|---|---|---|
| [Getting Started](user-guide/getting-started.md) | User | Install, launch, workspace, first-run orientation |
| [Interface Tour](user-guide/interface-tour.md) | User | Shell/workspace map and supporting panels |
| [Profiles](user-guide/profiles.md) | User | Create/edit personality definitions |
| [Datasets](user-guide/datasets.md) | User / operator | JSONL structure, validation, approval fingerprints, Training eligibility |
| [Training](user-guide/training.md) | User / operator | End-to-end Training workflow and safe operating rules |
| [Snapshots and model versions](user-guide/snapshots.md) | User / operator / auditor | Model-version registry, lineage, artifact references, lifecycle projection, reproducibility boundary |
| [Training pipeline specification](training_pipeline.md) | Advanced user / developer / auditor | Exact Training persistence, hashing, parsing, execution, artifact/provenance contract |
| [Workspace & Storage](operations/workspace-and-storage.md) | User / operator / developer | Data roots, `app.db`, external inputs, local models, artifacts, backup/reset |
| [Architecture Overview](architecture/overview.md) | Developer / auditor | System layers/composition/trust boundaries |
| [v1.0 Product Contract](reference/v1-product-contract.md) | Everyone | Stable-release guarantees/boundaries/non-goals |
| [Localization architecture](architecture/localization.md) | Developer / auditor | i18n/RTL architecture |
| [Runtime resource safety](architecture/runtime-resource-safety.md) | Developer / auditor | Runtime resource safety |

## Research/methodology references

Existing documents retained as research inputs include:

- [Experiment protocol](experiment_protocol.md)
- [Methodology limits](methodology_limits.md)
- [Personality portrait](personality_portrait.md)

They should be read together with current product/user/architecture contracts when a workflow crosses from research methodology into application behavior.

## Historical/internal project records

`docs/context/` and `docs/releases/v0.*` are **project-history inputs**, not the public v1.0 source of truth.

They remain while current documentation is reconstructed so useful rationale is not lost. Once a topic is migrated and verified against v1.0 code, historical instructions must not override the current docs silently.

## Documentation quality rules

The v1.0 documentation set follows these rules:

1. **Describe observed behavior, not intended behavior.** Reconstruct docs from audited code/tests/UI.
2. **Separate tutorials from specifications.** User workflow remains readable; technical contracts remain precise.
3. **Show the interface when spatial understanding matters.** Screenshots/diagrams support comprehension rather than decorate.
4. **State destructive effects before actions.** Deletion, replacement, Training, and Automation need persistence/recovery implications first.
5. **Use machine terms exactly.** IDs, paths, status/error codes, environment variables, schemas, and commands keep product spelling.
6. **Distinguish guarantees from assumptions.** In particular, Training content-pins Profile/Dataset inputs but v1.0 does not content-address the complete base-model directory or treat the Snapshots UI as an independent immutable artifact store.
7. **Keep screenshots reproducible.** Capture from a clean known commit and documented locale/theme/scale/state.
8. **Prefer a clean novice path.** Do not require repository history or unwritten project context.
9. **Cross-link instead of duplicating contracts.** One authoritative storage/trust/integrity contract per concept.
10. **Mark historical material as historical.** Old audit/release notes must not silently override current behavior.

## Planned v1.0 documentation structure

The remaining documentation work continues toward:

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
│   ├── runtime-resource-safety.md
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

The tree is a plan, not a claim that every listed file already exists. Placeholder links are avoided until a document is created/reviewed.

## Screenshot and diagram strategy

The final v1.0 documentation will use:

- full-window screenshots for spatial orientation;
- cropped/annotated screenshots when a control must be located precisely;
- Mermaid/architecture diagrams for lifecycle/relationship concepts;
- clean demo-workspace captures rather than accidental development state;
- recorded commit/locale/theme/scale metadata for reproducibility.

Images support the written contract; they do not replace exact paths, status/error semantics, integrity boundaries, or destructive-action warnings.
