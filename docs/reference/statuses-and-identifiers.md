# Statuses, Result Codes & Identifiers

This reference defines the machine-semantic status values, result/error/diagnostic codes, event identities, and generated identifier formats that Persona Training Lab v1.0 currently exposes in code and persistence.

It is intentionally strict about vocabulary. A persisted status, an application action code, a user-message key, a diagnostic code, an event type, and an object ID can all be short strings, but they are **not interchangeable contracts**.

The central rule is:

> **Use canonical machine semantics for program logic and persistence; translate only at presentation boundaries. Never infer state from a rendered label when a stable status/code/ID exists.**

## 1. Machine-semantic taxonomy

PTL currently uses several distinct string classes.

| Class | Example | Meaning |
|---|---|---|
| Canonical status | `approved_for_training` | Lifecycle/readiness state of a domain/runtime object |
| Compatibility alias | `approved`, `одобрен` | Legacy/rendered input accepted by a normalizer and mapped to a canonical status |
| Action/result code | `resource_busy` | Machine outcome of one attempted application action |
| Exception code | `invalid_hyperparameters` | Stable semantic code carried by a typed application exception |
| Diagnostic code | `invalid_json` | Machine reason attached to a validation/preview diagnostic |
| User-message key | `error.training.full_finetune.safe_stop` | Locale-independent reference resolved to presentation text |
| Event type | `automation.run.finished` | Structured event family/phase in `event_log` |
| Schema marker | `ptl:automation-audit:v1` | Versioned payload/manifest contract |
| Identifier | `trn_0123abcd` | Stable identity of a persisted/runtime entity |

Code must not compare across these classes merely because two values happen to use lower snake case.

## 2. Human labels are not canonical machine values

Several compatibility normalizers still recognize historical Russian/English display strings. This is a migration/compatibility surface, not permission to persist new localized states.

For example:

```text
Dataset alias "approved"
        ↓ normalize_dataset_status(...)
approved_for_training
```

and:

```text
Model-version alias "stable"
        ↓ normalize_model_version_status(...)
ready
```

New workflow logic should prefer the canonical enum/code and localize it only for display.

## 3. Profile status contract

`ProfileStatus` defines:

```text
ready
active
draft
archived
unknown
```

Current Profile creation/update writes `ready`.

These lifecycle values are separate from Profile `ActionResult` codes such as `created`, `updated`, or `title_required`.

## 4. Dataset version status contract

`DatasetVersionStatus` defines:

```text
draft
imported
validated
approved_for_training
structure_error
validation_failed
archived
unknown
```

Current import starts a Dataset at:

```text
status = imported
```

Validation can produce:

```text
validated
structure_error
validation_failed
```

Explicit author approval converts a successful validated Dataset to:

```text
approved_for_training
```

Training requires that approved state plus the stored approval content SHA-256.

## 5. Dataset readiness status contract

`DatasetReadinessStatus` defines a separate readiness vocabulary:

```text
awaiting_validation
awaiting_author_approval
approved_for_training
requires_fix
validation_failed
```

Do not treat Dataset version status and readiness status as the same enum just because `approved_for_training` occurs in both.

Current import initializes readiness to:

```text
awaiting_validation
```

and records schema identity:

```text
jsonl_finetune_v1
```

## 6. Dataset compatibility normalization

The Dataset status normalizer accepts historical/rendered aliases including forms such as:

```text
черновик                     -> draft
unchecked / не проверен      -> imported
ready for training           -> validated
готов к обучению             -> validated
approved                     -> approved_for_training
approved for training        -> approved_for_training
одобрен / одобрен для обучения -> approved_for_training
structure error              -> structure_error
ошибка структуры             -> structure_error
validation failed            -> validation_failed
архивный                     -> archived
```

Unrecognized input becomes:

```text
unknown
```

`ready for training -> validated` is particularly important: historical wording does **not** bypass the separate explicit approval step.

## 7. Training run status contract

`TrainingRunStatus` defines:

```text
created
ready
running
failed
completed
unknown
```

The current `TrainingService.create_training_run(...)` creates a persisted run directly as:

```text
ready
```

A successful start enters:

```text
running
```

and terminates as either:

```text
completed
failed
```

`created` remains part of the canonical enum/compatibility model even though the current create path stores `ready` after validating configuration.

## 8. Training compatibility normalization

Training status normalization supports exact aliases plus bounded prefix compatibility.

Examples include:

```text
создан / создано              -> created
ready to start / готов к запуску -> ready
выполняется / в процессе      -> running
failure / error / ошибка      -> failed
complete / завершено / завершён -> completed
```

Prefix matching also recognizes rendered strings beginning with the current running/ready/completed/failed stems.

Unknown text becomes `unknown`.

Do not generate new decorated status strings when the canonical enum is sufficient.

## 9. Training configuration and validation exception codes

Training has typed code-bearing exceptions:

```text
TrainingConfigurationError
TrainingValidationError
```

The current create path uses stable codes including:

```text
invalid_hyperparameters
profile_required
dataset_required
model_required
```

The current start path can raise validation codes including:

```text
start_failed
run_not_found
already_running
not_ready
```

These are **operation precondition codes**, not `TrainingRunStatus` values.

## 10. Training start `ActionResult` codes

`start_full_finetune_run(...)` returns locale-neutral `ActionResult` objects for non-exception outcomes.

Current result codes include:

```text
backend_unavailable
start_failed
model_missing
resource_busy
completed
safe_stop
```

Important distinctions:

- `completed` as an action result indicates successful completion of that start/run request; the persisted run status is also `completed`, but the contracts are still distinct.
- `resource_busy` carries structured `blocker_kind` data when available.
- `safe_stop` can carry an `error_id`.
- many specific technical failure reasons are persisted/logged in `error_message` while the outward action code remains `start_failed`.

Current technical terminal/error messages include values such as:

```text
backend_unavailable
configuration_missing
model_missing
training_input_missing
dataset_not_approved
dataset_approval_hash_missing
training_input_snapshot_missing
profile_invalid
profile_changed_after_run_creation
dataset_changed_after_run_creation
dataset_changed_after_approval
training_input_invalid:<detail>
safe_stop[:<error_id>]
operation_without_terminal_status
```

Do not automatically treat every free-form/colon-suffixed technical message as a stable public action-code enum.

## 11. Model availability status contract

`ModelAvailabilityStatus` defines:

```text
available
unavailable
```

This is separate from both local inference/probe status and model-version lifecycle status.

## 12. Model-version status contract

`ModelVersionStatus` defines:

```text
unknown
draft
ready
archived
failed
```

A model version created from a completed Training run is currently registered as:

```text
ready
```

The model-version normalizer accepts compatibility aliases such as:

```text
available / stable -> ready
archive             -> archived
error / ошибка      -> failed
```

It can also inspect the head of a decorated string before:

```text
·
|
:
```

This parsing is compatibility behavior; new persistence should use the canonical token directly.

## 13. Evaluation run status contract

`EvaluationRunStatus` defines:

```text
unknown
created
running
partial
failed
completed
```

Current personality-portrait persistence records:

```text
completed
```

only when every case both receives a responding model result and yields a valid score. Otherwise the stored evaluation status is:

```text
partial
```

The evaluation normalizer accepts historical/rendered aliases such as `not started`, `in progress`, `completed with errors`, `passed`, and localized equivalents.

## 14. Evaluation result codes

`ExperimentRunResult` separates:

```text
ok
message
experiment_id
message_code
message_values
```

`message_code` is the stable machine outcome field. Current portrait/evaluation paths use codes including:

```text
local_model_unavailable
model_version_not_found
selected_weights_unavailable
model_unavailable
battery_load_failed
resource_busy
safe_stop
storage_read_only
portrait_completed
portrait_partial
```

A partial portrait is a persisted `partial` evaluation and returns:

```text
ok = false
message_code = portrait_partial
```

Do not reinterpret `partial` as a successful complete evaluation merely because a record was persisted.

## 15. Local-model operational status contract

`LocalModelStatus` defines:

```text
unchecked
checking
found
missing
check_failed
not_loaded
responding
inference_unavailable
generating
empty_response
resource_exhausted
generation_failed
unknown
```

These states cover probe/load/generation behavior; they are not model-version lifecycle states.

For example:

```text
found
```

means the local-model file probe found the expected shallow file categories. It does not mean a registered `ModelVersionStatus.READY` exists, nor does it prove model trust/integrity.

Legacy Russian/English rendered labels are normalized at this compatibility boundary.

## 16. Runtime-operation states

Runtime coordination defines active states:

```text
starting
running
cancelling
```

and terminal states:

```text
succeeded
failed
cancelled
abandoned
```

The current coordinator begins a new operation directly in:

```text
running
```

`starting` and `cancelling` remain recognized active states for persisted/runtime compatibility.

`finish(...)` accepts only one of the terminal states.

Startup orphan recovery can change an active operation whose recorded owner PID is no longer alive to:

```text
abandoned
```

`abandoned` means the coordination lease was recovered; it does not imply external effects were rolled back.

## 17. Runtime resource claims

A claim is identified semantically by:

```text
resource_kind
resource_id
access_mode
```

Valid access modes are:

```text
read
write
```

Normalization rules:

- `resource_kind` is stripped and case-folded;
- `resource_id` is stripped but preserves its remaining case/text;
- access mode is stripped/case-folded;
- empty kind/ID is invalid;
- duplicate claims for one `(kind, id)` collapse, preferring `write` when any duplicate requests write.

Conflict semantics:

```text
read  + read  -> allowed
read  + write -> blocked
write + read  -> blocked
write + write -> blocked
```

Deletion safety is stricter: any active claim for a protected resource can block destructive deletion regardless of read/write mode.

## 18. `ActionResult` contract

`ActionResult` is the general locale-neutral application outcome:

```text
ok: bool
code: str
values: Mapping[str, object]
```

Its code must match lower snake case:

```text
^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$
```

The `values` mapping is frozen for consumer-facing semantics and carries structured interpolation/provenance data.

Presentation code should select localized text from `code`; it must not parse structured meaning back out of rendered text.

## 19. `UserMessage` contract

`UserMessage` is a different locale-independent presentation reference:

```text
key: str
values: Mapping[str, object]
```

Unlike `ActionResult.code`, the message key is not constrained to lower snake case and normally uses catalog-style dotted keys, for example:

```text
error.training.full_finetune.safe_stop
```

A `UserMessage` key is not a domain status or action result.

## 20. Profile action codes

Current Profile application operations use `ActionResult` codes including:

```text
valid
created
updated
save_failed
title_required
description_required
communication_style_required
principles_required
constraints_required
```

These describe validation/save attempts; they do not replace `ProfileStatus`.

## 21. Dataset service-error and action codes

`DatasetServiceErrorCode` defines:

```text
file_not_found
only_jsonl
save_failed
not_found
```

Dataset action results currently include:

```text
approval_blocked
approved
not_found
version_compare_unavailable
```

Again, action code `approved` is not the persisted Dataset status. The canonical stored status after successful approval is:

```text
approved_for_training
```

## 22. Dataset diagnostic wire format

Structured Dataset diagnostics use the prefix:

```text
ptl:dataset-diagnostic:v1:
```

followed by compact JSON with:

```text
code
line
values
```

Diagnostic codes must match lower snake case. `line`, when present, is a non-negative integer.

Malformed, unprefixed, wrong-shape, or invalid-code payloads decode to no structured diagnostic rather than being silently reinterpreted.

## 23. Current Dataset diagnostic codes

The current Dataset validation/preview implementation emits these diagnostic codes:

```text
file_not_found
only_jsonl
invalid_json
empty_file
record_not_object
messages_not_list
message_not_object
invalid_role
content_empty
messages_missing_pair
instruction_empty
output_empty
input_not_string
prompt_empty
response_empty
unsupported_schema
unknown
```

`unknown` is used only as a defensive preview fallback when validation returned no diagnostic object.

Preview quality/status presentation strings such as:

```text
structure_ok
structure_error
```

are not additional `DatasetVersionStatus` enum members beyond the canonical Dataset status set above.

## 24. Automation recipe schema and identity

Automation recipe manifests use:

```text
ptl:automation-recipe:v1
```

Workspace discovery matches:

```text
*.ptl-recipe.json
```

Recipe IDs are manifest-defined and validated by:

```text
^[a-z0-9][a-z0-9._-]*$
```

They are case-folded during manifest load.

Recipe versions are non-empty manifest-provided strings. PTL does **not** generate a UUID-shaped recipe ID/version.

The current built-in recipe identity is:

```text
workspace_health
```

version:

```text
1.0.0
```

## 25. Automation discovery issues

Current filesystem recipe discovery exposes coarse machine issue codes:

```text
manifest_invalid
recipe_duplicate
```

The specific manifest parse/validation reason is carried in the issue `detail` text. Examples of detail-level validation failures include invalid schema, empty fields, invalid recipe/input identifiers, invalid arrays/resources, or invalid timeout values.

Do not promote arbitrary exception/detail wording into a new stable discovery-code enum unless the implementation explicitly does so.

## 26. Automation run result codes

`AutomationRunResult` contains:

```text
ok
code
recipe_id
operation_id
return_code
execution_mode
effect_scope
command
working_directory
stdout
stderr
stdout_truncated
stderr_truncated
values
```

Current service result codes include:

### Recipe/input preparation

```text
recipe_not_found
input_unknown
input_required
recipe_invalid
```

### Ad-hoc authorization/configuration

```text
host_effects_not_authorized
command_invalid
audit_unavailable
```

### Runtime/audit/launch

```text
audit_failed
operation_blocked
launch_failed
```

### Process terminal result

```text
cancelled
timeout
succeeded
failed
```

These are Automation service outcomes, not runtime-operation state values, although terminal process results are deliberately mapped onto corresponding runtime lease terminal states where appropriate.

## 27. Automation execution mode/effect scope

Current execution modes are:

```text
exec
shell
```

Current effect scope is:

```text
trusted_host
```

The effect-scope value is a trust/execution classification, not a runtime-operation state and not a sandbox guarantee.

## 28. Automation audit event types

Structured Automation audit rows use schema:

```text
ptl:automation-audit:v1
```

and event types:

```text
automation.run.started
automation.run.finished
automation.run.blocked
automation.run.launch_failed
```

Current phase values are:

```text
started
finished
blocked
launch_failed
```

The audit also records:

```text
resource_claim_semantics = runtime_coordination
```

The event ID is an `evt_...` identifier; operation/correlation identity is attached when available.

## 29. Application error/notice event types

`ApplicationErrorReporter` writes structured event families:

```text
application.error
application.notice
```

There is no separate `ptl:error:v1` schema marker in the current reporter payload. The payload is identified by its event type and fields.

Current captured-error fields include:

```text
error_id
correlation_id
component
operation_id
exception_type
exception_message
traceback
context
fingerprint
```

Notice payloads contain their corresponding message/level/context/fingerprint fields.

Event persistence is best-effort and duplicate-window throttled; event absence must not be interpreted as proof that an incident never occurred.

## 30. Error/correlation identifiers are not authorization credentials

Current reporter identifiers use:

```text
error      err_<12 hex>
correlation corr_<12 hex>
```

They exist for diagnosis/correlation. Possessing one does not authenticate or authorize a caller.

The reporter's structured-context redaction currently checks top-level context key names for substrings:

```text
password
secret
token
api_key
key_material
```

That is a privacy helper, not an identifier/security scheme and not a general recursive secret scanner.

## 31. Generated identifier formats

Current feature-generated identifier formats are not globally uniform.

| Entity | Current generator/shape |
|---|---|
| Profile | `prf_<8 hex>` |
| Dataset | `ds_<8 hex>` |
| Training run | `trn_<8 hex>` |
| Model version | `mdl_<8 hex>` |
| Evaluation run | `evr_<8 hex>` |
| Runtime operation | `op_<12 hex>` |
| Runtime correlation | `corr_<12 hex>` |
| Application error | `err_<12 hex>` |
| Structured event | `evt_<12 hex>` |
| Shared helper | `<prefix>_<12 hex>` |
| Automation recipe | manifest-defined validated ID |
| Automation recipe version | manifest-defined non-empty version string |

Do **not** write validators that assume all PTL IDs have the same prefix length or hex width.

## 32. Shared ID helper

`shared.ids.new_id(prefix)` returns:

```text
<prefix>_<12 hex>
```

using the first 12 hex characters of a UUID4 value.

This helper explains several 12-hex identifiers, but some feature services currently generate their own 8-hex identifiers directly.

The existence of the shared helper is therefore not a promise that all older/current feature IDs have already migrated to it.

## 33. Semantic lineage identity is source identity first

Agents semantic lineage projects persisted Dataset, Training-run, model-version, and evaluation records. Their stable persisted IDs outrank mutable display titles/aliases.

Local/custom Agents organization has additional local-state identity, but this reference does not invent one universal textual format for those local IDs where the implementation does not expose a single public generated-ID contract.

When an Agents node represents a real persisted resource, downstream safety/navigation should use the linked stable resource identity rather than parsing the visible graph label.

## 34. Titles and labels are not IDs

Examples that are **not** safe replacements for stable identifiers include:

```text
Profile title
Dataset filename/title
Training title
model-version display title
Agents graph label
Automation recipe title
localized status label
```

Titles can change, collide, be translated, or represent compatibility data.

Use the entity's stable ID or explicit resource identity whenever the workflow provides one.

## 35. Unknown-state semantics

Several domain enums deliberately contain:

```text
unknown
```

This normally means the current normalization layer could not map the stored/input value to a known semantic state.

`unknown` is not equivalent to:

```text
failed
missing
archived
```

Consumers should display/diagnose unknown state rather than silently coercing it to whichever state is most convenient.

## 36. Forward/backward compatibility rule

Compatibility normalizers exist because older persisted/rendered state may use aliases.

The safe rule is:

```text
read old aliases -> normalize to canonical semantic code
write new state  -> persist canonical semantic code
render UI        -> localize canonical semantic code
```

Do not add new localized aliases to persistence merely because a normalizer can read them.

## 37. Result-code stability vs technical detail

Stable result codes are deliberately coarser than some diagnostic detail.

Examples:

```text
Training ActionResult: start_failed
Training persisted error: profile_changed_after_run_creation

Automation discovery code: manifest_invalid
Automation issue detail: specific ValueError/JSON/read reason

Application error event: application.error
Application payload: exception type/message/traceback/context/fingerprint
```

This separation lets UI/automation branch on stable outcomes without pretending every internal exception string is a versioned public API.

## 38. Developer rules

When adding or changing a machine-semantic surface:

1. decide whether the string is a status, result code, diagnostic, event type, schema marker, message key, or identifier;
2. do not reuse rendered/localized text as persistence identity;
3. prefer canonical enums/codes at application/domain boundaries;
4. preserve compatibility aliases only at explicit normalization boundaries;
5. keep structured values separate from rendered error text;
6. document newly generated ID formats instead of assuming the shared helper is universal;
7. never infer authorization from an operation/correlation/error/event ID;
8. update this reference whenever a stable code/status/event/schema/ID contract changes;
9. update tests that prove status normalization and code-to-message presentation separately;
10. keep `unknown` visible rather than silently mapping novel values to a misleading known state.

## 39. Audit checklist

For a new state/result/identifier, verify:

```text
What layer owns it?
Is it persisted or transient?
Is it canonical or only a compatibility alias?
Can it be localized?
What produces it?
What consumes it?
Does it have structured values/details?
Is unknown input preserved visibly?
Does any UI code compare rendered strings instead of semantic values?
Does the value appear in logs/event payloads?
Does a migration/normalizer need to read an older spelling?
Is the ID generated or supplied by a manifest/user/external source?
Is its exact prefix/width actually guaranteed by code?
```

## Related documentation

- [v1.0 Product Contract](v1-product-contract.md)
- [Evaluation contract](evaluation-contract.md)
- [Workspace layout reference](workspace-layout.md)
- [Keyboard & mouse bindings reference](keyboard-mouse-bindings.md)
- [Persistence architecture](../architecture/persistence.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
- [Agents lineage architecture](../architecture/agents-lineage.md)
- [Automation architecture](../architecture/automation.md)
- [Training pipeline specification](../training_pipeline.md)
- [Datasets](../user-guide/datasets.md)
- [Training](../user-guide/training.md)
- [Tests and Analysis](../user-guide/tests-and-analysis.md)
- [Automation](../user-guide/automation.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md)