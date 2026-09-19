# Runtime resource safety

## Purpose

Persona Training Lab executes long-running Training, inference, personality-test,
and Analysis operations while the user continues to work with the lineage tree.
The UI must never remove or mutate a model, artifact, Dataset, test record, or
lineage subtree that is still used by an active operation.

This document defines the runtime ownership and failure-containment invariants.
For the Agents-specific projection/history implementation, see
[Agents lineage architecture](agents-lineage.md) and
[Agents protected history and safety identity](agents-protected-history.md).

## Core invariants

1. **The lineage is a projection, not the source of truth.** Persisted Training
   runs, model versions, artifacts, and experiments remain authoritative. The
   tree projects these records and stores only local lineage state plus explicit
   links to real resources.
2. **Every coordinated long-running operation owns a persistent lease.** The
   lease is stored in SQLite together with every resource used by the operation.
3. **Read/read is compatible.** Several analyses may inspect the same immutable
   model version.
4. **Every write claim is exclusive against conflicting access.** A write claim
   conflicts with readers and writers of the same resource under the runtime
   coordination contract.
5. **Deletion is itself an operation bound to one safety identity.** Before
   changing local state, modern custom-branch deletion captures the exact
   `branch_delete_v1` resource-link snapshot, verifies it against current links,
   atomically acquires write claims for the subtree and linked real resources,
   and verifies the same identity again before staging history or deleting.
6. **Protected deletion Redo is also an operation.** Redo reacquires a fresh
   deletion lease and verifies the recorded safety identity both before and after
   guard acquisition; history cannot bypass either a runtime blocker or link
   drift that appeared after Undo.
7. **Protected creation Undo is destructive too.** Undoing a modern
   `branch_create_v1` entry removes the current custom node and its persisted
   safety links. It verifies recorded links before and after acquiring a fresh
   `lineage_delete` lease before consuming history.
8. **Protected deletion Undo cannot overwrite unexplained link rows.** The
   deleted node IDs must have empty current link sets before the recorded
   snapshot is restored. Non-empty rows fail closed even if their visible node
   IDs match history.
9. **No invalid intermediate claim set becomes active.** An operation either
   owns all requested claims or owns none of them.
10. **Committed-state failures stay truthful.** If local state/link removal has
   committed but lease finalization fails, the UI must reflect the committed
   transition before the finalization error is reported.
11. **A failed diagnostic path cannot fail the application.** Error reporting is
   best-effort, throttled, and isolated from the original workflow.
12. **Recoverable failures do not terminate the UI.** Service, worker-thread, Qt
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

Modern protected branch history stores exact link snapshots in
`agents_lineage_state.json` (`branch_create_v1` / `branch_delete_v1`) so the
cross-store history controller can restore/remove the same safety identity rather
than relying on incidental stale rows.

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

Physical artifact/model paths remain resource identities where the current
persistence model does not provide a stronger stable artifact identifier. The
runtime-safety contract therefore protects those path identities explicitly.

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

Normal modern custom-branch deletion follows this safety order:

1. determine the complete custom subtree;
2. ask for confirmation without holding a runtime lease;
3. re-check the subtree against the prepared deletion plan;
4. capture exact `branch_delete_v1` resource-link metadata for that subtree;
5. verify the captured identity still equals current SQLite links;
6. atomically acquire a `lineage_delete` write lease for all nodes and linked
   resources;
7. verify the **same captured identity again** after lease acquisition;
8. if the identity changed during acquisition, cancel the lease and return
   `STALE` before staging history or changing local state;
9. capture local transaction state and stage the already-captured metadata for
   the `branch_delete` history entry;
10. remove local lineage state while the lease is held;
11. verify that the actual removed IDs match the prepared subtree;
12. remove persisted lineage resource links;
13. finish the lease and refresh the UI.

If lease acquisition conflicts with active work, the tree remains unchanged and
the UI shows the active blocker. If link cleanup fails after local state mutation,
PTL restores the captured local transaction state before reporting the failure
where compensation succeeds.

The pre/post-acquisition identity comparison matters because the lease claims and
the history metadata must describe the same resource-link generation. A lease
protecting one link set must not authorize deletion while `branch_delete_v1`
records another set that appeared during guard acquisition.

Registered model-version rows and physical artifact directories are not deleted
by the local-tree command. PTL v1.0 does not provide transactional/quarantine
artifact deletion through this operation, so destructive artifact removal is
outside the custom-branch delete contract.

## Protected deletion Undo/Redo

Branch deletion is recorded as critical history with a snapshot of the removed
nodes' exact `lineage_resource_links`.

### Undo

A committed deletion normally leaves the recorded custom node IDs absent from
Agents state and their SQLite link sets empty. Protected Undo first verifies this
empty-slot precondition for every recorded node ID.

If any current link row already exists, Undo fails closed rather than replacing
that unexplained identity with old history. This protects split-snapshot/manual
recovery states such as an `agents_lineage_state.json` restored from one snapshot
and `app.db` from another.

Only after the slots are proven empty does Undo restore the saved links and
verify the exact restored identity **before** restoring the visible lineage
snapshot. If the lineage-state restore then fails, PTL compensates by removing
the links it just restored.

This prevents a branch from visually reappearing with weaker safety identity than
it had before deletion and prevents old history from silently overwriting foreign
safety evidence.

### Redo

Redo does not call ordinary branch deletion as a new action. Instead it:

1. verifies that the current custom subtree still matches the recorded delete;
2. verifies that current resource links exactly match `branch_delete_v1`;
3. acquires a fresh `lineage_delete` lease;
4. verifies that the same recorded identity still matches after acquisition;
5. consumes exactly the existing deletion redo entry;
6. verifies that the recorded subtree disappeared;
7. removes its restored resource links;
8. finalizes the lease;
9. applies the saved history/layout transition.

If a conflicting Training/Test/Analysis operation started after Undo, the fresh
lease acquisition blocks Redo and leaves the branch, links, and redo entry
intact. If safety links drifted before or during guard acquisition, Redo returns
`STALE`; the pending history entry is not consumed.

Older redo entries are preserved because protected Redo consumes history rather
than recording a new deletion action that would clear the redo stack.

## Protected creation history

Modern branch creation stores `branch_create_v1` history metadata containing the
created child id and the exact safety links bound at creation time.

### Creation

The creation controller:

1. captures exact pre-creation Agents transaction state;
2. persists the local branch/history entry;
3. binds or inherits the child safety links in SQLite;
4. persists exact `branch_create_v1` metadata into that history entry;
5. exposes/selects the child in the UI only after both stores succeeded.

If link binding or metadata persistence fails, the controller compensates the
Agents JSON state. Already-bound links are removed only after the local state was
successfully restored, avoiding a still-present safety-empty branch if
compensation itself fails.

### Undo

Protected creation Undo is a destructive transition even though its user-facing
meaning is “undo creation.” It removes a currently existing custom node and the
resource association represented by that node.

The controller therefore:

1. verifies that the current subtree is exactly `(child_node_id,)`;
2. verifies that current links exactly match `branch_create_v1`;
3. captures exact pre-Undo Agents transaction state;
4. acquires a fresh `lineage_delete` lease for the child plus its linked real
   resources;
5. verifies the same recorded link identity again after lease acquisition;
6. consumes the existing `branch_create` undo entry;
7. verifies the transition is creation/Undo;
8. removes the exact saved child links;
9. finalizes the lease;
10. returns the history transition for UI application.

If lease acquisition is blocked, no history/state/link mutation occurs and the UI
shows the current blocker. If either the subtree or recorded safety identity no
longer matches, the controller fails closed before history mutation. Link drift
that occurs during guard acquisition closes the new lease without consuming
history.

If link cleanup fails after the JSON transition, the controller restores the
captured pre-Undo Agents state and fails the lease where compensation succeeds.

If state and link removal have already committed but `lease.succeed()` fails,
`BranchCreationHistoryCommittedError` carries the committed transition. The
screen applies that transition before re-raising the finalization failure through
the normal diagnostic boundary.

### Redo

Protected creation Redo first requires the recorded child id to be absent. It
then consumes the existing redo entry, verifies that exactly the recorded child
was restored, and restores the exact safety-link snapshot from
`branch_create_v1` before exposing the UI transition.

If link restoration fails, the controller restores the exact pre-Redo Agents
state. Redo is a restoration of local association, not a destructive removal, so
it does not acquire a deletion lease merely to re-create that association.

### Legacy boundary

Older `branch_create` history without `branch_create_v1` metadata cannot be given
exact historical safety provenance after the fact. Those entries remain on the
generic compatibility history path and can leave conservative stale link rows
rather than deleting an unproven association.

## Projection/resource reconciliation

Persisted semantic lineage can change while Agents is open. Projection resource
links are reconciled against a successfully built semantic projection.

The screen distinguishes a worker **last-good build** from a projection that has
actually crossed the runtime-safety publication boundary. A coordinator result is
allowed to become the screen's active semantic projection only after its exact
`projection.resources` set has been reconciled into
`lineage_resource_links`.

Current publication ordering is:

```text
proven immutable projection
    ↓
transactional projection-link reconciliation
    │
    ├─ failure -> rollback links; keep previous published projection
    │
    └─ success
          ↓
publish full/content UI generation
          ↓
commit accepted revision
```

Local branch/history redraws use the screen's already accepted
`_real_projection`; they do not pull `coordinator.last_good` directly and
therefore cannot bypass a failed safety reconciliation.

A failed/unproven refresh is not treated as evidence that previously known
projection nodes/resources disappeared. When a background refresh fails, Agents
keeps its last-good accepted projection where one exists and reports the incident
instead of replacing the graph with partial state.

If presentation publication fails after successful safety-link reconciliation,
the registry can temporarily be conservatively newer than the visible graph.
That direction can over-block but does not expose a new graph with stale safety
identity.

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

## Current limitations and separate stress evidence

- Training's current full fine-tune backend does not expose cooperative per-step
  cancellation; the UI Pause/Stop controls are disabled in v1.0.
- Persisted physical artifact deletion is not part of the current Agents
  custom-branch deletion contract.
- Protected cross-store Agents history is compensating orchestration across
  SQLite and JSON, not one ACID transaction spanning both stores.
- Historical creation history without `branch_create_v1` metadata cannot recover
  exact resource-link provenance that was never persisted.
- Agents background projection refresh is documented for the current local
  desktop/SQLite operating model. Large-graph interaction/soak limits require
  separate adversarial/stress evidence and are not implied by this architecture
  contract.
- SQLite atomic leases coordinate local processes sharing the same persistence
  store; PTL does not provide distributed/multi-host locking.
- A normal release-gate PASS does not by itself prove extreme contention,
  resource-exhaustion, duration, or fault-injection envelopes.

These are current boundaries. If a separate stress/falsification pass causes
implementation or contract changes, those changes form a new candidate and must
be revalidated rather than being described as already covered by this document.

## Related documentation

- [Agents lineage architecture](agents-lineage.md)
- [Agents protected history and safety identity](agents-protected-history.md)
- [Persistence architecture](persistence.md)
- [Agents lineage user guide](../user-guide/agents-lineage.md)
- [Troubleshooting](../operations/troubleshooting.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
