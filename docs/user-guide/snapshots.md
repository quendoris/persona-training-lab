# Snapshots and model versions

The **Snapshots** workspace is the read-only user view of PTL's persisted **model version registry**.

This distinction matters: in v1.0 a Snapshot is **not** a second copy of model weights, a separate immutable database object, or a content-addressed checkpoint. The screen projects records from `model_versions` and follows their stored lineage back to the Training run and artifact path.

For the Training-side provenance contract, see [Training](training.md) and the [Training pipeline specification](../training_pipeline.md).

## 1. Where Snapshots come from

A normal successful flow is:

```text
Profile + approved Dataset + base model
                ↓
          Training run
                ↓
       full fine-tune artifact
                ↓
        model_versions row
                ↓
          Snapshots screen
```

After a completed Training run has a non-empty artifact path, the Training view-model attempts to register a model version automatically.

The model-version service does not create a second model artifact. It stores metadata that points to the artifact already produced by Training.

## 2. What a model-version record stores

The current v1.0 `model_versions` record contains:

```text
id
title
status
base_model
profile_title
dataset_title
training_run_id
artifact_path
quality_summary
created_at
updated_at
```

The generated ID has the form:

```text
mdl_<8 hexadecimal characters>
```

A model version created from a successful Training run starts with:

```text
status = ready
```

The generated title is based on the Profile title and Training run ID.

## 3. One Training run should register one model version

`create_from_training_run(...)` first looks for an existing model version with the same `training_run_id`.

If one already exists, PTL returns that existing version instead of deliberately creating another record for the same Training run.

This is application-level idempotency. The current SQLite schema does not declare `training_run_id` itself as a unique database column, so operators should still treat the normal PTL workflow as the authority rather than inserting model-version rows manually.

## 4. What the Snapshots workspace shows

The workspace contains:

- a **Snapshot registry** list;
- a **Snapshot summary** area;
- a derived **Lifecycle** view;
- a **Lineage chain**;
- a **Next best step** panel;
- **Refresh snapshots**.

Selecting an item updates the summary, lifecycle, and lineage panels for that model-version record.

The screen is currently read-only with respect to model-version records. It does not expose a create, delete, archive, rename, or artifact-copy operation.

## 5. Snapshot registry ordering

Model versions are loaded from SQLite ordered by:

```text
updated_at DESC,
title ASC
```

The most recently updated records therefore appear first, with title as the secondary ordering rule.

## 6. Empty and failure states

The Snapshots UI distinguishes three non-version states:

- model-version service unavailable;
- load failed;
- no snapshots/model versions yet.

If the registry is empty, the normal next step is to complete a Training run that produces an artifact and allows a model version to be registered.

## 7. Summary fields

For a registered version, the summary presents the record through user-facing metrics such as:

- lifecycle/status;
- source Training run;
- whether an artifact path is present;
- Profile title.

The screen header also projects:

- base model;
- Profile title;
- Dataset title.

These values come from the model-version record rather than by reopening the original Profile/Dataset objects on every render.

## 8. Lineage chain

The current lineage panel renders this metadata chain:

```text
Base model
Profile
Dataset version
Training run
Artifact
```

This is useful traceability, but each item has a different strength of identity.

### Training run

`training_run_id` is the strongest direct link back into PTL's Training provenance.

The Training run stores the pinned Profile and Dataset fingerprints introduced by the v1.0 Training-integrity contract.

### Artifact

`artifact_path` points to the model artifact saved by Training.

The model-version record does not copy those model bytes into SQLite.

### Profile and Dataset

The model-version row stores human-readable Profile and Dataset **titles**, not the Profile/Dataset SHA-256 values.

For cryptographic input provenance, follow `training_run_id` back to the Training run rather than treating the titles as immutable identifiers.

### Base model

The model-version row stores the same base-model reference/path supplied from the Training result.

As documented in the Training guide, v1.0 does not cryptographically content-address the complete base-model directory.

## 9. Why “Snapshot” does not mean “independent frozen copy” in v1.0

The product name **Snapshots** describes the user-facing inspection surface, but the persisted object underneath is a model-version registry row.

The current implementation does **not** create:

- a second copy of the trained model solely for the Snapshot screen;
- a separate `snapshots` SQLite table for model-version snapshots;
- a SHA-256 of the complete trained artifact directory inside `model_versions`;
- a SHA-256 of the complete base-model directory inside `model_versions`;
- an immutable copy of the Profile or Dataset payload inside the model-version row.

Therefore the safe mental model is:

> **A v1.0 Snapshot is a traceable registry view of a trained model version, not a self-contained immutable package.**

## 10. Artifact-path integrity

Because a model version references the Training artifact by path, moving or deleting that artifact can leave the registry row present while the model files are gone.

For the standard local full-fine-tune backend, the artifact normally lives under:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
```

Do not clean `artifacts/` as though it were disposable cache.

A complete backup should preserve both:

```text
app.db
+ referenced artifact directories
```

See [Workspace & Storage](../operations/workspace-and-storage.md).

## 11. Lifecycle panel is a derived presentation

For a normal registered version, the Snapshots screen shows a conceptual lifecycle:

```text
Training completed
Artifact saved
Model version registered
Ready for tests
```

This panel is derived from the currently selected model-version fields and quality summary.

It is **not** a separate timestamped event ledger and should not be interpreted as proof that four independent lifecycle events were persisted in a dedicated history table.

For actual operational/audit history, use the relevant Training logs and PTL event/runtime records where applicable.

## 12. Quality summary

A newly registered model version receives a compact machine-readable quality summary generated from the completed Training run.

The current encoding uses a versioned prefix:

```text
ptl:model-version-quality:v1:
```

followed by compact JSON.

The normal Training completion code is:

```text
training_completed
```

with values including:

```text
loss
checkpoints
```

The Snapshots and Training view-models parse this machine representation and render localized user-facing text.

The parser also understands a small set of legacy quality strings for compatibility with older workspace data.

## 13. What the quality summary is not

The quality summary is not a full evaluation report.

A Training loss/checkpoint summary does not establish that a personality is stable, safe, aligned with a target profile, or superior to another model version.

Those claims belong to Tests/Evaluation and Analysis workflows.

The current Snapshots UI therefore points the user toward Tests as the next verified action.

## 14. Model-version statuses

The domain recognizes:

```text
draft
ready
archived
failed
unknown
```

Model versions created automatically from a successful Training run use `ready`.

The Snapshots screen can display the other semantic statuses if such records exist, including compatibility/older data, but the current standard Training publication path does not expose an interactive status-management workflow here.

## 15. Refresh behavior

**Refresh snapshots** reloads the model-version registry and preserves the current selection when that ID still exists.

If the previously selected version no longer exists in the returned list, PTL selects the first available row.

Refreshing does not:

- re-run Training;
- re-hash an artifact directory;
- recreate a missing artifact;
- evaluate the model;
- create a new model version by itself.

## 16. Relationship to the Training workspace

Training and Snapshots expose the same model-version registry from different perspectives.

Training shows personality/model versions alongside run control so a user can see what completed runs have published.

Snapshots gives one selected model version more room for:

- status;
- source run;
- artifact path;
- lineage chain;
- lifecycle presentation;
- next-step guidance.

They are not two independent registries.

## 17. Relationship to Tests and Analysis

The current intended progression is:

```text
Training completed
       ↓
Model version registered
       ↓
Snapshots inspection
       ↓
Tests / evaluation
       ↓
Analysis
```

A model version being `ready` means the Training publication path registered it successfully. It does not mean evaluation has already passed.

## 18. Reproducibility boundary

For the strongest v1.0 reconstruction of how a model version was produced, preserve:

- the model-version row;
- the linked Training run;
- the Training run's Profile SHA-256;
- the Training run's Dataset SHA-256;
- the external Dataset source/provenance as appropriate;
- the trained artifact directory;
- the base-model source/revision/checksum outside PTL when exact base-model identity matters.

The model-version row alone is intentionally not claimed to be a complete cryptographic provenance bundle.

## 19. Manual database edits are not a supported workflow

Do not create or “repair” model versions by inserting rows directly into `model_versions` during normal use.

Doing so can bypass application-level assumptions such as one version per Training run and can create records whose artifact paths or lineage fields do not correspond to real PTL workflows.

Use the Training → publication flow as the supported creation path.

## 20. Screenshot plan for v1.0

The final documentation capture session should include:

1. empty Snapshots registry before any completed Training artifact exists;
2. registry containing a newly registered model version;
3. selected Snapshot summary;
4. Lifecycle panel;
5. Lineage chain showing base model → Profile → Dataset → Training run → artifact;
6. the same model version visible in Training's personality-version area;
7. a documented missing-artifact example only if it can be produced safely in a disposable demo workspace.

Screenshots should use the normal reproducible documentation capture metadata: commit, locale, theme, scale, and demo-workspace state.

## Next steps

- Understand how the version was produced: [Training](training.md)
- Inspect the exact Training provenance contract: [Training pipeline specification](../training_pipeline.md)
- Preserve database + artifact state correctly: [Workspace & Storage](../operations/workspace-and-storage.md)
- Continue to Tests/Evaluation, then Analysis, once those v1.0 guides are completed.
