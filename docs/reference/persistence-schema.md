# SQLite Persistence Schema Reference

> **Scope:** current v1.0 SQLite schema/bootstrap contract.
>
> This is a mechanical reference for the schema created and extended by `infrastructure/persistence/sqlite/schema.py`. For transaction ownership, cross-store semantics, Agents JSON, filesystem artifacts, QSettings and user-home key bindings, read [Persistence architecture](../architecture/persistence.md) and [Workspace layout](workspace-layout.md).

## 1. Database identity and connection policy

The workspace SQLite database is:

```text
<workspace>/app.db
```

`SQLiteDatabase.connect()` opens the shared writable connection with:

```text
timeout = 30 s
check_same_thread = False
row_factory = sqlite3.Row
PRAGMA foreign_keys = ON
PRAGMA journal_mode = WAL
PRAGMA synchronous = NORMAL
PRAGMA busy_timeout = 5000
```

`connect_read_only()` opens a URI `mode=ro` connection, enables `query_only`, keeps foreign keys enabled, and applies the same 5 s busy timeout. It does not enable WAL/synchronous because it is not a writer.

The schema bootstrap is idempotent in the limited sense implemented by `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and explicit additive-column helpers. It is **not** a general migration engine.

## 2. Bootstrap order

`create_minimal_schema(connection)` currently performs:

```text
create core tables/indexes if absent
        ↓
ensure newer Profile columns
        ↓
ensure newer Dataset columns
        ↓
ensure newer Training-run columns
        ↓
ensure training_logs table
        ↓
ensure lineage_resource_links table/index
        ↓
commit
```

The additive helpers inspect `PRAGMA table_info(...)` and issue `ALTER TABLE ... ADD COLUMN` only for known missing compatibility columns.

### Important boundary

Bootstrap can add the explicitly coded columns below. It does not automatically reconcile arbitrary type changes, dropped columns, renamed columns, changed constraints, or transformed data.

## 3. `ui_preferences`

Purpose: SQLite-backed application presentation preferences owned by the Style/localization/UI-scale services.

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `theme` | nullable `TEXT` |
| `accent_palette` | nullable `TEXT` |
| `button_style_preset` | nullable `TEXT` |
| `updated_at` | `TEXT NOT NULL` |

The current repository/service layer may encode additional preference semantics over these fields; this table is not the complete set of all PTL presentation state. Window/dock state uses Qt `QSettings`, and editable key bindings use a separate user-home JSON file.

## 4. `event_log`

Purpose: structured application/audit/diagnostic events.

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `event_type` | `TEXT NOT NULL` |
| `entity_kind` | `TEXT NOT NULL` |
| `entity_id` | `TEXT NOT NULL` |
| `correlation_id` | nullable `TEXT` |
| `causation_id` | nullable `TEXT` |
| `payload_json` | `TEXT NOT NULL` |
| `occurred_at` | `TEXT NOT NULL` |

Index:

```text
idx_event_log_entity(entity_kind, entity_id, occurred_at)
```

`payload_json` is application-serialized JSON stored as text. The SQL schema does not validate its JSON shape.

Security note: schema presence does not imply that arbitrary exception/error text is secret-free. Read the diagnostic privacy boundary in `operations/security-boundaries.md`.

## 5. `projects`

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `updated_at` | `TEXT NOT NULL` |

Index:

```text
idx_projects_updated(updated_at DESC)
```

`status` is stored as text; canonical application meanings belong to the domain/reference layer rather than an SQL `CHECK` constraint.

## 6. `persona_profiles`

Current columns:

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `subtitle` | `TEXT NOT NULL` |
| `description` | `TEXT NOT NULL DEFAULT ''` |
| `communication_style` | `TEXT NOT NULL DEFAULT ''` |
| `principles` | `TEXT NOT NULL DEFAULT ''` |
| `constraints` | `TEXT NOT NULL DEFAULT ''` |
| `notes` | `TEXT NOT NULL DEFAULT ''` |
| `status` | `TEXT NOT NULL` |
| `created_at` | `TEXT NOT NULL DEFAULT ''` |
| `updated_at` | `TEXT NOT NULL` |

Index:

```text
idx_persona_profiles_updated(updated_at DESC)
```

Compatibility bootstrap can add `description`, `communication_style`, `principles`, `constraints`, `notes`, and `created_at` to an older table.

## 7. `agents`

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `subtitle` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `updated_at` | `TEXT NOT NULL` |

Index:

```text
idx_agents_updated(updated_at DESC)
```

This table is distinct from the richer local Agents lineage workspace stored in `<workspace>/agents_lineage_state.json` and from `lineage_resource_links` safety metadata.

## 8. `experiments`

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `subtitle` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `updated_at` | `TEXT NOT NULL` |

Index:

```text
idx_experiments_updated(updated_at DESC)
```

The application layer interprets experiment/evaluation result state; SQL stores the status text without constraining it to a fixed enum.

## 9. `datasets`

Current columns:

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `subtitle` | `TEXT NOT NULL` |
| `path` | `TEXT NOT NULL DEFAULT ''` |
| `format` | `TEXT NOT NULL DEFAULT 'jsonl'` |
| `status` | `TEXT NOT NULL` |
| `record_count` | `INTEGER NOT NULL` |
| `valid_count` | `INTEGER NOT NULL DEFAULT 0` |
| `invalid_count` | `INTEGER NOT NULL DEFAULT 0` |
| `linked_profile` | `TEXT NOT NULL` |
| `quality_summary` | `TEXT NOT NULL` |
| `validation_errors_preview` | `TEXT NOT NULL DEFAULT ''` |
| `readiness` | `TEXT NOT NULL` |
| `schema_name` | `TEXT NOT NULL` |
| `content_sha256` | `TEXT NOT NULL DEFAULT ''` |
| `created_at` | `TEXT NOT NULL DEFAULT ''` |
| `updated_at` | `TEXT NOT NULL` |

Index:

```text
idx_datasets_updated(updated_at DESC)
```

Compatibility bootstrap can add `path`, `format`, `valid_count`, `invalid_count`, `validation_errors_preview`, `content_sha256`, and `created_at`.

`content_sha256` is the important approved-content fingerprint used by Training provenance. The SQL column does not itself guarantee that the referenced external file remains unchanged; service validation/approval semantics provide the stronger contract.

## 10. `training_runs`

Current columns comprise both original presentation fields and newer exact identity/provenance/execution fields.

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `subtitle` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `base_model` | `TEXT NOT NULL` |
| `profile` | `TEXT NOT NULL` |
| `dataset_version` | `TEXT NOT NULL` |
| `profile_id` | `TEXT NOT NULL DEFAULT ''` |
| `dataset_id` | `TEXT NOT NULL DEFAULT ''` |
| `profile_sha256` | `TEXT NOT NULL DEFAULT ''` |
| `dataset_sha256` | `TEXT NOT NULL DEFAULT ''` |
| `mode` | `TEXT NOT NULL` |
| `epochs` | `INTEGER NOT NULL DEFAULT 1` |
| `batch_size` | `INTEGER NOT NULL DEFAULT 1` |
| `learning_rate` | `REAL NOT NULL DEFAULT 0.0001` |
| `epoch_progress` | `TEXT NOT NULL` |
| `loss` | `TEXT NOT NULL` |
| `speed` | `TEXT NOT NULL` |
| `checkpoints_count` | `TEXT NOT NULL` |
| `updated_at` | `TEXT NOT NULL` |
| `started_at` | `TEXT NOT NULL DEFAULT ''` |
| `finished_at` | `TEXT NOT NULL DEFAULT ''` |
| `progress` | `REAL NOT NULL DEFAULT 0` |
| `artifact_path` | `TEXT NOT NULL DEFAULT ''` |
| `error_message` | `TEXT NOT NULL DEFAULT ''` |

Index:

```text
idx_training_runs_updated(updated_at DESC)
```

Compatibility bootstrap can add the exact IDs/hashes, hyperparameters, timestamps, numeric progress, artifact path and error message.

### Identity rule

Where modern fields are populated, `profile_id` / `dataset_id` and their SHA-256 fingerprints carry stronger identity than the legacy display-oriented `profile` / `dataset_version` strings. Consumers such as lineage projection should prefer the stable IDs where available.

## 11. `training_logs`

Created by `_ensure_training_log_table`:

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `run_id` | `TEXT NOT NULL` |
| `level` | `TEXT NOT NULL` |
| `message` | `TEXT NOT NULL` |
| `created_at` | `TEXT NOT NULL` |

Current schema does **not** declare a foreign key from `run_id` to `training_runs(id)`.

That means referential integrity for Training log ownership is an application/repository responsibility rather than an SQLite-enforced cascade contract.

## 12. `analysis_results`

This is a denormalized presentation/result table containing left/right summary values, arithmetic deltas, insights and two stored sample comparisons.

Primary fields:

```text
id
title
subtitle
left_*
right_*
delta_*
insight_1..3
delta_1..3
sample_1_*
sample_2_*
updated_at
```

All result/detail fields are `TEXT NOT NULL`; `id` is the primary key.

Index:

```text
idx_analysis_results_updated(updated_at DESC)
```

This table must not be mistaken for the complete scientific provenance of an evaluation protocol. Protocol identity and raw/serialized experiment semantics are described by `reference/evaluation-contract.md` and the experiments/evaluation services.

## 13. `model_versions`

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `title` | `TEXT NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `base_model` | `TEXT NOT NULL` |
| `profile_title` | `TEXT NOT NULL` |
| `dataset_title` | `TEXT NOT NULL` |
| `training_run_id` | `TEXT NOT NULL` |
| `artifact_path` | `TEXT NOT NULL` |
| `quality_summary` | `TEXT NOT NULL` |
| `created_at` | `TEXT NOT NULL` |
| `updated_at` | `TEXT NOT NULL` |

Index:

```text
idx_model_versions_updated(updated_at DESC)
```

Current SQL does not declare a foreign key from `training_run_id` to `training_runs(id)` and does not content-address `artifact_path`. Model-version provenance is therefore partly referential/application-level rather than enforced entirely by SQLite.

## 14. `runtime_operations`

Persistent runtime lease/operation state.

| Column | SQL contract |
|---|---|
| `id` | `TEXT PRIMARY KEY` |
| `operation_kind` | `TEXT NOT NULL` |
| `subject_kind` | `TEXT NOT NULL` |
| `subject_id` | `TEXT NOT NULL` |
| `state` | `TEXT NOT NULL` |
| `correlation_id` | `TEXT NOT NULL` |
| `owner_pid` | `INTEGER NOT NULL` |
| `started_at` | `TEXT NOT NULL` |
| `heartbeat_at` | `TEXT NOT NULL` |
| `finished_at` | `TEXT NOT NULL DEFAULT ''` |
| `error_message` | `TEXT NOT NULL DEFAULT ''` |

Indexes:

```text
idx_runtime_operations_active(state, heartbeat_at)
idx_runtime_operations_subject(subject_kind, subject_id, started_at)
```

Operation states are an application-level enum/contract; the SQL column itself has no `CHECK` restriction.

## 15. `runtime_operation_resources`

Persistent resource claims owned by runtime operations.

| Column | SQL contract |
|---|---|
| `operation_id` | `TEXT NOT NULL` |
| `resource_kind` | `TEXT NOT NULL` |
| `resource_id` | `TEXT NOT NULL` |
| `access_mode` | `TEXT NOT NULL CHECK(access_mode IN ('read', 'write'))` |

Composite primary key:

```text
(operation_id, resource_kind, resource_id)
```

Foreign key:

```text
operation_id
    -> runtime_operations(id)
    ON DELETE CASCADE
```

Lookup index:

```text
idx_runtime_resources_lookup(resource_kind, resource_id, operation_id)
```

Unlike many text-domain statuses, `access_mode` is enforced directly in SQL.

The atomic runtime repository acquires new operation/claim sets under `BEGIN IMMEDIATE` so conflict check and lease creation are one SQLite write transaction across connections.

## 16. `lineage_resource_links`

Persistent mapping from Agents lineage node IDs to the real resources represented/inherited by each node.

| Column | SQL contract |
|---|---|
| `node_id` | `TEXT NOT NULL` |
| `resource_kind` | `TEXT NOT NULL` |
| `resource_id` | `TEXT NOT NULL` |
| `access_mode` | `TEXT NOT NULL CHECK(access_mode IN ('read', 'write'))` |

Composite primary key:

```text
(node_id, resource_kind, resource_id)
```

Lookup index:

```text
idx_lineage_resource_links_lookup(resource_kind, resource_id, node_id)
```

There is intentionally no SQL foreign key from `node_id` because lineage identity spans derived semantic projection IDs and custom branch IDs stored outside SQLite in Agents local JSON.

### 16.1 Repository transaction semantics

`SQLiteLineageResourceLinksRepository.replace_links(node_id, claims)` executes:

```text
BEGIN/connection context
    DELETE all current rows for node_id
    INSERT complete replacement set
COMMIT
```

If insertion fails, the connection context rolls the deletion back as part of the same transaction.

`reconcile_projection_links(...)` similarly replaces all supplied current node sets and deletes stale node IDs in one repository transaction.

`delete_links(...)` deletes all requested node rows in one transaction.

### 16.2 What this does not make atomic

These repository transactions do **not** make Agents local JSON and SQLite one ACID database. Branch create/delete/history workflows cross the JSON/SQLite boundary and therefore use explicit compensation protocols described in `architecture/agents-lineage.md`.

They also do not by themselves establish a single-instance lock for multiple independent PTL processes. Runtime claims are persisted cross-connection, but lineage-link mutation has its own concurrency assumptions and remains part of the active architecture audit.

## 17. Referential-integrity summary

SQL-enforced foreign keys are deliberately limited in the current schema.

Confirmed direct SQL FK:

```text
runtime_operation_resources.operation_id
    -> runtime_operations.id
    ON DELETE CASCADE
```

Important relations that are currently **not** SQL foreign keys include:

```text
training_logs.run_id          -> training_runs.id
model_versions.training_run_id -> training_runs.id
lineage_resource_links.node_id -> Agents/projection identity
```

This is not equivalent to saying those relations have no application contract. It means SQLite does not independently enforce them.

## 18. Compatibility/migration policy visible in code

The current bootstrap strategy is additive and explicit:

- known older Profile tables receive missing text/created fields;
- known older Dataset tables receive path/format/count/error/hash/time fields;
- known older Training tables receive exact IDs/hashes, hyperparameters, timing/progress/artifact/error fields;
- Training logs and lineage resource links are created if absent.

There is no schema-version table in this bootstrap module and no general ordered migration framework.

Therefore a future destructive or data-transforming schema change should not be documented as supported until code provides an explicit migration/upgrade path.

## 19. Backup/recovery implications

Because the writable database uses WAL, an online backup must not be modeled as blindly copying only `app.db` while writes continue.

The current operator guidance prefers an offline whole-workspace snapshot. That also matters because some logically related state, especially Agents custom lineage/history, lives in a separate JSON file while its runtime safety identity lives here in `lineage_resource_links`.

For protected modern branch history, restore:

```text
app.db
agents_lineage_state.json
```

from the same offline snapshot.

## 20. Audit checklist for schema changes

Any schema change should trigger all applicable checks below:

1. update `schema.py` bootstrap/migration behavior;
2. update owning repository tests;
3. update this reference;
4. update `architecture/persistence.md` when ownership/transaction semantics change;
5. update `workspace-layout.md` when a new persistence surface appears;
6. update statuses/identifier reference for new machine values;
7. update backup/recovery guidance for new cross-store dependencies;
8. update security/privacy guidance when new diagnostic or sensitive fields are persisted;
9. run compatibility tests against an older schema fixture where additive migration is claimed;
10. run the clean release gate before treating the changed schema as a release contract.
