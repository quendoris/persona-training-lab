# Backup, Reset & Recovery

This guide defines conservative backup, restore, reset, and crash-recovery procedures for Persona Training Lab v1.0.

It is intentionally stricter than “copy the database” advice because PTL state is split across SQLite, workspace files, generated artifacts, external research inputs, and two presentation/configuration stores outside the workspace.

The central rule is:

> **Treat the complete PTL workspace as one research/workflow persistence unit, perform manual backups offline, preserve external Dataset/model/Automation dependencies separately, and preserve external shell/key-binding settings separately when exact UI/input-personalization restoration matters.**

For the detailed ownership map, read [Workspace & Storage](workspace-and-storage.md) and the [Workspace layout reference](../reference/workspace-layout.md). For incident triage before changing state, read [Troubleshooting & Diagnostic Evidence](troubleshooting.md).

## 1. What a complete research/workflow backup means

A PTL research/workflow backup is not equivalent to one `app.db` file.

The workspace can contain authoritative or operationally important state such as:

```text
<workspace>/
├── app.db
├── agents_lineage_state.json
├── artifacts/
├── automation/
│   └── recipes/
├── cache/
├── exports/
├── logs/
├── models/
└── temp/
```

Not every directory/file is always present, and not every item has the same importance.

A conservative research/workflow backup captures the **whole workspace root** while PTL is stopped.

## 2. Why `app.db` alone is incomplete

SQLite contains structured PTL state including Profiles, Datasets metadata, Training runs/logs, model versions, experiments/analysis, event history, runtime operations, lineage resource links, and SQLite-backed Style/localization preferences.

Other state lives outside SQLite.

Examples:

```text
agents_lineage_state.json
  -> custom branches, current marker, archive/overrides,
     undo/redo and graph-layout history

artifacts/full_finetune/<run_id>/...
  -> generated trained model/tokenizer and training metadata

automation/recipes/*.ptl-recipe.json
  -> executable trusted-host recipe manifests

models/
  -> optional workspace-local model inputs
```

A database-only backup can therefore leave valid rows pointing to files/history that were not preserved.

## 3. A whole workspace is still not every PTL setting

Two current presentation/configuration surfaces are **outside** the PTL workspace:

```text
Qt QSettings
  -> shell/window_geometry
  -> shell/dock_state
  -> shell/current_workspace

~/.persona_training_lab/key_bindings.json
  -> editable keyboard bindings
  -> editable Agents mouse gestures
```

Therefore:

> **“whole-workspace backup” means complete PTL-owned research/workflow workspace state, not byte-for-byte capture of every per-user presentation preference.**

This distinction is deliberate documentation of current placement, not a claim about why the placement was originally chosen.

## 4. Qt `QSettings` backup boundary

`WindowStateStore` saves shell geometry, dock state, and last workspace through Qt `QSettings` under the application/organization identity `Persona Training Lab`.

The native storage location is platform/backend dependent. PTL does not publish one portable filesystem path that can be copied identically on Linux, Windows, and macOS.

A workspace backup therefore does not guarantee restoration of:

- window geometry;
- dock layout/floating state;
- last-open workspace.

Losing this state does not delete research/workflow records. It changes the restored shell presentation/session layout.

If exact shell-state preservation matters, back up/export the platform's corresponding Qt settings using platform-appropriate tooling and record the OS/backend used.

## 5. Key-binding backup boundary

Editable keyboard and mouse bindings currently live at:

```text
~/.persona_training_lab/key_bindings.json
```

This file is outside the default PTL workspace.

Current format:

```text
version = 2
```

Version 1 is accepted as an older compatibility format; v2 persists both keyboard and mouse mappings.

A whole-workspace backup does **not** capture custom bindings unless this file is copied separately.

For exact input-personalization recovery, preserve it with the workspace backup provenance.

## 6. Key-binding write/recovery boundary

`KeyBindingManager` writes a complete JSON payload to:

```text
key_bindings.json.tmp
```

and then replaces the target file.

This gives a single-file temp-then-replace write boundary. It is not a transaction with SQLite or QSettings.

On load:

- a missing file means defaults remain active;
- unreadable/invalid JSON produces a warning/error state and defaults remain available;
- unsupported format is rejected;
- conflicting persisted keyboard mappings are repaired by falling back to defaults;
- conflicting persisted mouse mappings are likewise repaired to defaults;
- valid v1 keyboard state can be loaded, while v2 adds persisted mouse mappings.

Do not manually edit this file during PTL operation and assume a half-edited mapping is an atomic application state transition.

## 7. External research dependencies are outside the workspace backup

Some PTL records intentionally reference ordinary host filesystem inputs.

Important examples are:

- Dataset source JSONL files;
- explicit base-model directories outside the workspace;
- Automation companion scripts/binaries/data outside the workspace;
- host resources modified by trusted Automation commands.

A whole-workspace backup does not automatically capture those dependencies or effects.

For reproducible research, back them up/version them separately.

## 8. Default workspace roots

The default workspace is independent of repository/current working directory.

| Platform | Default root |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` with documented fallbacks |
| macOS | `~/Library/Application Support/Persona Training Lab` |

An explicit `AppSettings(workspace_dir=...)` can select another root in controlled code/tests.

Always identify the actual active root before backing up or resetting state.

## 9. Why the recommended manual workspace backup is offline

PTL configures writable SQLite connections with:

```text
journal_mode = WAL
synchronous = NORMAL
busy_timeout = 5000 ms
```

and uses runtime/background workers that can update SQLite or filesystem state while the application is open.

A naive copy of only `app.db` during active WAL writes can miss state residing in SQLite's write-ahead-log lifecycle or race with concurrent application changes.

PTL v1.0 does not expose a dedicated coordinated hot-backup command that freezes SQLite plus Agents JSON plus artifacts/recipes/external state into one atomic capsule.

Therefore the documented manual procedure is:

> stop PTL and its relevant owned work, then copy the entire workspace.

The external key-binding file should also be copied while PTL is stopped when preserving it.

## 10. Pre-backup checklist

Before copying a workspace:

1. identify the active workspace root;
2. finish/stop work you care about;
3. close PTL normally;
4. make sure the application process has exited;
5. make sure intentionally launched external work is in a known state;
6. record the PTL version/commit;
7. identify external Dataset/model/Automation dependencies that need separate preservation;
8. decide whether shell QSettings state matters;
9. decide whether `~/.persona_training_lab/key_bindings.json` should be preserved.

Do not treat an Automation child process or another external tool as stopped merely because the PTL window disappeared unexpectedly.

## 11. Conservative Linux workspace backup example

With the default Linux workspace:

```bash
cp -a ~/.local/share/persona-training-lab \
      ~/Backups/persona-training-lab-2026-09-06
```

If exact key bindings matter, separately preserve:

```bash
cp -a ~/.persona_training_lab/key_bindings.json \
      ~/Backups/persona-training-lab-2026-09-06.key_bindings.json
```

Only run the second command if the source file exists.

`cp -a` is used here to preserve directory structure and filesystem metadata reasonably well. The destination should be a new or intentionally managed backup location.

Do not copy a backup back on top of a running PTL workspace.

## 12. Conservative backup on Windows/macOS

The same logical procedure applies:

1. close PTL;
2. copy the complete workspace directory as a directory tree;
3. preserve it under a distinct backup name/location;
4. separately preserve important external research dependencies;
5. preserve the key-binding JSON if exact bindings matter;
6. preserve native Qt settings only if exact shell layout/session restoration matters.

The exact shell/file-copy/settings-export tool is an operator/platform choice. PTL does not currently ship a platform-specific backup executable.

## 13. Record backup provenance

A useful backup record contains:

```text
backup timestamp
PTL version / Git commit
OS
workspace source path
backup destination
important external Dataset sources
base-model source/revision/checksum when required
Automation recipe/tool revisions when required
key-binding file captured: yes/no
Qt QSettings shell state captured: yes/no + platform/backend when relevant
```

For research reproducibility, the commit/version matters because persisted structures and interpretation rules can evolve.

## 14. Generated Training artifacts are persistent output

Do not classify:

```text
<workspace>/artifacts/full_finetune/<run_id>/
```

as disposable cache.

A successful run can place the only local copy of its trained model there.

A normal backup should preserve both:

```text
app.db
artifacts/
```

so run/model-version metadata and actual generated bytes remain together.

## 15. Training artifact provenance still has an external boundary

`training_metadata.json` and Training persistence record Profile/Dataset provenance and the base-model path/reference.

v1.0 does not cryptographically fingerprint the complete base-model directory as part of the Training run.

Therefore a backup that preserves the trained artifact still may not fully reproduce the original run unless the base model identity/environment was preserved separately.

## 16. Dataset backup boundary

Dataset import stores a source path; it does not copy the source JSONL into SQLite.

Approval stores a SHA-256 fingerprint of approved bytes, which can prove identity/mismatch but cannot reconstruct a missing file.

If a Dataset JSONL lives outside the workspace, preserve it separately.

For an exact historical run, preserve the approved bytes corresponding to the stored hash.

## 17. Automation backup boundary

Workspace Automation manifests are preserved by a whole-workspace backup:

```text
<workspace>/automation/recipes/
```

Import copies the manifest file only. A recipe can still depend on external scripts, executables, models, or data.

Structured Automation audit stores a command snapshot hash/metadata rather than a transitive content hash of every executable dependency.

Preserve the recipe manifest **and** relevant external tool/data revisions for reproducible Automation research.

## 18. Automation side effects are not rolled back by restore

Trusted-host Automation can modify resources outside the PTL workspace with the permissions of the PTL OS account.

Restoring an older workspace does not undo those already-applied external effects.

```text
Automation changed /some/external/file
          ↓
restore old PTL workspace
          ↓
/some/external/file remains changed
```

This is an explicit trust/recovery boundary of v1.0.

## 19. Agents backup boundary

Agents combines:

```text
app.db
  -> persisted semantic sources + lineage_resource_links

agents_lineage_state.json
  -> custom branches/current/archive/overrides/history/layout
```

Preserve both in the same workspace backup.

A database-only restore can leave the semantic graph intact while losing local Agents organization/history.

An Agents-JSON-only restore can restore local organization that no longer matches the intended SQLite snapshot.

## 20. Agents state writes are atomic at the file level

`AtomicLineageStateStore` saves `agents_lineage_state.json` by:

1. serializing the in-memory payload;
2. writing a temporary file in the same directory;
3. flushing and `fsync`ing that temporary file;
4. atomically replacing the target path with `os.replace(...)`;
5. attempting a directory `fsync`;
6. rolling in-memory state back to the last persisted payload if save fails.

This reduces the chance of a partially written JSON file during normal saves.

It does not make the entire PTL workspace one cross-file/database transaction.

## 21. If `agents_lineage_state.json` is unreadable or invalid

The atomic store distinguishes:

- missing file -> default local state can be used;
- filesystem read error -> `LineageStateLoadError`;
- invalid JSON -> `LineageStateLoadError`;
- non-object JSON root -> `LineageStateLoadError`.

Before any recovery experiment:

1. close PTL;
2. copy the invalid/unreadable file and `app.db` to an evidence directory;
3. record the PTL commit/version;
4. determine whether the problem followed a crash, manual edit, partial restore, or filesystem problem.

If you deliberately want to reset only Agents local organization/history, **rename** the JSON out of the active workspace rather than deleting the only copy immediately.

```bash
mv ~/.local/share/persona-training-lab/agents_lineage_state.json \
   ~/.local/share/persona-training-lab/agents_lineage_state.json.recovery-backup
```

On the next state-store creation, a missing active file produces default local Agents state.

This does **not** delete semantic Dataset/Training/model/evaluation rows from SQLite, but it does remove the active local custom branches/current/history/layout until the saved file is restored.

## 22. Do not “fix” Agents JSON by hand unless performing forensic recovery

Agents state contains schema/history/layout/protected-deletion metadata whose consistency matters.

Manual deletion of one field can produce a state that looks simpler but no longer represents a valid history transition or runtime-safety snapshot.

Normal recovery should prefer UI history behavior, restoring a known-good whole-workspace backup, or moving the entire local Agents state file aside for an explicit local-state reset.

## 23. SQLite concurrency and locking boundary

Writable PTL SQLite connections use WAL mode and a 30-second connection timeout, plus `busy_timeout = 5000`.

Repositories sharing one connection can also use a process-local `RLock` registry keyed by that connection.

These mechanisms improve in-process serialization/SQLite contention behavior; they do not provide distributed/multi-host locking for one workspace copied/shared across machines.

Do not run multiple independent PTL instances against the same live workspace over a shared/distributed filesystem and assume the v1.0 runtime-operation contract becomes distributed coordination.

## 24. Runtime-operation crash recovery

PTL persists runtime operations/resource claims in SQLite.

At startup, composition asks the runtime coordinator to recover active operations whose recorded owner PID is no longer alive.

Those operations are marked:

```text
abandoned
```

and a warning notice is reported when recovery releases one or more operations.

This prevents dead persisted leases from blocking PTL indefinitely after an ordinary process crash.

## 25. What `abandoned` does not mean

`abandoned` is a coordination-state recovery result.

It does not mean:

- Training artifacts were rolled back;
- an external Dataset was restored;
- an Automation command's host effects were undone;
- every descendant process was proven dead after an abnormal OS/process failure;
- a partially written external file was repaired.

After crash recovery, inspect the feature-specific external/persisted state before retrying the operation.

## 26. Normal application shutdown is preferable to force termination

The shell owns workspace background workers and guards shutdown.

If work has not stopped, the close event can be delayed/retried rather than destroying the workspace immediately.

Let normal shutdown complete whenever possible.

Force termination should be treated as crash recovery afterward: inspect runtime-operation state, artifacts, external side effects, and logs before starting new destructive work.

## 27. Restoring a whole workspace

Conservative research/workflow procedure:

1. stop PTL completely;
2. preserve the current workspace by moving/renaming it rather than overwriting it;
3. copy the chosen workspace backup into the expected root;
4. restore required external Dataset/model/Automation dependencies;
5. optionally restore the separately preserved key-binding file;
6. optionally restore the platform Qt settings when exact shell state matters;
7. start PTL;
8. inspect Dashboard, Agents, Automation, Issues, and logs;
9. verify model/artifact/Dataset paths before Training/Tests;
10. verify runtime-operation recovery state before destructive Agents actions.

Keeping the pre-restore workspace aside makes rollback/investigation possible if the selected backup was wrong.

Do not overwrite a newer key-binding/QSettings state merely because a workspace restore occurred unless you intentionally want the older presentation state too.

## 28. Example conservative Linux workspace restore

Suppose the current workspace is:

```text
~/.local/share/persona-training-lab
```

and the backup is:

```text
~/Backups/persona-training-lab-2026-09-06
```

With PTL stopped:

```bash
mv ~/.local/share/persona-training-lab \
   ~/.local/share/persona-training-lab.pre-restore

cp -a ~/Backups/persona-training-lab-2026-09-06 \
      ~/.local/share/persona-training-lab
```

Restore `~/.persona_training_lab/key_bindings.json` separately only when the matching binding snapshot was intentionally captured.

Only remove the pre-restore copy after the restored workspace has been validated and you no longer need the evidence/rollback point.

## 29. Restore validation checklist

After launch, verify:

```text
workspace root
Profiles present
Datasets present + source paths exist
Training runs/logs present
model-version records present
artifact paths exist
Agents custom branches/history expected
Automation recipes expected
Issues does not show restore/startup failures
runtime operations are not unexpectedly active
local model path resolves to expected bytes/source
```

If exact presentation restoration was requested, additionally verify:

```text
keyboard/mouse bindings
window geometry
dock layout
last workspace
```

For exact research work, also verify external checksums/revisions.

## 30. Schema bootstrap behavior

Current startup creates missing core tables/indexes with `CREATE ... IF NOT EXISTS` and ensures a known set of later Profile/Dataset/Training columns/tables exist.

This provides limited additive compatibility for known older workspace schemas.

It is **not** a general arbitrary migration/downgrade system.

Do not assume every future database can be opened safely by every older PTL binary, arbitrary manual schema edits will be repaired, or restoring a newer workspace into an older checkout is supported.

## 31. Downgrade caution

A workspace that has been opened by newer code may contain columns, values, state versions, or files an older checkout does not understand.

The key-binding file also has its own explicit format version independent of the SQLite schema.

v1.0 does not publish a general downgrade guarantee.

When testing an older version, use isolated copies and preserve the newer authoritative workspace/settings first.

## 32. Clean reset of the entire workspace

A complete fresh-workspace experiment is performed with PTL stopped by moving the whole workspace root aside.

```bash
mv ~/.local/share/persona-training-lab \
   ~/.local/share/persona-training-lab.before-reset
```

Then launch PTL. Bootstrap creates required new workspace/database state on demand.

This is safer than immediate recursive deletion because the previous state remains available.

## 33. What a whole-workspace reset removes/disconnects

Depending on what exists in the workspace, a complete reset removes from the **active workspace**:

- Profiles;
- Dataset metadata/approval state;
- Training runs/logs;
- model-version metadata;
- experiments/analysis state;
- event history;
- runtime operations/resource claims;
- lineage resource links;
- Agents custom branches/current/archive/history/layout;
- generated Training artifacts;
- workspace Automation recipes;
- workspace-local models;
- SQLite-backed theme/accent/UI-scale/language preferences;
- logs/cache/temp/exports.

External Dataset/model/Automation files remain wherever they already exist.

External Automation side effects also remain.

Crucially, a whole-workspace reset **does not by itself reset**:

```text
Qt QSettings shell state
~/.persona_training_lab/key_bindings.json
```

Those must be reset independently if that is the intended experiment.

## 34. Presentation-only reset is a different operation

Resetting shell geometry/docks/current workspace through `WindowStateStore` or removing/resetting key-binding state changes presentation/input configuration; it is not a clean research-workspace reset.

Likewise, moving the research workspace aside does not prove the application is using default window/binding configuration.

For reproducible UI/visual-audit work, explicitly declare both research state and presentation state.

## 35. Reset is not “clear cache”

A whole-workspace reset removes authoritative and generated state.

Do not describe it as cache cleanup and do not recommend it as the first response to a model error, runtime blocker, or UI issue.

Use [Troubleshooting](troubleshooting.md) to classify the incident first.

## 36. Partial cleanup: `cache/`

`cache/` is intended for regenerable cache material.

It is lower risk than deleting persistence/artifacts, but cleanup should still be performed with PTL stopped when diagnosing filesystem behavior.

A cache clear should not be expected to repair missing SQLite rows, invalid Dataset bytes, Training input-hash mismatches, or broken external model files.

## 37. Partial cleanup: `temp/`

`temp/` is temporary workspace state and is a lower-risk cleanup target only after PTL and relevant owned operations have stopped.

Do not remove temporary state while a Training/Automation/helper workflow is using it unless a feature-specific procedure explicitly allows that.

## 38. Partial cleanup: logs

Deleting `logs/` removes diagnostic evidence.

Do not clear logs before capturing a bug report or before understanding a crash.

Logs are not authoritative domain state, but losing them can make a failure significantly harder to reconstruct.

## 39. Partial cleanup: `exports/`

Exports can be user-facing outputs.

They are not automatically guaranteed to be regenerable from current state, so treat them as user data rather than cache unless the producing workflow explicitly says otherwise.

## 40. Partial cleanup: `artifacts/`

Do not use `artifacts/` as a routine cleanup target.

Model-version and Training rows can reference generated artifact paths. Removing the bytes can leave metadata pointing to missing models.

v1.0 does not currently provide a general transactional artifact garbage collector tied to all lineage/model-version references.

Back up and inspect references before deletion.

## 41. Partial cleanup: `models/`

Removing workspace-local models can make local-model checks, Training creation, Training launch, and Tests/inference unavailable.

Because Training does not content-address the complete base-model directory, replacing a directory under the same path with different bytes can also change reproducibility semantics without changing the stored path.

Treat model directories as deliberate inputs, not cache.

## 42. Partial cleanup: `automation/recipes/`

Deleting custom recipe manifests removes them from future workspace discovery.

It does not erase already-recorded Automation audit rows, undo commands already executed, or delete external scripts/data they used.

Preserve recipes required for reproducible operational history.

## 43. Partial reset: Agents local state only

Moving only:

```text
agents_lineage_state.json
```

out of the active workspace resets Agents local organization/history on next use while preserving semantic SQLite entities.

This is narrower than a whole-workspace reset but still destructive to the active local Agents custom branch/history/layout state.

Always keep the moved file until the recovery outcome is confirmed.

## 44. Partial reset: key bindings only

With PTL stopped, preserving then moving:

```text
~/.persona_training_lab/key_bindings.json
```

causes a later `KeyBindingManager` instance to use defaults because the file is absent.

This does not reset the workspace, Style preferences, Agents history, or shell QSettings.

Prefer rename/copy over immediate deletion until the result is verified.

## 45. Partial reset: SQLite only is dangerous

Replacing/removing only `app.db` while leaving the rest of the workspace can create split state:

```text
old artifacts + old Agents JSON + old recipes
new/empty SQLite metadata
```

That state may be useful for a deliberate forensic experiment, but it is not a normal clean reset.

For a normal fresh start, move the whole workspace root together.

## 46. Restoring only `app.db`

A database-only restore may be appropriate only when you deliberately understand and accept the split-state consequences.

Potential mismatches include model-version paths referencing other artifact bytes, Agents JSON from another semantic snapshot, recipes from another date, logs/events not matching external effects, and external Dataset bytes differing from stored approval hashes.

Prefer whole-workspace restore.

## 47. Restoring only artifacts

Copying artifact directories without their corresponding Training/model-version metadata produces files PTL may not know how to identify through normal lineage/registry workflows.

Artifact bytes are valuable, but they are not a substitute for database/provenance state.

Restore the matching workspace snapshot when possible.

## 48. Recovering after a failed Training run

Do not edit the failed run back to `ready` manually.

Preserve run row/logs, correlation/error IDs, partial artifacts if present, application logs, and Profile/Dataset/model input identity.

Correct the underlying condition, then create a new Training run if the original terminal run is not designed to be restarted.

A failed run is research/diagnostic evidence.

## 49. Recovering after a crash during Training

After restart:

1. allow runtime orphan recovery to run;
2. inspect the old Training run status/logs;
3. inspect the expected artifact directory for partial output;
4. do not assume partial model files are a valid completed artifact;
5. verify Dataset/Profile/model state before a new run;
6. preserve interrupted output if useful for diagnosis.

The v1.0 backend does not expose a general resumable checkpoint/restart contract.

## 50. Recovering after Automation cancellation/timeout/crash

For cancellation/timeout, PTL attempts to terminate the contained process tree.

After abnormal application/OS termination, verify host state explicitly: output files, external files/directories, service/process state, partial command output, Automation audit, and runtime-operation state.

Do not assume workspace restore reverses an external command effect.

## 51. Recovering after a failed Agents delete/redo

Agents destructive transitions use runtime leases and protected history/resource-link handling.

If a delete/redo is blocked, resolve the active resource blocker and retry through the UI.

Do not manually delete lineage resource links to make the button work.

If a true persistence failure occurs mid-transition, preserve the workspace and use last-known-good backup/evidence rather than editing state piecemeal.

## 52. Recovering from an apparently stale Agents graph

A background projection failure can intentionally retain the last-good semantic graph.

Before restoring/resetting anything:

1. inspect Issues/logs;
2. verify the source Dataset/Training/model/evaluation records actually exist;
3. allow/trigger a later healthy refresh;
4. distinguish persisted semantic data from local Agents presentation state.

An old but coherent last-good graph is not equivalent to corrupted persistence.

## 53. Recovering from a missing external Dataset source

The stored approval hash cannot restore missing bytes.

If the exact source was backed up, restore it to the expected path or intentionally re-run the Dataset workflow for a changed path/state. Create a new Training run when authorized input identity changes.

Do not fabricate a file merely to satisfy the stored path.

## 54. Recovering from a replaced base-model directory

Because v1.0 stores a path/reference rather than a complete model-directory hash, PTL cannot automatically reconstruct or prove previous base-model bytes.

If exact identity matters, restore the separately preserved model revision/checksum.

A model path becoming readable again is not proof that it is the same model used by an older Training run.

## 55. Recovery evidence before destructive action

Capture at least:

```text
PTL commit/version
OS
workspace root
backup timestamp/source
operation/error/correlation IDs
relevant Issues/Activity/logs
affected entity IDs
artifact/model/Dataset paths
whether crash/force-kill/manual edit/restore preceded the issue
key-binding storage state when input configuration is involved
Qt shell-state relevance when geometry/docks/session are involved
```

When recovery concerns Agents, preserve `agents_lineage_state.json` and matching `app.db` together.

When recovery concerns Automation, preserve relevant audit metadata and inspect external effects separately.

## 56. Backup privacy

A whole workspace can contain private research material and operational metadata.

Potentially sensitive areas include Profiles, Dataset metadata/paths, experiment responses, Training logs/metadata, model artifacts, Agents local research labels/history, Automation recipe manifests, event/audit metadata, and filesystem paths/usernames.

External presentation stores can also reveal user behavior/preferences:

```text
key_bindings.json -> customized input mappings
QSettings         -> shell layout / last workspace
```

PTL does not add an application-level encryption layer to these stores. Protect backups according to their sensitivity and do not publish complete state without review.

## 57. Backup integrity verification

PTL v1.0 does not currently produce a signed whole-workspace backup manifest.

For high-value research backups, operators can separately record filesystem/archive hashes using normal backup tooling.

Do not claim PTL itself cryptographically attests the whole backup when it does not.

The hashes PTL does maintain for specific contracts—such as approved Dataset bytes and Training Profile representation—have narrower meanings.

## 58. Suggested backup cadence

PTL does not enforce a schedule.

A practical operator policy is to create a backup before actions expensive to reconstruct, such as large Training runs, major Dataset/Profile changes, substantial Agents history reorganization, recipe/toolchain changes, schema/version experiments, or destructive recovery/reset work.

The cadence remains operator/research policy rather than a v1.0 application guarantee.

## 59. Developer/source checkout backup is separate

Git is the source-code/version-history mechanism; the PTL workspace is runtime/research state.

Backing up the repository does not back up the default user workspace, QSettings, or the user-home binding file.

Backing up the PTL workspace does not preserve uncommitted source changes.

For reproducible development investigation preserve the identities separately:

```text
Git commit/branch/worktree state
PTL workspace snapshot
external research dependencies
external presentation state when relevant
```

Do not mix them by storing runtime `app.db`/Agents state inside `src/`, `tests/`, or `tools/`.

## 60. Recovery acceptance checklist

Before declaring a restore/recovery successful:

1. PTL launches normally;
2. expected workspace root is active;
3. SQLite-backed entities are present;
4. Agents local state matches the intended snapshot;
5. referenced artifact paths exist;
6. required external Dataset/model/Automation dependencies exist;
7. no unexpected active runtime operations remain;
8. Issues/logs show no unresolved recovery errors;
9. local-model readiness is rechecked before inference/Training;
10. a small non-destructive workflow succeeds before large/destructive work resumes;
11. if exact input personalization was part of the restore, bindings match the intended snapshot;
12. if exact shell presentation was part of the restore, geometry/docks/current workspace match the intended snapshot.

For source/release work, validate the source checkout independently with the release gate after it is clean.

## 61. Current v1.0 recovery boundaries

PTL v1.0 does not claim:

- atomic hot backup of the complete multi-file workspace;
- automatic capture of external Dataset/model/Automation dependencies;
- automatic capture of Qt QSettings/key-binding state inside a workspace backup;
- portable cross-platform backup path for native Qt settings;
- automatic rollback of trusted-host command effects;
- automatic repair of arbitrary SQLite corruption/manual edits;
- arbitrary database downgrade compatibility;
- distributed/multi-host workspace locking;
- resumable Training from an interrupted partial artifact;
- cryptographic whole-workspace backup signing;
- reconstruction of an unpreserved base-model revision from its historical path alone.

These are explicit operating boundaries.

## 62. Developer invariants

Backup/recovery changes must preserve these rules unless the product contract is deliberately revised:

1. workspace ownership remains independent of process CWD;
2. `app.db` is not documented as the complete backup by itself;
3. Agents local JSON and SQLite semantic state remain distinguishable;
4. external Dataset/model/Automation dependencies remain explicitly external when they are external;
5. QSettings and the user-home key-binding JSON remain explicitly outside the workspace while code stores them there;
6. manual workspace backup guidance remains offline until PTL implements/audits a coordinated hot-backup contract;
7. runtime orphan recovery must not be described as external side-effect rollback;
8. artifact/model deletion must not be presented as cache cleanup;
9. recovery procedures prefer reversible rename/copy steps over immediate deletion;
10. version/schema compatibility claims must not exceed implemented migrations;
11. key-binding format compatibility must be documented separately from SQLite schema compatibility;
12. recovery documentation must be updated whenever a persistence location or atomicity boundary moves.

## Next steps

- Workspace ownership/details: [Workspace & Storage](workspace-and-storage.md)
- Exact store/path matrix: [Workspace layout reference](../reference/workspace-layout.md)
- Diagnose before modifying state: [Troubleshooting](troubleshooting.md)
- Local models/reproducibility: [Local Models](local-models.md)
- Input personalization: [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md)
- Training provenance: [Training](../user-guide/training.md)
- Agents state/history: [Agents lineage](../user-guide/agents-lineage.md)
- Automation external-effects boundary: [Automation](../user-guide/automation.md)
- Stable guarantees/non-goals: [v1.0 Product Contract](../reference/v1-product-contract.md)