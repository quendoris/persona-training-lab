# Datasets

The **Datasets** workspace imports, previews, validates, and explicitly approves JSONL data for Persona Training Lab workflows.

A Dataset record is persistent PTL metadata that points to a source file. Importing a Dataset does **not** copy the JSONL bytes into `app.db` or automatically create a private duplicate.

## 1. Workspace purpose

The Dataset flow is:

```text
Add source path
    ↓
Imported
    ↓
Preview / Validate
    ↓
Validated
    ↓
Explicit Approve
    ↓
Approved + content SHA-256
    ↓
Eligible for Training run creation
```

The top action bar exposes **Add dataset**, **Validate**, **Approve**, and **Compare versions**.

Version comparison is deliberately unavailable in the current v1.0 implementation. The service reports `version_compare_unavailable` rather than pretending that a comparison occurred.

## 2. Source-file ownership

PTL stores the source path and reopens that file for preview, validation, approval, and Training.

Therefore:

- moving/renaming the source breaks the stored path;
- deleting it makes later validation/Training impossible;
- a backup containing only `app.db` does not preserve an external source JSONL;
- important Dataset sources should live in a stable, backed-up location.

Generated Training artifacts are different: those are PTL-owned outputs under the workspace `artifacts/` tree.

## 3. Supported file type

The v1.0 import path accepts only regular files with the extension:

```text
.jsonl
```

Missing paths and other extensions are rejected.

## 4. Add a Dataset

1. Open **Datasets**.
2. Choose **Add dataset**.
3. Select a `.jsonl` file.
4. PTL creates a persistent Dataset row.
5. Inspect its preview.
6. Run **Validate**.
7. Approve only after the validation result is acceptable.

New Dataset IDs use:

```text
ds_<8 hexadecimal characters>
```

Initial metadata includes:

```text
format      = jsonl
status      = imported
readiness   = awaiting_validation
schema_name = jsonl_finetune_v1
content_sha256 = ""
```

Record/valid/invalid counts begin at zero.

## 5. JSONL rule

Each physical non-empty line is one JSON value. Blank lines are ignored.

Correct:

```text
{"prompt":"A","response":"B"}
{"prompt":"C","response":"D"}
```

Do not pretty-print one record across several physical lines.

Malformed JSON on a non-empty line is counted as an invalid row.

## 6. Supported record shapes

Every non-empty line must contain a JSON object matching one of the supported Training-compatible shapes.

### A. `prompt` / `response`

```json
{"prompt":"Question text","response":"Answer text"}
```

Both fields must be non-empty strings.

### B. `instruction` / `output`

```json
{"instruction":"Answer briefly","input":"Question text","output":"Answer text"}
```

Requirements:

- `instruction` is a non-empty string;
- `output` is a non-empty string;
- optional `input`, when present, is a string.

### C. Chat `messages`

```json
{"messages":[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi."}]}
```

Requirements:

- `messages` is a non-empty list;
- each item is an object;
- `role` is `system`, `user`, or `assistant`;
- `content` is a non-empty string;
- the record contains at least one **trainable** assistant target with preceding user context.

That final rule is stricter than merely finding both roles somewhere in the array.

This is invalid for Training compatibility:

```json
{"messages":[{"role":"assistant","content":"A"},{"role":"user","content":"B"}]}
```

because the assistant turn has no preceding user context. The Datasets validator and Training parser intentionally share this requirement so an approved record cannot later fail simply because its conversation order was unusable.

A `system` message is allowed but does not replace the required user-before-assistant training context.

## 7. Validate

Validation reopens the source file and computes:

- total non-empty rows;
- valid rows;
- invalid rows;
- validation status;
- bounded diagnostic preview;
- SHA-256 of the source bytes when the path can be read.

The result is persisted to the Dataset row.

If every record is valid and the file is non-empty:

```text
status = validated
```

If structural errors exist or the file is empty:

```text
status = structure_error
```

If the stored path no longer points to a file:

```text
status = validation_failed
```

## 8. Diagnostic preview

The service persists at most the first **8** diagnostics in `validation_errors_preview`.

That does not cap the total number of invalid rows; use `invalid_count` for the total.

Common diagnostics include invalid JSON, non-object record, bad `messages` shape, unsupported role, empty content, missing trainable user/assistant pair, empty instruction/output/prompt/response, non-string `input`, unsupported schema, and empty file.

## 9. Preview

Preview is read-only. It does not edit the JSONL in place.

The service default preview limit is 25 records. Rows show a row ID, shortened input/prompt or diagnostic, detected structural schema, and structural quality.

Long values are compacted for display; preview is not a byte-for-byte editor.

## 10. Approve

Approval is an explicit authorization step, not a label toggle.

When you choose **Approve**, PTL validates the current source file again. Approval succeeds only if that fresh validation result is `validated`.

A successful approval persists:

```text
status = approved
content_sha256 = SHA256(current source bytes)
```

This hash is the **approval fingerprint** for the current external JSONL content.

## 11. Why the approval SHA-256 matters

The Dataset ID identifies a PTL record, not immutable file bytes. The external file can be edited later at the same path.

The approval fingerprint lets downstream Training distinguish:

```text
same dataset_id
```

from:

```text
same dataset_id + same approved bytes
```

When a Training run is created, the current approved `content_sha256` is copied into that run as its pinned Dataset fingerprint.

## 12. Dataset changes after approval

If you edit the source JSONL after approval, the old approval hash no longer describes the current bytes.

Two cases matter.

### Changed but not re-approved

Training recomputes the current Dataset SHA-256 at its input boundary. If the bytes differ from the run/approval fingerprint, launch fails rather than silently consuming the changed file.

### Changed and re-approved

Re-approval stores the new SHA-256 under the same Dataset ID. An older Training run still retains the previous pinned Dataset hash and therefore refuses to follow the newly approved bytes.

The safe workflow is:

```text
edit Dataset
→ Validate
→ Approve
→ create a new Training run
```

## 13. Validation vs approval

Validation asks:

> Does the current file satisfy the structural contract?

Approval asks:

> Do I explicitly accept these exact currently validated bytes for downstream work?

Keeping those actions separate makes both machine validity and user intent visible.

## 14. Editing Dataset contents

PTL v1.0 does not provide an in-table JSONL editor.

To change a Dataset:

1. edit/regenerate the external `.jsonl` with another tool;
2. keep the stored path or import a separate Dataset when your versioning strategy requires it;
3. return to PTL;
4. Validate again;
5. Approve the new bytes;
6. create new Training runs for the new approved content.

## 15. Persistence

Dataset metadata is stored in the SQLite `datasets` table, including:

- ID/title/subtitle;
- source path and format;
- status/readiness;
- total/valid/invalid counts;
- diagnostic/quality fields;
- schema metadata;
- `content_sha256`;
- timestamps.

The source JSONL itself remains filesystem input at the stored path.

## 16. Backup implications

A complete PTL workspace backup does **not** automatically include Dataset sources located outside the workspace.

For reproducible Training work, preserve:

```text
PTL workspace
+ external JSONL source
+ source provenance/version information
```

The approval SHA-256 is useful evidence of content identity, but it cannot restore bytes that were not backed up.

## 17. Safe first Dataset

Create a small 3–10 record JSONL using one supported schema, for example:

```jsonl
{"prompt":"Say hello in one sentence.","response":"Hello — glad to meet you."}
{"prompt":"Answer with one word: sky color?","response":"Blue."}
{"prompt":"What should you do if uncertain?","response":"Say that I am uncertain and ask for missing context."}
```

Then import, preview, Validate, verify counts, and Approve it. Once the flow is clear, replace the demo source with real research/training data.

## 18. Screenshot plan for v1.0

The final capture pass should include the workspace overview, add-file dialog, successful validation, a failed validation example, and the approved state.

The demo source should be deterministic so the walkthrough can be reproduced.

## Next steps

- Define personality intent: [Profiles](profiles.md)
- Run a fine-tune: [Training](training.md)
- Understand file/database ownership: [Workspace & Storage](../operations/workspace-and-storage.md)
- Learn the shell: [Interface Tour](interface-tour.md)
