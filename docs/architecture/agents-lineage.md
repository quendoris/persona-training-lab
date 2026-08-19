# Agents lineage architecture

## Purpose

Agents is the integration layer that projects persisted PTL workflow state into one navigable graph and augments it with local research branches, history, layout, runtime resource links, and contextual navigation.

The architectural requirement is stronger than "draw a graph":

> **Agents must never invent persisted identity, lose safety identity, or present a partial multi-subsystem read as a coherent lineage.**

This document defines the v1.0 implementation contract behind that requirement.

## 1. Architectural boundaries

Agents combines three state classes that must remain distinguishable:

```text
A. persisted semantic sources
   SQLite: datasets / training_runs / model_versions / experiments

B. local lineage workspace state
   <workspace>/agents_lineage_state.json

C. derived/presentation state
   projection nodes / canonical aliases / placeholders / detail text / layout rendering
```

The screen presents them together, but ownership is separate.

### 1.1 Persisted semantic sources

Real workflow entities remain authoritative in their owning persistence/services. Agents reads them; it does not duplicate their primary records as a second source of truth.

### 1.2 Local lineage state

Custom branches, current marker, local overrides, archive flags, and history/layout snapshots are Agents-owned workspace state.

### 1.3 Derived projection

Projection nodes, canonical aliases such as `base`, `dataset`, `training`, `snapshot`, `portrait`, and `delta`, placeholders, tones, and guidance are derived presentation structures. They must not be mistaken for primary persisted entity IDs.

## 2. End-to-end data flow

The current lineage path is conceptually:

```text
SQLiteDatabase
    │
    ├─ datasets
    ├─ training_runs
    ├─ model_versions
    └─ experiments
         │
         ▼
SQLiteLineageSnapshotRepository
         │  one BEGIN DEFERRED snapshot
         ▼
LineageSourceSnapshot
         │
         ▼
AtomicLineageProjectionService
         │  status normalization + semantic builder
         ▼
LineageProjection
         │
         ▼
UI presentation adapter
         │
         ├─ semantic nodes/details/context/resources
         ├─ canonical aliases/placeholders
         └─ protocol-compatible Delta state
         │
         ▼
LineageStateStore / AtomicLineageStateStore.apply(...)
         │
         ├─ local current
         ├─ custom branches
         ├─ overrides/archive
         └─ history/layout state
         │
         ▼
Agents graph + detail + contextual navigation
```

Runtime safety is reconciled alongside this path through `lineage_resource_links` and the runtime-operation coordinator.

## 3. Atomic semantic snapshot

`SQLiteLineageSnapshotRepository.read_lineage_snapshot()` reads all semantic lineage source sets under the shared connection lock and one `BEGIN DEFERRED` SQLite transaction.

The snapshot contains:

- Dataset records;
- Training-run records;
- model-version records;
- evaluation/experiment records.

Only after all four reads succeed is the transaction committed and a `LineageSourceSnapshot` returned.

On failure, the transaction rolls back.

### Invariant

A single projection build must not combine independently timed repository reads that could describe mutually inconsistent workflow moments.

The snapshot is read-consistent; it is not a long-lived database lock after the source copy has been constructed.

## 4. Stable identity

Visible labels are not sufficient identity.

The projection must prefer stable persisted IDs whenever available.

### 4.1 Training input identity

Modern `training_runs` rows include:

```text
profile_id
dataset_id
```

The lineage snapshot uses those values in preference to legacy display fields `profile` and `dataset_version`.

This prevents two classes of errors:

- same-title Datasets becoming ambiguous even though the run has an exact `dataset_id`;
- Agents resource claims using `profile=<title>` while the real Training operation protects `profile=<profile_id>`.

Legacy rows without the newer IDs retain the historical fallback fields for compatibility.

### 4.2 Titles

Titles remain presentation metadata. Code that needs safety, navigation, dependency, or provenance identity should use stable entity/resource IDs when available.

## 5. Projection semantics

The application projection builder receives normalized source records and derives semantic relationships.

Projection output is not only a tuple of visible nodes. It also carries supporting maps such as:

- detail content;
- entity context;
- runtime resource claims;
- projection signature/revision information used by the UI update path.

The UI adapter then converts that application projection into the final presentation lineage used by the graph.

## 6. Canonical aliases and placeholders

Aliases such as:

```text
base
dataset
training
snapshot
portrait
delta
```

exist to maintain a stable workflow-shaped presentation when the real source graph is sparse or when a canonical stage needs a stable UI anchor.

A placeholder context is explicitly distinguishable from a real entity context.

### Invariant

A placeholder must never be treated as proof that the corresponding persisted entity exists.

Canonical IDs are presentation contract identifiers, not globally unique persisted-domain IDs.

## 7. Delta protocol compatibility

Agents and Analysis share the same protocol-comparability rule through the application-level experiment protocol helper.

A Delta is ready only when the selected portrait/evaluation pair has known and matching:

```text
battery_version
scoring_version
```

Formally:

```text
portrait_protocols_match(left, right) == True
```

requires both protocol keys to be complete and equal.

If protocol metadata is unknown or versions differ, the projection keeps Delta pending even if two evaluation runs exist.

### Invariant

Agents must not visually assert a valid Delta for a pair that Analysis will reject as protocol-incomparable.

This is a shared scientific-integrity contract, not a screen-specific style decision.

## 8. Local state store

Production Agents uses `AtomicLineageStateStore`.

Default path:

```text
<workspace>/agents_lineage_state.json
```

The workspace root comes from the same platform resolver used by the rest of PTL.

The old home-relative path `~/.persona_training_lab/agents_lineage_state.json` is not the production default in the v1.0 architecture.

### 8.1 Local payload ownership

The state store owns local data including:

- `current_node_id`;
- custom-node payloads;
- per-node overrides;
- undo stack;
- redo stack;
- quick-history direction;
- lineage/layout snapshots stored in history entries.

### 8.2 Schema normalization

Loaded JSON is normalized before becoming active state. Historical/legacy payload shapes are handled by the store's normalization logic rather than passed raw into rendering.

## 9. Atomic JSON persistence

`AtomicLineageStateStore._save()` performs durable replacement rather than writing the live file in place.

Conceptually:

```text
serialize payload
    ↓
write temporary file in same directory
    ↓
flush
    ↓
fsync(temp file)
    ↓
os.replace(temp, target)
    ↓
fsync(parent directory where supported)
```

If persistence fails before replacement completes, temporary debris is best-effort removed and in-memory state is restored to the last successfully persisted payload.

### Invariant

A failed local-state write must not leave the active in-memory payload claiming a state that was never durably saved.

## 10. Transaction snapshots for destructive workflows

The atomic state store can capture and restore the complete local transaction state.

Branch deletion uses this capability so state changes can be compensated if runtime-link cleanup or lease finalization fails before the operation reaches an irreversible committed point.

The transaction snapshot is distinct from user history: one is failure compensation, the other is an intentional user-visible undo/redo record.

## 11. Runtime resource links

`lineage_resource_links` maps a lineage node to the real resources represented or inherited by that node.

`LineageRuntimeSafety` normalizes resource links to read claims for lineage association.

Examples include:

```text
training_run
model_version
artifact_path
model_path
model_definition
dataset
profile
experiment
compute_device
```

For destructive checks, these read associations are converted into write-conflict claims so deletion conflicts with active readers/writers of the same real resources.

`lineage_node=<node_id>` write claims are also included for the affected local subtree.

## 12. Projection resource reconciliation

Persisted semantic projection nodes can gain, change, or disappear as source state changes.

The projection safety binding reconciles projection resource links against the latest proven semantic projection.

A failed/unproven background load must not be used as evidence that previously known persisted projection links disappeared.

This prevents a transient refresh failure from accidentally weakening runtime safety.

## 13. Custom-branch inheritance

Creating a local branch binds runtime resource identity at branch creation time.

If the parent is custom, the child inherits the parent's persisted links. If the parent is a semantic projection node, fallback claims from the projection are bound to the child.

Conceptually:

```text
parent projection/custom node
       │
       └─ resource claims
              │
              ▼
          branch_00N
```

### Invariant

A newly created custom branch must not become safety-empty merely because no new persisted Training/model entity has been materialized yet.

## 14. Runtime operations and deletion conflicts

Long-running PTL work acquires persistent runtime-operation leases and resource claims.

For lineage deletion, `LineageRuntimeSafety.begin_deletion(...)` derives destructive claims for the complete custom subtree and asks `RuntimeOperationCoordinator` to begin a `lineage_delete` operation.

If an existing operation conflicts, acquisition fails atomically and no deletion mutation begins.

Read/read remains compatible; any write conflict blocks.

## 15. Branch deletion protocol

`BranchDeletionController` coordinates local state, history metadata, runtime links, and runtime lease lifetime.

Normal deletion flow:

```text
prepare complete custom subtree
    ↓
confirm in UI
    ↓
begin lineage_delete lease
    ↓
capture local transaction snapshot
    ↓
capture exact resource-link history metadata
    ↓
stage metadata for branch_delete history entry
    ↓
delete local subtree
    ↓
verify removed IDs match plan
    ↓
forget resource links
    ↓
finalize lease succeeded
```

### 15.1 Stale-plan protection

The controller re-reads the current custom subtree before acquiring the lease. If it differs from the prepared plan, the action returns `STALE` rather than deleting a different subtree.

It also verifies the actual removed IDs after mutation.

### 15.2 Cleanup failure compensation

If resource-link cleanup fails after local state deletion, the controller restores the captured local transaction state and marks/finalizes the deletion lease through the failure path.

If compensation itself fails, `BranchDeletionExecutionError` exposes both the original and compensation failures.

### 15.3 Committed finalization failure

If state deletion and link cleanup have committed but lease finalization fails, the operation cannot honestly be reported as a normal pre-commit failure.

`BranchDeletionCommittedError` carries the already-committed `BranchDeletionResult` plus the finalization error so UI/state handling can reflect what actually happened.

## 16. Protected deletion history metadata

Before normal branch deletion mutates local state, `LineageBranchTransactions.capture_deletion_history(...)` stores:

```text
kind = branch_delete_v1
subject_node_id
removed_ids
resource_links per removed node
```

Each stored claim records:

```text
resource_kind
resource_id
access_mode
```

The metadata is attached to the corresponding critical history entry by `AtomicLineageStateStore`.

History entries without valid deletion metadata are not treated as protected deletion transactions.

## 17. Undo deletion ordering

Protected deletion Undo deliberately restores safety identity before restoring the visible lineage state.

Flow:

```text
preview branch_delete undo
    ↓
parse/validate deletion metadata
    ↓
restore exact resource-link snapshot
    ↓
consume undo entry via undo_only(...)
    ↓
restore local lineage/current/layout snapshot
    ↓
apply history transition
    ↓
refresh runtime safety
```

If lineage-state undo fails after resource links were restored, the UI path compensates by forgetting those restored links again.

### Invariant

A branch must not reappear as valid local lineage while silently losing the runtime resources it represented before deletion.

## 18. Guarded redo deletion

Redo is not allowed to use generic blind snapshot replay for protected deletion.

`BranchDeletionController.execute_history_redo(...)` performs a new safety transaction:

```text
verify current subtree == expected removed_ids
    ↓
begin fresh lineage_delete lease
    ↓
capture transaction state
    ↓
consume exactly one existing redo entry via redo_last_action(...)
    ↓
verify transition is branch_delete/redo
    ↓
verify expected subtree disappeared
    ↓
forget resource links
    ↓
finalize lease
    ↓
return deletion result + HistoryTransition
```

The screen applies the returned saved layout transition through the normal history-transition path.

### Why generic `delete_subtree()` is not used for Redo

Calling normal `delete_subtree()` would record a **new** action and clear redo history. That would violate redo semantics and could erase older redo entries.

Consuming the existing redo entry preserves the rest of the redo stack.

### Fresh blocker semantics

An operation can start after Undo and before Redo. Therefore Redo must acquire a new lease rather than trusting the lease conditions that existed during the original deletion.

If blocked, the redo entry remains pending and the custom branch remains present with its resource links intact.

## 19. History model

Agents local history stores snapshots rather than replaying arbitrary mutation commands.

History entries contain:

- action code;
- critical flag;
- lineage snapshot;
- layout snapshot;
- optional protected metadata.

The store maintains undo and redo stacks plus `quick_direction`.

### 19.1 Quick toggle

Default `Ctrl+Z` maps to `history_toggle`. It chooses undo or redo from the current quick-history direction and stack availability.

### 19.2 Undo-only

Default `Ctrl+Shift+Z` maps to `undo_only` and walks backward without intentionally toggling to redo.

### 19.3 Retention

History keeps a bounded recent set and reserves capacity for older critical entries. Critical deletion history therefore receives stronger retention than ordinary old layout actions, within the configured total history limits.

## 20. History input routing

Agents history shortcuts bypass ordinary Qt shortcut routing when using the guarded default history sequences.

The input stack accounts for:

- editable key bindings;
- physical/layout-specific key resolution;
- modifier snapshots/polling;
- key repeat timing;
- event orchestration;
- ownership so one gesture does not execute twice through competing routing paths.

This is why history has dedicated infrastructure rather than relying only on a pair of generic `QShortcut` objects.

The public user contract is the binding/action semantics, not the internal event machinery.

## 21. Layout and semantic state

Layout snapshots participate in history but remain presentation data.

Graph operations can include node/subtree moves, mixed moves, and layout resets. The saved layout is applied alongside the corresponding history transition.

Layout changes must not modify persisted Dataset/Training/model/evaluation identity.

Zoom/pan/scroll compensation exists to keep workspace interaction stable while the graph geometry changes.

## 22. Background projection refresh

Agents can use `LineageRefreshCoordinator` to build projections outside the main UI path.

The coordinator owns the last successful result (`last_good`).

When a refresh succeeds, the screen uses `ProjectionUpdatePlanner` to choose between:

- no-op;
- content-only update where safe;
- full projection replacement.

When a refresh fails, the incident is reported and the last-good projection remains authoritative for display if available.

### Invariant

A failed background refresh must not replace coherent lineage with a partial/empty graph merely because the latest read attempt failed.

## 23. Content-only update safety

Where projection identity/geometry is unchanged, Agents can update node content without rebuilding the entire graph.

If the graph cannot safely apply the content-only update, the screen falls back to a full projection update.

After a successful update, projection resources are rebound/reconciled and the selected node detail is refreshed.

## 24. Localization boundary

Changing language is presentation work.

`_refresh_language()` captures the semantic projection signature, refreshes presentation/localized text, and asserts that localization did not replace the semantic projection.

### Invariant

Locale changes must not create/delete lineage entities, alter semantic identity, or persist a different research state merely because strings changed.

## 25. Contextual navigation

`LineageContextRouter` builds navigation context for target workspaces from:

- selected/current node context;
- stable entity IDs;
- visible title/status as supplemental presentation context;
- runtime resource claims.

The main window can then route to a target workspace with a mutable context payload.

Agents supplies navigation context; target services remain responsible for validation and execution.

## 26. Registered model-version deletion boundary

Runtime/presentation policy explicitly disables local-tree deletion for registered model-version semantic nodes.

Local branch deletion is not an artifact garbage collector.

Deleting a custom branch does not delete the registered model-version row or physical model artifact that may be linked to it.

Transactional artifact deletion would require separate storage semantics such as dependency validation, quarantine/trash, rollback, and eventual garbage collection.

## 27. Persistence and backup boundary

A complete Agents backup spans both:

```text
<workspace>/app.db
<workspace>/agents_lineage_state.json
```

plus referenced workspace files/artifacts as required by the broader product workflow.

`app.db` contains semantic records and `lineage_resource_links`; the JSON contains local custom branches/current/overrides/history/layout.

Backing up only one side is not a complete Agents-state backup.

## 28. Failure containment summary

Agents uses several independent containment mechanisms:

| Failure | Containment |
|---|---|
| SQLite semantic snapshot read fails | rollback read transaction; keep last-good UI projection where available |
| local JSON save fails | restore last persisted in-memory payload; temporary file cleanup best effort |
| deletion plan changes before execution | return `STALE`; do not delete unexpected subtree |
| runtime conflict | lease acquisition fails; keep lineage unchanged |
| local state deletion fails | fail lease; propagate original error |
| resource-link cleanup fails | restore local transaction state; fail lease |
| compensation/finalization also fails | raise structured execution/committed error preserving both facts |
| protected Undo state restore fails | compensate restored resource links |
| protected Redo becomes blocked | keep branch, links, and redo entry intact |
| localization refresh | presentation-only; semantic projection signature invariant |

## 29. v1.0 operating boundaries

The audited v1.0 architecture deliberately does not claim:

- distributed/multi-host runtime locking;
- unlimited lineage graph scale;
- transactional deletion of real model artifacts from Agents;
- that custom branches are independently persisted ML models;
- that every historical/legacy row has modern stable-ID provenance;
- that a visible label is unique identity;
- that protocol-incompatible portraits can produce a valid exact Delta;
- that background refresh never fails;
- post-v1.0 stress/soak qualification of extreme interaction rates.

SQLite runtime leases cover coordinated local processes using the same persistence model, not a distributed cluster.

## 30. Release/audit expectations

Changes to Agents should preserve regression coverage for at least these contracts:

- atomic semantic snapshot;
- persisted stable Training input IDs in lineage;
- projection identity/resource reconciliation;
- last-good background refresh behavior;
- local state atomic persistence;
- custom branch inheritance;
- deletion conflict/lease semantics;
- deletion compensation/finalization errors;
- protected deletion history metadata;
- exact resource-link restoration on Undo;
- fresh runtime guard on Redo;
- preservation of older redo entries and saved layout;
- keyboard-layout/history routing;
- protocol-compatible Delta;
- localization not mutating semantic projection;
- contextual navigation identity.

Runtime changes during final v1.0 documentation/release work require a concrete audit/test/docs/release finding, not an aesthetic refactor opportunity.

## Related documentation

- [Agents lineage user guide](../user-guide/agents-lineage.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Architecture Overview](overview.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Training pipeline specification](../training_pipeline.md)
- [Evaluation contract](../reference/evaluation-contract.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
