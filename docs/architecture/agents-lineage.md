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

## 10. Transaction snapshots for cross-store lineage workflows

The atomic state store can capture and restore the complete local transaction state.

Both branch creation and branch deletion use this capability when a logical user action crosses the Agents JSON / SQLite resource-link boundary. The stores are still not one ACID transaction; the controller makes the workflow compensating instead.

The transaction snapshot is distinct from user history: one is failure compensation, the other is an intentional user-visible undo/redo record.

### Invariant

A workflow that requires both local lineage state and runtime-safety links must not report/expose a successful new lineage state after the paired safety-link mutation failed and was compensatable.

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

For a **proven new projection**, publication is now deliberately safety-first:

```text
worker produces coherent SQLite snapshot + immutable projection
        ↓
reconcile projection.resources into lineage_resource_links
        │
        ├─ failure -> SQLite reconciliation rolls back;
        │             keep previously published UI projection
        │
        └─ success
              ↓
publish new _real_projection / graph content
              ↓
commit projection revision in ProjectionUpdatePlanner
```

The same ordering applies to both full graph replacement and content-only updates. The screen must not expose semantic generation N+1 while persisted destructive-safety links still describe generation N.

`SQLiteLineageResourceLinksRepository.reconcile_projection_links(...)` performs current-link replacements and stale persisted-projection deletion in one SQLite transaction. A failure therefore preserves the previous link generation rather than partially applying the next one.

If UI publication itself fails **after** successful safety reconciliation, the safety registry can temporarily be more conservative/newer than the visible graph. That direction is intentionally fail-closed: stale/newer safety metadata may over-block an action, but the previous dangerous direction—new UI with old safety identity—is not accepted.

A later accepted refresh can retry normal projection publication. The coordinator's `last_good` remains a successfully built semantic snapshot; publication safety is a separate UI/persistence acceptance boundary.

This prevents both a transient refresh failure and a safety-link persistence failure from accidentally weakening destructive runtime protection.

## 13. Custom-branch creation and inheritance

Creating a local branch is a cross-store workflow: the custom-node/history mutation lives in `agents_lineage_state.json`, while inherited runtime-safety identity lives in SQLite `lineage_resource_links`.

If the parent is custom, the child inherits the parent's persisted links. If the parent is a semantic projection node, fallback claims from the projection are bound to the child.

Conceptually:

```text
capture exact local transaction state
       ↓
persist branch_00N in atomic Agents JSON
       ↓
bind/inherit child resource links in SQLite
       ↓
attach branch_create_v1 metadata to the history entry
       │
       ├─ success → select/expose branch and refresh UI
       │
       └─ failure → restore exact pre-creation Agents JSON state
                     then forget child links when that state restore succeeded
```

`BranchCreationController` owns that ordering. The screen does not select or render the new child until link binding and durable creation-history metadata attachment have both succeeded.

The SQLite link replacement itself is one repository transaction. If link binding raises, that repository transaction rolls back; the branch-creation controller compensates the already-persisted Agents JSON side.

If link binding succeeded but history metadata persistence fails, the controller first restores the exact pre-creation Agents state. Only after that restore succeeds does it forget the already-bound child links. This ordering deliberately avoids turning a still-present branch into a safety-empty branch if local-state compensation itself fails.

If compensation also fails, `BranchCreationExecutionError` preserves the original and compensation failures rather than pretending the workflow cleanly rolled back.

### 13.1 Protected creation history metadata

A successful modern branch creation attaches metadata to the corresponding `branch_create` history entry:

```text
kind = branch_create_v1
child_node_id
resource_links[]
  resource_kind
  resource_id
  access_mode
```

`AtomicLineageStateStore.attach_latest_history_metadata(...)` verifies that the latest history action is actually `branch_create`, writes the metadata into that entry, and persists the updated JSON through the same atomic-save path.

The atomic history store already copies entry metadata when moving an entry between undo and redo stacks, so the safety identity follows the history transition rather than depending on stale SQLite rows remaining behind by accident.

### 13.2 Protected branch-creation Undo

For a `branch_create` entry with valid `branch_create_v1` metadata, the composed Agents screen routes Undo through `BranchCreationController` rather than generic snapshot replay.

Undo is destructive: it removes a currently visible custom branch and forgets the resource identities attached to that node. It therefore acquires a **fresh runtime deletion lease** before mutating history.

Before that lease is acquired, the controller requires both:

```text
current custom subtree == (child_node_id,)
recorded branch_create_v1 links == current SQLite links
```

After lease acquisition, it verifies the exact link equality a second time before consuming history. This closes the local TOCTOU window between proving safety identity and acquiring the destructive guard.

Flow:

```text
verify subtree + recorded safety identity
       ↓
capture exact pre-Undo Agents transaction state
       ↓
begin fresh lineage_delete lease for the child + linked resources
       │
       ├─ conflict → keep branch/history/links unchanged; show runtime blockers
       │
       └─ acquired
             ↓
verify recorded safety identity again
       │
       ├─ changed → cancel lease; keep history untouched
       │
       └─ unchanged
             ↓
consume branch_create undo entry
       ↓
branch disappears from Agents JSON
       ↓
forget that child's lineage_resource_links in SQLite
       ↓
finalize deletion lease succeeded
       │
       ├─ success → apply saved UI/history transition
       │
       └─ pre-commit failure → restore exact pre-Undo Agents state
```

The subtree equality check prevents one old creation-history entry from deleting an unexpected descendant subtree if lineage/history state has diverged. The identity checks prevent the same visible branch ID from authorizing deletion of a changed resource association.

The SQLite link deletion is a repository transaction. If it fails, the branch state is restored and the deletion lease is failed before the error is surfaced.

If state + link removal have already committed but lease finalization itself fails, `BranchCreationHistoryCommittedError` carries the committed `HistoryTransition`. The screen applies that committed transition before reporting the finalization failure, so visible state does not pretend the branch still exists.

### 13.3 Protected branch-creation Redo

Redo likewise cannot rely on stale links surviving the previous Undo.

Before consuming the redo entry, the controller verifies that the recorded child ID is currently absent. After the history transition it verifies that the restored custom subtree is exactly that child before restoring safety links.

Flow:

```text
verify child_node_id is absent
       ↓
capture exact pre-Redo Agents transaction state
       ↓
consume branch_create redo entry
       ↓
verify restored subtree == (child_node_id,)
       ↓
restore exact saved resource_links from branch_create_v1 metadata
       │
       ├─ success → apply saved UI/history transition
       │
       └─ failure → restore exact pre-Redo Agents state
```

The screen applies the visible history transition only after the controller has restored the persisted safety identity successfully.

Redo is not itself a destructive removal of a linked resource, so it does not acquire a deletion lease merely to re-create the local branch association.

### 13.4 Legacy creation-history compatibility boundary

Historical `branch_create` entries that predate `branch_create_v1` metadata are still readable by the generic lineage-history compatibility path. They cannot be retrospectively given exact resource-link provenance that was never stored in their history entry.

Generic Undo of such an old entry can therefore leave conservative stale `lineage_resource_links` behind rather than deleting links whose exact historical ownership cannot be proven. A later modern branch creation for the same node ID uses link replacement and does not rely on those stale rows as provenance.

This compatibility behavior is intentionally narrower than the protected contract for newly created metadata-bearing entries.

### Invariants

A newly created custom branch must not become safety-empty merely because no new persisted Training/model entity has been materialized yet.

A branch whose required safety-link bind or creation-history metadata persistence failed must not remain durably exposed as a successful creation when local-state compensation succeeds.

Protected creation Undo must not remove a branch/resource association while a current runtime operation owns a conflicting linked resource.

Protected creation Undo must remove both the local branch and its exact saved safety links, or restore the prior state.

Protected creation Redo must restore both the local branch and its exact saved safety links before UI exposure.

## 14. Runtime operations and deletion conflicts

Long-running PTL work acquires persistent runtime-operation leases and resource claims.

For lineage deletion, `LineageRuntimeSafety.begin_deletion(...)` derives destructive claims for the complete custom subtree and asks `RuntimeOperationCoordinator` to begin a `lineage_delete` operation.

If an existing operation conflicts, acquisition fails atomically and no deletion mutation begins.

Read/read remains compatible; any write conflict blocks.

Protected branch-creation Undo uses this same destructive lease boundary because undoing creation removes the current custom node and its runtime-safety links.

## 15. Branch deletion protocol

`BranchDeletionController` coordinates local state, history metadata, runtime links, and runtime lease lifetime.

Modern normal deletion binds the destructive lease and the eventual `branch_delete_v1` history entry to the same recorded safety identity:

```text
prepare complete custom subtree
    ↓
confirm in UI
    ↓
re-read subtree; require exact plan match
    ↓
capture exact branch_delete_v1 resource-link metadata
    ↓
verify captured identity == current SQLite links
    ↓
begin lineage_delete lease
    ↓
verify the SAME captured identity again
    │
    ├─ changed → cancel lease; return STALE; stage no history
    │
    └─ unchanged
          ↓
capture local transaction snapshot
    ↓
stage captured metadata for branch_delete history entry
    ↓
delete local subtree
    ↓
verify removed IDs match plan
    ↓
forget resource links
    ↓
finalize lease succeeded
```

The second identity check closes a time-of-check/time-of-use gap: the runtime lease must not protect one generation of links while the durable deletion history records another generation that appeared during guard acquisition.

### 15.1 Stale-plan and identity protection

The controller re-reads the current custom subtree before acquiring the lease. If it differs from the prepared plan, the action returns `STALE` rather than deleting a different subtree.

It also compares the exact captured resource-link identity before and after runtime-guard acquisition. Drift before acquisition returns `STALE` without a lease; drift during acquisition cancels the newly acquired lease and returns `STALE` before local/history mutation.

After mutation, the controller still verifies that the actual removed IDs match the prepared subtree.

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

The captured metadata is verified against current links, carried unchanged across destructive lease acquisition, verified again, and only then staged for the corresponding critical history entry by `AtomicLineageStateStore`.

History entries without valid deletion metadata are not treated as protected deletion transactions.

## 17. Undo deletion ordering

Protected deletion Undo deliberately restores safety identity before restoring the visible lineage state, but it will not overwrite unexplained current links for the deleted node IDs.

Flow:

```text
preview branch_delete undo
    ↓
parse/validate deletion metadata
    ↓
require current links for every recorded deleted node == empty
    │
    ├─ non-empty → fail closed; preserve current rows and pending history
    │
    └─ empty
          ↓
restore exact resource-link snapshot
    ↓
verify restored identity == branch_delete_v1 metadata
    ↓
consume undo entry via undo_only(...)
    ↓
restore local lineage/current/layout snapshot
    ↓
apply history transition
    ↓
refresh runtime safety
```

If lineage-state undo fails after resource links were restored, the UI path compensates by forgetting those restored links again. The empty-slot precondition makes that compensation safe with respect to pre-existing foreign rows: there were none to overwrite or erase.

This strict precondition also makes split-snapshot recovery fail closed. If `app.db` and `agents_lineage_state.json` come from different backup generations and a supposedly deleted node ID already has links, old history does not silently replace them.

### Invariant

A branch must not reappear as valid local lineage while silently losing the runtime resources it represented before deletion, and old history must not overwrite an unexplained present-day safety identity merely because the node ID matches.

## 18. Guarded redo deletion

Redo is not allowed to use generic blind snapshot replay for protected deletion.

`BranchDeletionController.execute_history_redo(...)` performs a new safety transaction:

```text
verify current subtree == expected removed_ids
    ↓
resolve branch_delete_v1 metadata for pending redo
    ↓
verify recorded links == current SQLite links
    ↓
begin fresh lineage_delete lease
    ↓
verify recorded links == current SQLite links AGAIN
    │
    ├─ changed → cancel lease; return STALE; keep redo pending
    │
    └─ unchanged
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

### Fresh blocker and identity semantics

An operation can start after Undo and before Redo. Therefore Redo must acquire a new lease rather than trusting the lease conditions that existed during the original deletion.

Safety identity can also drift independently of the visible branch ID. Therefore Redo verifies the recorded `branch_delete_v1` links before and after guard acquisition rather than assuming that a matching subtree ID still denotes the same protected resources.

If blocked, the redo entry remains pending and the custom branch remains present with its resource links intact. If identity mismatches, Redo returns `STALE` and likewise leaves history unconsumed.

## 19. History model

Agents local history stores snapshots rather than replaying arbitrary mutation commands.

History entries contain:

- action code;
- critical flag;
- lineage snapshot;
- layout snapshot;
- optional protected metadata.

The store maintains undo and redo stacks plus `quick_direction`.

Metadata-bearing `branch_create` and `branch_delete` entries receive cross-store handling in the composed screen; ordinary local/layout actions remain generic snapshot history.

### 19.1 Quick toggle

Default `Ctrl+Z` maps to `history_toggle`. It chooses undo or redo from the current quick-history direction and stack availability.

### 19.2 Undo-only

Default `Ctrl+Shift+Z` maps to `undo_only` and walks backward without intentionally toggling to redo.

### 19.3 Retention

History keeps a bounded recent set and reserves capacity for older critical entries. Critical deletion history therefore receives stronger retention than ordinary old layout/creation actions, within the configured total history limits.

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

The content-only path still performs projection-resource reconciliation **before** calling the graph content updater. A reconciliation exception therefore leaves the previously published projection/content in place.

If reconciliation succeeds but the graph cannot safely apply the content-only update, the screen falls back to a full projection update. The same semantic resource set may be reconciled again on that fallback; the repository operation is replacement/reconciliation, not an append-only duplication.

After successful publication, the selected node detail is refreshed and the accepted revision is committed to the update planner.

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

The current storage/runtime contract does not provide transactional artifact deletion with dependency validation, quarantine/trash, rollback, and garbage collection. Therefore no such destructive artifact behavior is implied by Agents branch deletion.

## 27. Persistence and backup boundary

A complete Agents backup spans both:

```text
<workspace>/app.db
<workspace>/agents_lineage_state.json
```

plus referenced workspace files/artifacts as required by the broader product workflow.

`app.db` contains semantic records and `lineage_resource_links`; the JSON contains local custom branches/current/overrides/history/layout and protected history metadata.

Because creation/deletion history metadata can describe the exact resource-link identity expected in SQLite, the database and JSON should come from the same offline workspace backup snapshot.

Backing up only one side is not a complete Agents-state backup. If the two files come from different generations, protected history is designed to fail closed on missing, foreign, or drifted link identity rather than silently reconciling the mismatch.

## 28. Failure containment summary

Agents uses several independent containment mechanisms:

| Failure | Containment |
|---|---|
| SQLite semantic snapshot read fails | rollback read transaction; keep last-good UI projection where available |
| local JSON save fails | restore last persisted in-memory payload; temporary file cleanup best effort |
| branch creation safety-link bind fails | rollback SQLite link transaction; restore exact pre-creation Agents transaction snapshot; do not select/render child |
| branch creation history-metadata save fails after link bind | restore pre-creation Agents state first, then forget bound links when state restore succeeded |
| branch creation compensation also fails | raise `BranchCreationExecutionError` preserving original and compensation errors; never hide partial outcome |
| protected creation Undo runtime conflict | keep branch/history/links unchanged and expose current blockers |
| protected creation Undo subtree or safety identity differs from recorded entry | fail closed before history mutation |
| protected creation Undo links drift during guard acquisition | cancel fresh lease; keep branch/history/current links unchanged |
| protected creation Undo link cleanup fails | restore exact pre-Undo Agents state; fail the deletion lease; do not apply UI transition |
| protected creation Undo committed but lease finalization fails | raise `BranchCreationHistoryCommittedError`; apply committed history transition before surfacing failure |
| protected creation Redo target already exists / restores unexpected subtree | fail closed and restore pre-Redo state where mutation occurred |
| protected creation Redo link restore fails | restore exact pre-Redo Agents state; do not apply UI transition |
| deletion plan changes before execution | return `STALE`; do not delete unexpected subtree |
| deletion safety identity differs before lease | return `STALE`; acquire no destructive lease |
| deletion links drift during lease acquisition | cancel newly acquired lease; return `STALE`; stage no delete history |
| runtime conflict | lease acquisition fails; keep lineage unchanged |
| local state deletion fails | fail lease; propagate original error |
| resource-link cleanup fails | restore local transaction state; fail lease |
| compensation/finalization also fails | raise structured execution/committed error preserving both facts |
| protected deletion Undo finds non-empty supposedly deleted link slots | fail closed; preserve current rows and pending history |
| protected deletion Undo state restore fails after exact link restoration | compensate only the links restored by that Undo attempt |
| protected deletion Redo safety identity differs before/during lease | return `STALE`; cancel acquired lease when needed; keep redo pending |
| protected deletion Redo becomes blocked | keep branch, links, and redo entry intact |
| proven projection resource reconciliation fails | roll back SQLite reconciliation; do not publish new full/content projection generation |
| UI publication fails after successful projection-link reconciliation | safety registry may remain conservatively newer than visible graph until retry; do not roll safety identity backward merely to match a failed presentation update |
| localization refresh | presentation-only; semantic projection signature invariant |

## 29. v1.0 operating boundaries

The audited v1.0 architecture deliberately does not claim:

- distributed/multi-host runtime locking;
- unlimited lineage graph scale;
- one ACID transaction spanning Agents JSON and SQLite resource links;
- transactional deletion of real model artifacts from Agents;
- that custom branches are independently persisted ML models;
- that every historical/legacy branch-creation history entry contains modern `branch_create_v1` safety metadata;
- that every historical/legacy row has modern stable-ID provenance;
- that a visible label is unique identity;
- that protocol-incompatible portraits can produce a valid exact Delta;
- that background refresh never fails;
- that protected history can safely combine `app.db` and `agents_lineage_state.json` from different backup generations;
- stress/soak qualification of extreme interaction rates beyond separately recorded evidence.

SQLite runtime leases cover coordinated local processes using the same persistence model, not a distributed cluster. Separate adversarial/stress/falsification evidence must not be inferred from this architecture contract alone.

## 30. Release/audit expectations

Changes to Agents should preserve regression coverage for at least these contracts:

- atomic semantic snapshot;
- persisted stable Training input IDs in lineage;
- projection identity/resource reconciliation;
- safety-first full/content projection publication when link reconciliation fails;
- last-good background refresh behavior;
- local state atomic persistence;
- custom branch inheritance;
- branch-creation compensation across Agents JSON and SQLite safety links;
- durable `branch_create_v1` history metadata;
- exact pre/post-lease safety identity on protected creation Undo;
- protected creation Undo removes exact safety links or restores state;
- protected creation Undo preserves committed transition on lease-finalization failure;
- protected creation Redo validates target identity and restores exact safety links before UI exposure;
- deletion conflict/lease semantics;
- primary deletion binds one captured safety identity across guard acquisition and history staging;
- deletion compensation/finalization errors;
- protected deletion history metadata;
- deletion Undo requires empty deleted link slots and restores exact recorded identity;
- fresh runtime guard plus exact pre/post-lease safety identity on deletion Redo;
- preservation of older redo entries and saved layout;
- keyboard-layout/history routing;
- protocol-compatible Delta;
- localization not mutating semantic projection;
- contextual navigation identity.

Runtime changes during final v1.0 documentation/release work require a concrete audit/test/docs/release finding, not an aesthetic refactor opportunity.

For the exact cross-store history state machine and fail-closed matrices, use [Agents protected history and safety identity](agents-protected-history.md).

## Related documentation

- [Agents lineage user guide](../user-guide/agents-lineage.md)
- [Agents protected history and safety identity](agents-protected-history.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Persistence architecture](persistence.md)
- [Architecture Overview](overview.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Training pipeline specification](../training_pipeline.md)
- [Evaluation contract](../reference/evaluation-contract.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
