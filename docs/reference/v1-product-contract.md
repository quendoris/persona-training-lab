# Persona Training Lab v1.0 Product Contract

This document defines the intended contract of the first stable Persona Training Lab release.

It is stricter than a feature list: it states what behavior is part of the product promise, what integrity/security/storage boundaries exist, and what v1.0 deliberately does not claim.

## 1. Product purpose

Persona Training Lab is a local, desktop-first workstation for personality-oriented AI research and operations. It combines Profile definition, Dataset preparation, local Training/evaluation workflows, lineage inspection, snapshots, analysis, automation, telemetry, localization, and configurable interaction controls in one application workspace.

PTL is designed around inspectable local state rather than a remote SaaS dependency.

## 2. Stable-release scope

The v1.0 contract includes:

- desktop shell and navigation;
- Dashboard operational overview;
- personality Profiles;
- Agents lineage/version workspace and history interactions;
- Datasets import/validation/approval workflows;
- Training run and local-model workflows;
- Snapshots;
- Tests/evaluation surfaces;
- Analysis;
- Automation trusted-host recipe/ad-hoc execution and audit metadata;
- Style, language, and UI-scale configuration;
- configurable key bindings;
- Inspector, Activity, Issues, and Telemetry supporting surfaces;
- SQLite-backed persistence and runtime-operation coordination;
- complete UI localization catalogs for Arabic, English, Spanish, and Russian.

A capability being in scope means its current audited behavior is part of the stable product surface. It does not mean every possible workload/model/hardware combination has been stress-qualified.

## 3. Workspace and persistence contract

PTL's default workspace is independent from process current working directory.

| Platform | Default root |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` with documented fallbacks |
| macOS | `~/Library/Application Support/Persona Training Lab` |

An explicit `workspace_dir` overrides the default.

The workspace includes `app.db` and runtime areas such as artifacts, exports, temporary data, cache, plus feature/conventional directories such as logs, Automation recipes, and local models where applicable.

Agents local lineage state is also workspace-owned:

```text
<workspace>/agents_lineage_state.json
```

Automation custom manifests are workspace-owned under:

```text
<workspace>/automation/recipes/
```

A complete workspace backup therefore spans SQLite, Agents local state, Automation manifests, generated artifacts, and other workspace-owned files; `app.db` alone is not a complete product backup.

Trusted-host Automation can still depend on or modify host resources outside the workspace. Those external dependencies/effects are not automatically captured by a workspace backup.

Mutable runtime state must not be placed inside the installed/source package tree as a hidden input to product behavior.

## 4. Source and execution integrity

The release process treats a recorded Git commit as the source-of-truth input to validation.

Release validation rejects:

- dirty worktrees;
- missing quick-test manifest entries;
- hidden ignored runtime inputs under `src/`, `tests/`, or `tools/` except explicitly harmless interpreter/platform debris;
- production model-loading calls that enable `trust_remote_code=True`.

This prevents an editable checkout from validating against local hidden inputs that are absent from a clean clone or built distribution.

## 5. Local-model trust boundary

PTL may load local model files when inference/training capabilities are installed and configured.

Production loaders do **not** opt into Hugging Face `trust_remote_code=True`. v1.0 therefore does not intentionally grant a model repository permission to execute arbitrary repository-supplied Python through that Transformers mechanism.

Model weights, configuration, tokenizer data, templates, and other files are still inputs and should come from sources the user trusts.

## 6. Dataset approval integrity

A Dataset record identifies a filesystem source path; importing does not copy the source JSONL into SQLite.

Validation/approval computes a SHA-256 fingerprint of the current source bytes. Successful explicit approval persists that fingerprint with the Dataset state.

The approval hash distinguishes the Dataset record ID from the exact bytes currently authorized for downstream Training.

## 7. Training input-pinning contract

Creating a Training run pins both the selected Profile Training representation and approved Dataset content.

The run stores:

```text
profile_id
profile_sha256
dataset_id
dataset_sha256
```

The Profile hash covers the exact rendered Training instruction built from title/persona name, description, communication style, principles, and constraints. Profile operator `notes` are deliberately excluded from Training input and therefore from that fingerprint.

The Dataset hash is copied from the approved Dataset fingerprint.

At Launch, PTL refuses to silently follow changed Profile/Dataset state under the same IDs. If a training-relevant Profile field changes or different Dataset bytes are re-approved after run creation, the old run must not start on those new inputs.

Training also rechecks current Dataset bytes at its input boundary against the pinned approval fingerprint.

## 8. Training provenance boundary

A successful local full fine-tune writes a PTL artifact directory and `training_metadata.json` containing run/backend/hyperparameter/result/provenance information.

v1.0 provides content fingerprints for the Profile Training representation and approved Dataset bytes.

The base model is identified by its resolved local path/reference; v1.0 does **not** persist a cryptographic fingerprint of the complete base-model directory in the Training run.

For exact research reproducibility, operators must keep the base-model directory immutable during the run lifecycle and separately record source revision/checksum when required.

The product also does not claim bit-for-bit reproducibility across arbitrary Python/driver/CUDA/hardware states.

## 9. Training execution boundary

The production Training backend is local supervised full-parameter causal-language-model fine-tuning.

The current UI does not expose a production LoRA/QLoRA workflow. Pause and Stop controls are present but disabled in v1.0; the backend does not implement cooperative per-step cancellation.

Training executes through owned background work and runtime-resource coordination rather than running the fine-tune loop directly on the Qt GUI thread.

## 10. Automation execution and trust contract

Automation is an explicit **trusted-host** execution surface.

The only current effect-scope identifier is:

```text
trusted_host
```

A recipe or authorized ad-hoc command executes under the PTL process/OS-account permissions.

Automation is **not** a sandbox and does not claim to provide container isolation, restricted syscalls, filesystem confinement, network isolation, or a separate low-privilege identity.

### 10.1 Recipe contract

Workspace recipes use:

```text
ptl:automation-recipe:v1
```

and are discovered under:

```text
<workspace>/automation/recipes/
```

Recipe execution uses explicit argv/`exec` semantics. Inputs/placeholders/resource claims/timeout/working directory are validated/rendered before the execution snapshot is created.

The built-in `workspace_health` diagnostic declares a workspace read claim.

### 10.2 Ad-hoc authorization

Ad-hoc host commands require explicit:

```text
host_effects_authorized = true
```

before launch.

This authorization is an acknowledgement of host effects, not a sandbox switch.

Ad-hoc commands support separate `exec` and `shell` modes. Their command representations are mutually exclusive and validated before runtime lease acquisition.

### 10.3 Resource coordination

Automation acquires runtime-operation claims before process launch.

Read/write claims coordinate cooperative PTL workflows. Conflicting claims block launch.

These claims are **runtime coordination semantics**, not OS permission enforcement. PTL does not inspect arbitrary process syscalls to prove that a command touches only declared resources.

When an ad-hoc command declares no resources, v1 inserts a conservative workspace `write` claim.

### 10.4 Timeout/cancellation/process-tree containment

Automation captures child output through bounded pipes and owns the launched process tree.

On POSIX, execution uses a separate session/process group and group termination. On Windows, execution uses a kill-on-close Job Object boundary.

Cancellation/timeout target the contained process tree rather than only the immediate child.

A one-shot Automation command should not rely on leaving unmanaged detached descendants alive after run finalization.

### 10.5 Output bounds

Stdout and stderr are captured independently with a default per-stream limit of 1 MiB and a hard per-stream maximum of 64 MiB.

Excess bytes are drained but not retained; truncation is reported in the result/audit metadata.

### 10.6 Audit contract

Production composition wires Automation to the shared event log through:

```text
ptl:automation-audit:v1
```

The structured audit stores execution metadata including command SHA-256/part count, environment **keys**, working directory, timeout/output bound, resource claims, and terminal metadata.

It intentionally does not store plaintext command text or environment-variable values as the normal command record, and it does not copy stdout/stderr contents into the structured audit payload.

Ad-hoc execution fails closed when audit is unavailable or the start-audit record cannot be persisted.

Audit rows can still reveal sensitive operational metadata such as paths, resource IDs, environment key names, errors, subjects, and timing information.

### 10.7 Recipe mutability/provenance boundary

Recipe IDs/versions are metadata, not signed/content-addressed execution identities.

The Automation UI can display one discovered workspace recipe snapshot while `run_recipe()` reloads the recipe by ID before execution. v1.0 does not cryptographically pin the displayed manifest to the later Run click.

Operators must Refresh/review after recipe edits and preserve exact manifest/tool/data revisions separately when exact reproducibility matters.

The Automation command SHA-256 identifies the command snapshot PTL launched; it is not a transitive hash of every executable/script/data file that command can consume.

## 11. Runtime safety contract

PTL coordinates operations touching shared persistent resources and contains explicit safety machinery for lineage/destructive operations and background work.

Stable-release contracts include:

- shared SQLite serialization/connection ownership;
- atomic runtime-operation claims;
- lineage runtime safety and persisted `lineage_resource_links`;
- branch deletion planning/finalization/compensation paths;
- protected branch-deletion undo/redo safety;
- Automation pre-launch resource coordination;
- workspace-leave guards;
- background worker ownership/shutdown;
- application, worker-thread, and Qt diagnostic error boundaries.

Read/read claims can coexist; a conflicting write blocks. Destructive lineage work obtains a deletion lease before mutation rather than relying only on an earlier UI availability check. Automation obtains its execution lease before launching a host process.

## 12. Agents lineage integrity contract

Agents is a projection/integration workspace, not an alternative source of truth for Training/Dataset/model/evaluation persistence.

The v1.0 lineage contract includes:

- one coherent SQLite semantic snapshot for Dataset, Training-run, model-version, and evaluation source sets;
- stable persisted IDs used for identity when available, including modern Training `profile_id` and `dataset_id` references;
- local custom-branch/current/archive/history/layout state stored separately in `<workspace>/agents_lineage_state.json`;
- explicit runtime links between lineage nodes and real resources;
- inherited runtime identity for newly created custom branches;
- last-good background projection retention when a refresh fails;
- presentation/localization refreshes that do not silently replace semantic projection identity;
- protocol-compatible Delta semantics shared with Analysis.

A custom `branch_00N` is local research structure. Creating, renaming, archiving, or removing that branch does not by itself create/delete a persisted trained model or artifact.

### Protected branch deletion

Normal custom-branch deletion:

1. plans the complete current subtree;
2. acquires a fresh `lineage_delete` runtime lease;
3. records exact linked-resource metadata for history;
4. mutates local state;
5. removes persisted lineage-resource links;
6. finalizes the lease.

Undo restores resource links before restoring the visible lineage/history snapshot.

Redo is **not** blind JSON replay: it obtains a fresh runtime deletion lease and consumes the existing redo entry. Therefore an operation started after Undo can legitimately block Redo, and history is not a bypass around runtime safety.

Registered model-version rows and physical artifacts are not destructively removed by the local custom-branch delete command.

### Delta compatibility

Agents must not present Delta as ready merely because two evaluations exist. Exact Delta requires known, matching evaluation `battery_version` and `scoring_version`, consistent with the Analysis protocol guard.

## 13. Localization and RTL contract

The v1.0 UI catalog set is complete for:

- `ar`
- `en-US`
- `es-ES`
- `ru-RU`

Catalogs maintain key/placeholder compatibility with the base catalog.

Arabic support includes plural-category behavior, RTL text handling, mixed-direction leaf-text policy, stable shell geometry, and a bundled Noto Sans Arabic UI font with recorded provenance/license material.

PTL does not rely on accidental host Arabic font fallback.

## 14. Validation contract

Before packaging/release acceptance, PTL is validated through multiple independent mechanisms, including:

- Python compilation checks;
- Ruff;
- production mypy checking;
- type-suppression audit;
- curated quick pytest profile;
- complete pytest suite;
- i18n catalog/reference/UI-literal auditing;
- visual audit tooling across routes/locales;
- source-tree/release-policy checks;
- build and clean-install acceptance during packaging.

The evidence for a specific release belongs in that release's verification record rather than being frozen into this general contract.

## 15. What v1.0 does not claim

v1.0 does not claim exhaustive proof of:

- long-duration soak behavior under arbitrary workloads;
- maximum Automation concurrency/process-tree complexity;
- malicious/untrusted-code containment for Automation;
- filesystem/network isolation of Automation commands;
- cryptographic signing/content-pinning of Automation recipe manifests;
- transitive hashing of Automation executables/scripts/data dependencies;
- extreme SQLite contention beyond audited contracts;
- arbitrary model sizes/architectures;
- every GPU/driver/OS combination;
- maximum Agents lineage graph size/interaction rate;
- every filesystem/process/database fault mode;
- distributed/multi-host runtime locking;
- transactional garbage collection of registered model artifacts from Agents local branch deletion;
- formal real-time guarantees or performance ceilings;
- cryptographic content-addressing of the full base-model directory;
- bit-identical ML reruns across arbitrary runtime/hardware environments.

These are explicit operating boundaries, not hidden promises.

## 16. Stability does not mean immobility

A v1.0 release means the documented behavior/boundaries form a coherent, usable baseline.

Post-release stress testing may justify internal, instrumentation, persistence, performance, or subsystem changes. Later versions must preserve or deliberately revise the public contracts documented here.

## 17. Documentation is part of the product contract

For v1.0, documentation is release material.

It must provide:

- a first-run path understandable without source knowledge;
- task-oriented user workflows;
- screenshots/diagrams where spatial/structural understanding matters;
- destructive-action/recovery guidance;
- operator/troubleshooting material;
- architecture/persistence references;
- security/trust boundaries;
- Training/Dataset provenance and reproducibility boundaries;
- Agents semantic-vs-local state and protected history boundaries;
- Automation trusted-host authorization/claims/audit/process-containment/provenance boundaries;
- development/test/visual-audit/packaging/release procedures;
- clear separation between supported behavior and post-v1.0 stress/experimental work.

If documentation and code disagree, the discrepancy is a release defect to resolve before stable publication.
