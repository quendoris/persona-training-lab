# Persistence Architecture

This document describes the actual Persona Training Lab v1.0 persistence architecture: ownership, connection/transaction boundaries, repository contracts, SQLite configuration, filesystem state, Agents local state, Qt shell settings, user-home key bindings, runtime leases, and cross-medium consistency limits.

It is an architecture document rather than a backup tutorial. For operator procedures, see [Workspace & Storage](../operations/workspace-and-storage.md), [Backup, Reset & Recovery](../operations/backup-reset-recovery.md), and the [Workspace layout reference](../reference/workspace-layout.md).

The central rule is:

> **PTL does not have one universal persistence mechanism or one global transaction. SQLite is the primary structured research/workflow store; Agents local organization, generated artifacts, Automation manifests, external model/Dataset inputs, logs, Qt shell settings, and the user-home key-binding file have distinct ownership and atomicity boundaries.**

## 1. Persistence topology

The production topology is approximately:

```text
                              Persona Training Lab
                                      │
              ┌───────────────────────┼────────────────────────┐
              │                       │                        │
        workspace state        user/platform state       external inputs/effects
              │                       │                        │
      <workspace>/app.db              ├─ Qt QSettings          ├─ Dataset JSONL
              │                       │  shell geometry/docks  ├─ explicit model dirs
              ├─ domain records       │  current workspace    ├─ Automation tools/data
              ├─ Training/logs        │                        └─ trusted-host effects
              ├─ event_log            └─ ~/.persona_training_lab/
              ├─ runtime operations       key_bindings.json
              └─ lineage links
              │
              ├─ agents_lineage_state.json
              ├─ artifacts/
              ├─ automation/recipes/
              ├─ logs/
              ├─ models/ (optional)
              ├─ cache/
              ├─ temp/
              └─ exports/
```

There is no single ACID transaction that atomically commits all of these media together.

## 2. Production composition owns one primary writable SQLite connection

`build_container()` resolves workspace directories, configures logging, constructs `SQLiteDatabase(paths.sqlite_db)`, opens one writable connection, applies the additive schema bootstrap, and builds normal application repositories over that connection.

Repositories for UI preferences, events, Projects, Profiles, Agents, Analysis, Datasets, Experiments, model versions, Training, runtime operations, and lineage resource links therefore share the same primary connection in production composition.

## 3. Primary writable connection configuration

The long-lived writable connection is opened with:

```text
timeout = 30.0 seconds
check_same_thread = false
```

and applies:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
```

PTL uses application-level synchronization around repositories sharing this connection rather than Python's default same-thread SQLite restriction.

## 4. Read-only SQLite connections are a separate contract

Read-only connections apply:

```sql
PRAGMA foreign_keys = ON;
PRAGMA query_only = ON;
PRAGMA busy_timeout = 5000;
```

and are opened through a URI with:

```text
mode=ro
```

The Agents semantic-lineage loader owns one such read-only connection in its calling thread. It is not the same connection as the application's primary writable one.

## 5. WAL is not a whole-product backup format

WAL is a SQLite concurrency/recovery choice. It does not turn an online copy of `app.db` into a coordinated snapshot of SQLite + Agents JSON + artifacts + recipe files + external files + settings.

PTL v1.0 does not expose a coordinated whole-product hot-backup operation. Manual workspace backup therefore stops PTL first.

## 6. Process-local repository locking

`connection_lock(connection)` returns a `threading.RLock` keyed by the Python connection object's identity.

Repositories over the same primary connection therefore share one process-local re-entrant lock.

This lock is:

- process-local;
- connection-local;
- not distributed;
- not a filesystem lock;
- not an authorization mechanism.

It serializes use of the shared Python connection; it does not coordinate independent PTL processes on different connections/hosts.

## 7. Repository ports separate application contracts from SQLite

Application services depend on repository `Protocol` contracts rather than constructing SQLite directly.

Current examples include read/write ports for Profiles, Datasets, Training, Experiments, model versions, UI preferences, and other structured areas.

The production infrastructure supplies explicit SQLite implementations.

This is a dependency-direction boundary, not an ORM/session/unit-of-work architecture.

## 8. Repository payloads are explicit rows/records

Many persistence boundaries exchange lightweight dictionaries/records. Services and view models normalize them into stronger status/semantic objects where required.

Do not infer SQLAlchemy-style entity/session identity or an implicit transaction spanning multiple service calls.

## 9. Ordinary SQLite write boundary

Typical mutation methods use the connection as a context manager while holding the connection lock:

```python
with self._lock, self._connection:
    self._connection.execute(...)
```

A successful block commits; an exception rolls the transaction back.

Examples include normal domain mutation, Training run/log updates, event-log append, and UI preference writes.

The usual transaction boundary is the repository method, not the entire GUI action/application request.

## 10. Ordinary reads are not automatically one multi-repository snapshot

Simple repository list/get calls normally execute while holding the shared connection lock, but sequential independent calls do not imply one database snapshot across several tables/repositories.

When one coherent multi-source view matters, PTL creates an explicit transaction boundary instead.

## 11. Schema bootstrap is additive compatibility

Startup calls `create_minimal_schema(connection)` and uses `CREATE ... IF NOT EXISTS` plus explicit ensure helpers for known additions.

Known ensure paths cover later Profile, Dataset, Training, Training-log, and lineage-link fields/tables. `SQLiteUIPreferencesRepository` separately ensures its later `ui_scale` and `language` columns.

## 12. There is no universal migration history engine

The current path does not implement a generic migration ledger capable of translating arbitrary historical/future schemas or guaranteeing downgrade compatibility.

Consequences:

- known compatible older workspaces can gain expected additive columns/tables;
- arbitrary manual schema edits are not guaranteed to be repaired;
- older binaries are not promised to understand newer state;
- backup provenance should record PTL version/commit.

## 13. Core SQLite areas

Current structured tables include:

| Area | Table(s) |
|---|---|
| UI/style/localization preferences | `ui_preferences` |
| events/errors/Automation audit | `event_log` |
| Projects | `projects` |
| Profiles | `persona_profiles` |
| Agents registry | `agents` |
| evaluations/portrait runs | `experiments` |
| Datasets | `datasets` |
| Training | `training_runs`, `training_logs` |
| Analysis | `analysis_results` |
| model versions | `model_versions` |
| runtime lifecycle | `runtime_operations` |
| runtime resource claims | `runtime_operation_resources` |
| Agents/resource safety links | `lineage_resource_links` |

This table map is persistence layout, not workflow permission policy. Services define allowed transitions.

## 14. Foreign-key enforcement is enabled

PTL-created SQLite connections execute:

```sql
PRAGMA foreign_keys = ON;
```

Declared relational constraints are therefore enforced. This does not mean every semantic textual relationship/path/ID is represented as a SQL foreign key; many workflow invariants remain application logic.

## 15. SQLite UI preferences

`SQLiteUIPreferencesRepository` stores:

```text
theme
accent_palette
button_style_preset
ui_scale
language
updated_at
```

When no row exists it returns defaults. The repository treats at most one row as effective (`LIMIT 1`) and updates that row on save.

These preferences belong to the active PTL workspace because they live in `app.db`.

## 16. Shell geometry/docks/current workspace use Qt `QSettings`

`WindowStateStore` persists:

```text
shell/window_geometry
shell/dock_state
shell/current_workspace
```

through Qt `QSettings`.

Production sets organization/application identity to `Persona Training Lab` before constructing the shell.

This storage is platform/backend state outside `<workspace>/app.db`. Its native location is not one cross-platform path defined by PTL.

Missing/invalid geometry/dock byte arrays are treated as not restored rather than crashing normal shell initialization. `clear()` removes the three keys and synchronizes QSettings.

## 17. Key bindings are a third settings surface

`KeyBindingManager` does **not** store editable keyboard/mouse mappings in SQLite or QSettings.

Its default path is:

```text
~/.persona_training_lab/key_bindings.json
```

That path is user-home-relative and outside the default PTL workspace.

Therefore the current settings architecture is deliberately documented as three distinct surfaces:

```text
app.db/ui_preferences
  -> theme/accent/button preset/UI scale/language

Qt QSettings
  -> shell geometry/docks/current workspace

~/.persona_training_lab/key_bindings.json
  -> editable keyboard + mouse bindings
```

The code establishes the placement; this document does not invent an unproven historical rationale for it.

## 18. Key-binding file format/version compatibility

Current key-binding format version is:

```text
2
```

The manager explicitly supports old version:

```text
1
```

Current v2 payload contains:

```text
version
bindings
mouse_bindings
```

Version 1 contributes compatible keyboard state; mouse mappings are loaded only for the current v2 shape.

Unsupported/non-object formats are rejected with semantic UI-message state rather than treated as valid mappings.

## 19. Key-binding load repairs malformed conflict state conservatively

At load time:

- missing file leaves defaults active;
- read/JSON failure sets `keybindings.error.read`;
- unsupported root/version sets `keybindings.error.unsupported_format`;
- invalid individual keyboard entries are skipped in favor of defaults;
- duplicate keyboard sequences cause the keyboard mapping to fall back to defaults with `keybindings.error.keyboard_conflicts_repaired`;
- invalid individual mouse entries are skipped;
- conflicting mouse mappings cause mouse mappings to fall back to defaults with `keybindings.error.mouse_conflicts_repaired`.

This is recovery behavior for one settings file, not a workspace migration system.

## 20. Key-binding writes use temp-then-replace

A full mapping write creates a sibling temporary file:

```text
key_bindings.json.tmp
```

writes formatted JSON, then performs:

```python
temporary.replace(self._storage_path)
```

On `OSError`, the temporary file is cleaned up best-effort and `keybindings.error.write` is returned/stored.

This provides a single-file replacement boundary. It does **not** atomically commit with SQLite preferences, QSettings, or Agents JSON.

## 21. Profile persistence and Training identity are related but different

Profile persistence includes fields such as:

```text
title
subtitle/description
communication_style
principles
constraints
notes
status
created_at/updated_at
```

Training computes a separate SHA-256 over the exact Training-relevant Profile representation. Persistence row identity and Training input identity must not be conflated.

## 22. Dataset persistence stores metadata + external-file identity

Dataset rows persist path, format, status/count/validation data, readiness/schema metadata, and content SHA-256.

The source JSONL bytes are not copied into SQLite by import.

The path remains an external filesystem dependency. The stored SHA-256 can identify approved bytes but cannot restore a missing source file.

## 23. Training rows pin selected input identity

A Training run stores configuration and pinned identifiers/fingerprints such as:

```text
profile_id
profile_sha256
dataset_id
dataset_sha256
base_model
epochs
batch_size
learning_rate
```

Runtime fields add status/progress/metrics/timestamps/artifact/error state.

Start revalidates the current selected inputs against the pinned identity before executing.

## 24. Training logs are separate structured rows

`training_logs` stores per-run log entries independently from the rotating application logfile.

Repository listing selects a bounded newest set and returns it in chronological display order.

Do not confuse Training logs with `<workspace>/logs/persona_training_lab.log` or SQLite `event_log`.

## 25. Training artifacts are outside the SQLite transaction

A full fine-tune can write:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

The filesystem artifact write and SQLite run/model-version mutations are not one database transaction.

A crash can therefore require feature-level inspection/recovery rather than one universal rollback.

## 26. Model-version rows are registry metadata

`model_versions` persists identity/status/provenance references such as Training run and artifact path.

The model bytes remain at the referenced filesystem path. Copying/deleting database rows does not recreate/delete those bytes transactionally.

## 27. Evaluation persistence serializes the current result grammar into experiment text

The `experiments` table is compact:

```text
id
title
subtitle
status
updated_at
```

Current portrait/evaluation case structure is serialized into `subtitle` and parsed by Tests/Analysis code under the documented evaluation contract.

This is not a normalized row-per-question schema.

## 28. Event log is generic structured persistence

`event_log` stores:

```text
id
event_type
entity_kind
entity_id
correlation_id
causation_id
payload_json
occurred_at
```

Normal recent-event listing clamps requested limits to at most 500 rows.

Payload JSON schema depends on the event family. Automation uses `ptl:automation-audit:v1`; application error/notice events use their event type/field contract without a separate current `ptl:error:v1` schema marker.

## 29. Event log and rotating file log are different sinks

SQLite events support structured Operations Center/history/correlation. The rotating logfile supports diagnostic logging independently.

Application error event persistence is best-effort and may be duplicate-window throttled. An event-store failure is swallowed so it does not replace the original application workflow failure.

No one sink should be treated as an infallible complete forensic ledger.

## 30. Runtime lease acquisition has a stronger transaction boundary

Atomic runtime-operation creation uses:

```sql
BEGIN IMMEDIATE
```

inside the shared connection lock.

The transaction checks active conflicting claims and either returns blockers or inserts the operation + claims before commit.

This prevents the supported check-then-insert path from being split into unrelated transactions.

## 31. Adding claims is likewise atomic against the runtime repository path

`try_add_claims(...)` uses `BEGIN IMMEDIATE` to check conflicts excluding the current operation, verify the operation is still active, insert claims, and commit/rollback as one transaction.

This is a stronger local boundary than unrelated repository calls.

## 32. Runtime resource identity is semantic application data

Claims use:

```text
resource_kind
resource_id
access_mode = read|write
```

Duplicate operation/resource rows are prevented by the database key. Application semantics permit read/read and reject conflicts involving a write.

Claims coordinate PTL operations; they do not create filesystem locks, syscall policy, or OS permissions.

## 33. Runtime lifecycle persists crash evidence

Operations store identity/kind/subject/state/correlation/owner PID/timestamps/error information.

Startup orphan recovery can mark active operations whose owner PID no longer exists as:

```text
abandoned
```

This repairs coordination state. It does not roll back Training files or Automation host effects.

## 34. Lineage resource links are persistent safety metadata

`lineage_resource_links` maps visible/local Agents nodes to real resource identities/access modes so destructive lineage operations can query active runtime ownership.

The links bridge graph/history safety to runtime resources without making the graph the authoritative domain database.

## 35. Agents semantic lineage owns a dedicated read-only connection

`SQLiteLineageProjectionLoader` lazily opens its own read-only SQLite connection/service, reuses it for the loader instance, and explicitly closes it through `close()`.

Building after close raises rather than silently creating a new hidden lifetime.

## 36. Agents semantic lineage reads one coherent SQLite snapshot

`SQLiteLineageSnapshotRepository.read_lineage_snapshot()` holds its connection lock and executes:

```sql
BEGIN DEFERRED
```

then reads Datasets, Training runs, model versions, and evaluations before commit.

Failure rolls the transaction back.

This ensures one graph refresh is built from one coherent persisted SQLite snapshot rather than four independently timed reads.

## 37. Agents local organization is a separate JSON layer

Semantic source records remain SQLite-backed. Local research organization/history lives in:

```text
<workspace>/agents_lineage_state.json
```

including custom branches/current/archive/overrides/undo/redo/layout and protected cross-store history metadata.

The split avoids making the local presentation/history file a duplicate authoritative semantic database.

## 38. Agents JSON uses stronger file-durability steps than key bindings

`AtomicLineageStateStore` writes a temporary file, flushes/`fsync`s it, replaces the target with `os.replace(...)`, and attempts directory `fsync`. It also restores the remembered in-memory payload if persistence fails.

The key-binding file also uses temp-then-replace but does **not** implement the same explicit `fsync` sequence in the current manager.

Do not call both files “equally durable atomic stores” merely because both replace a temporary file.

## 39. Missing Agents JSON and corrupt Agents JSON differ

Missing Agents JSON produces default local state. Existing unreadable/invalid/non-object JSON raises `LineageStateLoadError` rather than silently becoming blank state.

That preserves failure evidence.

## 40. SQLite + Agents JSON is not one ACID transaction

An Agents JSON replacement and SQLite resource-link/runtime-operation transaction are different media/boundaries.

The current lineage controllers therefore use explicit orchestration/compensation where one logical action needs both stores.

For modern branch creation, `BranchCreationController`:

```text
captures exact pre-creation Agents state
  -> persists the child branch
  -> binds/inherits child SQLite safety links
  -> captures branch_create_v1 safety metadata
  -> durably attaches that metadata to the branch_create history entry
  -> only then lets the screen expose/select the child
```

If link binding fails, its SQLite transaction rolls back and the controller restores the pre-creation Agents state.

If link binding succeeded but history-metadata persistence fails, the controller restores the pre-creation Agents state first and then forgets the child links. If restoring the Agents state itself fails, it deliberately does not remove already-bound links and thereby turn a still-present branch safety-empty. `BranchCreationExecutionError` preserves original and compensation failures.

The same `branch_create_v1` metadata follows the history entry between undo/redo stacks.

Protected creation Undo is a destructive cross-store history transition. Before consuming history it verifies that the current custom subtree is exactly the recorded child, captures pre-Undo Agents state, and acquires a fresh SQLite-backed `lineage_delete` runtime lease covering that node and its linked resources. A conflict therefore leaves JSON history/state and SQLite links unchanged. After acquisition, Undo removes the branch state and exact links; link-cleanup failure restores pre-Undo Agents state and fails the lease where compensation succeeds.

If branch/link removal has committed but runtime-lease finalization fails, `BranchCreationHistoryCommittedError` carries the committed `HistoryTransition`; the composed screen applies that transition before the finalization error is reported. This is a committed-state/finalization boundary, not a rollback.

Protected creation Redo first requires the recorded child to be absent, consumes the redo entry, verifies that exactly that child was restored, and then restores the exact saved links. If link restoration fails, the controller restores the pre-Redo Agents state. The composed screen applies the visible history transition only after the controller operation succeeds.

Historical `branch_create` entries without `branch_create_v1` metadata remain on the generic compatibility history path because exact old link provenance was never persisted. Generic Undo of such an old entry can leave conservative stale link rows rather than guessing which historical links are safe to delete.

Protected branch deletion/Undo/Redo use their own lease/history compensation protocol described in [Agents lineage architecture](agents-lineage.md).

These are compensation protocols across local persistence boundaries, not a claim that JSON, safety-link transactions, and runtime leases became one database transaction.

## 41. Automation manifests are executable filesystem persistence inputs

Workspace manifests live under:

```text
<workspace>/automation/recipes/**/*.ptl-recipe.json
```

The current filesystem provider validates `ptl:automation-recipe:v1`, reports invalid/duplicate manifests through discovery issues, and keeps valid recipes available when another manifest is bad.

A manifest is ordinary mutable trusted-host configuration, not a signed database record.

## 42. Current recipe import is copy-based

Import loads/validates the selected manifest and copies it into the registry as:

```text
<recipe_id>.ptl-recipe.json
```

when source and destination differ, then reloads the imported manifest and refreshes discovery.

Companion scripts/data are not copied transactionally with the manifest.

## 43. Automation audit returns to SQLite

`AutomationAuditTrail` writes event-log rows under schema:

```text
ptl:automation-audit:v1
```

The audit records execution mode/effect scope, command hash/part count, environment keys, working directory, timeout/output bounds, resource claims, and terminal metadata.

External process side effects remain outside SQLite rollback.

## 44. Local models can be workspace-local or external

The default model reference resolves under:

```text
<workspace>/models/qwen3.5-0.8b
```

but explicit paths can live elsewhere.

Training stores/resolves the path/reference and selected downstream fingerprints; v1.0 does not hash the entire base-model directory into the Training run.

## 45. File logs are another persistence surface

Production rotating logs live under:

```text
<workspace>/logs/persona_training_lab.log
```

Log-file creation failure is non-fatal to startup.

SQLite `event_log`, Training logs, and the rotating logfile have distinct availability/failure semantics.

## 46. Workspace directory names have different authority

- `cache/`: intended for regenerable cache;
- `temp/`: temporary workspace material;
- `exports/`: user-facing output whose regenerability depends on producer;
- `artifacts/`: persistent generated workflow output and **not** routine cache;
- `models/`: model inputs, potentially authoritative for reproducibility.

“Clean workspace” must not indiscriminately delete them as one class.

## 47. Source tree is not a runtime persistence backend

`README.md`, `src/`, `tests/`, `tools/`, docs and packaged assets are source/project material.

Release policy rejects hidden ignored runtime-affecting files under source/test/tool trees outside narrow debris exceptions.

Mutable runtime state must not silently become package/CWD-relative input simply because a checkout is editable.

## 48. Atomicity boundaries are local

Current strong/local examples include:

```text
repository write      -> SQLite transaction
runtime lease acquire -> BEGIN IMMEDIATE check + insert
lineage source read   -> BEGIN DEFERRED multi-table snapshot
Agents JSON save      -> temp + fsync + replace (+ dir fsync attempt)
key bindings save     -> sibling .tmp + replace
QSettings save        -> Qt/native settings backend contract
```

None implies one transaction across:

```text
SQLite
+ Agents JSON
+ model artifacts
+ external Dataset/model/tool files
+ Automation host effects
+ Qt QSettings
+ key_bindings.json
```

Cross-boundary workflows need explicit orchestration and recovery rules.

## 49. Failure semantics should preserve previous authoritative state where possible

Examples:

- SQLite transactions roll back on exceptions;
- runtime lease acquisition rolls back on blockers/errors;
- lineage snapshot rolls back on read failure;
- Agents atomic store restores its remembered previous payload if save fails;
- branch creation restores exact pre-creation Agents state when child link binding fails after the JSON mutation;
- branch creation restores state before removing already-bound links when later history-metadata persistence fails;
- protected branch-creation Undo acquires a fresh destructive lease before history mutation and leaves state unchanged on conflict;
- protected branch-creation Undo refuses an unexpected current descendant subtree before mutating history;
- protected branch-creation Undo restores pre-Undo Agents state and fails the lease if child-link cleanup fails;
- protected branch-creation Undo reports a committed transition separately if only lease finalization fails after state/link removal;
- protected branch-creation Redo validates target identity and restores pre-Redo Agents state if exact link restoration fails;
- cross-store creation failures expose `BranchCreationExecutionError` when compensation itself also fails instead of hiding the partial outcome;
- invalid persisted key-binding conflicts fall back to known defaults rather than activating ambiguous mappings;
- failed background lineage refresh retains last-good projection in the UI integration layer.

These are boundary-specific protections, not universal rollback.

## 50. Stable IDs outrank labels

Persistence/workflows use IDs such as:

```text
profile_id
dataset_id
run_id
model_version_id
experiment_id
operation_id
node/resource identity
```

Human titles are presentation/provenance and are not guaranteed globally unique.

Lineage projection prefers modern persisted IDs when available and uses older title-like compatibility data only where required.

See [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md) for exact current ID shapes and machine-string taxonomy.

## 51. Timestamps are metadata, not synchronization locks

`created_at`/`updated_at`/runtime timestamps support ordering/history/diagnostics.

Runtime conflict correctness is based on active state/resource identity under transactional acquisition, not merely wall-clock comparison.

Do not turn `updated_at` into an optimistic lock/version token unless a future contract explicitly defines it.

## 52. Persistence and localization are separate concerns

Canonical status/result semantics should remain machine-readable and locale-neutral. Compatibility aliases may accept historical rendered text, but new persistence should write canonical values.

Changing UI language must not mutate domain meaning.

## 53. Backup boundary follows topology

A conservative **research/workflow** backup preserves the whole workspace:

```text
app.db
agents_lineage_state.json
artifacts/
automation/recipes/
workspace-local models when required
other workspace state
```

For Agents specifically, `app.db` contains current `lineage_resource_links`, while `agents_lineage_state.json` contains local branch/history state and can contain `branch_create_v1` / `branch_delete_v1` metadata describing the safety identity expected by protected history. Those two files should therefore come from the same offline workspace backup snapshot rather than independently selected backup generations.

The backup separately preserves external Dataset/model/Automation dependencies when required.

For exact UI/input-personalization restoration it also separately preserves:

```text
Qt QSettings shell state
~/.persona_training_lab/key_bindings.json
```

Those two are not part of the whole-workspace backup merely because PTL uses them.

## 54. Security/privacy follows every storage surface

PTL's SQLite, JSON, artifacts, logs, recipe manifests, key-binding JSON, and Qt settings are ordinary host/platform state. v1.0 does not add a product-wide encryption layer.

Confidentiality therefore depends on OS/filesystem/storage policy.

See [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md).

## 55. Current persistence non-goals

The v1.0 architecture does not claim:

- one global ACID transaction across SQLite/filesystem/platform/external effects;
- a general arbitrary schema migration/downgrade engine;
- distributed/multi-host locking;
- encrypted database/workspace/settings storage;
- signed whole-workspace snapshots;
- automatic content-addressing of complete base-model directories;
- automatic copying of Dataset source bytes into SQLite;
- transactional artifact garbage collection from Agents branch deletion;
- automatic reconstruction of exact safety metadata for historical branch-creation history entries that never stored it;
- hot whole-workspace backup atomicity;
- automatic inclusion of QSettings/key bindings in a workspace backup;
- one universal settings database;
- process-independent synchronization through the Python `RLock` registry.

## 56. Developer invariants

Persistence changes must preserve these current rules unless the architecture/product contract is deliberately revised:

1. research/workflow mutable state must not become source-CWD/package-relative hidden input;
2. normal production repositories sharing the primary connection share connection-level synchronization;
3. PTL-created SQLite connections keep foreign-key enforcement enabled;
4. multi-source semantic lineage remains one coherent database snapshot;
5. runtime claim check+acquire remains atomic against supported competing lease acquisition;
6. Agents local JSON remains distinguishable from authoritative semantic SQLite records;
7. cross-store workflows are not documented as globally atomic when they rely on orchestration/compensation;
8. a newly created custom Agents branch is not exposed as successfully created before its required persisted safety-link bind and history-metadata attachment succeed;
9. metadata-bearing branch-creation Undo acquires a fresh destructive runtime lease before removing current branch/link state;
10. metadata-bearing branch-creation Undo/Redo keeps JSON branch state and SQLite safety links consistent or restores the previous state before UI exposure;
11. committed state/link removal is not documented as rolled back when only runtime-lease finalization failed;
12. Training artifacts remain distinct from disposable cache;
13. external Dataset/model/Automation dependencies remain visibly external when external;
14. Qt shell state remains documented outside workspace/SQLite while `WindowStateStore` uses QSettings;
15. key bindings remain documented outside workspace/SQLite/QSettings while `KeyBindingManager.default_storage_path()` points to the user-home JSON;
16. key-binding file format compatibility is not conflated with SQLite schema compatibility;
17. schema compatibility claims do not exceed implemented additions;
18. canonical machine status/identity is not replaced by localized display text;
19. backup/recovery docs are updated whenever a persistence location/atomicity boundary moves.

## 57. Audit questions for future persistent features

Before merging a new persistent feature, answer:

```text
Where is authoritative state?
Who owns the path/connection/backend?
Is it workspace-local, QSettings, user-home config, or external?
What stable ID names the object?
What format/schema version exists?
What transaction/atomic-replace boundary exists?
Does the write fsync durable state or only replace a file?
Which other stores must change with it?
What happens if a later store fails?
How is recovery performed?
Does whole-workspace backup include it?
Does whole-workspace reset remove it?
Does it contain private data?
Can background threads access it safely?
Does lineage need it in one coherent projection snapshot?
```

If those answers are not explicit, the feature is not persistence-complete merely because it can write a row/file.

## Related documentation

- [Architecture Overview](overview.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [UI shell architecture](ui-shell.md)
- [Agents lineage architecture](agents-lineage.md)
- [Automation architecture](automation.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md)
- [Workspace layout reference](../reference/workspace-layout.md)
- [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md)
- [Keyboard & mouse bindings reference](../reference/keyboard-mouse-bindings.md)
- [Training pipeline specification](../training_pipeline.md)
- [Evaluation contract](../reference/evaluation-contract.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
