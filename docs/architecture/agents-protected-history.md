# Agents protected history and safety identity

Status: **current implementation contract** for metadata-bearing custom-branch creation/deletion history.

This document isolates the cross-store history protocol that is easy to lose inside the broader Agents architecture. It is authoritative for modern:

```text
branch_create_v1
branch_delete_v1
```

history entries.

The broader graph/projection/local-state architecture remains documented in [Agents lineage architecture](agents-lineage.md).

## 1. Why protected history exists

A custom Agents branch is represented in two persistence domains:

```text
agents_lineage_state.json
    -> branch existence
    -> local hierarchy
    -> current/archive/overrides
    -> undo/redo history
    -> layout snapshots

app.db :: lineage_resource_links
    -> safety identity of real resources represented/inherited by the branch
```

A generic JSON snapshot Undo/Redo can restore the first domain but cannot prove what the second domain should contain.

Modern branch history therefore records the exact safety identity needed to coordinate the two stores.

The protocol is compensating, not ACID. The stores remain independent.

## 2. Safety identity

For protected history, a branch's safety identity is the normalized set of persisted `ResourceClaim` associations recorded for the affected local node IDs.

Each claim contains:

```text
resource_kind
resource_id
access_mode
```

Lineage associations are normalized as read links. During destructive operations, `LineageRuntimeSafety` derives write claims for conflict detection.

Safety identity is **set-like** for comparison:

- duplicate claims do not create distinct identity;
- ordering does not create distinct identity;
- resource kind/ID/access mode do.

## 3. Creation history metadata

A successful modern custom-branch creation records:

```text
kind = branch_create_v1
child_node_id
resource_links[]
```

The metadata is attached to the corresponding `branch_create` history entry only after the branch exists durably and its SQLite links have been bound successfully.

Conceptually:

```text
capture pre-create Agents state
        ↓
write new branch to Agents JSON
        ↓
bind inherited/fallback links in SQLite
        ↓
attach branch_create_v1 metadata durably
        ↓
expose/select branch in UI
```

If a cross-store step fails before completion, the controller compensates toward the exact pre-create Agents state and removes child links only when doing so cannot leave an existing branch safety-empty.

## 4. Creation Undo is destructive

Undoing `branch_create_v1` removes a currently existing branch, so it must be treated as a fresh destructive operation rather than blind history replay.

The current controller requires:

```text
current custom subtree == (recorded child_node_id,)
```

and checks:

```text
recorded safety links == current SQLite safety links
```

**before** acquiring the deletion lease.

It then acquires a fresh `lineage_delete` runtime lease and checks the same equality **again before mutating history**.

The second check closes a time-of-check/time-of-use gap in which safety links could theoretically change while the runtime guard is being acquired.

Only then may it:

```text
consume creation Undo
    ↓
remove branch from Agents JSON
    ↓
forget exact recorded child links
    ↓
finalize lease
```

A mismatch fails closed; PTL does not reinterpret a changed safety identity as equivalent merely because the visible branch ID is unchanged.

## 5. Creation Redo restores exact identity

Redo of `branch_create_v1` first requires the recorded child ID to be absent.

It then restores the branch through the existing history entry, validates that the resulting subtree is exactly the expected one-child subtree, restores the recorded links, and verifies the restored links match the metadata.

UI exposure follows successful state/link restoration.

Creation Redo is restorative rather than destructive, so it does not acquire a deletion lease merely to recreate the association.

## 6. Deletion history metadata

Before modern branch deletion removes local state, PTL captures:

```text
kind = branch_delete_v1
subject_node_id
removed_ids[]
resource_links{
    node_id -> exact normalized claim set
}
```

The metadata describes the complete custom subtree being removed and the safety identity attached to each affected node immediately before deletion.

Normal deletion then proceeds behind a fresh destructive lease and removes both:

```text
custom subtree in Agents JSON
lineage_resource_links for removed IDs
```

with local-state compensation if SQLite cleanup fails before commit.

## 7. Deletion Undo requires an empty deleted identity slot

A successful deletion leaves the recorded custom node IDs absent from Agents local state and their `lineage_resource_links` absent from SQLite.

Protected deletion Undo therefore does **not** treat arbitrary existing links for those deleted node IDs as harmless stale data.

Before restoring the recorded safety snapshot, `restore_deletion_history(...)` verifies that every recorded deleted node currently has an empty link set.

Conceptually:

```text
preview branch_delete Undo
        ↓
parse branch_delete_v1 metadata
        ↓
for every recorded deleted node:
    current SQLite links must be empty
        │
        ├─ non-empty → fail closed; do not overwrite them
        │
        └─ empty
              ↓
restore exact recorded links transactionally
              ↓
verify exact restored link sets
              ↓
consume JSON Undo
              ↓
branch subtree reappears
```

This matters for inconsistent recovery states. If `app.db` and `agents_lineage_state.json` came from different snapshots, or someone manually introduced rows for a deleted node ID, Undo must not silently destroy that foreign safety evidence to make old history replay succeed.

## 8. Why non-empty links block deletion Undo even when they equal history

The current contract intentionally uses a strict empty-slot precondition rather than treating pre-existing matching links as idempotent completion.

Reason: the normal committed deleted state has no links for those custom nodes. Non-empty links therefore mean PTL cannot prove that it is still operating on the exact post-deletion cross-store state from which the Undo was recorded.

Failing closed preserves the unexpected rows for diagnosis instead of normalizing an ambiguous recovery state silently.

If future recovery machinery introduces a formally journaled partial-Undo state, that would justify a different idempotency contract. Current v1.0 history has no such cross-store journal.

## 9. Deletion Undo compensation

After links have been restored successfully, the screen consumes the JSON history Undo.

If that local-state Undo fails, the current compensation path forgets the links that were just restored, returning toward the pre-Undo deleted state.

Because the restore path now requires the link slots to have been empty before restoration, that cleanup does not erase a pre-existing foreign link set.

This is why the empty-slot guard is not merely validation; it also makes the existing compensation direction well-defined.

## 10. Deletion Redo is destructive again

After a successful deletion Undo, the branch and its recorded links exist again. Redo removes them again.

Therefore deletion Redo must not trust the conditions of the original deletion.

It revalidates:

```text
current custom subtree == recorded removed_ids
recorded safety links == current SQLite safety links
```

before acquiring a fresh destructive runtime lease.

Then it acquires `lineage_delete` and checks the exact safety-link equality **again after lease acquisition and before history mutation**.

Only after both identity checks pass may Redo consume the existing `branch_delete` redo entry and remove the subtree/links.

## 11. Deletion Redo fail-closed matrix

| Condition | Result |
|---|---|
| recorded subject/subtree no longer matches current subtree | `STALE`; no history mutation |
| current safety links differ from recorded metadata before lease | `STALE`; no lease/history mutation |
| runtime operation conflicts with destructive claims | `BLOCKED`; redo remains pending |
| safety links change while lease is being acquired | lease is cancelled; `STALE`; redo remains pending |
| redo entry no longer resolves to `branch_delete/redo` | restore local transaction state; fail/stale path |
| expected subtree remains after redo transition | compensate local state/lease; `STALE` |
| link cleanup fails after local redo | restore captured local transaction state and fail lease |
| lease finalization fails after deletion committed | `BranchDeletionCommittedError` carries committed result |

## 12. Why the second link check exists

The outer desktop workspace lease already excludes a second cooperating PTL process from the same workspace.

That does not make a single pre-lease safety-link read sufficient as a local correctness proof.

The destructive runtime lease itself is acquired from SQLite and depends on the claims derived from current links. Re-reading the exact safety identity after lease acquisition verifies that the semantic object protected by the newly acquired lease still corresponds to the history object about to be consumed.

This is defensive TOCTOU closure and also protects tests/internal callers that can mutate stores outside the normal UI path.

## 13. Split-snapshot recovery behavior

Protected history is intentionally sensitive to mismatched recovery generations.

Example:

```text
agents_lineage_state.json from backup A
app.db from backup B
```

Possible outcomes include:

- a history entry expects links that SQLite does not contain;
- a deleted node ID unexpectedly has links;
- a restored branch has different links than its history records.

Protected Undo/Redo must fail closed in those cases.

It must not infer that two different safety identities are equivalent from visible labels or branch IDs.

The operator recovery rule remains: restore `app.db` and `agents_lineage_state.json` from the same offline workspace snapshot.

## 14. Legacy history boundary

Older `branch_create` / `branch_delete` entries may lack modern protected metadata.

PTL cannot reconstruct exact historical resource-link provenance that was never stored.

The compatibility path is therefore weaker than `branch_create_v1` / `branch_delete_v1` and may conservatively retain stale safety rows rather than deleting identities it cannot prove belong to the legacy history transition.

Documentation must never describe legacy history as having the same cross-store proof as modern metadata-bearing history.

## 15. What is and is not atomic

### Atomic inside SQLite

Repository replacement/reconciliation of lineage resource links uses SQLite transactions.

### Atomic for one Agents JSON publication

`AtomicLineageStateStore` writes a complete temporary payload, flushes/fsyncs it, publishes with `os.replace()`, and attempts directory fsync.

### Not one ACID transaction

There is no transaction manager that atomically commits:

```text
agents_lineage_state.json
+
app.db :: lineage_resource_links
+
runtime-operation lease terminal state
+
UI transition
```

Controllers instead use ordering, exact identity checks, transaction snapshots and compensation.

## 16. Epistemic rule for safety identity

PTL treats stored protected-history metadata as evidence about one historical transition, not as authority to overwrite any present state that happens to use the same node ID.

That yields the rule:

> **History may restore or remove cross-store safety identity only when current state satisfies the preconditions that prove the recorded transition still applies.**

This is the same general philosophy used elsewhere in PTL: evidence mismatch is surfaced, not normalized away silently.

## 17. Regression evidence

The protected-history suite includes coverage for:

- creation metadata persistence across Undo/Redo stacks;
- exact creation-link restoration/removal;
- creation Undo runtime conflicts;
- creation Undo link drift before and during lease acquisition;
- deletion metadata persistence;
- deletion Undo restoration ordering;
- deletion Redo preserving unrelated older redo entries/layout transition;
- deletion Redo runtime blockers;
- deletion Undo refusing foreign/non-empty link identity;
- deletion Redo refusing links that drifted from recorded history;
- deletion Redo re-checking link identity after runtime-guard acquisition.

The newest deletion identity tests live in:

```text
tests/test_branch_delete_redo_identity.py
```

and that test file is part of the blocking quick-release manifest.

The branch containing these changes is **not** considered release-green merely because the regression tests have been committed. A clean release gate still has to execute them successfully.

## 18. Related documents

- [Agents lineage architecture](agents-lineage.md)
- [Persistence architecture](persistence.md)
- [Workspace concurrency and ownership](workspace-concurrency.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Agents lineage user guide](../user-guide/agents-lineage.md)
