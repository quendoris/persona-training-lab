# Persona Training Lab — Architecture Context

This file is a compact handoff map. Detailed contracts live in `docs/architecture/`, `docs/reference/`, `docs/operations/`, and the code/tests.

## 1. Layer map

### Bootstrap / composition

`persona_training_lab.bootstrap` resolves workspace ownership, SQLite/repositories, application services, localization/theme/input managers, runtime coordinators, workspaces/panels and final shutdown ownership.

### Domain

`persona_training_lab.domain` holds small domain entities/statuses/types for Profiles/persona, Datasets, Training, evaluation, models, snapshots and monitoring.

### Application

`persona_training_lab.application` owns use-case semantics:

- Profiles / Datasets / Training;
- Experiments / evaluation / Analysis;
- model versions and local-model probing;
- Agents lineage projection/snapshot/runtime safety;
- Automation;
- Operations Center;
- Telemetry;
- runtime-operation coordination;
- error reporting.

Application state/results should remain machine-semantic. Human-readable presentation belongs at UI/localization boundaries.

### Infrastructure

`persona_training_lab.infrastructure` provides concrete adapters:

- SQLite persistence/repositories/transactions;
- filesystem/local-model probing;
- telemetry providers;
- Automation manifest/process infrastructure;
- structured logging.

### UI

The PySide6 UI contains twelve registered workspaces:

- Dashboard
- Profiles
- Agents
- Datasets
- Training
- Snapshots
- Tests
- Analysis
- Automation
- Style
- Documentation
- Key bindings

Supporting shell surfaces include Inspector, Activity, Issues and Telemetry.

## 2. Important ownership boundaries

### Workspace

The workspace owns `app.db`, generated artifacts, logs, Automation manifests and Agents local lineage state. QSettings and the user-home key-binding file are external user-level presentation/input stores.

### Background work

Screens/panels that start long-running work own their worker lifecycle. Shell close/leave guards query those owners; final bootstrap drain keeps workspace ownership until participating background work is finished.

### Runtime operations

Runtime-operation leases coordinate PTL operations against resource identities. They are cooperative product-level safety, not filesystem/process security enforcement.

### Agents

Agents combines a coherent persisted semantic projection with separate local graph/history/layout state. Safety links and protected history are fail-closed across mixed generations.

### Training

Training is local full-parameter supervised causal-LM fine-tuning. Profile/Dataset inputs are pinned; base-model identity remains path/reference based; final artifact publication is staged before exposing the final run namespace.

### Automation

Automation executes trusted host commands. Recipe review identity, rendered command identity, runtime resource claims, process-tree containment and audit metadata are distinct contracts.

## 3. Persistence and atomicity

Do not describe PTL as having one global transaction.

There are several mechanisms with different scopes:

- SQLite transactions/repository locking;
- atomic runtime-operation claim changes;
- atomic file replacement for selected JSON state;
- staged Training artifact publication;
- explicit compensation/fail-closed rules across SQLite + Agents JSON.

Cross-medium consistency limits must stay explicit in docs and recovery guidance.

## 4. Localization and presentation

Current complete selectable UI locales are:

```text
ru-RU
en-US
es-ES
ar
```

Arabic is RTL. Human-readable UI text is catalog-driven; semantic domain/application values must not become a second presentation source.

Theme/style decisions belong in shared theme/presentation mechanisms rather than per-screen hard-coded palettes.

## 5. Research boundary

`architecture/training-dynamics-mathematics.md` and `architecture/training-dynamics-instrumentation.md` are proposed research architecture. They describe the post-v0.1.0 direction and must not be presented as current runtime instrumentation.

## 6. Canonical architecture entry points

Read together:

- `docs/architecture/overview.md`
- `docs/architecture/persistence.md`
- `docs/architecture/workspace-concurrency.md`
- `docs/architecture/background-work-lifecycle.md`
- `docs/architecture/runtime-resource-safety.md`
- `docs/architecture/agents-lineage.md`
- `docs/architecture/agents-protected-history.md`
- `docs/architecture/automation.md`
- `docs/architecture/telemetry.md`
- `docs/architecture/evaluation-analysis.md`
- `docs/architecture/localization.md`
- `docs/architecture/provenance-and-external-state.md`
