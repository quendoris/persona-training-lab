# Workspace & Storage

This document defines where Persona Training Lab stores mutable runtime data, what each area owns, and how Training artifacts, Agents lineage state, model inputs, and SQLite persistence fit into the v1.0 workspace contract.

The central rule is:

> **PTL runtime state belongs in the PTL workspace, not in the source tree and not in whichever directory happened to be the process current working directory.**

## 1. Default workspace location

PTL resolves a stable per-user data directory at runtime.

| Platform | Default workspace root |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` |
| macOS | `~/Library/Application Support/Persona Training Lab` |

Windows falls back through `%APPDATA%` and then the conventional user `AppData/Local/Persona Training Lab` path when required.

Changing terminal CWD does not select a PTL workspace.

## 2. Explicit workspace override

Controlled code/tests can create `AppSettings(workspace_dir=...)`. That explicit root becomes the base for the same workspace-owned persistence model.

This is useful for isolated tests, demo workspaces, documentation capture, and packaging checks.

## 3. Core workspace layout

The bootstrap-owned core layout is conceptually:

```text
<workspace>/
├── app.db
├── agents_lineage_state.json
├── artifacts/
├── exports/
├── temp/
└── cache/
```

`agents_lineage_state.json` is created lazily by Agents when local lineage state is persisted; it is listed here because it is part of the product workspace/backup unit even though the core directory bootstrap does not create the file eagerly.

Feature-owned/conventional directories can also appear, including:

```text
<workspace>/
├── models/
├── logs/
└── automation/
    └── recipes/
```

Not every optional/conventional directory is created eagerly by the core `ensure_workspace_dirs(...)` bootstrap helper.

## 4. `app.db`

`app.db` is the primary SQLite database for persistent application state.

It stores structured records for UI preferences, Profiles, Datasets, Training, model versions, experiments/analysis, event metadata, runtime-operation coordination, lineage resource links, and other registered application state.

Training-specific persisted state includes run IDs, configuration, status/progress, artifact paths, and input fingerprints such as `profile_sha256` and `dataset_sha256`.

Agents semantic lineage is **derived from persisted source records** in this database rather than being duplicated as a second complete semantic graph.

## 5. `agents_lineage_state.json`

Agents owns one additional workspace-local JSON file:

```text
<workspace>/agents_lineage_state.json
```

It stores local research/presentation state such as:

- custom branches;
- Agents current marker;
- local node overrides/archive state;
- undo stack;
- redo stack;
- history snapshots including graph layout;
- protected branch-deletion metadata where applicable.

It does **not** replace the Dataset/Training/model-version/evaluation records in `app.db`.

Production `AtomicLineageStateStore` resolves this file from the same PTL workspace root used by the rest of the application. The historical home-relative location `~/.persona_training_lab/agents_lineage_state.json` is not the v1.0 production default.

Because semantic lineage sources/resource links live in SQLite while local branch/history/layout state lives in this JSON, a complete Agents backup requires the whole workspace rather than either file alone.

## 6. `artifacts/`

`artifacts/` contains persistent generated outputs owned by PTL workflows.

For local full fine-tuning, the canonical layout is:

```text
<workspace>/artifacts/full_finetune/<run_id>/
├── model/
└── training_metadata.json
```

The `model/` directory contains the saved trained model/tokenizer output. `training_metadata.json` records run/backend/provenance information.

Do **not** treat `artifacts/` as disposable cache. Generated model output may be the only copy of a completed workflow result.

Agents local branch deletion does not garbage-collect these artifact directories merely because a branch referenced them.

## 7. `models/`

`models/` is the conventional location used by the default local-model configuration.

The configured default `Qwen3.5-0.8B` resolves to:

```text
<workspace>/models/qwen3.5-0.8b
```

The core workspace bootstrap does not currently guarantee that `models/` is created eagerly; users/operators populate it when using that default local-model path.

PTL can also use an explicit model directory elsewhere.

### Base-model reproducibility boundary

Training stores the resolved model path/reference but v1.0 does **not** cryptographically fingerprint the complete base-model directory in the Training run.

If exact research reproducibility matters, keep that directory immutable for the run and record the upstream model revision/checksum separately.

## 8. External Dataset sources

Dataset rows store a filesystem path to an external `.jsonl` source. Importing does not copy those bytes into `app.db`.

Approval stores a SHA-256 content fingerprint, and Training pins that approved fingerprint into the run. The hash proves content identity but cannot restore a missing source file.

Therefore a workspace backup is not automatically a complete Dataset-source backup when the JSONL lives elsewhere.

## 9. `exports/`

`exports/` is workspace-owned output intended for exported/user-facing material.

Whether an individual export is reproducible depends on the producing workflow. Do not assume exported files are authoritative substitutes for SQLite records or model artifacts.

## 10. `temp/`

`temp/` is temporary workspace state. It is a lower-risk cleanup target only when PTL and relevant owned operations are stopped.

Do not clear temporary state during active Training/Automation/model work unless a feature-specific recovery procedure says it is safe.

## 11. `cache/`

`cache/` is intended for regenerable cache material. Clearing it should not delete the sole authoritative copy of a Profile, Dataset row, Training run, local Agents branch history, or generated model artifact.

## 12. `logs/`

Structured application logs are diagnostic state. Production composition configures rotating logs under:

```text
<workspace>/logs/persona_training_lab.log
```

The file rotates at approximately 5 MB with five backups in the current implementation.

Failure to create the diagnostic log file does not prevent application startup.

Logs may contain operational metadata useful for startup/runtime/Training/Automation/Agents investigations. Review them before public sharing when workspace privacy matters.

## 13. `automation/recipes/`

Automation recipes are executable operational inputs associated with the workspace.

Treat them as code/commands, not inert preferences. Back them up when they represent work you care about.

## 14. SQLite and filesystem state form one product workspace

A complete PTL workspace is not equivalent to `app.db` alone.

For example:

```text
training_runs.artifact_path
model_versions.artifact_path
```

can point to generated files under `artifacts/`.

Agents also splits authoritative state across:

```text
app.db
  ├─ semantic source records
  └─ lineage_resource_links

agents_lineage_state.json
  ├─ custom branches
  ├─ current/overrides/archive
  └─ undo/redo + layout history
```

Copying only SQLite can preserve semantic records while losing Agents local branch/history/layout state and generated artifact bytes. Copying only artifacts/JSON can preserve files/local organization while losing the persisted Profiles, Datasets, Training runs, model-version records, evaluations, and runtime links that explain them.

Treat the **whole workspace root** as one backup unit unless a feature-specific export is explicitly self-contained.

## 15. Important SQLite areas

| Area | Main table(s) | Purpose |
|---|---|---|
| UI preferences | `ui_preferences` | Presentation preferences |
| Event history | `event_log` | Structured events/errors/audit data |
| Profiles | `persona_profiles` | Personality/profile definition |
| Datasets | `datasets` | Source path, validation state, approval SHA-256 |
| Training | `training_runs`, `training_logs` | Configuration, input fingerprints, runtime state, artifact path, logs |
| Model versions | `model_versions` | Published model-version metadata/artifact path |
| Experiments | `experiments` | Experiment/evaluation records |
| Analysis | `analysis_results` | Stored analysis/comparison results |
| Agents | `agents` | Agent records |
| Runtime coordination | `runtime_operations`, `runtime_operation_resources` | Operation lifecycle and resource claims |
| Lineage safety | `lineage_resource_links` | Protected lineage-node ↔ real-resource relationships |

Do not manually add/remove schema columns as a normal user workflow.

## 16. Agents semantic snapshot boundary

Agents reads the Dataset, Training-run, model-version, and evaluation source sets under one SQLite read transaction when constructing a semantic lineage snapshot.

This gives one refresh a coherent persisted view instead of combining separately timed reads from several repositories.

The local `agents_lineage_state.json` is applied after the semantic projection is built; it does not become a replacement source for those domain records.

## 17. Runtime-operation state

Long-running coordinated operations persist lifecycle/resource-claim state in SQLite.

An operation can record its ID/kind/subject, state, correlation ID, owner PID, timestamps, error text, and read/write claims.

This supports crash recovery and conflict detection. Agents uses `lineage_resource_links` plus these active claims to block unsafe local branch deletion/redo.

Do not manually edit rows to "unlock" PTL; use a documented recovery path.

## 18. Event/audit data

`event_log` is shared structured application-event infrastructure. Automation audit behavior intentionally avoids persisting inherited environment-variable **values** merely because a child process received them.

Event/audit rows may still contain sensitive operational metadata and belong in normal workspace privacy decisions.

## 19. Source tree vs workspace

A source checkout contains code/material such as:

```text
README.md
pyproject.toml
src/
tests/
tools/
docs/
```

Mutable runtime state must not silently become an input from those trees.

Release-policy tests check ignored/untracked inputs under `src/`, `tests/`, and `tools/` so an editable checkout cannot be validated using hidden runtime-affecting source files that are absent from the recorded commit.

Neither `app.db` nor `agents_lineage_state.json` should be created under a package/source subdirectory merely because the process was launched there.

## 20. Clean reset

For a complete fresh workspace:

1. close PTL completely;
2. ensure Training/Automation/helper work you care about is stopped;
3. rename or remove the entire workspace root;
4. launch PTL again.

Linux example:

```bash
mv ~/.local/share/persona-training-lab \
   ~/.local/share/persona-training-lab.backup
```

Renaming first is safer than immediate deletion.

A complete reset can remove/disconnect Profiles, Dataset metadata, Training records/logs, model-version metadata, generated artifacts, experiment/analysis state, Agents custom branches/history/layout, Automation recipes, audit history, preferences, runtime-operation state, lineage links, logs/cache/temp/exports, and any workspace-local models.

Do not describe a whole-workspace reset as "clear cache".

## 21. Backup

For a conservative offline manual backup:

1. stop PTL;
2. stop/finish relevant PTL-owned work;
3. copy the entire workspace root;
4. preserve filesystem metadata when practical;
5. record the PTL version/commit for reproducibility.

Linux example:

```bash
cp -a ~/.local/share/persona-training-lab \
      ~/Backups/persona-training-lab-2026-08-19
```

This captures both `app.db` and `agents_lineage_state.json` when present.

Then separately back up any important external Dataset sources and explicit base-model directories that live outside the workspace.

## 22. Restore

The conservative restore procedure is:

1. stop PTL;
2. move the current workspace aside;
3. restore the saved workspace to the expected root;
4. restore externally managed Dataset/model inputs as needed;
5. launch PTL;
6. inspect Dashboard/Agents/Issues/logs before destructive or long-running work.

Restoring metadata without referenced files can produce incomplete workflows even when SQLite opens successfully.

Restoring `app.db` without the corresponding Agents JSON can also preserve the semantic graph while losing local branches/current/history/layout organization.

## 23. Partial cleanup risk

- `cache/`: normally lower risk while PTL is stopped.
- `temp/`: normally lower risk after owned operations stop.
- `logs/`: removes diagnostic history.
- `exports/`: may delete user-visible outputs.
- `agents_lineage_state.json`: removes local Agents branches/current/overrides/history/layout; does not delete semantic SQLite entities.
- `models/`: may remove required base-model inputs.
- `artifacts/`: potentially highly destructive; not routine cleanup.
- only `app.db`: dangerous split because files/local Agents state can remain without authoritative semantic metadata.

## 24. Troubleshooting evidence

When reporting workspace/storage problems, collect:

- PTL version/commit;
- OS;
- actual workspace root;
- relevant environment overrides such as `XDG_DATA_HOME`/`LOCALAPPDATA`;
- relevant log/Issues text;
- whether `agents_lineage_state.json` exists when diagnosing Agents local-state/history problems;
- whether the issue followed a crash, forced shutdown, manual file move, Dataset edit, model replacement, or partial restore.

Do not publish a complete `app.db`, Agents state JSON, Dataset source, Training metadata, or Automation recipe directory without reviewing it for private content.

## 25. Developer rules

Persistent features must obtain workspace-owned paths from configuration/composition instead of CWD or package-relative mutable state.

Agents production state follows the same rule: `AtomicLineageStateStore` resolves its default JSON file through the platform workspace resolver.

A clean `git status` is also not sufficient when ignored files exist. Release policy treats hidden runtime-affecting inputs under source/test/tool trees as release-integrity defects.

## 26. v1.0 visual plan

The documentation asset pass should include:

- a workspace directory diagram showing `app.db`, `agents_lineage_state.json`, `models/`, and `artifacts/`;
- a backup/reset decision diagram;
- an Agents state-ownership diagram showing SQLite semantic state vs local JSON state;
- operational screenshots that help diagnose workspace problems.

Exact paths and destructive effects remain written contracts; images are supporting explanation.

## Related documentation

- [Getting Started](../user-guide/getting-started.md)
- [Interface Tour](../user-guide/interface-tour.md)
- [Agents lineage](../user-guide/agents-lineage.md)
- [Agents lineage architecture](../architecture/agents-lineage.md)
- [Datasets](../user-guide/datasets.md)
- [Training](../user-guide/training.md)
- [Training pipeline specification](../training_pipeline.md)
- [Architecture Overview](../architecture/overview.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
