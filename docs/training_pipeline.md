# Training pipeline specification

This document is the technical v1.0 specification for Persona Training Lab's local Training pipeline.

It describes the behavior implemented by the audited codebase, not a future training architecture. The task-oriented workflow is documented separately in [Training](user-guide/training.md).

## 1. Scope

The v1.0 Training pipeline is a local supervised **full-parameter** causal-language-model fine-tune.

The pipeline accepts a Profile, an approved Dataset, a local base-model path, and explicit `epochs`, `batch_size`, and `learning_rate` values. On success it produces:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

The UI may also register a model-version row derived from the completed run.

## 2. Layered flow

```text
TrainingScreen
    ↓
TrainingViewModel
    ↓
TrainingService
    ├── ProfilesService
    ├── DatasetsService
    ├── LocalModelService
    ├── RuntimeOperationCoordinator
    └── Training repository
            ↓
load_training_input_bundle(...)
            ↓
LocalFullFineTuneBackend.run(...)
            ↓
model artifact + metadata
            ↓
Training run terminal state
            ↓
ModelVersionsService publication attempt
```

The screen moves the blocking Training call to a background `QThread`; the fine-tune backend itself is synchronous.

## 3. Training run persistence

`training_runs` persists creation-time configuration plus runtime state. Important fields include:

```text
id
title
status
base_model
profile
profile_id
profile_sha256
dataset_version
dataset_id
dataset_sha256
mode
epochs
batch_size
learning_rate
epoch_progress
loss
speed
checkpoints_count
progress
started_at
finished_at
artifact_path
error_message
updated_at
```

A new run ID is `trn_<8 hexadecimal characters>`.

## 4. Create-run preconditions

`TrainingService.create_training_run(...)` rejects creation unless:

- `epochs > 0`;
- `batch_size > 0`;
- `learning_rate > 0`;
- the selected Profile exists and renders a non-empty Training instruction;
- the selected Dataset exists;
- the Dataset status normalizes to `approved`;
- the Dataset has a non-empty `content_sha256` recorded by approval;
- a local-model service is configured;
- the resolved model path passes the local model-file probe.

A successful run is stored as `ready`.

## 5. Profile Training representation

Training does not serialize the entire Profile row into the model prompt. `build_profile_instruction(...)` renders only:

```text
Persona: <title>
Description: <description>
Communication style: <communication_style>
Principles: <principles>
Constraints: <constraints>
```

Empty rendered fields are omitted. Profile `notes` are intentionally excluded and remain operator/workspace metadata.

The Profile Training fingerprint is:

```text
SHA256(UTF-8(profile_instruction))
```

This value is persisted as `training_runs.profile_sha256` at run creation.

## 6. Dataset approval fingerprint

Datasets are external JSONL filesystem inputs referenced by stored path. Validation/approval computes SHA-256 over the source file bytes and persists it in `datasets.content_sha256`.

Creating a Training run copies the current approved value into `training_runs.dataset_sha256`. This separates Dataset identity (`dataset_id`) from the exact approved content snapshot used to authorize the run.

## 7. Run-level input pinning

A run is not allowed to silently follow later mutations under the same Profile or Dataset ID.

At launch PTL checks:

```text
current profile Training hash == run.profile_sha256
current approved Dataset hash  == run.dataset_sha256
```

If the Profile changed after creation, the terminal condition is `profile_changed_after_run_creation`. If the Dataset was changed and re-approved after creation, it is `dataset_changed_after_run_creation`. If the run does not contain the required fingerprints, it fails as `training_input_snapshot_missing`.

A new run is required after an intentional training-relevant Profile change or Dataset re-approval. Changing only Profile notes does not invalidate the run because notes are not part of the Training representation.

## 8. Dataset byte check at Training boundary

After run-level checks, `load_training_input_bundle(...)` reopens the JSONL and computes a SHA-256 digest over the current file bytes. The resulting `bundle.dataset_sha256` must equal the run-pinned Dataset SHA-256.

A mismatch is terminal as `dataset_changed_after_approval`.

The source JSONL remains externally owned filesystem state; PTL does not copy it into SQLite when it is imported.

## 9. Base-model identity boundary

The run stores a resolved local **path/reference** for the base model. PTL probes that model location at creation and again at launch, but v1.0 does not persist a cryptographic digest of the complete model directory.

Therefore the Training provenance contract is content-pinned for the Profile representation and Dataset approval bytes, while the base model is path-identified.

For exact research reproducibility, operators should keep the base-model directory immutable and separately record its source revision/checksum.

## 10. Model-path resolution and probe

The configured default model is `Qwen3.5-0.8B`. An empty reference or that exact configured name resolves to:

```text
<workspace>/models/qwen3.5-0.8b
```

The filesystem provider requires `config.json`, at least one tokenizer indicator (`tokenizer.json`, `tokenizer.model`, or `tokenizer_config.json`), and weights as `*.safetensors` or `pytorch_model.bin`.

The probe is a file-readiness check, not a claim of hardware feasibility or architecture compatibility.

## 11. Model-loading trust boundary

Production local model inference/training uses Transformers loaders without opting into `trust_remote_code=True`.

A future compatibility change that reintroduces remote repository Python execution would alter the product trust model and must be deliberate.

## 12. Dataset schemas

Each non-empty JSONL line must be a JSON object accepted by one of three schemas.

### `prompt` / `response`

Both are required non-empty strings. The Training prompt is the Profile system prefix followed by `User:` and the prompt; the supervised target is `response`.

### `instruction` / `output`

`instruction` and `output` are required non-empty strings. Optional `input` must be a string. The supervised target is `output`.

### `messages`

`messages` must be a non-empty list of objects with roles from `system`, `user`, `assistant` and non-empty string content.

Training emits one sample per assistant turn that has at least one preceding user turn. The prompt contains the Profile system prefix plus all preceding normalized message context; the current assistant content becomes the supervised target.

## 13. Dataset validator compatibility requirement

Datasets approval is intentionally aligned with the Training parser.

A `messages` record is invalid if it cannot yield at least one trainable assistant target with preceding user context. A record ordered as assistant then user must not pass approval merely because both roles exist.

This alignment prevents Datasets from approving a record that Training would later reject as `messages_missing_pair`.

## 14. Training input bundle

A successful `load_training_input_bundle(...)` returns:

```text
samples
dataset_path
dataset_sha256
profile_instruction
profile_sha256
schema_counts
```

Each `TrainingSample` records `prompt`, `response`, `source_line`, and `schema`. The Dataset must produce at least one Training sample or the boundary raises `dataset_empty`.

## 15. Runtime operation claims

Before backend execution, Training requests an operation lease with claims for the Training run (write), model path (read), Dataset (read), Profile (read), and `compute_device:local_training` (write).

A conflict produces controlled `resource_busy` behavior and does not start the backend.

If a lease is opened, the Training service closes it with success/failure terminal state. The `finally` boundary fails an otherwise unclosed lease as `operation_without_terminal_status`.

## 16. Backend dependency loading, device, and dtype

The full backend imports `torch` and `transformers` at runtime. If those dependencies are unavailable, it returns `training_backend_unavailable`.

The backend selects CUDA when `torch.cuda.is_available()` and CPU otherwise. It uses float16 on CUDA and float32 on CPU, moves the model to the selected device, and sets training mode.

## 17. Trainable parameters

The backend trains every model parameter whose `requires_grad` flag is true and records the total count as `trainable_params`.

If none are trainable, it returns `no_trainable_parameters`.

v1.0 does not expose LoRA/QLoRA/adapters as the Training workspace's production backend.

## 18. Supervised objective

For each sample, the backend concatenates:

```text
prompt + " " + response + eos
```

The tokenized prompt prefix is masked in `labels` with `-100`; only answer tokens contribute to the supervised causal-language-model loss.

The packed example is truncated to `max_length = 512`. If truncation leaves no answer labels, example construction fails.

## 19. Batching, optimizer, and gradient handling

The effective batch size is:

```text
max(1, min(configured_batch_size, sample_count))
```

Batches are padded to the longest sequence in the batch. Attention-mask padding is `0`; label padding is `-100`.

The v1.0 backend uses SGD at the configured learning rate. For each step it zeroes gradients, performs the forward pass, backpropagates loss, clips gradient norm to `1.0`, and steps the optimizer. A missing loss returns `training_loss_missing`.

## 20. Epoch/step calculation

```text
steps_per_epoch = ceil(sample_count / effective_batch_size)
target_steps    = epochs * steps_per_epoch
```

The backend loops through samples in loaded order for every epoch and does not shuffle them between epochs. It records initial, final, and best loss plus completed/target step counts.

## 21. Checkpoint behavior

The backend does not create periodic step/epoch checkpoints.

After all configured steps complete successfully it saves one final model/tokenizer artifact. The run's `checkpoints_count` is therefore `01` when a final artifact path exists and `00` otherwise.

## 22. Artifact layout

Successful output is stored under:

```text
<workspace>/artifacts/full_finetune/<run_id>/
├── model/
└── training_metadata.json
```

The exact files inside `model/` depend on the Transformers model/tokenizer save implementation. The entire run directory is persistent generated state.

## 23. Training metadata and provenance

`training_metadata.json` uses:

```text
schema = ptl:full-finetune:v1
backend = local_full_finetune
```

and records the run ID, model path, configured/effective batch size, epochs, learning rate, sample/step counts, trainable parameter count, losses, device, provenance, and terminal status.

The Training service supplies provenance containing:

```text
profile_id
profile_title
profile_instruction
profile_sha256
dataset_id
dataset_title
dataset_path
dataset_sha256
approved_dataset_sha256
run_dataset_sha256
sample_count
schema_counts
```

The hash values bind the persisted run/artifact provenance to the accepted Profile Training representation and approved Dataset bytes. `model_path` is recorded separately but does not cryptographically fingerprint the complete base-model directory.

## 24. Run state transitions

Normal success path:

```text
ready → running → completed
```

Failure can occur before `running` or during backend execution and produces a persisted `failed` state.

A run already in `running` is rejected as `already_running`; a run not in `ready` is rejected as `not_ready`.

On success PTL persists completed status, `progress = 1.0`, final epoch progress/loss, `speed = full fine-tune`, artifact/checkpoint count, finish time, artifact path, and empty error text. On failure it persists a terminal failed state with error text and finish time.

## 25. Error boundary

Unexpected exceptions are captured through the application error reporter when configured. The Training service then records `safe_stop` or `safe_stop:<error_id>` and returns a controlled action result.

## 26. Model-version publication

After the Training call returns and the view-model refreshes, a completed run with an artifact path is eligible for model-version publication through `ModelVersionsService.create_from_training_run(...)`.

Publication is downstream metadata registration; it is not part of the backend weight update itself.

## 27. Local inference probe distinction

The Training screen's local inference probe uses the configured `LocalModelService` model path. It is a readiness/smoke test for that configured local model.

Completion of a Training run does not automatically repoint that service to the new `<run_id>/model` artifact.

## 28. Pause/stop limitation

The current Training UI includes Pause and Stop controls, but they are disabled in v1.0. The full backend does not implement cooperative per-step cancellation.

The application owns background thread shutdown and can refuse window closure while owned work has not stopped within the configured shutdown wait.

## 29. Reproducibility statement

v1.0 provides strong provenance for the Profile Training representation, approved Dataset bytes, run hyperparameters, sample/schema counts, backend/device/result metrics, and generated artifact path.

v1.0 does **not** claim full content-addressed reproducibility of the base-model directory, Python/driver/CUDA binaries, hardware state, or every nondeterministic behavior of the underlying ML stack.

A research workflow that requires bit-level rerun identity must record those additional inputs outside the current Training run schema.

## 30. Acceptance coverage

The Training contracts are covered by release tests for run creation, Dataset/Training structural compatibility, input rendering and hashing, run-level Profile/Dataset snapshot integrity, approval-byte mismatch behavior, runner completion/failure semantics, the supervised objective, local-model probing, and model-version publication.

The canonical release gate, not this document, is the source of truth for a particular commit's pass/fail evidence.

## Related documentation

- [Training user guide](user-guide/training.md)
- [Datasets](user-guide/datasets.md)
- [Profiles](user-guide/profiles.md)
- [Workspace & Storage](operations/workspace-and-storage.md)
- [v1.0 Product Contract](reference/v1-product-contract.md)
- [Runtime resource safety](architecture/runtime-resource-safety.md)
