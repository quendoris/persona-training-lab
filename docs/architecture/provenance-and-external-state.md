# Provenance & External-State Boundaries

Persona Training Lab uses several different kinds of identity. Some inputs are content-fingerprinted, some are represented only by filesystem paths, some are copied into the workspace, and some remain ordinary external host state.

The central rule is:

> **A stable PTL identifier or filesystem path is not automatically proof of stable bytes. Provenance strength must be stated separately for each input/output surface.**

This document is the cross-cutting v0.1.0 provenance map for Datasets, Profiles, base models, Training artifacts, model versions, Automation dependencies, Telemetry and backups.

## 1. Provenance classes used by current PTL

The current implementation exposes four materially different identity strengths:

```text
content identity
    exact bytes / exact rendered training representation are SHA-256 pinned

semantic snapshot identity
    a normalized structured object is hashed for one workflow boundary

path/reference identity
    a path or reference is stored/resolved, but the bytes behind it are not content-addressed

external operator provenance
    PTL stores insufficient information to reproduce the dependency by itself
```

These classes are not interchangeable.

## 2. Current provenance matrix

| Surface | Current identity | Copied into workspace? | Rechecked before use? | Important limit |
|---|---|---:|---:|---|
| Profile Training representation | SHA-256 of rendered Training instruction | SQLite stores Profile fields, not a duplicate rendered blob | yes, at Training start | operator notes are deliberately outside the Training fingerprint |
| Dataset JSONL | SHA-256 of complete source bytes | no; Dataset import stores path/metadata | yes, Training re-hashes source bytes | missing bytes cannot be reconstructed from the hash |
| Base-model directory | resolved filesystem path/reference | only when operator placed it under workspace | shallow file probe only | no complete directory digest; bytes may change under the same path |
| Training input bundle | Profile SHA-256 + Dataset SHA-256 + parsed samples | derived in memory; provenance written to Training metadata | yes, before backend execution | does not add a base-model content digest |
| Training model artifact | staged same-parent run directory, then final filesystem artifact path | yes for standard full fine-tune output | publication requires model/tokenizer + metadata staging success; later use is still path/existence based | final artifact directory is not content-addressed after publication; hard crashes can leave unpublished staging debris |
| Model-version record | stable model-version ID + Training run ID + artifact path | metadata in SQLite | registry read only | no trained-artifact directory hash in `model_versions` |
| Automation recipe review snapshot | semantic SHA-256 of normalized recipe object | workspace recipes are copied manifests; built-ins are code | yes for the current UI review-to-run path | hash is session/workflow identity, not a signed durable manifest provenance record |
| Automation companion executable/script/data | path/command dependency | no automatic copy | no transitive digest | command identity does not prove dependency bytes |
| Telemetry snapshot | transient sampled values + machine status codes | no | next refresh replaces it | no persisted time-series/provenance artifact |
| Whole-workspace backup | copied workspace tree | yes, by operator backup procedure | restore-time structure only | external Dataset/model/Automation dependencies remain separate |

## 3. Profile Training identity

Training does not hash an arbitrary serialized Profile row. The current input pipeline renders only the fields that participate in Training: Persona, Description, Communication style, Principles and Constraints. Operator notes are deliberately excluded.

The rendered UTF-8 instruction is SHA-256 hashed and persisted as `training_runs.profile_sha256`. At launch PTL renders the current Profile again and requires the digest to match the run snapshot. The Training input bundle computes the same identity again before backend execution.

> **The supported Training path refuses to run when the Training-relevant Profile representation changed after run creation.**

This does not prove that every Profile field or operator note is immutable.

## 4. Dataset byte identity

Dataset import records the external JSONL path. It does **not** copy the source bytes into SQLite.

Validation/approval computes SHA-256 over the complete file bytes. Training creation pins that approved digest into `training_runs.dataset_sha256`, and Training launch re-hashes the current JSONL bytes while constructing the input bundle.

If current bytes no longer match the approved/run fingerprint, Training fails closed instead of silently consuming different data.

The hash proves byte identity only. It does not prove authorship, licensing, ethical suitability, confidentiality, semantic quality, or availability of the original file after deletion.

## 5. Dataset path remains an external dependency

A Dataset row can remain present after the external JSONL source has moved or disappeared. Therefore `Dataset metadata + SHA-256` is not a Dataset backup. Exact reproduction requires preserving the source bytes whose digest was approved.

A workspace-only backup is complete for Dataset bytes only when those source files were themselves intentionally stored inside the copied workspace tree.

## 6. Base-model identity is path/reference based

Training resolves the configured base-model reference to a filesystem directory and performs the current local-model file probe. The run stores the resolved model path/reference.

Current PTL does **not** compute one SHA-256/Merkle identity for the complete base-model directory before Training or inference.

```text
same base-model path
        !=
proof of same base-model bytes
```

The runtime `model_path` read claim coordinates cooperating PTL operations. It does not prevent an external process from changing files under that path.

## 7. Local-model readiness is not provenance

The local-model probe checks expected file categories such as configuration/tokenizer/weight markers. A `found` result means the shallow file-shape requirement passed.

It does not mean every file was hashed, the model came from a trusted publisher, the directory matches an earlier run, the model will load successfully, enough resources exist, or the directory is immutable.

Use external revision IDs/checksums or an independently preserved immutable model directory when exact base-model provenance matters.

## 8. Training execution provenance

Immediately before backend execution, the Training service constructs provenance containing Profile/Dataset IDs and titles, Profile SHA-256, rendered Profile instruction, Dataset path and SHA-256, the approved/run Dataset digests, sample count and schema counts.

The standard full-fine-tune backend embeds that mapping into `<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json` together with backend/run/hyperparameter/result information.

This is stronger than a display-only log, but it still inherits the base-model limitation: current metadata stores `model_path`, not a complete content digest of the source model directory.

## 9. Standard Training artifact identity and publication

The authoritative published layout is:

```text
<workspace>/artifacts/full_finetune/<run_id>/
├── model/
└── training_metadata.json
```

The local full-fine-tune backend first writes those components into a same-parent hidden staging directory and only publishes the final `<run_id>/` directory after model, tokenizer, and metadata writes have all succeeded. The backend refuses to overwrite an already existing final run directory. The Training orchestration layer independently requires a non-empty returned artifact path before it will persist a run as `completed`, so an inconsistent backend result cannot create a completed no-artifact Training record.

This closes a provenance seam in which model bytes could previously be written into the final run namespace before metadata publication succeeded. Under ordinary exception handling, failed staging is best-effort removed and no final artifact path is returned.

The guarantee is intentionally narrow. It is a publication/namespace rule, not a complete filesystem transaction:

```text
published <run_id>/ exists
        =>
backend completed model + tokenizer + metadata staging before publication

but

process/host crash during staging
        =>
hidden .<run_id>-staging-* debris may remain
```

An unpublished staging directory is not a completed artifact and must not be promoted manually merely because it contains plausible model files.

After publication, `model/` remains the trained model/tokenizer output and PTL records its path in the Training run and later in a model-version row. Current v0.1.0 still does not compute/persist a canonical digest for the complete output directory. Moving, deleting or mutating published files in place can therefore change availability/effective bytes without changing `artifact_path`.

Treat published generated artifacts as persistent research outputs, not cache.

## 10. Model-version provenance

The current publication path creates a model-version record only when a completed Training result has a non-empty artifact path. The record carries model-version ID, status, base-model reference, Profile title, Dataset title, Training run ID, artifact path, quality summary and timestamps.

`training_run_id` is the strongest direct link back to the pinned Profile/Dataset Training inputs.

The model-version row does not currently persist Profile SHA-256, Dataset SHA-256, complete base-model digest or complete trained-artifact digest. For cryptographic Training-input identity, follow the Training run rather than treating visible titles as provenance.

## 11. “Snapshot” is a registry view, not a frozen byte package

The Snapshots workspace projects the model-version registry. It does not create another copy of weights and does not freeze the referenced artifact directory.

> **A Snapshot is traceable metadata about a published model version, not a self-contained immutable package.**

If a future release adds content-addressed model bundles, that would be a different contract and must not be inferred from current terminology.

## 12. Automation recipe semantic identity

Workspace Automation recipes are ordinary JSON manifests under `<workspace>/automation/recipes/`. Import copies the manifest itself after validation/collision checks; it does not automatically package companion executables/scripts/data.

The current UI review-to-run path computes a semantic SHA-256 over the normalized `AutomationRecipe` snapshot shown to the user. At Run time the service re-resolves the recipe and compares current identity with the expected reviewed identity.

Mismatch returns `recipe_stale` before runtime lease acquisition and before process launch. This closes the supported UI review-to-run manifest TOCTOU seam.

## 13. Recipe identity is not a signed package identity

The review hash covers normalized recipe fields such as command, inputs, outputs, claims, source/path, working directory and timeout. It does **not** prove the contents of every dependency the command can execute/read.

For example a reviewed `python /opt/research/tool.py` command can keep the same recipe identity even if `/opt/research/tool.py` changes afterward.

```text
reviewed recipe identity
        !=
transitive executable provenance
```

## 14. Automation audit command identity is also narrow

Automation audit identifies the rendered command snapshot PTL launched. It is not a dependency-lock graph and does not automatically hash executable bytes, interpreter packages, referenced scripts/files, network responses or downstream tools.

For reproducible Automation research, preserve those external revisions/checksums explicitly.

## 15. Telemetry has no durable provenance artifact

Current Telemetry is an in-memory operator snapshot surface. It does not persist a versioned measurement artifact or time series.

A screenshot can demonstrate what the UI displayed at one moment, but without a dedicated artifact contract it does not establish continuous resource history, Training-step attribution, exact sampling schedule, measurement completeness, multi-GPU identity, or reproducible causal evidence.

Do not promote current Telemetry into Training Dynamics provenance.

## 16. Paths can dangle

Several supported records contain paths to bytes that are not embedded in SQLite, including `datasets.path`, Training base-model/artifact paths, `model_versions.artifact_path`, and Automation source/working-directory/dependency paths.

A database row can survive after referenced bytes are moved/deleted. Operator/recovery tooling should distinguish:

```text
metadata exists
        !=
referenced bytes exist
        !=
referenced bytes match historical bytes
```

## 17. Same path can point to different bytes

A referenced path can continue to exist while its bytes change. PTL protects this strongly for approved Dataset bytes and Training-relevant Profile representation, but not for the complete base-model directory or a Training artifact **after** it has been published.

Staged artifact publication prevents an ordinary backend save failure from exposing a partial final run directory; it does not make the later published directory immutable or content-addressed.

This distinction must remain visible in research claims.

## 18. Workspace ownership vs external state

A normal workspace contains PTL-owned mutable state such as `app.db`, `agents_lineage_state.json`, `artifacts/`, `automation/recipes/`, logs/exports/cache/temp and workspace-local models.

PTL can also reference host state outside that tree: external Dataset JSONL, explicit base-model directories, Automation executables/scripts/data, Qt QSettings and `~/.persona_training_lab/key_bindings.json`.

Whole-workspace backup semantics apply only to the first set.

## 19. Backup completeness is dependency-relative

A whole-workspace offline backup preserves PTL-owned workspace state together. It does not automatically preserve every dependency required to reproduce every historical workflow.

For reproducibility-grade backup, separately preserve the external Dataset source bytes, base-model revision/checksums, Automation scripts/tools/data, external configuration, and required software/dependency revisions for the experiment.

## 20. Evidence hierarchy for reconstruction

For a completed Training-produced model version, use this order:

```text
model-version ID
        ↓
training_run_id
        ↓
Training run configuration
        ↓
Profile SHA-256 + Dataset SHA-256
        ↓
training_metadata.json provenance
        ↓
trained artifact directory
        ↓
external base-model revision/checksums
```

The lower levels contain byte-level dependencies that the higher registry rows may only reference.

## 21. Failure interpretation

When provenance is incomplete, report the missing layer explicitly. Examples:

```text
Dataset bytes verified by SHA-256; base model identified only by path.
Training artifact directory preserved, but no complete artifact digest was recorded.
Automation recipe review identity matched, but companion script provenance was external.
Model-version row exists, but referenced artifact directory is missing.
```

Do not flatten these into either “fully reproducible” or “no provenance”.

## 22. What current PTL can prove strongly

Within supported paths, current PTL has comparatively strong evidence for exact approved Dataset bytes used by Training, exact Training-relevant Profile representation, Training run identity/configuration/status, semantic Automation recipe review identity for the supported UI run path, linkage from published model version back to a Training run, and standard artifact location/backend metadata.

These guarantees remain narrower than complete experiment/environment provenance.

## 23. What current PTL cannot prove by itself

Current v0.1.0 does not by itself prove complete base-model directory byte identity, complete trained-artifact directory byte identity, immutable external Dataset availability after approval, transitive Automation executable/data identity, complete Python/package/driver/CUDA environment identity for every historical run, persisted Telemetry history suitable for research evidence, or authorship/trustworthiness merely from SHA-256 equality.

These are explicit boundaries, not implied defects in hashing itself.

## 24. Developer invariants

Changes affecting provenance should preserve these rules unless the product contract is deliberately revised:

1. never describe a filesystem path as content-addressed identity without an implemented content digest;
2. Dataset byte hashing and Profile Training hashing must stay distinct from authorship/trust claims;
3. Training must not silently consume Dataset/Profile content that differs from the run's pinned fingerprints;
4. model-version titles must not replace `training_run_id` as provenance identity;
5. staged Training publication must stay distinct from immutable/content-addressed artifact identity; artifact paths must not be described as artifact hashes;
6. Automation recipe review identity must remain distinct from transitive dependency provenance;
7. runtime resource claims must not be described as external filesystem immutability;
8. workspace backups must not be described as complete when required dependencies live outside the workspace;
9. current Telemetry must remain outside research-evidence claims until a persisted/versioned instrumentation contract exists;
10. new content hashes must document exactly which bytes/semantic representation they cover;
11. provenance failures should fail closed only where the implementation owns and checks the corresponding identity;
12. documentation must be updated whenever a path-only dependency becomes content-addressed or vice versa.

## 25. Audit checklist

For any new persisted or executable surface, answer:

```text
What is the stable ID?
What bytes or semantic object does it identify?
Is the identity content-derived or merely a path/reference?
Where is the identity persisted?
Are the referenced bytes copied into the workspace?
Are they rechecked immediately before use?
Can another process change them under the same identity?
Does backup include them?
Can a restore reconstruct the bytes?
Does the UI wording imply stronger immutability than implementation provides?
Does audit evidence identify only the command/record, or also transitive dependencies?
```

## Related documentation

- [Export & Portability Boundaries](../operations/export-portability.md)
- [Training pipeline specification](../training_pipeline.md)
- [Training](../user-guide/training.md)
- [Snapshots and model versions](../user-guide/snapshots.md)
- [Datasets](../user-guide/datasets.md)
- [Automation architecture](automation.md)
- [Telemetry architecture](telemetry.md)
- [Local Models](../operations/local-models.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md)
- [Persistence architecture](persistence.md)
