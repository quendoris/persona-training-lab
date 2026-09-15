# Agents lineage

Agents is the integration workspace of Persona Training Lab. It turns the persisted research workflow into one navigable lineage view and adds local experimental branches, history, layout, runtime-safety information, and contextual navigation to the rest of PTL.

This chapter explains how to **use** that workspace safely. For implementation details, read [Agents lineage architecture](../architecture/agents-lineage.md). For the exact cross-store protected-history state machine, read [Agents protected history and safety identity](../architecture/agents-protected-history.md).

## 1. The most important mental model

Agents is not a second database and it is not a visual file manager for model folders.

The screen combines three different layers:

1. **Persisted semantic lineage** — real Dataset, Training, model-version, evaluation, and comparison state derived from PTL persistence.
2. **Local research state** — custom branches, current marker, archive state, overrides, undo/redo history, and graph-layout history stored in `agents_lineage_state.json`.
3. **Presentation state** — canonical aliases, placeholders, labels, tones, layout, selection, and guidance used to make the workflow readable.

Those layers are intentionally shown together, but they do not mean the same thing.

A custom `branch_003` is a research branch in the Agents workspace. It is **not automatically** a new trained model, a copied artifact, or a new Dataset.

A persisted `model_version` node, by contrast, represents a registered PTL model-version record and can point back to an actual Training run and artifact.

## 2. What Agents connects

At a high level, the persisted workflow is:

```text
Profile ───────────────┐
                       │
Base model ──┐         │
             ├─ Training run ── trained artifact ── Model version
Dataset ─────┘                                      │
                                                    ├─ Evaluation / portrait
                                                    │
                                                    └─ Analysis / Delta
```

Agents overlays this with local research structure:

```text
persisted semantic lineage
        │
        ├─ current marker
        ├─ custom branches
        ├─ rename/archive overrides
        ├─ layout
        ├─ undo/redo history
        └─ runtime resource links
```

This is why Agents often feels like the center of the laboratory: it does not replace Profiles, Datasets, Training, Snapshots, Tests, or Analysis; it gives those workflows a common lineage context.

## 3. What comes from SQLite

The semantic projection is built from one consistent SQLite source snapshot containing:

- Datasets;
- Training runs;
- model versions;
- evaluations/experiments.

PTL reads those source sets inside one SQLite transaction before building the lineage projection. This prevents one refresh from combining, for example, an old Training set with a newer model-version set.

Stable IDs are used whenever the persisted schema provides them. In particular, modern Training runs carry exact `profile_id` and `dataset_id` references; Agents does not intentionally resolve those relationships by visible title when a stable ID is available.

Visible labels are for people. IDs are for identity.

## 4. What comes from `agents_lineage_state.json`

Local Agents state is stored inside the active PTL workspace:

```text
<workspace>/agents_lineage_state.json
```

It contains state such as:

- custom branch definitions;
- the Agents current marker;
- per-node local overrides;
- archive state;
- undo history;
- redo history;
- saved layout/history snapshots;
- protected branch-history metadata used to keep local history aligned with SQLite runtime-safety links.

The file belongs to the workspace backup unit. It is not stored relative to the repository CWD.

Deleting only this JSON resets local Agents organization/history, but does **not** delete the persisted Dataset, Training, model-version, or evaluation rows represented by the semantic projection. It also does not automatically clean custom-node `lineage_resource_links` stored in SQLite. Do not use manual file deletion as a normal workflow; use the UI unless you are deliberately performing recovery/reset work.

## 5. Reading the graph

### 5.1 Real nodes

Real semantic nodes represent persisted workflow entities or relationships derived from them. Depending on current data, the graph can represent concepts including:

- base model;
- persona/profile input;
- Dataset;
- Training run;
- Training artifact;
- model version;
- evaluation run / portrait;
- analysis Delta.

The exact visible projection is data-dependent.

### 5.2 Canonical aliases

Agents also uses stable canonical positions/aliases such as:

```text
base
dataset
training
snapshot
portrait
delta
```

These are presentation anchors. They help a sparse or evolving workspace retain a readable shape. Do not assume that an alias string is itself the primary persisted entity ID.

### 5.3 Placeholders

When a workflow stage has no real entity yet, Agents can show a placeholder rather than collapsing the route entirely.

A placeholder means **the next semantic stage is missing**, not that a hidden Dataset/Training run/model version exists somewhere else.

Use the suggested next action or open the corresponding workspace to create the missing persisted state.

### 5.4 Custom branches

Custom branches have IDs such as:

```text
branch_001
branch_002
branch_003
```

They are local research structure. A branch can inherit runtime resource links from its parent so Agents knows which real persisted resources the branch currently depends on.

Creating a branch does not duplicate those resources.

## 6. Selection and the detail panel

Selecting a node updates the Agents detail surface with the available semantic context for that node.

Depending on node kind/state, the detail area can expose:

- title/status/type;
- dependency information;
- workflow checks;
- next actions;
- linked runtime resources;
- active-operation blockers;
- contextual actions to other PTL workspaces.

When a runtime operation blocks a destructive action, the dependency/detail area can show the operation and resource responsible for the block.

## 7. Continue / create a local branch

Use the branch/continue action when you want to explore a new local research path from the selected node.

Conceptually:

```text
selected parent
    │
    └── branch_00N
```

The child inherits the parent's known runtime resource links. This is important: a new visual branch is not treated as resource-free just because it has not yet materialized into a Training run or model version.

For modern branch creation, PTL does not expose/select the child until both the local branch state and its persisted safety-link/history identity have been committed successfully. If that cross-store creation workflow fails, the branch is not intentionally left visible as a successful safety-empty child.

A branch becomes meaningful persisted research only when you subsequently create real workflow entities in the corresponding PTL workspaces.

## 8. Rename a custom branch

Rename changes the local branch label. It does not rename the underlying Dataset, Training run, model version, or artifact represented elsewhere.

Use branch names as research notes/organization, not as stable programmatic identifiers.

## 9. Make current

The Agents current marker expresses which lineage node is currently treated as the active research position in the Agents workspace.

Changing it updates local lineage state. It does not rewrite model weights, mutate a Dataset source, or physically move an artifact.

For registered model-version nodes, `Make current` is available only where the runtime/presentation policy permits it.

## 10. Archive and unarchive

Archive is a local organizational state for custom lineage work.

Archiving a custom branch/subtree changes its local presentation/state; it does not delete the branch, persisted model artifacts, Training records, or Dataset files.

Use archive when a research path should remain recoverable/history-visible but no longer be treated as active work.

## 11. Deleting a custom branch

Deletion is intentionally stricter than archive.

### 11.1 What local branch deletion removes

The local delete command removes the selected **custom branch subtree** from Agents local lineage state and removes its persisted `lineage_resource_links` after safety checks succeed.

It does **not** delete:

- registered model-version database rows;
- Training run rows;
- external Dataset source files;
- trained artifact directories;
- model weights merely because a branch referenced them.

Registered model-version nodes are not treated like disposable local branches.

### 11.2 Why deletion can be blocked or become stale

Before changing lineage state, modern PTL:

1. re-checks that the complete current custom subtree still matches the prepared deletion plan;
2. captures the exact `branch_delete_v1` resource-link identity for that subtree;
3. verifies that captured identity equals current SQLite links;
4. acquires a runtime `lineage_delete` lease covering the lineage nodes and linked real resources;
5. verifies the **same captured identity again** before staging history or deleting the branch.

If an active operation has a conflicting claim, deletion remains blocked and the tree stays unchanged.

Example:

```text
branch_004
  └─ linked model_version = mdl_123

Training operation
  └─ active claim on mdl_123

Delete branch_004
  └─ BLOCKED
```

If the subtree or safety identity changes before the mutation is committed, PTL returns/refuses through the stale/fail-closed path instead of assuming that a matching visible node ID still represents the same protected resources.

If the links change while the deletion lease is being acquired, PTL cancels that fresh lease and leaves branch/history state untouched.

This is deliberate. A visual action is not allowed to invalidate the safety meaning of an active Training/Test/Analysis operation, and an old plan is not authority to delete a different present-day safety identity.

## 12. Undo and redo

Agents history is more than a visual convenience. It restores lineage state and layout, and modern branch creation/deletion entries can carry exact cross-store runtime-safety metadata.

Default history bindings are:

```text
Ctrl+Z        history toggle
Ctrl+Shift+Z  undo only
```

They are routed specially by Agents so the history gesture remains reliable across supported keyboard layouts and Qt shortcut handling. The bindings are configurable through PTL key bindings.

### 12.1 `Ctrl+Z`: history toggle

The default `Ctrl+Z` action toggles according to the current quick-history direction. After an undo it can act as redo, allowing fast back-and-forth inspection of the last history transition.

This differs from the conventional assumption that every `Ctrl+Z` press is necessarily another strict undo.

### 12.2 `Ctrl+Shift+Z`: strict undo

The default `Ctrl+Shift+Z` path requests undo-only semantics. Use it when you want to keep walking backward rather than toggling the last transition.

### 12.3 Protected branch-creation history

Modern branch creation records exact `branch_create_v1` metadata for the child and the runtime resource links it inherited/bound.

That makes **Undo create** a destructive action: it removes the currently existing branch and its safety-link association. Before consuming that history entry, PTL therefore:

1. verifies that the current subtree is exactly the originally created child;
2. verifies that the recorded `branch_create_v1` links exactly equal the child's current SQLite links;
3. acquires a fresh runtime deletion lease for that child and its linked resources;
4. verifies the exact recorded/current link equality **again after lease acquisition**;
5. only then consumes the creation Undo;
6. removes the exact saved safety links;
7. finalizes the lease;
8. applies the saved history/layout transition.

If another active operation owns a conflicting linked resource, Undo create is blocked and the branch/history/links remain unchanged. The blocker is shown through the normal Agents runtime-blocker presentation.

If the branch unexpectedly has a descendant subtree, or its current resource links no longer match the safety identity recorded by the creation entry, the protected path fails closed rather than deleting a different present-day branch association.

If the resource links change while the fresh lease is being acquired, PTL closes/cancels that lease and leaves history unconsumed.

On **Redo create**, PTL requires the recorded child ID to be absent, restores the branch from the existing redo entry, verifies that exactly that child returned, restores its exact saved resource links, verifies the restored identity, and only then applies the visible history transition.

History is therefore not allowed to make a modern branch disappear while an active operation still depends on the resource identity it represents, and it is not allowed to reinterpret a changed safety identity as equivalent merely because the node ID is unchanged.

Historical creation entries that predate `branch_create_v1` metadata remain compatibility history. PTL cannot reconstruct exact old resource-link provenance that was never stored.

### 12.4 Protected branch-deletion history

Branch deletion has additional guarantees.

On modern primary delete, PTL captures the exact runtime resource-link snapshot for the removed subtree **before** lease acquisition, verifies it, acquires the destructive lease, and verifies that same snapshot again before it stages `branch_delete_v1` history or mutates local state.

On **Undo delete**:

1. PTL first requires every recorded deleted node to have an **empty** current `lineage_resource_links` slot;
2. if unexplained current links already exist, Undo fails closed and does not overwrite them;
3. only from an empty slot does PTL restore the exact saved resource-link snapshot;
4. it verifies the restored identity;
5. the lineage/history snapshot is restored;
6. the saved current/layout state is applied;
7. runtime-safety presentation is refreshed.

The empty-slot requirement matters during recovery: old history is not allowed to overwrite current SQLite identity merely because the same node ID appears in both places.

On **Redo delete**:

1. PTL verifies that the current custom subtree still matches the recorded deleted subtree;
2. it verifies that current links exactly match `branch_delete_v1`;
3. it acquires a fresh runtime deletion lease;
4. it verifies the same recorded/current identity **again after lease acquisition**;
5. only then does it consume exactly the existing deletion redo entry;
6. it verifies the expected subtree actually disappeared;
7. it removes the restored resource links;
8. it applies the saved history/layout transition;
9. older redo entries remain intact.

Therefore a Training or other conflicting operation started after Undo can block Redo. A changed safety identity can make Redo stale even without an active blocker. In both cases history remains a guard-respecting transition rather than a bypass around current runtime/resource truth.

## 13. Layout history

Graph position/structure changes participate in Agents history.

Layout snapshots are restored with history transitions so undo/redo can return both semantic local state and the corresponding graph arrangement.

The graph supports interaction such as pan/scroll/zoom and node/subtree layout operations. Layout is presentation state; it does not change persisted Training/Dataset/model provenance.

## 14. Runtime resource links

Agents maintains explicit links between lineage nodes and real runtime resources.

Examples of resource kinds used by PTL include:

```text
training_run
model_version
artifact_path
model_path / model_definition
dataset
profile
experiment
compute_device
lineage_node
```

Custom branches inherit relevant links from their parent until later persisted workflow state gives them a different material identity.

These links are what allow Agents to answer a question that a picture alone cannot answer:

> "If I remove this local branch right now, is some active operation still depending on what it represents?"

They also form part of modern protected-history identity. A branch ID without the expected resource-link set is not, by itself, enough evidence to authorize a destructive historical transition.

## 15. Stable IDs vs visible titles

Do not use visible titles as identity when diagnosing lineage problems.

Two Datasets can legitimately share the same title. Modern Training runs persist `dataset_id`, and Agents uses that stable reference rather than guessing by title.

The same principle applies to Profile resource claims: modern Training lineage uses the persisted `profile_id` when available.

When reporting a bug, include stable IDs from the detail/context surfaces when practical.

## 16. Tests, portraits, and Delta

Agents can project evaluation/portrait state and guide the user toward Analysis.

A Delta is not considered ready merely because two evaluations exist.

For a valid exact comparison, the two portrait/evaluation runs must have compatible protocol identity:

```text
battery_version known and equal
+
scoring_version known and equal
=
protocol-compatible comparison
```

If the versions differ or required protocol metadata is missing, Agents keeps Delta pending rather than showing a false ready/good state.

This matches the Analysis comparability guard. Agents and Analysis share the same protocol-comparison rule.

See [Tests and Analysis](tests-and-analysis.md) and the [Evaluation contract](../reference/evaluation-contract.md) for interpretation details.

## 17. Contextual navigation

Agents can open other PTL workspaces with context derived from the selected/current lineage node.

This allows navigation such as:

```text
Agents node
    ├─ Tests
    └─ Analysis
```

Context is built from semantic entity data plus stable runtime resource claims where available.

The target workspace remains authoritative for executing its own workflow. Agents provides context; it does not silently perform a Training/Test/Analysis action merely because you selected a node.

## 18. Background refresh and last-good projection

Persisted semantic lineage can change while PTL is open. Agents therefore refreshes its real projection in the background.

The important failure rule is:

> a failed refresh must not replace a known-good graph with a partially read or broken projection.

When background loading fails, PTL reports the incident/status and keeps the last successful projection available when one exists.

A later successful refresh can replace it.

This behavior is especially important because Agents combines several persisted subsystems in one screen.

## 19. What a refresh does not do

A presentation/language refresh must not silently rewrite lineage persistence.

Changing locale, repainting content, or receiving a content-only projection update should not create/delete custom branches or change the current marker merely as a side effect of rendering.

If the semantic source set changes, the projection can update. If only visible language changes, the projection identity should remain stable.

## 20. Status and tone

Agents uses semantic status plus presentation tone to make workflow state readable.

Do not interpret a color alone as provenance proof. When a decision matters, inspect the node detail and the authoritative target workspace.

Examples:

- pending can mean a stage is not yet materialized or a comparison is not yet valid;
- bad can represent a failed/problem state;
- neutral can represent archived/local organizational state;
- good indicates a successful/ready presentation state only under the corresponding semantic contract.

For Delta specifically, protocol incompatibility prevents the ready state.

## 21. Recommended first workflow

A useful first pass through Agents is:

1. create a Profile;
2. import, validate, and approve a Dataset;
3. create and complete a Training run;
4. confirm the resulting model version in Snapshots;
5. open Agents and inspect how the persisted chain is projected;
6. create a local branch from the model/version area;
7. rename the branch to a research hypothesis;
8. navigate to Tests and create an evaluation/portrait;
9. return to Agents and inspect the updated projection;
10. create a second protocol-compatible evaluation if you want exact Delta analysis;
11. test archive and history on a disposable local branch;
12. only then experiment with deletion/undo/redo so the safety behavior is familiar.

## 22. Troubleshooting

### The graph does not show a newly created persisted entity

Check:

- whether the source workflow actually committed successfully;
- whether Agents has refreshed;
- Issues/status/log output for a projection refresh incident;
- whether you are looking at a placeholder/canonical alias rather than the real entity node.

If a refresh failed, the screen may intentionally retain the last-good projection.

### Delete or protected Undo/Redo is blocked

Inspect the runtime dependency/blocker text. An active operation can hold a conflicting resource claim.

A runtime blocker means the protected destructive transition remains unconsumed. Wait for or normally cancel the owning operation, then retry through Agents.

Do not edit SQLite rows manually to force deletion/history through.

### A destructive action is stale/refused even though no blocker is shown

Modern protected operations also require the current subtree and safety identity to match the prepared/recorded transition.

Examples:

```text
primary delete
  captured links must remain equal before/after lease acquisition

branch_create_v1 Undo
  recorded links must equal current links before/after lease acquisition

branch_delete_v1 Redo
  recorded links must equal current links before/after lease acquisition
```

A mismatch is not the same thing as an active-operation blocker. PTL fails closed rather than treating the same node ID as proof that the same protected resources are still present.

Preserve `app.db` and `agents_lineage_state.json` together and inspect current/backup provenance rather than forcing the operation by editing JSON or SQLite.

### Undo delete refuses to restore a branch

Protected `branch_delete_v1` Undo expects every recorded deleted node to have an empty current link slot. If one of those node IDs already has current `lineage_resource_links`, PTL preserves them and refuses to overwrite them with old history.

This can expose a mixed-generation restore or other unexplained cross-store state. It is a fail-closed recovery signal, not permission to delete the rows manually.

### A creation Undo reports a committed/finalization error

If diagnostics report `BranchCreationHistoryCommittedError`, the branch and its exact saved safety links were already removed, but finalizing the temporary runtime lease failed afterward. The UI applies the committed history transition before the error is reported.

Treat this as a committed-state/finalization incident. Inspect Activity/Issues/logs and do not manually recreate the branch or edit runtime rows as an immediate fix.

### Two same-title Datasets look suspicious

Use IDs, not titles. Modern Training lineage is linked through `dataset_id` when available.

### Delta stays pending even though two portraits exist

Check `battery_version` and `scoring_version` in the evaluation/Analysis workflow. Two runs are not comparable merely because both completed.

### A branch came back after Undo

That is expected when undoing a protected deletion. Its exact runtime resource links are restored and verified before the local lineage snapshot is restored.

### Redo deletion is blocked or stale after Undo

Both are possible controlled outcomes. Redo acquires a new runtime lease, so an operation started after the original deletion can block it. It also rechecks exact recorded/current safety identity before and after lease acquisition, so link drift can make the Redo stale without a runtime blocker.

## 23. Backup and reset implications

Agents cross-store state spans:

```text
<workspace>/app.db
  -> semantic records + lineage_resource_links

<workspace>/agents_lineage_state.json
  -> local branches/history/layout + protected history metadata
```

For normal recovery, those files should come from the **same offline whole-workspace backup snapshot**. Protected `branch_create_v1` / `branch_delete_v1` metadata can describe the exact safety-link identity expected in SQLite, so mixing backup generations can create history/link mismatch.

Modern protected history is deliberately fail-closed for that mismatch. For example, deletion Undo will not overwrite a non-empty supposedly deleted link slot, while creation Undo/deletion Redo require exact recorded/current safety identity around destructive lease acquisition.

PTL v1.0 does not automatically merge or reconcile different backup generations. If a protected history action exposes such a mismatch, preserve the pair and restore a coherent same-snapshot workspace when available rather than editing links/history into agreement.

A backup of `app.db` alone does **not** include local Agents JSON layout/history/custom branches. An Agents-JSON-only restore likewise does not restore the matching SQLite safety-link state.

See [Backup, Reset & Recovery](../operations/backup-reset-recovery.md), [Workspace & Storage](../operations/workspace-and-storage.md), and [Agents protected history and safety identity](../architecture/agents-protected-history.md).

## 24. v1.0 boundaries

The v1.0 Agents contract does not claim:

- unlimited graph size or interaction-rate stress qualification;
- distributed/multi-host locking;
- one ACID transaction spanning Agents JSON, SQLite links, and runtime leases;
- destructive deletion of registered model artifacts from the local branch command;
- that local custom branches are persisted ML artifacts;
- that historical creation entries without `branch_create_v1` metadata have reconstructable exact safety provenance;
- automatic reconciliation of mixed-generation `app.db` and `agents_lineage_state.json`;
- that a visible title or node ID alone proves the current safety identity of protected history;
- that every protocol-incompatible evaluation pair can be compared;
- that background refresh can never fail.

It does claim that the documented safety/integrity behavior is preserved inside the supported local workspace model.

## 25. Screenshot plan

The final documentation capture pass should include at least:

1. full Agents workspace with a healthy persisted chain;
2. canonical placeholders before a workflow stage exists;
3. selected persisted model-version detail;
4. custom branch selected;
5. renamed side branch;
6. archived branch/subtree;
7. delete confirmation for a custom subtree;
8. runtime-blocked deletion with blocker detail visible;
9. modern branch-creation Undo blocked by a linked active operation;
10. branch restored by deletion Undo;
11. guarded deletion Redo blocked by a newly active operation;
12. controlled safety-identity mismatch/stale state in a demo recovery workspace;
13. two protocol-compatible portraits with Delta ready;
14. protocol-mismatched portraits with Delta pending;
15. contextual jump from Agents to Tests;
16. contextual jump from Agents to Analysis;
17. last-good projection retained after an injected refresh failure.

Generate these from a clean demo workspace with the existing [`tools/visual_audit.py`](../development/visual-audit.md) automatic/interactive capture workflow rather than manually accumulating screenshots. Review captures and manifests for sensitive data before publication.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Profiles](profiles.md)
- [Datasets](datasets.md)
- [Training](training.md)
- [Snapshots and model versions](snapshots.md)
- [Tests and Analysis](tests-and-analysis.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Agents lineage architecture](../architecture/agents-lineage.md)
- [Agents protected history and safety identity](../architecture/agents-protected-history.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)