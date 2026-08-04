# Runtime resource safety

## Purpose

Persona Training Lab executes long-running training, inference, personality-test,
and analysis operations while the user continues to work with the lineage tree.
The UI must never remove or mutate a model, artifact, dataset, test record, or
lineage subtree that is still used by an active operation.

This document defines the runtime ownership and failure-containment invariants.

## Core invariants

1. **The lineage is a projection, not the source of truth.** Persisted training
   runs, model versions, artifacts, and experiments remain authoritative. The
   tree projects these records and stores only local lineage state plus explicit
   links to real resources.
2. **Every long-running operation owns a persistent lease.** The lease is stored
   in SQLite together with every resource used by the operation.
3. **Read/read is compatible.** Several analyses may inspect the same immutable
   model version.
4. **Every write is exclusive.** Training, deletion, replacement, or any future
   mutation conflicts with all readers and writers of the same resource.
5. **Deletion is itself an operation.** A subtree deletion atomically acquires
   write claims for the subtree and all linked real resources after user
   confirmation and before changing state. This closes the check-to-delete race.
6. **No invalid intermediate state becomes active.** An operation either owns
   all requested claims or owns none of them.
7. **A failed diagnostic path cannot fail the application.** Error reporting is
   best-effort, throttled, and isolated from the original workflow.
8. **Recoverable failures do not terminate the UI.** Service, worker-thread, Qt
   event, and Qt warning boundaries report the incident and keep unrelated
   workflows usable.

## Persistent model

### `runtime_operations`

One row per operation. Important fields:

- operation kind and subject;
- state (`starting`, `running`, `cancelling`, or a terminal state);
- process owner;
- correlation id;
- start, heartbeat, and finish timestamps;
- terminal error message.

### `runtime_operation_resources`

One row per claimed resource:

- resource kind;
- stable resource id;
- access mode (`read` or `write`).

The production SQLite implementation performs conflict detection and claim
insertion inside `BEGIN IMMEDIATE`, so two application processes cannot both
win the same exclusive lease.

### `lineage_resource_links`

Maps a lineage node to the real resources represented by that node. A local
branch inherits links from its parent until it materializes into its own
training run and model version.

## Resource identity

Resource ids must be stable and must not depend on a visible label alone when a
persistent id exists. Current kinds include:

- `training_run`;
- `model_version`;
- `artifact_path`;
- `model_path` / `model_definition`;
- `dataset`;
- `profile`;
- `experiment`;
- `compute_device`;
- `lineage_node`.

Future storage services should introduce stable artifact ids instead of relying
only on paths. Paths remain claimed during the transition so physical weights
are still protected.

## Operation lifecycle

1. Validate user input without changing persistent state.
2. Resolve the exact model version, artifact, dataset, and profile.
3. Atomically acquire all claims.
4. Mark the domain operation as running.
5. Execute work and periodically refresh status/heartbeat where useful.
6. Persist outputs before attaching them to lineage.
7. Mark the lease terminal (`succeeded`, `failed`, or `cancelled`).
8. Refresh the real-lineage projection.

If the process previously terminated without closing a lease, startup recovery
marks operations owned by dead PIDs as `abandoned` and releases their resources.

## Lineage deletion protocol

1. Determine the complete custom subtree.
2. Ask for confirmation without holding a lock.
3. Atomically acquire a `lineage_delete` write lease for all nodes and linked
   resources.
4. If acquisition fails, keep the tree unchanged and show the active blocker.
5. Remove local lineage state and persisted links while the lease is held.
6. Finish the lease and refresh the UI.

Registered model-version rows and physical artifact directories are not deleted
by the local-tree command. A future storage transaction must implement
quarantine/trash, dependency validation, rollback, and eventual garbage
collection before destructive artifact deletion is enabled.

## Error and diagnostic policy

- Recoverable Python and Qt failures receive an error id and correlation id.
- Full details go to the rotating application log and structured SQLite event
  log.
- Repeated identical events are throttled to prevent log flooding.
- Secrets and tokens are redacted from structured context.
- Qt warnings are routed to logs instead of stderr spam.
- Only unrecoverable process-level failures may reach the terminal.

Default rotating log location when launched from the repository root:

```text
./logs/persona_training_lab.log
```

## Current limitations and next hardening steps

- Training and test execution still use the existing worker model; cancellation
  tokens and periodic heartbeats should be added when the backend becomes truly
  long-lived or remote.
- Persisted artifact deletion is deliberately disabled until a transactional
  artifact store with quarantine is implemented.
- The real-lineage projection currently polls while the Agents workspace is
  visible. A domain-event subscription and incremental projection should replace
  polling before large-scale datasets are used.
- Multi-host coordination will require a server-side lock service or database;
  SQLite atomic leases cover multiple local processes, not distributed hosts.
- Operation progress, cancellation, retries, and incident details should later
  be exposed in the Activity and Problems panels.
