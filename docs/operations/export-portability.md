# Export & Portability Boundaries

Persona Training Lab v0.1.0 reserves an `exports/` directory inside each workspace, but the current production application does **not** expose a general workspace export, import, migration, or portable-bundle workflow.

The central rule is:

> **A directory named `exports/` is a storage location, not proof that PTL currently implements a product-level exporter.**

For complete backup/recovery procedures, read [Backup, Reset & Recovery](backup-reset-recovery.md). For path ownership, read [Workspace layout reference](../reference/workspace-layout.md).

## 1. Current workspace path

`WorkspacePaths` defines:

```text
<workspace>/exports/
```

and `ensure_workspace_dirs(...)` creates it eagerly together with the workspace root, `artifacts/`, `temp/`, and `cache/`.

The path is therefore stable current workspace structure.

## 2. What current v0.1.0 does not provide

Current production code does not expose a dedicated:

```text
Export workspace
ExportService
workspace bundle exporter
workspace bundle importer
cross-machine migration wizard
portable project package
signed export manifest
export schema/version negotiation
```

Do not describe such a workflow in user documentation unless implementation and tests are added.

## 3. Meaning of `exports/`

The workspace layout classifies `exports/` as:

```text
user-facing output
```

This means files intentionally produced there should be treated as user output rather than disposable cache.

It does **not** mean every PTL record can currently be exported there through a supported UI action.

## 4. Exports are not cache

Do not delete `exports/` merely as routine cache cleanup.

An export or operator-created output may not be reproducible from current database/artifact state.

The backup guide therefore treats `exports/` as workspace data included in a whole-workspace copy.

## 5. Whole-workspace copy is backup, not portable export

The supported v0.1.0 preservation direction is an **offline whole-workspace backup**.

That backup can preserve together:

```text
app.db
agents_lineage_state.json when present
artifacts/
automation/recipes/
models/ when workspace-local
logs/
exports/
cache/
temp/
```

This is a storage/recovery snapshot.

It is not a normalized portable interchange format and is not guaranteed to be independently meaningful without external dependencies.

## 6. External dependencies remain external

A whole-workspace copy does not automatically include state referenced outside the workspace, including:

```text
external Dataset JSONL
explicit external base-model directory
external Automation scripts/binaries/data
Qt QSettings shell state
~/.persona_training_lab/key_bindings.json
Git source checkout
external Automation side effects
```

A copied workspace can therefore be internally intact while still being insufficient to reproduce every historical workflow on another machine.

## 7. Path portability boundary

Several current records use filesystem paths rather than content-addressed portable object identities.

Important examples include:

```text
Dataset source path
base-model path/reference
Training artifact path
model-version artifact path
Automation working directory/dependencies
```

Moving a workspace or restoring it on another host can make an absolute external path invalid.

A path surviving in SQLite does not prove the referenced bytes moved with the workspace.

## 8. Content identity does not imply transport

PTL has strong SHA-256 identity for some workflow inputs, notably approved Dataset bytes and the Training-relevant Profile representation.

Those digests answer identity/integrity questions.

They do not copy missing bytes to a new machine.

For example:

```text
stored Dataset SHA-256
        !=
portable Dataset payload
```

If the Dataset source was external, it must be preserved separately.

## 9. Model artifact portability

Standard full-fine-tune output normally lives under:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
```

A whole-workspace copy therefore includes that artifact when it remains in the standard workspace location.

However, current model-version metadata uses an artifact path/reference and PTL does not persist a canonical digest for the complete model artifact directory.

A successful copy preserves bytes physically present in the workspace, but PTL does not currently provide a signed portable model bundle proving those bytes independently.

## 10. Base-model portability

The configured base model can be workspace-local or an external absolute path.

Current PTL does not content-address the complete base-model directory.

For reproducible migration, preserve the external model revision/checksum separately when the model is not part of the copied workspace.

Do not treat the historical path string as enough to reconstruct the model.

## 11. Dataset portability

Dataset import stores a path rather than copying source bytes into SQLite.

A Dataset source is portable with a workspace copy only when the actual source file is also inside the copied tree or is separately transferred.

The persisted approval SHA-256 can verify restored exact bytes when available; it cannot regenerate them.

## 12. Automation portability

Workspace recipe manifests are included in a whole-workspace copy.

Companion scripts, executables and data are not automatically packaged merely because a recipe references them.

Relative/absolute path assumptions can also differ after migration.

A recipe manifest is therefore not a self-contained portable automation bundle.

## 13. Agents portability

Normal recovery should preserve:

```text
app.db
agents_lineage_state.json
```

from the same offline workspace snapshot.

Copying one without the other can create cross-generation protected-history identity mismatch.

Portability procedures must not “repair” such mismatch by fabricating lineage links.

## 14. Presentation-state portability

A workspace copy includes SQLite Style preferences but not all presentation/input state.

Outside the workspace are:

```text
Qt QSettings
~/.persona_training_lab/key_bindings.json
```

If exact UI/input personalization is part of a migration goal, preserve those separately according to platform/user policy.

They are not part of the research workspace portability contract by default.

## 15. Source-code portability is separate

Git/source state is not part of the runtime workspace.

For a reproducible development/research migration, preserve independently:

```text
Git commit / source release
workspace snapshot
external research dependencies
software/runtime environment
presentation state when relevant
```

Copying only the repository does not copy the runtime workspace.

Copying only the workspace does not identify uncommitted source changes.

## 16. Cross-platform boundary

A raw workspace copy may contain paths or external assumptions specific to the source host.

Current v0.1.0 does not implement a cross-platform path-remapping migration engine.

Therefore:

> **Whole-workspace backup is the supported preservation primitive; portable cross-platform import is not a current product guarantee.**

After moving a workspace between environments, verify every external path/dependency rather than assuming path strings remain valid.

## 17. Minimum manual portability record

When moving research state between machines, record at least:

```text
PTL release/commit
source OS
destination OS
workspace root used for the copy
backup timestamp
Dataset paths + expected SHA-256 identities
base-model revision/checksum strategy
model-version/training-run IDs
artifact locations
external Automation dependencies
Python/dependency environment when reproducibility matters
```

This companion record does not create an official export format; it makes the manual transfer auditable.

## 18. Restore/migration acceptance

Before treating a moved workspace as usable:

1. verify PTL opens the intended workspace;
2. verify SQLite-backed entities;
3. verify Agents local state and same-snapshot safety identity;
4. verify referenced artifact directories;
5. verify external Dataset files and hashes;
6. verify external/base model paths and intended revisions;
7. verify Automation dependencies;
8. check Issues/application logs;
9. run a small non-destructive workflow before expensive/destructive work;
10. separately restore key bindings/QSettings only when those presentation details are required.

A successful application launch alone is not proof of full research portability.

## 19. Future exporter requirements

If PTL later gains a real export/import feature, its contract should state explicitly:

```text
bundle schema/version
included stores
excluded/external dependencies
path remapping
content hashes
artifact identity
Agents JSON/SQLite consistency
encryption/signing, if any
compatibility/migration policy
failure atomicity
partial-import behavior
```

Until those are implemented and tested, they remain requirements for a future feature, not v0.1.0 guarantees.

## 20. Developer invariants

Portability-related changes should preserve these rules unless deliberately redesigned:

1. `exports/` existence must not be presented as proof of a general exporter;
2. exports remain user data rather than routine cache;
3. whole-workspace backup remains distinct from normalized portable export;
4. external dependencies remain explicit when not copied into the workspace;
5. a path/reference is not described as content-addressed identity;
6. Dataset/Profile hashes are not described as transport mechanisms;
7. model artifact/base-model path identity is not upgraded into a byte-provenance claim;
8. Agents JSON and SQLite state remain a coordinated same-snapshot recovery pair;
9. QSettings/key bindings remain outside workspace portability while code stores them there;
10. any future exporter/importer must receive its own schema, failure, provenance, compatibility and regression contracts before documentation calls it supported.

## Related documentation

- [Workspace & Storage](workspace-and-storage.md)
- [Backup, Reset & Recovery](backup-reset-recovery.md)
- [Workspace layout reference](../reference/workspace-layout.md)
- [Provenance & External-State Boundaries](../architecture/provenance-and-external-state.md)
- [Persistence architecture](../architecture/persistence.md)
- [Security, Trust & Privacy Boundaries](security-boundaries.md)
- [Training](../user-guide/training.md)
- [Datasets](../user-guide/datasets.md)
- [Automation](../user-guide/automation.md)
