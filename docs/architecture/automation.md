# Automation architecture

## Purpose

Automation is Persona Training Lab's trusted-host execution subsystem. It turns a recipe or explicit operator command into a bounded process execution that participates in PTL runtime coordination and structured audit infrastructure.

Its architectural requirement is:

> **Execution must be explicit, attributable, bounded, cancellable, and coordinated — without pretending that host commands are sandboxed.**

This document defines the v1.0 implementation contract.

## 1. Composition

Production composition constructs Automation with:

```text
FilesystemAutomationRecipeProvider(<workspace>/automation/recipes)
        │
        ▼
AutomationService
        ├─ RuntimeOperationCoordinator
        ├─ workspace_root
        ├─ run_automation_process
        └─ AutomationAuditTrail(event_log)
        │
        ▼
AutomationViewModel
        │
        ▼
AutomationScreen
```

The provider owns recipe discovery/import. The service owns validation/rendering/runtime coordination/execution result semantics. The process runner owns host-process containment/output. The audit trail owns durable structured execution metadata. The UI owns operator review/input and background-worker lifecycle.

## 2. Core schemas and identifiers

Recipe manifest schema:

```text
ptl:automation-recipe:v1
```

Audit payload schema:

```text
ptl:automation-audit:v1
```

Built-in workspace diagnostic output schema:

```text
ptl:automation-output:workspace-health:v1
```

Current execution effect scope:

```text
trusted_host
```

The effect-scope value is intentionally explicit in both execution/result/audit structures.

## 3. Recipe domain object

`AutomationRecipe` carries:

```text
recipe_id
version
title
description
command
tags
inputs
outputs
resource_claims
source
source_path
working_directory
timeout_seconds
```

The command is a tuple of argv tokens. Recipe execution is always constructed as `mode="exec"`.

Recipes do not silently switch to shell mode based on punctuation/content.

## 4. Recipe registry

`FilesystemAutomationRecipeProvider` owns:

```text
<workspace>/automation/recipes/
```

It recursively scans:

```text
*.ptl-recipe.json
```

and merges valid workspace recipes with built-in recipes.

The built-in registry currently contains:

```text
workspace_health
```

### Discovery isolation

One invalid manifest produces an `AutomationDiscoveryIssue` but does not invalidate unrelated recipes.

Supported discovery issue codes include:

```text
manifest_invalid
recipe_duplicate
```

The provider caches only the latest issue tuple; recipe data itself is reloaded by discovery calls.

## 5. Manifest validation

The provider validates at least these contracts:

- root JSON must be an object;
- schema must equal `ptl:automation-recipe:v1`;
- ID must match `[a-z0-9][a-z0-9._-]*` after case-folding;
- version is required text;
- command is a non-empty string array;
- tags are string-array values and de-duplicated case-insensitively;
- inputs are objects with valid identifier names;
- `python` and `workspace` are reserved input names;
- duplicate input names are rejected;
- outputs are objects with names;
- resource access is only `read` or `write`;
- timeout is a non-negative integer.

Invalid manifests are not converted into partially trusted recipe objects.

## 6. Import semantics

`import_recipe(path)` performs:

```text
resolve source
    ↓
validate/load source manifest
    ↓
copy to registry/<recipe_id>.ptl-recipe.json
    ↓
reload copied manifest
    ↓
refresh discovery issues
```

The imported recipe's new `source_path` is the workspace registry copy.

### Important boundary

Only the manifest is copied. External companion scripts/assets are not automatically transitive imports.

This matters because relative `working_directory` resolution uses the manifest source directory.

## 7. Recipe lookup and review boundary

The UI keeps a presentation snapshot of discovered recipe metadata.

When the operator clicks Run, the worker passes only `recipe_id` plus input values. `AutomationService.run_recipe()` then calls `get_recipe(recipe_id)`, which asks the provider to list/load recipes again.

Therefore the execution-side recipe object can be newer than the recipe view last rendered by the UI.

### v1 invariant / limitation

There is no persisted recipe-content SHA-256 or signed manifest revision that binds the displayed recipe snapshot to the later Run request.

This is acceptable only inside the declared `trusted_host` local trust model. Workspace recipe files must be treated as executable trusted inputs, and external mutation between review and execution is outside the v1 consent-pinning contract.

## 8. Recipe input resolution

`run_recipe()` builds a declared-input map and rejects supplied names outside it.

Resolution order:

```text
declared defaults
    ↓
operator supplied values
```

Required inputs must be non-empty after resolution.

Substitution map then adds:

```text
python    = sys.executable
workspace = resolved workspace root
```

Recipe inputs cannot shadow these reserved substitutions.

## 9. Token rendering

Command tokens, resource IDs, and recipe working-directory strings are rendered through Python `format_map` semantics.

Unknown placeholders raise a controlled `recipe_invalid` result.

The rendering step creates one immutable `AutomationExecution` snapshot before the runtime lease/process launch path.

## 10. Recipe working-directory resolution

Resolution is:

```text
no working_directory
    -> workspace root

absolute working_directory
    -> absolute resolved path

relative working_directory + source_path
    -> source manifest parent / relative path

relative working_directory without source_path
    -> workspace root / relative path
```

Built-in recipes have no workspace manifest source path and therefore naturally use the workspace root fallback.

## 11. Recipe environment

Recipe execution calls `_environment_snapshot()` with inheritance enabled and no recipe-specific overrides.

Result:

```text
child env = current PTL process environment
child env[PTL_WORKSPACE] = actual resolved workspace
```

`PTL_WORKSPACE` is assigned after any general override step and therefore remains authoritative.

## 12. Ad-hoc command request

`AutomationCommandRequest` carries:

```text
command_id
mode
argv
shell_command
working_directory
environment
inherit_environment
resource_claims
timeout_seconds
output_limit_bytes
host_effects_authorized
```

The UI first parses an `AutomationCommandDraft` into this immutable request.

## 13. Ad-hoc draft validation

`build_automation_command_request()` validates the operator form before service execution.

### Exec mode

The command text must decode to a non-empty JSON array containing only strings, with a non-empty executable in item 0.

### Shell mode

The command string must be non-empty.

### Environment

Environment text must be a JSON object with string keys and string values.

### Resource claims

Resource text must be a JSON list of objects with non-empty `kind`/`id` and access in `read|write`.

### Timeout

Timeout must parse as a non-negative floating-point value.

### Output limit

Output limit must parse as a non-negative integer and must not exceed the hard maximum.

### Host effects

The draft is rejected unless `host_effects_authorized` is true.

The service independently checks that authorization again.

## 14. Explicit execution shape

`AutomationExecution` enforces a mutually exclusive command representation.

For `exec`:

```text
argv != empty
shell_command == empty
```

For `shell`:

```text
shell_command != empty
argv == empty
```

Ambiguous command shapes raise `ValueError` before process launch.

This prevents a caller from providing both argv and hidden shell text and relying on implementation precedence.

## 15. Trusted-host effect scope

`AutomationExecution.effect_scope` currently accepts only:

```text
trusted_host
```

Any other value is rejected.

This makes the absence of a sandbox explicit in the execution object instead of leaving it as undocumented behavior.

## 16. Ad-hoc working directory

`_command_working_directory()` resolves:

```text
empty    -> workspace root
relative -> workspace root / relative
absolute -> absolute path
```

The result is normalized with `resolve()` before execution/audit.

## 17. Ad-hoc environment semantics

`_environment_snapshot(overrides, inherit=...)` behaves as:

```text
inherit = true
    base = os.environ

inherit = false
    base = {}

base.update(operator overrides)
base[PTL_WORKSPACE] = actual workspace root
```

An operator-provided `PTL_WORKSPACE` value therefore cannot redirect the mandatory marker.

## 18. Ad-hoc default resource claim

If the operator supplies no resource claims, `run_command()` inserts:

```text
ResourceClaim(
    kind="workspace",
    id=<resolved workspace>,
    access="write"
)
```

This is intentionally conservative.

Recipe execution does **not** synthesize the same fallback; recipe authors are expected to declare their coordination contract explicitly. The built-in `workspace_health` recipe declares a workspace read claim.

## 19. Runtime-operation lease

Both recipes and ad-hoc commands enter the shared runtime coordinator before process launch.

The service calls:

```text
operation_coordinator.begin(
    operation_kind,
    subject_kind,
    subject_id,
    claims,
)
```

Operation kinds are currently:

```text
automation_recipe
automation_command
```

If claim acquisition raises `OperationConflictError`, the child process is not launched and the result becomes:

```text
operation_blocked
```

when audit recording itself succeeds.

## 20. Runtime claims are coordination metadata

Automation resource claims share the same read/write conflict model used elsewhere in PTL.

They protect cooperative PTL workflows from overlapping logical operations.

They do not:

- chroot a process;
- block undeclared filesystem paths;
- block network access;
- inspect syscalls;
- prove recipe honesty.

The audit therefore records:

```text
resource_claim_semantics = runtime_coordination
```

rather than implying OS authorization semantics.

## 21. Audit composition

Production `build_container()` constructs:

```text
AutomationAuditTrail(event_log_repo)
```

and supplies it to `AutomationService`.

Therefore normal v1 production recipe/ad-hoc execution has structured audit support.

## 22. Ad-hoc audit fail-closed rule

`run_command()` contains an explicit precondition:

```text
if audit_trail is None:
    return audit_unavailable
```

This check happens before lease acquisition/process launch.

After lease acquisition, if `record_started()` fails, the lease is failed and the command is not launched.

This gives ad-hoc host execution a strong no-audit/no-launch contract.

Recipe execution does not have a separate `audit_unavailable` preflight branch; it relies on production composition supplying the audit trail.

## 23. Audit payload

`AutomationAuditTrail._execution_payload()` records:

```text
mode
effect_scope
resource_claim_semantics
working_directory
command_sha256
command_parts
environment_keys
timeout_seconds
output_limit_bytes
resource_claims
```

The command hash is SHA-256 over a compact JSON encoding of the execution command snapshot.

Terminal events additionally record fields such as:

```text
state
return_code
cancelled
timed_out
stdout_truncated
stderr_truncated
```

## 24. Audit privacy design

The audit intentionally does not store:

- plaintext command tokens/string;
- environment values;
- stdout bytes/text;
- stderr bytes/text.

It stores environment keys and command hash/count instead.

This reduces accidental secret persistence but does not make the payload non-sensitive. Working directories, resource IDs, subject IDs, environment names, errors, and timing metadata can still expose operational context.

## 25. Audit events

Current event types are:

```text
automation.run.started
automation.run.finished
automation.run.blocked
automation.run.launch_failed
```

Records carry event ID, entity kind/ID, UTC timestamp, correlation/causation IDs where available, and JSON payload.

## 26. Audit failure semantics

Audit is part of the result contract rather than best-effort decoration in the ad-hoc path.

Possible failures include:

```text
audit_unavailable
audit_failed
```

If blocked-operation audit recording fails, the result is `audit_failed` rather than silently returning only `operation_blocked`.

If finish-audit persistence fails after the child has completed, the lease is marked failed and the user receives `audit_failed` while retaining captured child output/return-code context in the immediate result.

## 27. Process runner output bounds

`AutomationExecution` defines:

```text
DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES = 1 MiB
MAX_AUTOMATION_OUTPUT_LIMIT_BYTES     = 64 MiB
```

The limit applies independently to stdout and stderr capture.

Two daemon drain threads continuously consume the pipes in 64 KiB chunks.

`_BoundedCapture` retains at most the configured number of bytes per stream while continuing to drain excess data and setting a truncation flag.

This design prevents a verbose child process from deadlocking because PTL stopped reading once the display limit was reached.

## 28. UTF-8 decoding

Captured bytes are decoded as UTF-8 with replacement semantics:

```text
errors="replace"
```

Invalid byte sequences therefore do not crash result rendering.

The displayed text can contain replacement characters when child output is not valid UTF-8.

## 29. Runner polling

The process runner polls process/cancel/timeout state approximately every:

```text
0.05 seconds
```

This is a responsiveness implementation detail, not a real-time scheduling guarantee.

## 30. Timeout semantics

A positive execution timeout measures elapsed monotonic time from process start.

When elapsed time reaches the configured timeout:

```text
timed_out = True
terminate_tree()
```

The process is then waited/reaped and the service maps the result to:

```text
code  = timeout
state = failed
```

## 31. Cancellation semantics

The UI worker owns a `threading.Event`.

Cancel sets the event. The process runner polls `cancel_requested()` and calls `terminate_tree()` when it becomes true.

The service maps the result to:

```text
code  = cancelled
state = cancelled
```

Cancellation wins over timeout in the service result mapping when the process result marks `cancelled`.

## 32. POSIX containment

POSIX execution uses:

```text
subprocess.Popen(..., start_new_session=True)
```

The process PID becomes the process-group/session leader used for containment.

Termination sequence:

```text
killpg(SIGTERM)
wait up to 2 seconds
killpg(SIGKILL) if group still exists
```

Finalization calls the same group-termination path, including after the direct child exits normally. This prevents a successful one-shot parent from leaving ordinary background descendants alive under the Automation run.

## 33. Windows containment

Windows execution creates a Job Object using kill-on-close semantics.

PTL starts an internal helper process, assigns it to the Job Object, then sends the requested execution payload over stdin.

The Job Object owns descendant containment.

Cancellation/exception handling can terminate the job, and finalization closes it.

The helper boundary avoids depending on ad-hoc Windows subprocess flag combinations for tree ownership.

## 34. Windows launch payload

The helper receives JSON containing:

```text
mode
argv
shell_command
cwd
env
```

The payload is an internal execution transport, not the durable audit representation.

Environment values can therefore cross this private process boundary even though the structured event log stores only their keys.

## 35. Process stdin

Normal POSIX child execution uses:

```text
stdin = DEVNULL
```

Automation v1 is therefore non-interactive at the process-stdin level.

Commands requiring an interactive terminal/prompt are outside the one-shot execution UX contract unless they can operate non-interactively.

## 36. Result mapping

`AutomationRunResult` exposes:

```text
ok
code
recipe_id / command_id
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

Important codes:

```text
succeeded
failed
cancelled
timeout
launch_failed
operation_blocked
recipe_not_found
recipe_invalid
input_required
input_unknown
command_invalid
host_effects_not_authorized
audit_unavailable
audit_failed
```

## 37. UI thread ownership

`AutomationScreen` executes work through `_AutomationRunWorker` moved to a `QThread`.

At start:

```text
running = true
Run recipe disabled
Run command disabled
Cancel enabled
```

Worker completion/failure quits the thread and schedules worker/thread deletion.

The UI displays immediate result output but does not turn stdout/stderr into a durable Automation run-history table.

## 38. Workspace-leave guard

`request_leave_workspace()` returns false while `_running` is true and displays the Automation leave-blocked status.

This is a UX safety guard against abandoning the visible run context during ordinary navigation.

Application close is handled through the broader shell/background shutdown ownership path rather than by pretending the screen itself can synchronously stop every child in a close event.

## 39. Background shutdown hook

`shutdown_background_work()`:

1. requests worker cancellation;
2. asks the QThread event loop to quit;
3. optionally waits for a caller-supplied timeout;
4. reports whether the thread stopped.

The process runner remains responsible for terminating/reaping the contained child tree after cancellation is observed.

## 40. Built-in workspace-health contract

The built-in recipe uses:

```text
{python} -m persona_training_lab.automation_recipes.workspace_health
```

and declares:

```text
resource: workspace/<workspace>/read
```

It is intentionally a low-risk first Automation workflow and is covered by headless tests.

## 41. Security boundary

The following statements are v1 architectural truths:

1. `trusted_host` commands are trusted code.
2. Host-effect authorization is explicit for ad-hoc commands.
3. Recipe Run itself is the operator authorization gesture for trusted recipes.
4. Runtime claims coordinate PTL operations but do not constrain OS side effects.
5. Audit minimizes plaintext command/environment persistence but does not hide all operational metadata.
6. Recipe manifests are not signed/content-addressed execution capsules.
7. Absolute working directories can leave the PTL workspace.
8. Inherited environment can expose secrets to trusted child processes.
9. Shell mode intentionally delegates parsing/expansion to the host shell.
10. stdout/stderr can contain secrets and are visible in the UI even though they are not copied into the structured Automation audit payload.

## 42. Recipe mutability and reproducibility boundary

Recipe `id`/`version` are metadata, not a persisted cryptographic manifest identity.

A workspace file can be edited without changing its version string.

Because `run_recipe()` reloads by ID, exact reproduction requires the operator to separately preserve the manifest bytes and referenced tool/data versions when that level of provenance matters.

Future hardening could add a manifest content fingerprint/review token, but v1 documentation must not claim this already exists.

## 43. External dependency boundary

An Automation recipe can invoke any executable/path visible to the OS account.

PTL does not currently persist content hashes for:

- external executables;
- scripts referenced by command tokens;
- command interpreters other than the current `{python}` path;
- arbitrary files consumed by those commands.

Therefore an audit `command_sha256` identifies the command snapshot, not the transitive executable/data contents used by that command.

## 44. Shell boundary

`AutomationExecution(mode="shell")` passes a command string using host shell semantics.

The shell can perform expansions/redirections/subcommands that are not represented as separate argv items in the command hash.

The hash still covers the exact shell command string snapshot PTL passed to the launcher.

## 45. Failure containment

Expected operational failures return structured results rather than crashing the UI.

Examples:

- bad recipe input;
- invalid command draft;
- runtime claim conflict;
- process launch error;
- timeout;
- cancellation;
- non-zero exit;
- audit persistence failure.

Unexpected worker exceptions are caught by `_AutomationRunWorker` and surfaced to the UI as an internal-error state.

## 46. Test evidence

The current test suite directly exercises contracts including:

- valid recipes remain discoverable beside invalid manifests;
- malformed outputs/resource fields are rejected;
- declared command/cwd/workspace/timeout/claims reach the execution snapshot;
- ad-hoc host-effect authorization is mandatory;
- ad-hoc execution fails closed without audit;
- audit-start persistence failure prevents launch;
- plaintext command/environment values are absent from structured audit payloads;
- environment keys are retained;
- default ad-hoc workspace write claim;
- cancelled/timed-out/blocked terminal semantics;
- bounded stdout/stderr capture;
- explicit exec vs shell shape validation;
- timeout terminates descendants;
- cancellation terminates descendants;
- successful POSIX execution does not leave a background descendant;
- built-in workspace health runs headlessly.

## 47. What the tests do not prove

The pre-v1 suite does not claim exhaustive proof of:

- every possible process-tree escape technique;
- every Windows shell/tool combination;
- hostile kernel/container boundary conditions;
- maximum concurrent Automation workloads;
- arbitrary OS permission/ACL layouts;
- malicious code containment;
- network isolation;
- every external executable behavior;
- distributed runtime locking.

Those remain explicit operating/stress boundaries.

## 48. v1.0 invariants

A v1.0 Automation implementation must preserve these invariants unless the public contract is deliberately revised:

1. ad-hoc host effects require explicit authorization;
2. `exec` and `shell` shapes remain unambiguous;
3. no-audit ad-hoc execution fails closed;
4. structured audit does not persist inherited environment values or plaintext command text as the normal command record;
5. output capture remains bounded while pipes continue to drain;
6. timeout/cancel terminate the owned process tree rather than only the immediate child;
7. runtime claims are acquired before launch;
8. conflicts prevent launch;
9. `PTL_WORKSPACE` reflects the actual resolved workspace;
10. Automation remains documented as trusted-host execution rather than a sandbox.

## Related documentation

- [Automation user guide](../user-guide/automation.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
