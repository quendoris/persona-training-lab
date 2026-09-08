# Local Models: Setup, Readiness & Health Checks

This operator guide documents the local-model path, file-readiness probe, optional inference stack, smoke-generation path, Training integration, and current v1.0 trust/reproducibility boundaries in Persona Training Lab.

The central distinction is:

> **A model directory passing the PTL file probe means that the expected local files are present. It does not prove that Transformers can load the model, that the host has enough compute/memory, or that a Training run is reproducible from the path alone.**

For workspace ownership and backup semantics, also read [Workspace & Storage](workspace-and-storage.md). For Training input/artifact semantics, read the [Training pipeline specification](../training_pipeline.md).

## 1. Optional model stack

The desktop core does not require Torch or Transformers to launch.

From a source checkout, install local-inference support with:

```bash
uv sync --locked --extra inference
```

The current `inference` extra contains:

- `torch`;
- `transformers`;
- `accelerate`;
- `safetensors`;
- `tokenizers`;
- `sentencepiece`.

For local full fine-tuning, install the Training stack instead:

```bash
uv sync --locked --extra training
```

The `training` extra includes the inference dependencies plus `datasets`.

PTL can therefore start and expose the rest of the workstation even when local inference is intentionally unavailable.

## 2. Default model identity and path

The current application-level default model identity is:

```text
Qwen3.5-0.8B
```

When no explicit model path is configured, or when that model name is used as the model reference, `LocalModelService` resolves it to:

```text
<workspace>/models/qwen3.5-0.8b
```

The workspace root is the same stable platform data root used by the rest of PTL.

Typical defaults are:

```text
Linux:  ${XDG_DATA_HOME:-~/.local/share}/persona-training-lab
Windows: %LOCALAPPDATA%\Persona Training Lab
macOS:  ~/Library/Application Support/Persona Training Lab
```

So the conventional Linux model directory is:

```text
~/.local/share/persona-training-lab/models/qwen3.5-0.8b
```

The core bootstrap does not require `models/` to exist before model workflows are used.

## 3. Relative paths are workspace-relative

PTL deliberately does **not** interpret a relative model reference relative to the terminal/process current working directory.

For example, with workspace root:

```text
/home/user/.local/share/persona-training-lab
```

this model reference:

```text
models/base
```

resolves to:

```text
/home/user/.local/share/persona-training-lab/models/base
```

Changing terminal CWD does not change that resolution.

`~` is expanded, and the final path is resolved to an absolute filesystem path before the probe/generation path uses it.

An explicit absolute model directory can live outside the PTL workspace. Such an external directory is then an operator-managed dependency and is not captured by a workspace-only backup.

## 4. What the file-readiness probe checks

The production provider performs a deliberately shallow filesystem readiness check.

The model path must:

1. exist;
2. be a directory;
3. contain `config.json`;
4. contain at least one supported tokenizer marker;
5. contain at least one supported model-weight marker.

### Tokenizer marker

At least one of these files is sufficient for the file probe:

```text
tokenizer.json
tokenizer.model
tokenizer_config.json
```

### Weight marker

At least one of these conditions is sufficient:

```text
*.safetensors
```

or:

```text
pytorch_model.bin
```

A directory that satisfies these filename checks is reported as `found`.

## 5. What the file probe does not prove

The readiness probe does **not** parse or validate the full model configuration, tokenizer content, tensor integrity, shard index consistency, architecture compatibility, required Transformers version, or available device memory.

It also does not load the model as part of the file check.

Therefore:

```text
found
```

means **expected local files are present**, not **inference is guaranteed to succeed**.

This boundary matters during troubleshooting: a healthy file probe followed by a generation failure is a valid and expected class of failure rather than a contradiction.

## 6. File-probe diagnostics

The application/provider boundary uses machine-readable diagnostic codes and values rather than localized prose as the primary contract.

Current file-probe diagnostics include:

| Diagnostic code | Meaning |
|---|---|
| `model_directory_missing` | The resolved model path does not exist as a directory |
| `required_files_missing` | One or more required file categories are absent |
| `model_files_ready` | The shallow file-readiness contract passed |
| `model_check_failed` | The provider could not complete the filesystem check |

The UI maps these semantic diagnostics to the active locale.

Do not automate against the rendered Russian/English/Spanish/Arabic sentence when the machine code is available.

## 7. Local-model status codes

The local-model state machine currently includes these semantic status values:

| Status | Operational meaning |
|---|---|
| `unchecked` | No current readiness check has been presented |
| `checking` | UI-side readiness check is in progress |
| `found` | File-readiness probe passed |
| `missing` | Model directory or required file category is missing |
| `check_failed` | Readiness check failed unexpectedly |
| `not_loaded` | Generation was requested but the file gate did not pass |
| `generating` | UI-side smoke generation is in progress |
| `responding` | Generation returned non-empty model text |
| `inference_unavailable` | Torch/Transformers inference stack could not be imported/used at the provider entry boundary |
| `empty_response` | Generation completed without usable decoded text |
| `resource_exhausted` | Runtime generation raised a `RuntimeError`; current provider maps this class to insufficient-resource semantics |
| `generation_failed` | Generation failed through another exception path |
| `unknown` | Compatibility/fallback state for an unrecognized status |

Historical rendered-text aliases remain accepted by the normalization layer for compatibility, but semantic status codes are the canonical machine contract.

## 8. Backend probe vs actual generation

`check_inference_backend(...)` is currently a **deferred** probe. It returns the semantic diagnostic:

```text
inference_check_deferred
```

It does not eagerly load Torch, Transformers, tokenizer, or model weights.

The real inference/backend check therefore occurs when PTL attempts generation.

Do not interpret a deferred backend probe as proof that CUDA, CPU inference, model loading, or generation has already succeeded.

## 9. Training workspace smoke test

The Training workspace exposes the current local-model readiness and smoke-generation workflow.

A file check calls the model service and presents semantic status/diagnostic data through localized UI text.

The default smoke prompt is:

```text
MIA_SENTINEL_FT_TEST_001
```

A custom prompt can be supplied by the caller/UI path where supported.

The smoke path is intended to answer an operational question:

> Can the configured local model be loaded by the current inference stack and return non-empty text on this host?

It is **not** the Tests/Analysis evaluation protocol and must not be treated as personality/evaluation evidence.

The generic Training smoke path calls local generation without an instruction prompt. The infrastructure provider therefore does not add a hidden system instruction to that request.

PTL prevents a second Training-workspace smoke generation from being started while the current one is marked in progress.

## 10. Generation path

Before generation, `LocalModelService` runs the same model-file gate for the resolved path.

If that gate does not return `found`, generation stops before provider inference and returns:

```text
status = not_loaded
diagnostic = model_not_loaded
```

If files pass, the production provider imports Torch and Transformers dynamically.

If that import boundary is unavailable, generation returns:

```text
status = inference_unavailable
diagnostic = inference_backend_unavailable
```

This is why a desktop-core installation can remain usable while model generation is unavailable.

## 11. Device and dtype selection

The current production inference provider chooses:

```text
CUDA available -> device=cuda, dtype=float16
otherwise      -> device=cpu,  dtype=float32
```

There is currently no operator-facing device selector in this local smoke path.

The loaded model is moved to the selected device and put into evaluation mode before generation.

A successful CPU fallback can be much slower than CUDA; it is still a legitimate execution path.

## 12. Tokenizer/model loading

The provider loads both components from the resolved local model directory:

```text
AutoTokenizer.from_pretrained(model_path)
AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=...)
```

PTL does not enable Hugging Face `trust_remote_code=True` in this production path.

That means the supported local-model boundary does not intentionally authorize arbitrary model-repository Python through that Transformers mechanism.

The normal OS/Python dependency trust boundary still applies to the installed Torch/Transformers stack and to files the libraries parse.

If the tokenizer has no `pad_token` but does have an EOS token, the provider uses the EOS token as the pad token before generation.

## 13. Chat-template and instruction ownership

The provider always constructs a user message from the requested prompt. A system message is included **only** when the caller supplies a non-blank `instruction_prompt`.

Conceptually:

```text
instruction_prompt absent/blank
    -> user message only

instruction_prompt supplied
    -> system message + user message
```

This means the infrastructure layer does not invent a locale-specific or behavioral instruction for a generic generation request. Workflows that require a protocol instruction must own and pass that instruction explicitly. The current personality-portrait path does this with its scored-response instruction; the generic Training smoke path does not.

The provider first attempts the tokenizer's chat template with:

- the caller-owned message sequence described above;
- `add_generation_prompt=True`;
- tensor output;
- `enable_thinking=False` where the tokenizer accepts that argument.

For tokenizer/template compatibility, PTL retries without `enable_thinking` when the first call raises `TypeError`.

If chat-template construction still cannot be used, the provider falls back to a plain combined prompt. With an explicit instruction the shape is:

```text
System: <instruction>
User: <prompt>
Assistant:
```

Without an instruction the fallback is:

```text
User: <prompt>
Assistant:
```

This fallback is compatibility behavior, not a guarantee that every model family will interpret the prompt identically.

## 14. Current smoke-generation parameters

The production local smoke path currently uses deterministic short generation:

```text
max_new_tokens = 24
min_new_tokens = 1
do_sample = false
no_repeat_ngram_size = 3
repetition_penalty = 1.12
```

EOS is used as both `pad_token_id` and `eos_token_id` for `generate(...)` in the current provider.

These settings are an operational smoke configuration. They are not the canonical Tests evaluation-generation contract.

## 15. Response cleanup

After decoding newly generated tokens, the provider:

1. decodes with `skip_special_tokens=True`;
2. replaces NUL bytes with spaces;
3. collapses whitespace;
4. removes literal `<think>` / `</think>` markers;
5. trims the result.

If no usable text remains, the result is `empty_response`.

The Training smoke panel therefore presents cleaned smoke output rather than a byte-for-byte copy of the raw generated token stream.

## 16. Training integration

Training does not accept an arbitrary base-model label and defer validation until the backend starts.

When a Training run is created, the service:

1. resolves the requested base-model reference through `LocalModelService`;
2. probes the resulting local model directory;
3. requires semantic status `found`;
4. stores the resolved model path in the Training run.

Training repeats the model-file probe when a full fine-tune run is actually started.

This protects against a model directory disappearing between run creation and execution.

It does **not** protect against silent replacement of the files with different bytes at the same path.

## 17. Base-model reproducibility boundary

Training currently stores the resolved base-model path/reference but does not calculate and persist a cryptographic fingerprint of the complete model directory.

Therefore two runs referring to the same path are not automatically proof that they used identical base-model bytes.

For research where exact base-model identity matters:

- keep the source model directory immutable for the relevant run set;
- preserve the upstream model/revision information;
- record independent checksums when necessary;
- back up an external model directory separately from the PTL workspace.

Do not describe the model path itself as content-addressed provenance.

## 18. Model replacement while PTL is running

PTL resolves/probes the model path at operation boundaries, but the model directory remains ordinary host filesystem state.

The local-model service does not lock or snapshot the complete directory and does not create a content hash before smoke inference.

Avoid replacing or partially copying a model directory while a readiness check, inference, or Training operation is using it.

For reproducible work, stage the complete model first and then treat that directory as immutable.

## 19. Security/trust boundary

A local model directory is a trusted local input, but it is not a PTL plugin.

Current production loading does not request `trust_remote_code=True`.

This is narrower than authorizing arbitrary Python from a model repository, but it is not equivalent to opening an untrusted file inside a sandbox. Torch/Transformers/tokenizer/model parsers still process model-controlled data inside the PTL process and OS-account boundary.

Use model files from sources whose integrity/provenance you are prepared to trust.

PTL v1.0 does not provide a model-file malware scanner or a model-loading sandbox.

## 20. Common readiness failures

### `missing` + `model_directory_missing`

Check the resolved path first.

Remember that a relative path is workspace-relative, not terminal-CWD-relative.

### `missing` + `required_files_missing`

Check the diagnostic `files` value. The probe reports missing categories such as:

```text
config.json
tokenizer
weights
```

A tokenizer or weight layout outside the current shallow contract can be valid for another tool while still being unsupported by this PTL readiness check.

### `found`, then `inference_unavailable`

The filesystem shape passed, but the Python inference stack is unavailable at generation time.

For a source checkout, verify that the inference or training extra was installed into the environment from which PTL is actually launched.

### `found`, then `resource_exhausted`

The provider reached runtime model work and caught a `RuntimeError`.

The current status mapping treats this class as a resource-exhaustion failure. Check GPU/CPU memory pressure, model size, device availability, and the host logs before retrying.

### `found`, then `generation_failed`

The shallow file probe cannot guarantee model/config/tokenizer/runtime compatibility. Review the actual model family, installed dependency versions, and diagnostic logs.

### `empty_response`

The model loaded and generated, but no usable text remained after decoding/cleanup. This is different from a missing model or unavailable inference stack.

## 21. What to collect for a local-model bug report

Before changing files, collect:

- exact PTL commit/version;
- OS;
- Python version;
- resolved PTL workspace root;
- resolved model path;
- whether the model is workspace-local or external;
- installed PTL extra (`inference` or `training`);
- local-model semantic status and diagnostic code/values;
- whether the failure occurs in file check, smoke generation, Training-run creation, or Training start;
- CPU/GPU environment and available memory where relevant;
- relevant PTL logs/Issues text;
- model source/revision information without publishing private model data.

Do not post model files, private prompts/responses, complete environment dumps, or workspace databases publicly without reviewing them first.

## 22. Operator checklist before Training

Before creating/starting a real local fine-tune run:

1. confirm the intended workspace root;
2. confirm the resolved base-model directory;
3. ensure model copying/downloading has finished;
4. run the Training local-model file check;
5. run a smoke generation when you need to validate actual inference loading;
6. confirm the correct approved Dataset and Profile;
7. keep the base-model directory stable for the run;
8. ensure sufficient compute/storage for Training artifacts;
9. preserve model provenance/checksums separately when exact reproducibility matters.

## 23. Current v1.0 limitations

The current local-model operator contract deliberately does **not** claim:

- automatic model download;
- exhaustive model-format validation in the readiness probe;
- eager backend/model loading during the backend probe;
- an operator-facing smoke-inference device selector;
- content-addressing of the complete base-model directory;
- automatic immutability/snapshotting of external model files;
- universal compatibility with every Transformers model/chat template;
- remote-code execution through `trust_remote_code=True`;
- sandboxed processing of untrusted model files.

These are boundaries of the implementation, not promises hidden behind the UI.

## 24. Developer invariants

Changes to local-model support must preserve these current architectural rules unless the product contract is deliberately revised:

1. relative model paths are resolved from the PTL workspace, never incidental process CWD;
2. application/UI behavior consumes semantic status/diagnostic codes rather than using localized prose as protocol state;
3. file readiness and actual inference readiness remain distinguishable states;
4. the desktop core remains launchable without optional inference dependencies;
5. Training validates the resolved model path at run creation and again before execution;
6. local model loading must not silently broaden the trust boundary through `trust_remote_code=True`;
7. documentation must not claim complete base-model reproducibility while the model directory lacks a persisted content fingerprint;
8. infrastructure must not invent a system instruction for generic generation; protocol/workflow layers own any explicit `instruction_prompt` they require.
