# Workspace Layout Reference

This reference is the compact path/ownership map for Persona Training Lab v1.0.

For explanations and operating procedures, see [Workspace & Storage](../operations/workspace-and-storage.md), [Backup, Reset & Recovery](../operations/backup-reset-recovery.md), and [Persistence architecture](../architecture/persistence.md).

## 1. Default workspace root

| Platform | Default PTL research/workflow workspace |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` |
| macOS | `~/Library/Application Support/Persona Training Lab` |

Windows fallback order when `LOCALAPPDATA` is unavailable:

```text
%APPDATA%\Persona Training Lab
~/AppData/Local/Persona Training Lab
```

The process current working directory does not select the workspace.

## 2. Core workspace map

```text
<workspace>/
├── app.db
├── agents_lineage_state.json             # lazy / Agents local state
├── artifacts/
│   └── full_finetune/
│       └── <run_id>/
│           ├── model/
│           └── training_metadata.json
├── automation/
│   └── recipes/
│       └── **/*.ptl-recipe.json
├── cache/
├── exports/
├── logs/
│   └── persona_training_lab.log
├── models/
│   └── qwen3.5-0.8b/                     # conventional default model path
└── temp/
```

Some entries are lazy/conventional rather than created by the initial workspace-directory helper.

## 3. Eager directory creation

`ensure_workspace_dirs(...)` currently creates:

```text
<workspace>/
<workspace>/artifacts/
<workspace>/exports/
<workspace>/temp/
<workspace>/cache/
```

It does not itself create every other path in this reference.

## 4. Primary SQLite database

Path:

```text
<workspace>/app.db
```

Configured from:

```text
AppSettings.sqlite_filename = "app.db"
```

Primary structured areas include:

```text
ui_preferences
projects
persona_profiles
agents
datasets
training_runs
training_logs
model_versions
experiments
analysis_results
event_log
runtime_operations
runtime_operation_resources
lineage_resource_links
```

Use service/repository workflows rather than manual row editing.

## 5. Agents local state

Path:

```text
<workspace>/agents_lineage_state.json
```

Ownership:

```text
custom branches
current marker
local overrides/archive state
undo/redo history
layout/history snapshots
protected deletion metadata
```

Creation is lazy.

This file is separate from semantic Dataset/Training/model/evaluation records in `app.db`.

Historical path that is **not** the v1.0 production Agents default:

```text
~/.persona_training_lab/agents_lineage_state.json
```

Do not confuse that historical Agents location with the still-current key-binding file described below.

## 6. Training artifacts

Canonical full-fine-tune output root:

```text
<workspace>/artifacts/full_finetune/<run_id>/
```

Expected successful-output structure:

```text
model/
training_metadata.json
```

`artifacts/` is persistent generated output, not normal cache.

## 7. Automation recipe registry

Root:

```text
<workspace>/automation/recipes/
```

Discovery pattern:

```text
**/*.ptl-recipe.json
```

Current manifest schema:

```text
ptl:automation-recipe:v1
```

The registry can be created lazily by the recipe provider.

Imported manifests do not automatically bring along external companion scripts/binaries/data.

## 8. Application log

Path:

```text
<workspace>/logs/persona_training_lab.log
```

Current rotation contract:

```text
approximately 5 MiB per active file
5 backup files
```

The `logs/` directory/file is created by logging configuration rather than by `ensure_workspace_dirs(...)`.

File-log creation failure is non-fatal to application startup.

## 9. Default local model path

Default configured model name:

```text
Qwen3.5-0.8B
```

Default resolved path:

```text
<workspace>/models/qwen3.5-0.8b
```

`models/` is a conventional model-input location; the core directory bootstrap does not guarantee eager creation.

An explicit absolute model path can live outside the workspace.

## 10. Dataset source files can be external

Dataset persistence stores a filesystem path to an external `.jsonl` source.

The source bytes are not copied into `app.db` by import.

Therefore an example Dataset path can be:

```text
/home/user/research/dataset.jsonl
D:\research\dataset.jsonl
```

with only its metadata/approval SHA-256 stored in PTL persistence.

## 11. Automation dependencies/effects can be external

Trusted-host commands may use:

```text
absolute working directories
external scripts
external executables
external model/data files
host files outside <workspace>
network resources permitted by the host
```

The workspace is not an Automation sandbox boundary.

## 12. External shell state: Qt QSettings

These values are **outside** `<workspace>`:

```text
shell/window_geometry
shell/dock_state
shell/current_workspace
```

Owner:

```text
WindowStateStore
```

Backend:

```text
platform Qt QSettings
```

Production application identity:

```text
OrganizationName   = Persona Training Lab
OrganizationDomain = persona-training-lab.local
ApplicationName    = Persona Training Lab
ApplicationVersion = <PTL __version__>
```

The exact OS storage path/registry location follows Qt's platform `QSettings` behavior and is not hard-coded as one portable filesystem path by PTL.

## 13. External editable input bindings

Current default path:

```text
~/.persona_training_lab/key_bindings.json
```

Owner:

```text
KeyBindingManager
```

Current format version:

```text
2
```

Contains:

```text
editable keyboard bindings
editable Agents mouse bindings
```

This file is user-home-relative and not automatically moved by `workspace_dir`.

## 14. Three presentation/settings stores

Current v1.0 UI/operator state is split across:

```text
<workspace>/app.db / ui_preferences
  -> theme
  -> accent_palette
  -> button_style_preset
  -> ui_scale
  -> language

platform Qt QSettings
  -> window geometry
  -> dock state
  -> last workspace

~/.persona_training_lab/key_bindings.json
  -> keyboard shortcuts
  -> mouse gestures
```

Do not collapse these into one fictional “settings file”.

## 15. Development release-audit artifacts are not runtime workspace artifacts

From a source checkout, release gate reports default under:

```text
<repository>/artifacts/release-audit/
```

Typical run directory:

```text
<timestamp>-<commit>-seed-<seed>/
```

This belongs to development/release validation.

It is different from:

```text
<workspace>/artifacts/full_finetune/
```

which contains runtime Training outputs.

## 16. Source tree

A source checkout normally contains areas such as:

```text
README.md
pyproject.toml
uv.lock
src/
tests/
tools/
docs/
artifacts/release-audit/    # generated development audit reports when present
```

Runtime research state must not silently be placed under `src/`, `tests/`, or `tools/` as a hidden dependency.

Release policy explicitly checks for unexpected ignored runtime-affecting inputs in those trees.

## 17. Backup inclusion matrix

| State | Whole `<workspace>` copy | Must preserve separately when needed |
|---|---:|---:|
| `app.db` | yes | no |
| Agents JSON | yes, when present | no |
| Training artifacts | yes | no |
| workspace Automation manifests | yes | no |
| workspace-local models | yes | optional separate provenance/checksum still recommended |
| logs/cache/temp/exports | yes | no |
| external Dataset source | no | **yes** |
| external model directory | no | **yes** |
| external Automation script/tool/data | no | **yes** |
| external Automation side effect | no rollback/capture guarantee | manage separately |
| Qt QSettings shell state | no | only for exact shell presentation/session restore |
| key-binding JSON | no | only for exact input-binding restore |
| Git source worktree | no | preserve through Git/source backup separately |

## 18. Reset inclusion matrix

Moving/removing only `<workspace>` resets/disconnects the active research/workflow workspace, including SQLite-backed Style preferences.

It does **not necessarily reset**:

```text
Qt QSettings shell state
~/.persona_training_lab/key_bindings.json
external Dataset/model/tool files
prior external Automation effects
source checkout
```

## 19. Authority classes

Use these categories when adding or auditing paths:

### Authoritative structured state

```text
<workspace>/app.db
```

### Authoritative/local workflow organization

```text
<workspace>/agents_lineage_state.json
```

### Persistent generated output

```text
<workspace>/artifacts/
```

### Executable trusted configuration

```text
<workspace>/automation/recipes/
```

### External research inputs

```text
Dataset JSONL
explicit base model
external recipe dependencies
```

### Diagnostic state

```text
<workspace>/logs/
release-audit reports
```

### Regenerable/temporary workspace state

```text
cache/
temp/
```

### User-facing output

```text
exports/
```

### External presentation/operator configuration

```text
Qt QSettings
~/.persona_training_lab/key_bindings.json
```

## 20. Path-resolution rules

Current important rules:

```text
PTL workspace root
  -> platform resolver / explicit AppSettings(workspace_dir=...)

relative local-model path
  -> resolved relative to workspace root

empty/default model name
  -> default workspace model path

Automation empty ad-hoc working directory
  -> workspace root

Automation relative ad-hoc working directory
  -> workspace-relative

Automation absolute working directory
  -> remains host-absolute

workspace recipe relative working_directory
  -> resolved according to recipe manifest/provider source semantics

key-binding default path
  -> Path.home()/.persona_training_lab/key_bindings.json

Qt shell state
  -> QSettings platform backend
```

Do not substitute process CWD for these ownership rules.

## 21. Paths that should not be manually “fixed” by copying state into source

Do not solve a missing/runtime-path problem by placing authoritative state under:

```text
src/
tests/
tools/
```

Examples of incorrect workarounds:

```text
src/.../app.db
src/.../agents_lineage_state.json
tools/models/<runtime-model> as an undocumented local dependency
ignored helper/data files that make release tests pass only on one checkout
```

Use the documented workspace/external-input contract instead.

## 22. Reference invariants

When a persistence path changes, update at least:

- this reference;
- [Workspace & Storage](../operations/workspace-and-storage.md);
- [Persistence architecture](../architecture/persistence.md);
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md) when backup scope changes;
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md) when trust/privacy scope changes;
- relevant feature user guide;
- release/migration notes when compatibility changes.

A path existing in code is not enough; its ownership, backup/reset behavior, and external-dependency boundary must remain explicit.

## Related documentation

- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md)
- [Persistence architecture](../architecture/persistence.md)
- [UI shell architecture](../architecture/ui-shell.md)
- [Local Models](../operations/local-models.md)
- [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md)
- [Training](../user-guide/training.md)
- [Automation](../user-guide/automation.md)
