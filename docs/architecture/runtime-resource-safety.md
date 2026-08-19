# Runtime resource safety

## Purpose

Persona Training Lab executes long-running Training, inference, personality-test,
and Analysis operations while the user continues to work with the lineage tree.
The UI must never remove or mutate a model, artifact, Dataset, test record, or
lineage subtree that is still used by an active operation.

This document defines the runtime ownership and failure-containment invariants.
For the Agents-specific projection/history implementation, see
[Agents lineage architecture](agents-lineage.md).

## Core invariants

1. **The lineage is a projection, not the source of truth.** Persisted Training
   runs, model versions, artifacts, and experiments remain authoritative. The
   tree projects these records and stores only local lineage state plus explicit
   links to real resources.
2. **Every coordinated long-running operation owns a persistent lease.** The
   lease is stored in SQLite together with every resource used by the operation.
3. **Read/read is compatible.** Several analyses may inspect the same immutable
   model version.
4. **Every write is exclusive.** Training, deletion, replacement, or any future
   mutation conflicts with all readers and writers of the same resource.
5. **Deletion is itself an operation.** A subtree deletion atomically acquires
   write claims for the subtree and all linked real resources after user
   confirmation and before changing state. This closes the check-to-delete race.
6. **Protected deletion Redo is also an operation.** Redo reacquires a fresh
   deletion lease; history cannot bypass a runtime blocker that appeared after
   Undo.
7. **No invalid intermediate claim set becomes active.** An operation either
   owns all requested claims or owns none of them.
8. **A failed diagnostic path cannot fail the application.** Error reporting is
   best-effort, throttled, and isolated from the original workflow.
9. **Recoverable failures do not terminate the UI.** Service, worker-thread, Qt
   event, and Qt warning boundaries report the incident and keep unrelated
   workflows usable.

## Persistent model

### `runtime_operations`

One row per operation. Important fields include:

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
insertion inside `BEGIN IMMEDIATE`, so two local application processes using the
same database cannot both win the same exclusive lease.

### `lineage_resource_links`

Maps a lineage node to the real resources represented by that node. A local
branch inherits links from its parent until later workflow state gives the branch
new persisted meaning.

These links are separate from the visual graph layout and separate from the
custom-branch JSON payload. They are persisted in SQLite because runtime safety
must survive ordinary UI refresh/restart behavior.

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

Modern Training lineage uses persisted `profile_id` and `dataset_id` where
available. Human-readable titles remain presentation metadata.

Future storage services should introduce stable artifact ids instead of relying
only on paths. Paths remain claimed during the transition so physical weights
are still protected.

## Operation lifecycle

A coordinated workflow generally follows this shape:

1. validate user input without changing persistent state;
2. resolve the exact model version, artifact, Dataset, Profile, and other inputs;
3. atomically acquire all claims;
4. mark the domain operation as running;
5. execute work and refresh status/heartbeat where implemented/useful;
6. persist outputs before attaching them to lineage;
7. mark the lease terminal (`succeeded`, `failed`, or `cancelled`);
8. refresh the real-lineage projection.

If the process previously terminated without closing a lease, startup recovery
marks operations owned by dead PIDs as `abandoned` and releases their resources.

## Lineage deletion protocol

Normal custom-branch deletion follows this safety order:

1. determine the complete custom subtree;
2. ask for confirmation without holding a runtime lease;
3. re-check the subtree against the prepared deletion plan;
4. atomically acquire a `lineage_delete` write lease for all nodes and linked
   resources;
5. capture local transaction state and exact resource-link history metadata;
6. if acquisition failed, keep the tree unchanged and show the active blocker;
7. remove local lineage state while the lease is held;
8. verify that the actual removed ids match the prepared subtree;
9. remove persisted lineage resource links;
10. finish the lease and refresh the UI.

If link cleanup fails after local state mutation, PTL restores the captured local
transaction state before reporting the failure where compensation succeeds.

Registered model-version rows and physical artifact directories are not deleted
by the local-tree command. A future storage transaction must implement
quarantine/trash, dependency validation, rollback, and eventual garbage
collection before destructive artifact deletion is enabled.

## Protected deletion Undo/Redo

Branch deletion is recorded as critical history with a snapshot of the removed
nodes' exact `lineage_resource_links`.

### Undo

Undo restores the saved links **before** restoring the visible lineage snapshot.
If the lineage-state restore then fails, PTL compensates by removing the links it
just restored.

This prevents a branch from visually reappearing with weaker safety identity than
it had before deletion.

### Redo

Redo does not call ordinary branch creation/deletion history as a new action.
Instead it:

1. verifies that the current custom subtree still matches the recorded delete;
2. acquires a fresh `lineage_delete` lease;
3. consumes exactly the existing deletion redo entry;
4. verifies that the recorded subtree disappeared;
5. removes its restored resource links;
6. finalizes the lease;
7. applies the saved history/layout transition.

If a conflicting Training/Test/Analysis operation started after Undo, the fresh
lease acquisition blocks Redo and leaves the branch, links, and redo entry
intact.

Older redo entries are preserved because protected Redo consumes history rather
than recording a new deletion action that would clear the redo stack.

## Projection/resource reconciliation

Persisted semantic lineage can change while Agents is open. Projection resource
links are reconciled against a successfully built semantic projection.

A failed/unproven refresh is not treated as evidence that previously known
projection nodes/resources disappeared. When a background refresh fails, Agents
keeps its last-good projection where one exists and reports the incident instead
of replacing the graph with partial state.

## Error and diagnostic policy

- Recoverable Python and Qt failures receive an error id/correlation context where
  the reporting boundary supports it.
- Full diagnostic details go to rotating application logs and structured SQLite
  event data according to the relevant reporter.
- Repeated identical events can be throttled to prevent log flooding.
- Secrets/tokens are redacted from structured context where the error reporter
  performs redaction.
- Qt warnings are routed into the application diagnostic path instead of becoming
  uncontrolled stderr noise.
- Only unrecoverable process-level failures should require terminal-level failure.

Production composition configures the rotating log under the PTL workspace:

```text
<workspace>/logs/persona_training_lab.log
```

The current rotating handler uses an approximately 5 MB file size and five
backups. Failure to create the diagnostic file does not block application startup.

## Current limitations and post-v1.0 hardening

- Training's current full fine-tune backend does not expose cooperative per-step
  cancellation; the UI Pause/Stop controls are disabled in v1.0.
- Persisted artifact deletion is deliberately disabled until a transactional
  artifact store with quarantine is implemented.
- Agents background projection refresh is designed around the current local
  desktop/SQLite scale. Large-graph interaction/soak behavior belongs to the
  post-v1.0 stress campaign rather than an undocumented stable guarantee.
- Multi-host coordination requires a server-side/distributed lock service or
  database; SQLite atomic leases cover coordinated local processes sharing the
  same persistence store, not distributed hosts.
- Additional progress/cancellation/retry/incident UX may be added in later
  releases without weakening the v1.0 ownership/conflict contracts.

## Related documentation

- [Agents lineage architecture](agents-lineage.md)
- [Agents lineage user guide](../user-guide/agents-lineage.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
