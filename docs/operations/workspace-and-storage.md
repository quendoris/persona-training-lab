# Workspace & Storage

This document defines where Persona Training Lab stores mutable runtime data, what each workspace area is for, and how to back up or reset a v1.0 workspace safely.

The central rule is simple:

> **PTL runtime state belongs in the PTL workspace, not in the source tree and not in whichever directory happened to be the process current working directory.**

That rule is part of the v1.0 product contract and is guarded by release-policy tests.

## 1. Default workspace location

PTL resolves a stable per-user data directory at runtime.

| Platform | Default workspace root |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` |
| macOS | `~/Library/Application Support/Persona Training Lab` |

Windows fallback behavior uses `%APPDATA%` if `LOCALAPPDATA` is unavailable and finally falls back to the conventional user `AppData/Local/Persona Training Lab` path.

On Linux, if `XDG_DATA_HOME` is set, PTL respects it. Otherwise the default is:

```text
~/.local/share/persona-training-lab
```

The default is computed when `AppSettings` is created. It is not captured from `Path.cwd()` and is not affected by launching PTL from another folder.

## 2. Explicit workspace override

Application code and controlled environments can create `AppSettings(workspace_dir=...)` with an explicit workspace root.

When supplied, the explicit root becomes the base for the same workspace layout described below.

This override is useful for:

- tests;
- isolated development/demo workspaces;
- controlled packaging checks;
- future explicit workspace-selection tooling.

It should not be confused with changing the terminal current directory. `cd` does not select a PTL workspace.

## 3. Workspace layout

A normal workspace has this conceptual shape:

```text
<workspace>/
├── app.db
├── artifacts/
├── exports/
├── temp/
├── cache/
├── logs/
└── automation/
    └── recipes/
```

Some directories are created during bootstrap; others are created when the owning feature is used.

### `app.db`

The primary SQLite database for persistent application state.

It stores structured records such as preferences, profiles, datasets, model/training state, event metadata, runtime-operation leases, and lineage resource relationships.

### `artifacts/`

Persistent generated artifacts and model/training outputs owned by PTL workflows.

The local full fine-tune backend receives this directory as its artifact root.

Do not treat `artifacts/` as disposable cache merely because it is a directory. A generated model/checkpoint/output may be the only copy of a workflow result unless it has been exported or backed up elsewhere.

### `exports/`

Workspace area reserved for exported material.

Exported files are conceptually user-facing outputs rather than authoritative SQLite rows. Whether an individual export can be regenerated depends on the producing workflow.

### `temp/`

Temporary workspace data.

This area is the best candidate for cleanup when PTL is fully stopped, but do not delete it while a workflow is active unless a feature-specific recovery procedure explicitly says that is safe.

### `cache/`

Regenerable cache material.

Cache should not be treated as the sole authoritative copy of a user record. Clearing cache is expected to be less destructive than removing `app.db` or `artifacts/`, although a cold rebuild may make the next operation slower.

### `logs/`

Structured application log files.

Logging uses rotation rather than unbounded growth. Logs are diagnostic data and can be useful when investigating startup, runtime, automation, model, or Qt problems.

### `automation/recipes/`

Filesystem-backed Automation recipes associated with the workspace.

Recipes are executable operational inputs. Back them up if they represent work you care about, and review them as code/commands rather than treating them as inert UI preferences.

## 4. What lives in SQLite

The current v1.0 schema includes structured persistence for the following major areas.

| Area | Main table(s) | Purpose |
|---|---|---|
| UI preferences | `ui_preferences` | Theme/accent and related presentation preferences |
| Event history | `event_log` | Structured application/audit/error events |
| Projects | `projects` | Project records |
| Profiles | `persona_profiles` | Personality profile content and status |
| Agents | `agents` | Agent records |
| Experiments | `experiments` | Experiment/evaluation run records |
| Datasets | `datasets` | Dataset metadata, validation counts, readiness |
| Training | `training_runs`, `training_logs` | Training state, progress, artifacts, logs |
| Analysis | `analysis_results` | Stored comparison/analysis results |
| Model versions | `model_versions` | Published model-version metadata and artifact paths |
| Runtime coordination | `runtime_operations`, `runtime_operation_resources` | Persistent operation lifecycle and resource claims |
| Lineage safety | `lineage_resource_links` | Links between lineage nodes and protected resources |

The exact schema is an implementation contract and may grow through explicit future migrations/evolution. Do not add or remove columns manually as a normal user workflow.

## 5. SQLite and filesystem state form one workspace

A complete PTL workspace is not equivalent to `app.db` alone.

For example, SQLite can contain a `model_versions.artifact_path` pointing to generated files under the workspace. Copying only the database can preserve metadata while losing the corresponding artifact bytes.

Likewise, copying only `artifacts/` can preserve model files while losing the structured profile/dataset/training/lineage records that explain what they are.

For a complete manual backup, treat the **entire workspace root** as one backup unit unless a feature-specific export mechanism explicitly creates a self-contained artifact.

## 6. Runtime-operation state

PTL persists long-running operation state in SQLite rather than keeping every lease only in process memory.

An operation records information including:

- operation ID;
- operation kind;
- subject kind and ID;
- state;
- correlation ID;
- owner process ID;
- start/heartbeat/finish timestamps;
- optional failure text;
- claimed resources and read/write access mode.

This persistence is important for crash recovery. On a later startup PTL can identify active operations whose owner PID is no longer alive and mark them abandoned.

Do not edit runtime-operation rows manually to “unlock” PTL. If an operation appears stuck, use the documented recovery/troubleshooting path so the related resource state is considered as a whole.

## 7. Event log and audit data

`event_log` is shared infrastructure for structured application events and operational diagnostics.

It includes entity/correlation/causation information plus JSON payload data and timestamps.

Automation uses an audit trail backed by this infrastructure. The automation audit contract deliberately avoids persisting environment-variable **values** merely because a child process inherited the environment.

The event log is still potentially sensitive operational metadata. Include it in normal workspace privacy/back-up decisions.

## 8. Source tree vs workspace

These are deliberately different locations.

A source checkout may contain:

```text
README.md
pyproject.toml
src/
tests/
tools/
docs/
```

It must **not** depend on hidden mutable runtime files inside those directories.

A previous audit discovered exactly why this matters: an ignored runtime-affecting file under the source tree can make an editable checkout behave differently from the recorded Git commit or clean wheel.

The release policy now checks ignored/untracked inputs under `src/`, `tests/`, and `tools/` so this class of failure is blocked.

## 9. Clean reset

If you deliberately want a completely fresh PTL workspace and do not need the old data, the safest reset is:

1. **Close PTL completely.**
2. Confirm no PTL training/automation/helper process you care about is still running.
3. Rename or remove the entire workspace root.
4. Start PTL again.

Example on a default Linux setup:

```bash
mv ~/.local/share/persona-training-lab \
   ~/.local/share/persona-training-lab.backup
```

Then launch PTL normally. It will recreate the workspace directories and initialize a new `app.db`.

Renaming first is safer than immediate deletion when you are uncertain whether the old data matters.

If you are certain it does not matter:

```bash
rm -rf ~/.local/share/persona-training-lab
```

Only run that command when PTL is stopped and you understand that it removes the entire workspace state.

### Windows

Stop PTL, then rename or remove:

```text
%LOCALAPPDATA%\Persona Training Lab
```

### macOS

Stop PTL, then rename or remove:

```text
~/Library/Application Support/Persona Training Lab
```

## 10. What reset removes

A complete workspace reset removes or disconnects all workspace-local state, including potentially:

- profiles;
- dataset metadata and validation state;
- training records/logs;
- model-version metadata;
- generated artifacts stored under the workspace;
- experiment and analysis records;
- Automation recipes stored in the workspace;
- event/audit history;
- style/UI preferences;
- runtime-operation records;
- lineage resource links;
- workspace logs/cache/temp/exported files that live under that root.

Do not present a complete workspace reset as a harmless “clear cache” operation.

## 11. Backup

For a simple offline manual backup:

1. stop PTL;
2. wait for any deliberately launched PTL-owned work you intend to preserve to stop;
3. copy the entire workspace directory to another location;
4. preserve filesystem metadata when practical;
5. record the PTL version/commit used to create the backup if reproducibility matters.

Example:

```bash
cp -a ~/.local/share/persona-training-lab \
      ~/Backups/persona-training-lab-2026-08-19
```

For large model artifacts you may choose a storage mechanism better suited to large files, but the backup should still keep enough workspace metadata to identify those artifacts.

## 12. Restore

The conservative manual restore procedure is:

1. stop PTL;
2. move the current workspace aside;
3. restore the backed-up workspace to the expected root;
4. launch PTL;
5. inspect Dashboard/Issues/Logs before starting destructive or long-running work.

Restoring database metadata without the corresponding referenced files can produce incomplete workflows even when SQLite opens successfully.

## 13. Partial cleanup

### Clearing `cache/`

Normally lower risk than a full reset. Do it while PTL is stopped. Expect regeneration/re-probing work afterward.

### Clearing `temp/`

Normally lower risk after PTL and owned operations are stopped. Avoid clearing it during active training/automation/model work.

### Clearing `logs/`

Removes diagnostic history. Safe only in the sense that it should not be authoritative business state; do not delete logs immediately before diagnosing a problem.

### Clearing `exports/`

Potentially deletes user-visible output files. Whether they are reproducible depends on the original workflow.

### Clearing `artifacts/`

Potentially highly destructive. Do not use this as routine cleanup.

### Removing only `app.db`

Creates a structurally dangerous split: files may remain while their authoritative metadata is gone. Prefer an intentional whole-workspace reset unless you are performing a documented recovery procedure.

## 14. Logs and troubleshooting

When reporting a workspace/startup problem, collect:

- PTL version/commit;
- operating system;
- actual workspace root;
- whether `XDG_DATA_HOME`, `LOCALAPPDATA`, or related variables are customized;
- relevant files from `logs/`;
- Issues-panel text if available;
- whether the problem followed a crash, forced shutdown, manual file move, or partial restore.

Do **not** upload a complete `app.db` or automation recipe directory publicly without reviewing it for private research/workspace content.

## 15. Developer note: do not use CWD as persistence

New persistent features must obtain a workspace-owned path from configuration/composition rather than using `Path.cwd()` or writing beside `__file__`.

The v1.0 code audit found a real failure mode where a CWD-based default created `app.db` inside a source package directory. The default workspace was changed to platform-stable user data storage and a regression test was added to the quick release gate.

Treat that incident as an architectural rule, not as a one-off filename bug.

## 16. Developer note: ignored source inputs are forbidden

A clean `git status` is not sufficient if a file is ignored.

Release-policy tests explicitly query Git for ignored/untracked files under:

- `src/`;
- `tests/`;
- `tools/`.

Only harmless interpreter/platform debris is allowed. A hidden `.py`, `.json`, `.svg`, `.ttf`, database, or other runtime-affecting asset in those trees must not be able to influence a validated release without appearing in the commit.

## 17. Workspace-health Automation recipe

PTL includes workspace-health recipe code that can report on workspace state, including the database at `<workspace>/app.db`.

That recipe does not choose the workspace location. It operates on the workspace root supplied to it. Workspace selection remains a configuration/composition concern.

## 18. v1.0 screenshot/diagram plan

The final documentation asset pass will add:

- a platform workspace-location diagram;
- an annotated workspace directory tree;
- a backup/reset decision diagram;
- a screenshot of the in-app operational surfaces that help diagnose workspace problems.

No screenshot is required to understand the storage contract itself; diagrams will be explanatory additions rather than substitutes for exact paths and warnings.

## Related documentation

- [Getting Started](../user-guide/getting-started.md)
- [Interface Tour](../user-guide/interface-tour.md)
- [Architecture Overview](../architecture/overview.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
