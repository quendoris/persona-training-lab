# Training

The **Training** workspace creates and runs local supervised full fine-tunes from a PTL Profile, an approved Dataset, a local base model, and explicit hyperparameters.

This guide explains the user workflow. For the exact input transformation, persistence, backend, artifact, and failure contracts, see [Training pipeline specification](../training_pipeline.md).

## 1. Before you create a run

A training run can be created only when all three inputs are available:

1. a PTL Profile;
2. an **approved** Dataset with a stored approval SHA-256;
3. a local model directory that passes PTL's model-file probe.

The recommended workflow is:

```text
Profile
  ↓
Dataset import → Validate → Approve
  ↓
Local model files ready
  ↓
Create Training run
  ↓
Launch
  ↓
Artifact + model-version record
```

If you have not prepared the first two inputs, start with [Profiles](profiles.md) and [Datasets](datasets.md).

## 2. Training workspace layout

The Training workspace has four main areas.

### Run controls

The top action strip shows the current run status and exposes:

- **Launch**;
- **Open logs**;
- **Pause**;
- **Stop**.

In v1.0, **Pause** and **Stop** are intentionally unavailable and remain disabled. A launched full fine-tune runs to a terminal result. Closing PTL while training is still active is guarded by the application's background-work shutdown policy.

### Run overview

The overview shows the current run's:

- status;
- epoch progress;
- loss;
- speed/mode text;
- checkpoint/artifact count;
- overall progress;
- artifact path when one exists.

### Create run

The create-run card contains:

- run name;
- Profile;
- Dataset;
- model reference/path;
- epochs;
- batch size;
- learning rate.

### Local model

The local-model card can:

- check the configured local model files;
- run a small inference probe against the configured local model.

The inference probe is a model-readiness diagnostic. It does **not** automatically switch to the newly produced training artifact after a run completes.

## 3. Default local model location

The default PTL model name is:

```text
Qwen3.5-0.8B
```

When the run's model field is empty, or contains that configured model name, PTL resolves it to:

```text
<workspace>/models/qwen3.5-0.8b
```

The `models/` directory is a conventional local-model location; it is not one of the core directories that bootstrap must create automatically. Create/populate it when you use the default model path.

You may also enter another local model directory explicitly.

## 4. What PTL checks in a model directory

The filesystem probe requires:

- `config.json`;
- at least one tokenizer file from `tokenizer.json`, `tokenizer.model`, or `tokenizer_config.json`;
- model weights as one or more `*.safetensors` files or `pytorch_model.bin`.

The production model loaders do not enable Hugging Face `trust_remote_code=True`.

A successful file probe means the required local files are present. It is not a guarantee that every architecture, driver combination, or model size will train successfully on the current machine.

## 5. Create a run

1. Open **Training**.
2. Choose the intended Profile.
3. Choose an approved Dataset.
4. Confirm the local model reference/path.
5. Set epochs, batch size, and learning rate.
6. Optionally enter a run name.
7. Choose **Create run**.

If the name is blank, PTL generates a title from the new run ID.

Run IDs have the form:

```text
trn_<8 hexadecimal characters>
```

A successfully created run begins in:

```text
ready
```

## 6. Hyperparameter validation

The current run-creation contract requires:

```text
epochs        > 0
batch_size    > 0
learning_rate > 0
```

The UI constrains these values further through its spin-box ranges.

The current local backend performs full-parameter supervised fine-tuning. It is not a LoRA/QLoRA configuration surface.

## 7. A run pins its Profile and Dataset inputs

Creating a run records more than the Profile and Dataset IDs.

PTL stores:

```text
profile_id
profile_sha256
dataset_id
dataset_sha256
```

The Profile fingerprint is the SHA-256 of the exact rendered personality instruction used by Training. It includes:

- profile title/persona name;
- description;
- communication style;
- principles;
- constraints.

It deliberately excludes Profile **notes**. Notes are operator/workspace metadata and are not silently injected into training examples.

The Dataset fingerprint is the SHA-256 recorded when the current external JSONL was approved.

## 8. What happens if inputs change after Create run

A ready run is tied to the Profile/Dataset state for which it was created.

If you edit a training-relevant Profile field after creating the run, the old run will not silently train on the new Profile. Launch fails with the internal condition:

```text
profile_changed_after_run_creation
```

If you change the external JSONL and approve the new bytes under the same Dataset ID, the old run will not silently follow that new approved content. Launch fails with:

```text
dataset_changed_after_run_creation
```

If the external JSONL changes after approval without a new approval, Training detects the byte mismatch at its input boundary and fails with:

```text
dataset_changed_after_approval
```

The safe rule is simple:

> If you intentionally change a training-relevant Profile field or approve different Dataset bytes, create a new Training run.

Changing only Profile notes does not invalidate the run because notes are not part of the training input.

## 9. Base-model identity is path-based in v1.0

The run stores the resolved **base-model path/reference**, and PTL probes that path again before launch.

v1.0 does **not** persist a cryptographic fingerprint of every base-model weight/tokenizer/config file as part of the run record.

For exact research reproducibility, therefore:

- keep the base-model directory immutable for the lifetime of the run;
- record the model source/revision/checksum externally when that identity matters;
- do not replace weights in place under the same path between run creation and launch.

This is a documented operating boundary, not a claim that the base-model bytes are content-addressed by PTL.

## 10. Launch a run

A run can launch only from `ready`.

When you choose **Launch**, PTL rechecks:

- run state;
- local model availability;
- Profile existence and pinned Profile fingerprint;
- Dataset existence;
- Dataset approval state;
- stored approval fingerprint;
- pinned run-level Dataset fingerprint;
- current JSONL bytes and Training parser validity;
- runtime resource availability.

Only after those checks does the backend move the run to `running` and begin fine-tuning.

## 11. Runtime resource coordination

Training claims runtime resources for the run, model path, Dataset, Profile, and local training compute device.

If another coordinated operation conflicts with those claims, launch returns a controlled `resource_busy` result rather than starting competing work blindly.

The Training screen executes the long-running call in a background `QThread`, so the Qt UI is not expected to run the fine-tune loop on the main GUI thread.

## 12. How Profile text enters samples

PTL renders the Profile into this conceptual system prefix:

```text
System persona specification:
Persona: ...
Description: ...
Communication style: ...
Principles: ...
Constraints: ...
```

Only non-empty rendered sections are included.

That prefix is prepended to all supported Dataset schemas before supervised examples are built.

## 13. Supported Dataset schemas during Training

Training accepts the same structural families documented by the Datasets workspace:

- `prompt` / `response`;
- `instruction` / `output`, with optional string `input`;
- `messages` with `system`, `user`, and `assistant` roles.

For `messages`, PTL produces one supervised sample for each assistant turn that has at least one user message before it in the same record.

Example:

```json
{"messages":[
  {"role":"user","content":"A"},
  {"role":"assistant","content":"B"},
  {"role":"user","content":"C"},
  {"role":"assistant","content":"D"}
]}
```

produces two supervised targets: `B` and `D`, each with the preceding conversation context appropriate to that assistant turn.

The Datasets validator is aligned with this rule: a `messages` record cannot be approved merely because a user and assistant both occur somewhere in the array; at least one assistant target must have preceding user context.

## 14. Current full-fine-tune behavior

The v1.0 local backend:

- loads the tokenizer and causal language model from the local directory;
- chooses CUDA when available, otherwise CPU;
- uses float16 on CUDA and float32 on CPU;
- trains all parameters whose `requires_grad` flag is true;
- uses SGD with the run learning rate;
- clips gradient norm to `1.0`;
- processes samples in their loaded order;
- uses an effective batch size no larger than the sample count;
- masks prompt tokens from the supervised loss;
- truncates each packed example to a maximum length of 512 tokens.

If truncation leaves no answer tokens to supervise, that example cannot be trained successfully.

## 15. What is and is not counted as a checkpoint

The current backend does not emit a periodic checkpoint after every epoch/step.

On successful completion it saves one final model artifact. The run surface therefore reports one artifact/checkpoint when that final output exists.

Do not interpret the v1.0 `checkpoints_count` field as a complete checkpoint-management system.

## 16. Artifact location

A successful local full fine-tune saves the final model under:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
```

The tokenizer is saved alongside the model.

The backend also writes:

```text
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

The metadata records backend/run information, hyperparameters, sample/step counts, losses, device, trainable parameter count, and Training provenance.

Treat the entire run directory as persistent generated output.

## 17. Training provenance

The backend provenance includes the selected Profile/Dataset identifiers and titles, Dataset path and SHA-256, approved/pinned Dataset SHA-256, Profile instruction/fingerprint, sample count, and schema counts.

This provenance binds the artifact to the Profile/Dataset snapshot actually accepted by the Training boundary.

Remember the base-model limitation from section 9: the model path is recorded, but v1.0 does not cryptographically content-address the full base-model directory.

## 18. Completion and model-version publication

A successful backend result moves the run to:

```text
completed
```

and records the artifact path.

The Training view-model then attempts to publish/register a model-version record from the latest completed run. The resulting model-version metadata includes the Training run ID and artifact path.

If you are inspecting lineage or later evaluation workflows, use those persisted identifiers rather than inferring provenance only from a directory name.

## 19. Failure behavior

A Training run can fail before or during backend execution.

Examples include:

- model missing;
- Profile/Dataset missing;
- Dataset not approved;
- missing approval/run fingerprints;
- Profile or Dataset changed after run creation;
- Dataset bytes changed after approval;
- invalid Training input;
- runtime resource conflict;
- unavailable training dependencies;
- insufficient compute/memory resources;
- artifact creation failure;
- unexpected exception captured by the application error boundary.

Terminal failures persist an error message and finish timestamp on the run.

Use **Open logs** for the technical sequence leading to the failure.

## 20. Logs

Training logs are persisted in SQLite and shown in the Training workspace.

A successful run records information such as:

- start;
- Profile/Dataset IDs and fingerprints;
- sample count;
- hyperparameters;
- backend result;
- loss/step/trainable-parameter summary;
- artifact path;
- model-version registration when publication succeeds.

Logs are useful diagnostic evidence, but they do not replace `training_metadata.json` or the persisted run fields as the provenance contract.

## 21. Safe first run

For a first real walkthrough:

1. create a small Profile with explicit principles/constraints;
2. import a 3–10 record JSONL;
3. validate and approve it;
4. prepare a small compatible local causal language model;
5. create a run with `epochs = 1`, `batch_size = 1`, and a conservative learning rate appropriate to the model;
6. launch;
7. watch the run status/logs;
8. confirm the artifact directory and `training_metadata.json` exist;
9. inspect the newly registered model version before moving into Tests/Analysis.

A tiny first run is for verifying the workflow, not for making a quality claim about the trained personality.

## 22. Backup implications

Training spans both SQLite and filesystem state:

```text
app.db
+ artifacts/full_finetune/<run_id>/...
+ external Dataset source
+ base-model directory/source identity
```

A backup of only `app.db` does not preserve the trained model artifact. A backup of only the artifact does not preserve the full PTL run/lineage metadata.

See [Workspace & Storage](../operations/workspace-and-storage.md) for the workspace-level backup contract.

## 23. Screenshot plan for v1.0

The final documentation capture session should include:

1. Training workspace overview;
2. create-run card with Profile/Dataset/model/hyperparameters;
3. ready run before launch;
4. running state with logs/progress;
5. completed run with artifact path;
6. controlled failure example for changed/unapproved input;
7. local-model probe/inference block.

Screenshots should be captured from a clean documented demo workspace and recorded commit/locale/theme/scale.

## Next steps

- Prepare data: [Datasets](datasets.md)
- Understand personality input: [Profiles](profiles.md)
- Read the exact technical contract: [Training pipeline specification](../training_pipeline.md)
- Understand storage/backup: [Workspace & Storage](../operations/workspace-and-storage.md)
- Continue into model versions, Snapshots, Tests, and Analysis as those v1.0 guides are completed.
