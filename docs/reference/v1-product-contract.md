# Persona Training Lab v1.0 Product Contract

This document defines the intended contract of the first stable Persona Training Lab release.

It is deliberately stricter than a feature list. A stable release must make clear what behavior is part of the product promise, what data and security boundaries exist, and what has **not** yet been claimed.

## 1. Product purpose

Persona Training Lab is a local, desktop-first workstation for personality-oriented AI research and operations. It brings profile definition, datasets, model training/evaluation workflows, lineage inspection, snapshots, analysis, automation, telemetry, localization, and configurable interaction controls into one application workspace.

PTL is designed around inspectable local state rather than a remote SaaS dependency. The primary persistent application state is stored in the local workspace.

## 2. Stable-release scope

The v1.0 contract includes the following product areas:

- desktop shell and navigation;
- Dashboard operational overview;
- personality Profiles;
- Agents lineage/version workspace and history interactions;
- Datasets import/validation/version workflows;
- Training run and local-model workflows;
- Snapshots;
- Tests/evaluation surfaces;
- Analysis;
- Automation execution and audit metadata;
- Style, language, and UI-scale configuration;
- configurable key bindings;
- Inspector, Activity, Issues, and Telemetry supporting surfaces;
- SQLite-backed persistence and runtime-operation coordination;
- complete UI localization catalogs for Arabic, English, Spanish, and Russian.

A capability being in scope means its current audited behavior is part of the stable product surface. It does not mean every theoretically possible workload or model has been stress-qualified.

## 3. Workspace and persistence contract

PTL's default workspace is independent from the process current working directory.

Default roots are:

| Platform | Root |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` with documented fallbacks |
| macOS | `~/Library/Application Support/Persona Training Lab` |

An explicitly supplied `workspace_dir` overrides the default.

The workspace contains the SQLite database (`app.db`) and runtime directories including artifacts, exports, temporary data, cache, and logs.

Mutable runtime state must not be placed inside the installed/source package tree as an implicit input to application behavior.

## 4. Source and execution integrity

The release process treats a recorded Git commit as the source-of-truth input to validation.

Release validation rejects:

- a dirty worktree;
- missing quick-test manifest entries;
- hidden ignored runtime inputs under `src/`, `tests/`, or `tools/` other than explicitly harmless platform/interpreter debris;
- production model-loading calls that enable `trust_remote_code=True`.

This policy exists because a locally present but untracked/ignored source file can otherwise make an editable checkout behave differently from a clean clone or built distribution.

## 5. Local-model trust boundary

PTL may load local model files when inference or training capabilities are installed and configured.

The production loaders do **not** opt into Hugging Face `trust_remote_code=True`.

Therefore the v1.0 model-loading contract does not intentionally grant a model repository permission to execute arbitrary repository-supplied Python through that Transformers mechanism.

This is a security boundary, not merely a default. Reintroducing remote-code execution would be a deliberate future change to the product trust model and must not happen as an incidental compatibility tweak.

Model weights, configuration, tokenizer files, templates, and other data are still inputs and should be obtained from sources the user trusts.

## 6. Automation boundary

Automation is an explicit execution surface and should be treated accordingly.

The current product architecture includes controlled execution, timeout/cancellation behavior, process handling, and persistent audit metadata. Audit storage is designed not to persist environment-variable **values** merely because the executed process inherited the environment; command audit data is also represented in a deliberately reduced form rather than as an unrestricted plaintext execution dump.

Automation is not a sandbox that turns arbitrary commands into untrusted-safe code. A user-approved command still executes with the permissions of the PTL process and operating system account, subject to the product's execution controls.

## 7. Runtime safety contract

PTL coordinates runtime operations that touch shared persistent resources and contains explicit safety machinery for lineage/destructive operations and background work.

The stable release includes contracts around:

- shared SQLite serialization/connection ownership;
- atomic runtime-operation claims;
- lineage runtime safety;
- branch deletion planning/finalization/compensation paths;
- workspace-leave guards;
- background worker ownership and shutdown;
- application, worker-thread, and Qt diagnostic error boundaries.

The exact implementation and invariants are documented in the architecture section of the v1.0 documentation set.

## 8. Localization and RTL contract

The v1.0 UI catalog set is complete for:

- `ar`
- `en-US`
- `es-ES`
- `ru-RU`

Catalogs are required to maintain key and placeholder compatibility with the base catalog.

Arabic support includes plural-category behavior, RTL text handling, mixed-direction leaf-text policy, stable shell geometry, and a bundled Noto Sans Arabic UI font with recorded provenance and license material.

The application does not rely on a host system accidentally selecting a usable Arabic fallback font.

## 9. Validation contract

Before v1.0 packaging/release acceptance, PTL is validated through multiple independent mechanisms rather than a single pytest count.

The validation system includes:

- Python compilation checks;
- Ruff;
- production mypy checking;
- an audit of type-suppression usage;
- a curated quick pytest release profile;
- the complete pytest suite;
- i18n catalog/reference/UI-literal auditing;
- visual audit tooling across application routes/locales;
- source-tree/release-policy checks;
- build and clean-install acceptance during the packaging phase.

The detailed evidence for a specific release belongs in that release's verification record rather than being frozen into this general product contract.

## 10. What v1.0 does not claim

The first stable release is intentionally **not** a claim that every subsystem has already been driven to its physical or operational limit.

In particular, the post-v1.0 stress campaign is a separate engineering phase. It is expected to probe workloads and failure modes that can reasonably create new engineering work rather than merely certify the existing implementation.

v1.0 therefore does not claim exhaustive proof of:

- long-duration soak behavior under arbitrary workloads;
- maximum Automation concurrency/process-tree complexity;
- extreme SQLite contention patterns beyond the audited contracts;
- arbitrary model sizes and architectures;
- every GPU/driver/OS combination;
- maximum Agents lineage graph size or interaction rate;
- fault-injection coverage for every filesystem/process/database failure;
- performance ceilings or formal real-time guarantees.

These are not hidden defects in the release definition. They are explicitly outside the first stable operating claim and form the basis of the next engineering stage.

## 11. Stability does not mean immobility

A v1.0 release means the documented behavior and boundaries form a coherent, usable product baseline.

Post-release stress testing may identify changes substantial enough to alter internals, instrumentation, persistence strategies, performance architecture, or subsystem boundaries. Those changes belong to later versions and must preserve or deliberately revise the public contracts documented here.

## 12. Documentation is part of the product contract

For v1.0, documentation is release material rather than an afterthought.

The release documentation must provide:

- a first-run path understandable without source-code knowledge;
- task-oriented user workflows;
- screenshots/diagrams where spatial or structural understanding matters;
- destructive-action and recovery guidance;
- operator/troubleshooting material;
- architecture and persistence references;
- security/trust boundaries;
- development, test, visual-audit, packaging, and release procedures;
- clear separation between supported behavior and post-v1.0 experimental/stress work.

If documentation and code disagree, the discrepancy is a release defect to be resolved before the stable release is published.
