# Datasets

The **Datasets** workspace imports and validates JSONL data used by Persona Training Lab workflows.

A dataset entry is persistent PTL metadata that points to a source file. Importing a dataset does **not** mean PTL copies the JSONL bytes into `app.db` or automatically makes a private duplicate of the source file.

That distinction is important: if you move, rename, or delete the source JSONL later, validation/preview can no longer read it from the stored path.

## 1. Datasets workspace layout

The workspace is organized around four tasks: choose data, inspect it, validate it, and decide whether it is approved for downstream work.

### Action bar

The top action bar exposes:

- **Add dataset**;
- **Validate**;
- **Approve**;
- **Compare versions**.

In the current v1.0 implementation version comparison is deliberately unavailable. The control is disabled and the service reports `version_compare_unavailable` rather than pretending that a comparison was performed.

### Left column

The left side contains:

- dataset registry;
- versions list for the selected dataset.

Selection is single-item. Changing the selected dataset/version refreshes the preview and validation/summary surfaces.

### Center

The center contains:

- record preview table;
- validation signals/details.

The preview table is read-only. It is for inspecting what PTL parsed, not for editing the JSONL in place.

### Right column

The right side contains:

- dataset/version summary information;
- quality/next-step guidance.

## 2. Supported file type

The v1.0 import path accepts:

```text
.jsonl
```

Only JSON Lines files are accepted by the dataset service.

A path that does not exist, is not a regular file, or has another extension is rejected.

## 3. Add a dataset

1. Open **Datasets**.
2. Select **Add dataset**.
3. Choose the source `.jsonl` file.
4. PTL creates a dataset record in the workspace database.
5. Select the new dataset in the registry if it is not already selected.
6. Review the preview.
7. Run **Validate** before attempting approval.

A new dataset receives an ID with the form:

```text
ds_<8 hexadecimal characters>
```

Initial metadata includes:

```text
format      = jsonl
status      = imported
readiness   = awaiting_validation
schema_name = jsonl_finetune_v1
```

The initial record/valid/invalid counts are zero until validation is performed.

## 4. Source-file ownership

PTL stores the source path in the dataset record:

```text
/path/to/your/data.jsonl
```

Validation and preview reopen that path later.

Therefore:

- do not delete the source file after import unless you no longer need the dataset;
- moving the source file breaks the stored path;
- a workspace backup containing only `app.db` does not automatically preserve an external dataset source;
- if reproducibility matters, keep source datasets in a stable, backed-up location and record their provenance separately.

This is different from generated PTL artifacts stored under the PTL workspace.

## 5. Supported JSONL record shapes

Each non-empty line must contain one JSON object matching one of the supported structural shapes.

### A. Chat `messages`

Example:

```json
{"messages":[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi."}]}
```

Requirements:

- `messages` must be a non-empty list;
- each message must be an object;
- `role` must be one of `system`, `user`, `assistant`;
- `content` must be a non-empty string;
- the record must contain at least one `user` message;
- the record must contain at least one `assistant` message.

A `system` message is allowed but does not replace the required user/assistant pair.

### B. `instruction` / `output`

Example:

```json
{"instruction":"Answer briefly","input":"Question text","output":"Answer text"}
```

Requirements:

- `instruction` is a non-empty string;
- `output` is a non-empty string;
- optional `input`, when present, must be a string.

### C. `prompt` / `response`

Example:

```json
{"prompt":"Question text","response":"Answer text"}
```

Requirements:

- `prompt` is a non-empty string;
- `response` is a non-empty string.

A record that matches none of these structures is reported as an unsupported schema.

## 6. JSONL rules

JSONL means one JSON value per physical non-empty line.

Correct:

```text
{"prompt":"A","response":"B"}
{"prompt":"C","response":"D"}
```

Do not format a single record across several pretty-printed lines.

Blank lines are ignored and do not increment the record count.

Malformed JSON on a non-empty line is counted as an invalid row.

## 7. Validate a dataset

Select a dataset and choose **Validate**.

Validation reads the source file from disk and computes:

- total non-empty rows;
- valid rows;
- invalid rows;
- validation status;
- a bounded preview of validation diagnostics.

The result is persisted back into the dataset record.

### Successful validation

If the file contains at least one record and every record passes structural validation:

```text
status = validated
```

### Structural failure

If one or more rows are structurally invalid:

```text
status = structure_error
```

An empty file is also a structural error.

### File disappeared

If the stored file path no longer points to a file:

```text
status = validation_failed
```

with a file-not-found diagnostic.

## 8. Diagnostic preview limit

Validation can encounter many bad rows, but PTL stores/previews only the first bounded set of diagnostics for the current validation result.

The v1.0 service keeps at most the first **8** validation diagnostics in `validation_errors_preview`.

Do not interpret “8 shown errors” as “the file contains only 8 bad rows”. Use `invalid_count` for the total number of invalid records found.

## 9. Common validation failures

The validator distinguishes problems such as:

- file not found;
- only JSONL is supported;
- invalid JSON;
- record is not an object;
- `messages` is missing/empty/not a list;
- message is not an object;
- unsupported message role;
- empty message content;
- missing user/assistant pair;
- empty instruction;
- empty output;
- non-string `input`;
- empty prompt;
- empty response;
- unsupported schema;
- empty file.

Use the validation panel and preview table together: the panel explains the failure category, while the preview helps identify the actual row/input context.

## 10. Preview behavior

The dataset preview reads at most the requested preview limit; the service default is 25 records.

Preview rows display:

- row identifier such as `#001`;
- a shortened input/prompt summary or diagnostic;
- detected structural schema (`messages`, `instruction/output`, or `prompt/response`);
- structure quality status.

Long text is compacted for preview. The preview is not a byte-for-byte editor of the original JSONL.

## 11. Approve a dataset

Approval is stricter than simply changing a label.

When you choose **Approve**, PTL validates the source file again.

If that validation result is not `validated`, approval is blocked and the failure result is persisted.

Only a structurally valid dataset becomes:

```text
status = approved
```

This revalidation matters because the external source JSONL may have changed since the previous validation.

## 12. Why validation and approval are separate

The two-step flow makes intent explicit:

```text
Imported
   ↓
Validate structure
   ↓
Validated
   ↓
Explicit approval
   ↓
Approved
```

Validation answers “does the current source satisfy the structural contract?”

Approval answers “do I accept this validated source for the next workflow stage?”

## 13. Editing dataset contents

PTL v1.0 does not provide an in-table JSONL editor in the Datasets preview.

To change dataset contents:

1. edit/regenerate the source `.jsonl` using your chosen data tool;
2. save it at the same stored path, or import it as a new dataset if the path/versioning strategy requires that;
3. return to PTL;
4. validate again;
5. approve again when appropriate.

Because approval revalidates, modifying an external file after approval should be treated as changing the effective dataset input even if the PTL dataset ID has not changed.

## 14. Dataset versions in the UI

The UI presents a versions list, but the current v1.0 version-compare operation is explicitly unavailable.

Do not document or rely on a side-by-side version-diff feature that the current service does not implement.

The final v1.0 documentation uses only the behavior actually present in the audited codebase.

## 15. Persistence

Dataset metadata is stored in the workspace SQLite `datasets` table, including fields such as:

- ID;
- title/subtitle;
- source path;
- format;
- status;
- total/valid/invalid counts;
- linked profile field;
- quality/validation summary fields;
- readiness/schema metadata;
- creation/update timestamps.

The JSONL source itself remains a filesystem input at the stored path.

## 16. Backup implications

A complete PTL workspace backup does **not** automatically back up dataset source files located outside the workspace.

For reproducible research or important training inputs, back up both:

```text
PTL workspace
+ external JSONL source/provenance
```

If you intentionally keep datasets inside a separately managed data repository, preserve the same path relationship or be prepared to re-import after restore.

## 17. Safe first dataset

For your first walkthrough, create a small JSONL with 3–10 records using one supported schema.

Example:

```jsonl
{"prompt":"Say hello in one sentence.","response":"Hello — glad to meet you."}
{"prompt":"Answer with one word: sky color?","response":"Blue."}
{"prompt":"What should you do if you are uncertain?","response":"Say that I am uncertain and ask for the missing context."}
```

Then:

1. import it;
2. inspect the preview;
3. validate it;
4. confirm total/valid/invalid counts;
5. approve it.

After you understand the flow, replace the demo input with real research/training data.

## 18. Screenshot plan for v1.0

The final documentation capture session will add:

1. **Datasets workspace overview** — action bar, registry/versions, preview, validation, summary.
2. **Add dataset file dialog** — JSONL selection.
3. **Successful validation** — all rows valid and dataset ready for approval.
4. **Failed validation** — one malformed/unsupported row with its diagnostic.
5. **Approved state** — the same demo dataset after explicit approval.

The example file used for screenshots will be committed/documented demo data or generated deterministically so readers can reproduce the exact walkthrough.

## Next steps

- Define personality intent first: [Profiles](profiles.md)
- Understand file/database ownership: [Workspace & Storage](../operations/workspace-and-storage.md)
- Continue to Training after approval: `training.md` (next v1.0 user-guide chapter)
- Learn the shell: [Interface Tour](interface-tour.md)
