# Agents lineage

Agents is the integration workspace of Persona Training Lab. It turns the persisted research workflow into one navigable lineage view and adds local experimental branches, history, layout, runtime-safety information, and contextual navigation to the rest of PTL.

This chapter explains how to **use** that workspace safely. For implementation details, read [Agents lineage architecture](../architecture/agents-lineage.md).

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
- saved layout/history snapshots.

The file belongs to the workspace backup unit. It is not stored relative to the repository CWD.

Deleting only this JSON resets local Agents organization/history, but does **not** delete the persisted Dataset, Training, model-version, or evaluation rows represented by the semantic projection. Do not use manual file deletion as a normal workflow; use the UI unless you are deliberately performing recovery/reset work.

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

### 11.2 Why deletion can be blocked

Before changing lineage state, PTL determines the complete custom subtree and acquires a runtime deletion lease covering:

- the lineage nodes;
- linked real resources inherited or bound to those nodes.

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

This is deliberate. A visual action is not allowed to invalidate the safety meaning of an active Training/Test/Analysis operation.

## 12. Undo and redo

Agents history is more than a visual convenience. It restores lineage state and layout, and branch deletion has extra runtime-safety semantics.

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

### 12.3 Protected branch-deletion history

Branch deletion has additional guarantees.

On delete, PTL stores the exact runtime resource-link snapshot for the removed subtree in the protected history metadata.

On **Undo delete**:

1. the saved resource links are restored;
2. the lineage/history snapshot is restored;
3. the saved current/layout state is applied;
4. runtime-safety presentation is refreshed.

This ordering prevents a visually restored branch from temporarily returning without its previous safety identity.

On **Redo delete**:

1. PTL does not blindly replay JSON state;
2. it acquires a fresh runtime deletion lease;
3. it consumes exactly the existing deletion redo entry;
4. it verifies the expected subtree actually disappeared;
5. it removes the restored resource links;
6. it applies the saved history/layout transition;
7. older redo entries remain intact.

Therefore a Training or other conflicting operation started after Undo can block Redo. History is not a bypass around runtime safety.

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

Custom branches inherit relevant links from their parent until future persisted workflow state gives them a different material identity.

These links are what allow Agents to answer a question that a picture alone cannot answer:

> "If I remove this local branch right now, is some active operation still depending on what it represents?"

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

### Delete is disabled or blocked

Inspect the runtime dependency/blocker text. An active operation can hold a conflicting resource claim.

Do not edit SQLite rows manually to force deletion through.

### Two same-title Datasets look suspicious

Use IDs, not titles. Modern Training lineage is linked through `dataset_id` when available.

### Delta stays pending even though two portraits exist

Check `battery_version` and `scoring_version` in the evaluation/Analysis workflow. Two runs are not comparable merely because both completed.

### A branch came back after Undo

That is expected. For a protected deletion, its runtime resource links are restored before the local lineage snapshot is restored.

### Redo deletion is blocked after Undo

That is also expected. Redo acquires a new runtime lease and can be blocked by an operation that started after the original deletion.

## 23. Backup and reset implications

Because Agents local state now lives inside the PTL workspace, a whole-workspace backup includes:

- `agents_lineage_state.json`;
- SQLite semantic records;
- lineage resource links;
- other PTL workspace state.

A backup of `app.db` alone does **not** include the local Agents JSON layout/history/custom branches.

See [Workspace & Storage](../operations/workspace-and-storage.md).

## 24. v1.0 boundaries

The v1.0 Agents contract does not claim:

- unlimited graph size or interaction-rate stress qualification;
- distributed/multi-host locking;
- destructive deletion of registered model artifacts from the local branch command;
- that local custom branches are persisted ML artifacts;
- that a visible title is a globally unique identifier;
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
9. branch restored by Undo;
10. guarded Redo blocked by a newly active operation;
11. two protocol-compatible portraits with Delta ready;
12. protocol-mismatched portraits with Delta pending;
13. contextual jump from Agents to Tests;
14. contextual jump from Agents to Analysis;
15. last-good projection retained after an injected refresh failure.

These should be generated from a clean demo workspace by the planned reproducible documentation-capture tool rather than manually accumulated screenshots.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Profiles](profiles.md)
- [Datasets](datasets.md)
- [Training](training.md)
- [Snapshots and model versions](snapshots.md)
- [Tests and Analysis](tests-and-analysis.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Agents lineage architecture](../architecture/agents-lineage.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
