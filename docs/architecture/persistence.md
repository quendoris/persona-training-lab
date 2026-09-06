# Persistence Architecture

This document describes the actual Persona Training Lab v1.0 persistence architecture: ownership, connection/transaction boundaries, repository contracts, SQLite configuration, filesystem state, Agents local state, Qt shell settings, runtime leases, and cross-medium consistency limits.

It is an architecture document rather than a backup tutorial. For operator procedures, see [Workspace & Storage](../operations/workspace-and-storage.md) and [Backup, Reset & Recovery](../operations/backup-reset-recovery.md).

The central rule is:

> **PTL does not have one universal persistence mechanism or one global transaction. SQLite is the primary structured state store; Agents local organization, generated artifacts, Automation manifests, external model/Dataset inputs, logs, and Qt shell settings have distinct ownership and atomicity boundaries.**

## 1. Persistence topology

The production topology is approximately:

```text
                         Persona Training Lab
                                │
                    ┌───────────┴───────────┐
                    │                       │
              main SQLite DB          filesystem / platform
               <workspace>/              state
                  app.db                    │
                    │                       ├─ agents_lineage_state.json
                    │                       ├─ artifacts/
                    │                       ├─ automation/recipes/
                    │                       ├─ logs/
                    │                       ├─ models/ (optional)
                    │                       ├─ external Dataset/model/tool files
                    │                       └─ Qt QSettings shell state
                    │
       ┌────────────┼────────────────────────────────────┐
       │            │            │           │           │
    domain       Training     event log    runtime     lineage
    records       logs                    operations    links
```

There is no single ACID transaction that atomically commits all of those media together.

## 2. Production composition owns one primary writable SQLite connection

`build_container()` performs the primary application composition.

It:

1. resolves/creates workspace directories;
2. configures logs;
3. constructs `SQLiteDatabase(paths.sqlite_db)`;
4. opens one writable SQLite connection;
5. applies the minimal/additive schema bootstrap;
6. constructs the normal application repositories over that same connection;
7. injects those repositories into services/view-models.

Repositories for UI preferences, events, Projects, Profiles, Agents, Analysis, Datasets, Experiments, model versions, Training, runtime operations, and lineage resource links therefore share the same primary connection in production composition.

## 3. The primary writable connection is long-lived application state

The composition root keeps repositories/services that hold the primary connection for the running application lifetime.

The connection is opened with:

```text
timeout = 30.0 seconds
check_same_thread = false
```

PTL uses application-level synchronization around shared repository access rather than relying on SQLite's default Python same-thread restriction for this connection.

This is distinct from the lineage read-only loader described later.

## 4. SQLite connection configuration

Writable connections apply:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
```

Read-only connections apply:

```sql
PRAGMA foreign_keys = ON;
PRAGMA query_only = ON;
PRAGMA busy_timeout = 5000;
```

The read-only connection is opened through a URI using:

```text
mode=ro
```

These settings are implementation facts, not a promise that arbitrary contention/failure workloads are fully solved.

## 5. WAL is a database-concurrency/recovery choice, not a backup format

WAL permits readers/writers to coexist under SQLite's WAL semantics and is used by the normal writable database.

It also means an online filesystem copy of only `app.db` is not the documented PTL backup contract.

PTL v1.0 does not expose one coordinated hot-backup operation that freezes SQLite plus Agents JSON plus artifacts/recipes/external state.

The manual operator contract therefore stops PTL before copying the whole workspace.

## 6. Process-local repository locking

`connection_lock(connection)` returns one `threading.RLock` keyed by the Python connection object's identity.

Every repository using that same connection and this helper receives the same process-local lock.

This provides serialization/reentrancy around repository operations sharing the connection.

It is:

- process-local;
- connection-local;
- not a distributed lock;
- not an OS/filesystem access-control mechanism.

## 7. Why one lock is shared across repositories

The lock registry is keyed by `id(connection)` rather than repository type.

Therefore two repositories over the same SQLite connection coordinate through one `RLock` instead of each protecting only its own methods with unrelated locks.

This matters because Python exposes one shared connection with `check_same_thread=False` to multiple application services/workers.

## 8. Repository ports separate application contracts from SQLite

The application layer defines `Protocol` contracts for read/write responsibilities such as:

```text
UIPreferencesRepositoryPort
ProfilesReadRepositoryPort
ProfilesWriteRepositoryPort
DatasetsReadRepositoryPort
DatasetsWriteRepositoryPort
TrainingReadRepositoryPort
TrainingWriteRepositoryPort
ExperimentsRead/WriteRepositoryPort
ModelVersionsRead/WriteRepositoryPort
```

Application services depend on those behavioral contracts rather than directly constructing SQL.

The production infrastructure supplies SQLite implementations.

This is a dependency-direction boundary, not an ORM.

## 9. Repository payloads are currently lightweight dictionaries/records

Many repository boundaries exchange `dict[str, ...]` payloads rather than persistence-domain ORM entities.

Services/view-models normalize those rows into stronger semantic objects/status enums where required.

The persistence layer therefore remains explicit SQL + mapping code.

Do not infer SQLAlchemy-style unit-of-work/session semantics; there is no ORM session in the current architecture.

## 10. Ordinary repository writes use connection transactions

Typical mutation methods use:

```python
with self._lock, self._connection:
    self._connection.execute(...)
```

Python's SQLite connection context manager commits the successful block and rolls it back when the block exits through an exception.

Examples include:

- Training run creation/update/log append;
- event-log append;
- UI preference save/schema additions;
- normal domain repository mutations.

The transaction boundary is normally the individual repository method, not an implicit global application request.

## 11. Reads normally acquire the shared lock without opening an explicit transaction

Simple list/get methods generally execute their SELECT while holding the shared connection lock.

They do not automatically combine several independent repository calls into one coherent database snapshot.

When coherence across multiple source sets matters—most notably Agents semantic lineage—PTL uses a dedicated snapshot path instead of assuming sequential list calls are atomic together.

## 12. Schema bootstrap is additive compatibility, not a general migration framework

Startup calls `create_minimal_schema(connection)`.

It uses `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` and explicit column/table ensure helpers for known additions.

Current ensure paths include later fields/tables for:

- Profile content/created time;
- Dataset path/validation/hash fields;
- Training input IDs/hashes/hyperparameters/runtime fields;
- Training logs;
- lineage resource links.

`SQLiteUIPreferencesRepository` also ensures its later `ui_scale` and `language` columns.

## 13. There is no general schema-version migration engine in this path

The current schema code does not implement a universal migration history capable of translating arbitrary historical/future database shapes.

Known additive changes are handled explicitly.

Consequences:

- opening a known older compatible workspace can gain expected missing columns/tables;
- arbitrary manual schema edits are not promised to be repaired;
- downgrade compatibility is not generally guaranteed;
- backup provenance should record the PTL version/commit.

## 14. Core SQLite tables

Current structured areas include:

| Area | Table(s) |
|---|---|
| UI/style preferences | `ui_preferences` |
| events/errors/Automation audit | `event_log` |
| Projects | `projects` |
| Profiles | `persona_profiles` |
| Agents registry | `agents` |
| evaluations/portrait runs | `experiments` |
| Datasets | `datasets` |
| Training | `training_runs`, `training_logs` |
| Analysis | `analysis_results` |
| model versions | `model_versions` |
| runtime operation lifecycle | `runtime_operations` |
| runtime resource claims | `runtime_operation_resources` |
| Agents/resource safety links | `lineage_resource_links` |

This table map is not permission/ownership policy by itself; services define allowed workflow transitions.

## 15. Foreign-key enforcement is enabled on PTL-created SQLite connections

Connections execute:

```sql
PRAGMA foreign_keys = ON;
```

For example, runtime operation resource rows reference operation IDs with `ON DELETE CASCADE` in the schema.

Foreign keys protect declared relational constraints only. Many semantic relationships—such as stored textual IDs/path provenance—remain enforced in application logic rather than through every possible SQL foreign key.

## 16. UI/style preferences in SQLite

`ui_preferences` stores the Style/localization preference surface handled by `SQLiteUIPreferencesRepository`:

```text
theme
accent_palette
button_style_preset
ui_scale
language
updated_at
```

When no row exists, the repository returns defaults rather than requiring bootstrap seed data.

The repository uses at most one effective preference row (`LIMIT 1`) and updates that row when saving.

## 17. Shell geometry/docks/current workspace are **not** in SQLite

`WindowStateStore` persists:

```text
shell/window_geometry
shell/dock_state
shell/current_workspace
```

through Qt `QSettings`.

Production sets Qt organization/application identity to `Persona Training Lab` before the shell is created.

This is a separate platform settings backend outside the PTL workspace/`app.db` ownership model.

The split is deliberate current behavior and must be visible in backup/reset documentation.

## 18. Invalid/missing shell state is non-fatal

`WindowStateStore.restore(...)` treats missing/invalid geometry/dock byte arrays as “not restored” rather than raising through normal shell initialization.

The saved workspace key is read independently.

`clear()` removes the three shell keys and synchronizes `QSettings`.

Tests use an explicit INI `QSettings` instance to prove round-trip and invalid-state handling without relying on the host's native settings store.

## 19. Profiles persist editable persona fields, not just display labels

The Profile table includes fields used by the training-input rendering path such as:

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

Training computes a separate fingerprint of the exact Training-relevant representation at run creation.

Persistence identity and Training input identity are therefore related but not identical concepts.

## 20. Dataset persistence stores metadata plus external-file identity

The Dataset table stores metadata such as:

```text
path
format
status
record_count
valid_count
invalid_count
validation_errors_preview
content_sha256
schema/readiness metadata
```

The source JSONL bytes themselves are not copied into SQLite by import.

The path remains an external filesystem dependency; the SHA-256 is an integrity identity for approved content, not storage of that content.

## 21. Training rows pin input identity

A Training run persists both user-facing configuration and pinned input identifiers/fingerprints:

```text
profile_id
profile_sha256
dataset_id
dataset_sha256
base_model
mode
epochs
batch_size
learning_rate
```

Runtime state adds fields such as:

```text
status
progress
epoch_progress
loss
speed
checkpoints_count
started_at
finished_at
artifact_path
error_message
```

Training launch revalidates the current inputs against the persisted pinned identity.

## 22. Training logs are a separate append-only-by-workflow table

`training_logs` stores:

```text
id
run_id
level
message
created_at
```

The repository generates log IDs and timestamps for each append.

Listing retrieves newest rows then returns them in chronological display order for the selected limit.

These logs are distinct from the rotating application log under `<workspace>/logs/`.

## 23. Training filesystem artifacts are outside the SQLite transaction

A successful full fine-tune writes files such as:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

SQLite subsequently/otherwise stores the artifact path/provenance state through the workflow.

Filesystem model writes and SQLite row updates are not one SQLite transaction.

A crash can therefore require feature-level recovery/inspection rather than relying on one database rollback to restore the entire Training world.

## 24. Model-version persistence is registry metadata, not a second artifact store

`model_versions` persists model-version identity/status and provenance references including:

```text
base_model
profile_title
dataset_title
training_run_id
artifact_path
quality_summary
created_at/updated_at
```

The actual model bytes remain at the referenced artifact path.

Deleting/copying the database alone does not recreate those bytes.

## 25. Evaluation persistence currently serializes structured cases into experiment text

The `experiments` table is intentionally compact:

```text
id
title
subtitle
status
updated_at
```

Current portrait/evaluation structure is serialized into the `subtitle` payload and parsed by the evaluation/Analysis code.

This is a versioned compatibility surface described by the evaluation contract, not a normalized SQL row-per-question schema.

## 26. Event log is structured but intentionally generic

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

The repository limits normal recent-event queries to at most 500 rows even when a larger limit is requested.

The payload is JSON text whose schema depends on the event family, for example application errors/notices or `ptl:automation-audit:v1` records.

## 27. Event logging is not the same as the rotating application log

The SQLite event log supports structured UI/Operations Center history and correlation.

The rotating file log captures diagnostic logging independently.

Application error reporting is deliberately best-effort: event-log append failure is swallowed so an event-store problem does not replace the original application workflow failure.

Therefore no single logging sink should be treated as an infallible complete forensic ledger.

## 28. Runtime-operation persistence has a stronger lease-acquisition transaction

Atomic runtime lease creation uses:

```sql
BEGIN IMMEDIATE
```

inside the shared connection lock.

Within that transaction PTL:

1. reads active conflicting resource claims;
2. rolls back and returns blockers when a conflict exists; or
3. inserts the operation;
4. inserts its resource claims;
5. commits.

This prevents the normal check-then-insert lease path from being split into unrelated transactions within the database contract.

## 29. Adding claims to an existing operation is also atomic

`try_add_claims(...)` similarly uses `BEGIN IMMEDIATE` to:

- check conflicts excluding the current operation;
- verify the target operation still exists and is active;
- insert additional claims;
- commit or rollback as one transaction.

This is a deliberate stronger boundary than ordinary unrelated repository calls.

## 30. Runtime resource identity is semantic application data

Claims use:

```text
resource_kind
resource_id
access_mode = read|write
```

The database prevents duplicate `(operation_id, resource_kind, resource_id)` rows through the primary key.

Conflict semantics are defined in application/runtime logic: read/read can coexist; any competing write conflicts.

The database does not turn these claims into filesystem locks or OS permissions.

## 31. Runtime lifecycle survives process crashes as persisted evidence

Operations store:

```text
operation ID/kind
subject identity
state
correlation ID
owner PID
start/heartbeat/finish timestamps
error message
```

Startup orphan recovery can convert active operations whose recorded owner PID is no longer alive to `abandoned`.

That repairs persistence/coordination state; it is not a rollback of filesystem/Automation side effects.

## 32. Lineage resource links are persistent safety metadata

`lineage_resource_links` maps Agents node IDs to real resource identities/access modes.

They allow destructive local lineage operations to ask whether a visible/custom node represents resources currently involved in active runtime work.

These rows connect the local graph/history world to runtime-operation safety without making the graph itself the authoritative domain database.

## 33. Agents semantic lineage uses a dedicated read-only connection

`SQLiteLineageProjectionLoader` lazily creates its own `SQLiteDatabase(...).connect_read_only()` connection.

That connection uses:

```text
mode=ro
check_same_thread=true
query_only=ON
```

and is owned by the loader in its calling thread.

This deliberately differs from the long-lived primary writable application connection.

## 34. The lineage loader has explicit lifetime ownership

The loader creates the read-only connection/service on first `build_snapshot()` and reuses it for that loader instance.

`close()`:

- marks the loader closed;
- drops service/connection references;
- closes the connection when it exists.

Calling `build_snapshot()` after close raises.

This makes worker/read-projection connection ownership explicit.

## 35. Semantic lineage reads one coherent SQLite snapshot

`SQLiteLineageSnapshotRepository.read_lineage_snapshot()` acquires its connection lock and executes:

```sql
BEGIN DEFERRED
```

then reads, in one transaction:

```text
Datasets
Training runs
model versions
evaluations
```

It commits on success and rolls back on failure.

This is stronger than performing four independent repository list calls at different times.

## 36. Why Agents needs the snapshot path

Agents builds cross-entity relationships.

If Dataset, Training, model-version, and evaluation sets were read independently while writes occurred between them, one graph refresh could combine states that never coexisted as one committed database view.

The dedicated read transaction avoids that class of projection inconsistency within SQLite.

## 37. Agents local organization is a separate JSON persistence layer

Semantic lineage source records remain in SQLite.

Agents local research organization/history lives in:

```text
<workspace>/agents_lineage_state.json
```

This includes custom branches/current/archive/overrides/undo/redo/layout state.

The split avoids duplicating the complete semantic domain graph into a second authoritative database.

## 38. Agents JSON writes use atomic replacement

`AtomicLineageStateStore` saves by:

1. deep-copying the payload;
2. serializing JSON;
3. creating a temporary file in the target directory;
4. writing/flushing it;
5. `fsync`ing the temporary file;
6. replacing the target with `os.replace(...)`;
7. attempting directory `fsync`;
8. updating the remembered persisted payload.

If save fails before completion, the in-memory payload is restored to the previous persisted copy and the temporary file is cleaned up best-effort.

## 39. Atomic file replacement is not a cross-store transaction

The Agents JSON save can be atomic as a file replacement while SQLite resource-link changes are a different persistence medium/transaction.

Protected lineage workflows therefore use explicit transaction/compensation orchestration described in [Agents lineage architecture](agents-lineage.md) rather than pretending SQLite and JSON share one ACID transaction manager.

This is an important architecture boundary.

## 40. Missing Agents JSON is different from corrupt Agents JSON

When the JSON file is absent, the store returns default local state.

When the file exists but cannot be read, is invalid JSON, or has a non-object root, the atomic store raises `LineageStateLoadError`.

The system does not silently translate malformed existing data into a blank state in that load path.

This preserves evidence instead of quietly discarding an unreadable persisted file.

## 41. Automation recipe manifests are executable persistence inputs

Workspace recipe manifests live under:

```text
<workspace>/automation/recipes/**/*.ptl-recipe.json
```

The recipe provider scans these files, validates `ptl:automation-recipe:v1`, and reports malformed/duplicate entries without making one bad manifest erase all valid recipes.

A manifest is ordinary mutable filesystem state, not a signed database record.

## 42. Recipe Import is copy-based persistence

Import:

1. resolves/loads/validates the selected source manifest;
2. copies it to `<registry>/<recipe_id>.ptl-recipe.json` when source and destination differ;
3. reloads/validates the copied manifest;
4. refreshes discovery state.

Companion scripts/data are not transactionally copied with it.

## 43. Automation audit is persisted back into SQLite

Production composition passes `AutomationAuditTrail(event_log_repo)` to the Automation service.

Audit events are normal structured event-log rows with schema marker:

```text
ptl:automation-audit:v1
```

The audit includes command hash/part count, environment keys, working directory, effect scope, timeout/output bounds, claims, and terminal metadata.

The executed external side effects themselves are not persisted/rolled back by SQLite.

## 44. Local models can be workspace-local or external

The default model reference resolves under:

```text
<workspace>/models/qwen3.5-0.8b
```

but an explicit absolute model path can live elsewhere.

Training stores the resolved base-model path/reference but not a whole-directory content hash.

Persistence therefore captures the reference and selected downstream fingerprints, not every input byte required for exact rerun.

## 45. Logs are filesystem persistence, not SQLite state

The normal structured application file log lives under:

```text
<workspace>/logs/persona_training_lab.log
```

with rotation.

Log creation failure is non-fatal to application startup.

SQLite `event_log` and the rotating file log overlap in purpose but have separate availability/failure boundaries.

## 46. Cache/temp/export directories have different authority levels

The directory names are not interchangeable persistence classes:

- `cache/`: intended for regenerable cache material;
- `temp/`: temporary workspace material;
- `exports/`: user-facing output whose reproducibility depends on the producer;
- `artifacts/`: persistent generated workflow output and **not** routine cache.

Architecture/recovery code must not implement “clean workspace” by deleting all four indiscriminately.

## 47. Source tree is not a runtime persistence backend

The repository contains code/tests/docs/tools/assets.

Release policy rejects hidden ignored runtime-affecting inputs under `src/`, `tests/`, and `tools/` outside narrow harmless debris exceptions.

Runtime persistence must not silently move into package-relative paths just because a source checkout is editable.

## 48. Persistence transactions are deliberately local in scope

Examples of strong local boundaries include:

```text
one repository write -> SQLite connection transaction
runtime lease acquire -> BEGIN IMMEDIATE conflict-check + insert
lineage source read   -> BEGIN DEFERRED multi-table snapshot
Agents JSON save      -> temp + fsync + os.replace
```

None of these implies one transaction across:

```text
SQLite + Agents JSON + model artifacts + external Dataset + Automation host effects + QSettings
```

Cross-boundary workflows need explicit orchestration and recovery rules.

## 49. Failure semantics should preserve the authoritative previous state where possible

Examples:

- SQLite context-manager/explicit transactions roll back database changes on exceptions;
- runtime lease acquisition rolls back when blockers/errors occur;
- lineage snapshot rolls back read transaction on error;
- Agents atomic store restores the in-memory payload to the previously persisted copy if save fails;
- failed background lineage refresh retains last-good projection at the UI integration layer.

These mechanisms reduce partial-state exposure inside their own boundary.

They do not create universal rollback across every external medium.

## 50. Persistence identity should use stable IDs before labels

Tables/workflows persist IDs such as:

```text
profile_id
dataset_id
run_id
model_version_id
experiment_id
operation_id
node_id/resource identity
```

Human-readable titles remain presentation/provenance information and are not guaranteed globally unique identity.

Lineage projection intentionally prefers persisted modern Training `profile_id`/`dataset_id` when available, falling back to older labels only for compatibility.

## 51. Timestamps are persistence metadata, not synchronization clocks

Rows record timestamps for ordering/history/diagnostics.

Runtime coordination correctness is not based solely on comparing wall-clock timestamps; lease conflict detection reads active states/resource identities transactionally.

Do not turn `updated_at` into an implicit lock/version token unless a future contract explicitly defines it that way.

## 52. Persistence and localization are separate concerns

Database status values increasingly use semantic machine codes/status enums, while UI text maps those semantics into the active locale.

Legacy rendered-text aliases can exist at compatibility boundaries, but persistence/domain identity must not rely on translated presentation text when a semantic code is available.

This keeps changing UI language from mutating domain meaning.

## 53. Backup boundary follows persistence topology

A conservative research/workflow backup preserves the whole workspace because authoritative/referenced state spans:

```text
app.db
agents_lineage_state.json
artifacts/
automation/recipes/
workspace-local models (when present/important)
other workspace files
```

It separately preserves external Dataset/model/Automation dependencies when required.

Qt QSettings shell state is outside the workspace and is only needed when exact shell presentation/session restoration matters.

## 54. Security/privacy follows storage ownership

PTL's SQLite/JSON/artifact/log/recipe files are ordinary host files; v1.0 does not add a workspace-wide encryption layer.

The persistence architecture therefore relies on OS/filesystem/storage policy for confidentiality.

See [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md) for the exact trust model.

## 55. Current persistence non-goals

The v1.0 persistence architecture does not claim:

- one global ACID transaction across SQLite and filesystem/external effects;
- a general arbitrary schema migration/downgrade engine;
- distributed/multi-host locking;
- encrypted database/workspace storage;
- signed whole-workspace snapshots;
- automatic content-addressing of complete base-model directories;
- automatic copying of Dataset source bytes into SQLite;
- transactional garbage collection of model artifacts from Agents local branch deletion;
- hot whole-workspace backup atomicity;
- process-independent synchronization through the Python `RLock` registry.

These are explicit boundaries.

## 56. Developer invariants

Persistence changes must preserve these current rules unless the architecture/product contract is deliberately revised:

1. research/workflow mutable state must not become source-CWD/package-relative hidden input;
2. normal production repositories sharing the primary connection must share connection-level synchronization;
3. SQLite connections keep foreign-key enforcement enabled;
4. multi-source lineage projection must remain one coherent database snapshot rather than unrelated sequential reads;
5. runtime claim check+acquire must remain atomic against competing application lease acquisition;
6. Agents local JSON must remain distinguishable from authoritative semantic SQLite records;
7. cross-store operations must not be documented as globally atomic when they depend on compensation/orchestration;
8. Training artifacts must remain distinct from disposable cache;
9. external Dataset/model/Automation dependencies must remain visible as external when they are external;
10. Qt shell state must not be silently described as workspace-owned while `WindowStateStore` uses QSettings;
11. schema compatibility claims must not exceed implemented explicit additions;
12. machine status/identity must not be replaced by localized display text in persistence contracts;
13. backup/recovery documentation must be updated whenever a persistence location or atomicity boundary moves.

## 57. Audit questions for future persistence changes

Before merging a new persistent feature, answer:

```text
Where is the authoritative state?
Who owns the path/connection?
Is it workspace-local, QSettings, or external?
What stable ID names the object?
What transaction/atomic-replace boundary exists?
Which other stores must change with it?
What happens if the second store fails?
How is recovery performed?
Does backup include it?
Does reset remove it?
Does it contain private data?
Can background threads access the same connection safely?
Does lineage need it in one coherent projection snapshot?
```

If those answers are not explicit, the feature is not persistence-complete merely because it can write a file/row.

## Related documentation

- [Architecture Overview](overview.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Agents lineage architecture](agents-lineage.md)
- [Automation architecture](automation.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md)
- [Training pipeline specification](../training_pipeline.md)
- [Evaluation contract](../reference/evaluation-contract.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
