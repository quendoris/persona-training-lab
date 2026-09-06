# Troubleshooting & Diagnostic Evidence

This guide describes how to diagnose Persona Training Lab v1.0 without destroying the evidence needed to understand the failure.

It is an operator guide, not a list of speculative fixes. Every procedure below is derived from current PTL behavior: workspace ownership, structured error reporting, Activity/Issues routing, runtime-operation leases, Training/Tests/Automation contracts, background-worker ownership, telemetry, and the release-audit tooling.

The central rule is:

> **Preserve state first, identify the failing boundary second, and change or delete state only after you know which layer is actually wrong.**

For storage ownership and backup semantics, read [Workspace & Storage](workspace-and-storage.md). For local model diagnostics, read [Local Models: Setup, Readiness & Health Checks](local-models.md). For executable-host behavior, read [Automation](../user-guide/automation.md).

## 1. Start by classifying the failure

PTL failures usually belong to one of these layers:

| Layer | Typical symptom | First evidence source |
|---|---|---|
| Source/development checkout | release gate refuses to start, import/build/test failure | terminal + release-audit logs |
| Application startup | window never appears or initialization fails | terminal critical output + application log |
| UI event handling | one action fails but PTL remains open | Issues + application log |
| Workspace/persistence | state missing, wrong workspace, database/storage error | actual workspace root + Issues + log |
| Runtime coordination | Launch/Delete/Automation action is blocked | Activity/Issues + operation/resource identity |
| Local model | model missing, backend unavailable, generation failure | Training local-model status + diagnostic code |
| Dataset/Profile/Training input | run cannot be created/launched or fails integrity checks | Training status/logs + Dataset/Profile state |
| Training backend | run reaches execution then fails | Training logs + application log + artifact directory |
| Tests/evaluation | portrait is partial or exact version cannot be evaluated | Tests case review + persisted run status |
| Analysis | Delta unavailable or unexpected | protocol IDs + exact selected model-version IDs |
| Agents lineage | stale graph, blocked delete/redo, local history issue | Agents detail + Activity/Issues + workspace state |
| Automation | recipe/command blocked, cancelled, timed out, failed | Automation result + operation ID + audit metadata |
| Telemetry | GPU/process metrics absent or refresh failed | Telemetry semantic status |
| Shutdown/background ownership | application refuses immediate close | current workspace/background-worker state |

Do not begin with a whole-workspace reset. Many PTL failures are intentionally represented as controlled status, integrity rejection, or runtime blocker rather than corruption.

## 2. Record the identity of the environment before changing it

For a reproducible report, collect at least:

```text
PTL version / Git commit
Git branch when running from source
OS
Python version
actual PTL workspace root
relevant model/Dataset/artifact path
semantic status/result code
operation ID when present
correlation ID when present
```

For a source checkout, useful commands are:

```bash
git rev-parse HEAD
git branch --show-current
git status --short
python --version
```

When using `uv`, also record that the application/test was launched through the expected environment rather than another Python installation.

Do not infer the active PTL workspace from the repository directory or terminal current working directory. PTL uses a platform data root unless an explicit `workspace_dir` is supplied.

## 3. Know the main evidence surfaces

PTL deliberately keeps several diagnostic surfaces because they answer different questions.

### 3.1 Activity

The Activity panel combines:

- currently active persisted runtime operations;
- recent runtime-operation history;
- recent structured application events.

Active items are separated from recent history. The panel refreshes while visible and can navigate to the related PTL workspace.

Activity is useful for answering:

- What operation is running now?
- Did the operation finish, fail, cancel, or become abandoned?
- Which PTL workspace owns the operation?
- What correlation ID is attached to this item?

Automation audit events beginning with `automation.run.` are not duplicated as separate Activity event rows when the corresponding runtime operation already represents the run.

### 3.2 Issues

The Issues panel presents recent structured application warnings/errors/critical notices.

It includes `application.error` events and warning-or-higher `application.notice` events. Informational notices are not treated as Issues.

Rows navigate toward a related workspace using the event component/entity metadata when PTL can determine one.

A clean Issues panel means no qualifying recent issue was returned by the current event source. It is not proof that every external dependency, model, Dataset source, or host command is healthy.

### 3.3 Training logs

Training has its own persisted run log stream in SQLite.

Use it for the sequence specific to one Training run: input IDs/fingerprints, backend start/result, sample/step information, artifact path, and model-version publication events where present.

Training logs are different from the general rotating application log.

### 3.4 Rotating application log

Production composition configures:

```text
<workspace>/logs/persona_training_lab.log
```

The current handler rotates at approximately 5 MB and retains five backups.

The log receives `INFO` and above from the managed root file handler. The managed console handler is intentionally `CRITICAL` only, so a recoverable warning/error may be visible in PTL/its file log without being printed to the terminal.

Failure to create the file handler does not prevent application startup. Therefore **absence of the log file is not by itself proof that PTL never started**.

### 3.5 SQLite event log

Structured application incidents and notices can also be persisted in the shared `event_log` table.

This is the source used by Operations Center/Issues. It is not a complete plaintext copy of every log line.

### 3.6 Release-audit artifacts

The development release gate writes isolated reports under the source checkout by default:

```text
artifacts/release-audit/<timestamp>-<commit>-seed-<seed>/
```

A successful gate directory contains per-step logs, metadata, and `summary.json` / `summary.md`.

This directory belongs to the development/release-audit workflow; do not confuse it with the runtime Training artifact directory under the PTL workspace.

## 4. Correlation IDs and error IDs

Unhandled/reported exceptions receive identifiers of the form:

```text
err_<12 hexadecimal characters>
corr_<12 hexadecimal characters>
```

The error ID identifies a reported incident. The correlation ID is intended to connect related UI/event/log evidence.

When an operation already has a correlation ID, service error reporting can preserve/use that identity rather than inventing unrelated context.

When reporting a problem, include the correlation ID if it is visible. It is usually more useful than copying only the localized sentence shown in the UI.

## 5. Error reporting is deliberately best-effort

`ApplicationErrorReporter` is designed not to become a second application failure.

For a captured exception it attempts to:

1. create error/correlation identities;
2. build structured exception/context data;
3. write the durable application log;
4. append a structured `application.error` event when duplicate throttling permits it;
5. return a safe user-facing message reference.

If event-log persistence itself fails, the reporter swallows that reporting-storage failure rather than re-raising it into the original workflow.

This means a missing Issues row does not prove an exception did not happen. Check the rotating application log when an expected structured event is absent.

## 6. Duplicate error throttling

Repeated identical incidents are fingerprinted by component + exception type + exception text.

The default duplicate persistence window is five seconds. Repeated incidents inside that window can still be written to the normal log path while only one structured event is appended to SQLite.

This exists to prevent a fast repeating UI/runtime fault from flooding persistent event storage.

Do not interpret "only one Issues row" as proof that an error happened only once.

## 7. Sensitive diagnostic context

Application error context automatically redacts values when the context key contains terms such as:

```text
password
secret
token
api_key
key_material
```

That is a defensive filter, not a complete data-loss-prevention system.

Other paths, IDs, model names, Dataset names, exception messages, command metadata, and arbitrary values can still be sensitive.

Review logs, databases, Automation output, model responses, Dataset samples, and complete environment dumps before sharing them.

## 8. Python and Qt exception boundaries

Production startup installs several containment boundaries.

### Main Python thread

Uncaught non-`KeyboardInterrupt` main-thread exceptions are reported through the application error reporter with component:

```text
python.main_thread
```

### Worker threads

Uncaught worker-thread exceptions are reported with component:

```text
python.worker_thread
```

`SystemExit` from the thread exception hook is ignored as an incident.

### Qt event dispatch

`SafeApplication.notify(...)` catches exceptions escaping Qt event handlers, reports them as:

```text
qt.event_dispatch
```

and returns `False` for that event rather than deliberately re-raising it through the Qt event loop.

The application stores the most recent reported UI error ID/message as application properties for the shell/error surface.

### Qt diagnostic messages

Qt warnings/info/critical/fatal messages are routed into the structured reporter through component:

```text
qt.message
```

Qt debug messages are ignored by this boundary in normal runtime.

A Qt warning therefore may appear in PTL diagnostic persistence/logging even when the terminal is quiet.

## 9. Application will not launch

First separate dependency/startup failure from a workspace/data failure.

From a source checkout, use the documented entry point:

```bash
uv run --locked python -m persona_training_lab.bootstrap.app
```

Check:

1. Python is 3.12 or newer.
2. `uv sync --locked` completed for the desktop core.
3. the desktop/Qt environment can create a PySide6 application;
4. the resolved workspace location is writable enough for required startup state;
5. the terminal contains a `CRITICAL` startup failure;
6. `<workspace>/logs/persona_training_lab.log` exists and contains a related exception when file logging was available.

Do not install the optional inference/training stack merely because the desktop shell does not launch. Torch/Transformers are not required for core startup.

## 10. PTL opens the wrong or apparently empty workspace

The usual first question is not "where did my data go?" but "which workspace root is this process using?"

Default roots are:

| Platform | Default root |
|---|---|
| Linux / other Unix | `${XDG_DATA_HOME:-~/.local/share}/persona-training-lab` |
| Windows | `%LOCALAPPDATA%\Persona Training Lab` with documented fallbacks |
| macOS | `~/Library/Application Support/Persona Training Lab` |

Changing the repository directory or terminal CWD does not select another workspace.

Check environment differences between launches, especially:

```text
XDG_DATA_HOME
LOCALAPPDATA
APPDATA
```

when relevant.

Before moving/deleting anything, compare the actual roots and preserve both if there is uncertainty.

## 11. `app.db` opens but files or lineage state are missing

SQLite is not the complete PTL workspace.

Important state also includes:

```text
agents_lineage_state.json
artifacts/
automation/recipes/
models/     # when workspace-local
```

and some dependencies can be external:

```text
Dataset JSONL source
explicit base-model directories
Automation scripts/binaries/data
```

A restore containing only `app.db` can therefore preserve metadata while losing Agents local history/layout or referenced generated/external files.

See [Workspace & Storage](workspace-and-storage.md) before attempting repair.

## 12. Application log is missing

The logging setup intentionally treats file-log creation as non-fatal.

If `<workspace>/logs/persona_training_lab.log` is absent:

1. verify the actual workspace root;
2. verify whether the `logs/` directory can be created/written by the PTL OS account;
3. do not conclude that PTL never initialized merely from the missing file;
4. inspect visible Issues/status and terminal `CRITICAL` output;
5. fix filesystem permissions/space outside PTL before expecting durable logs.

Do not redirect runtime logging into the source package tree as a workaround.

## 13. A UI action failed but the application stayed open

This is a supported failure-containment shape.

Check, in order:

1. Issues;
2. Activity;
3. the related workspace's status/log surface;
4. application log;
5. correlation/error ID.

A contained Qt event-handler exception can cause one action/event to fail while allowing the application to continue processing later events.

Do not assume the entire workspace state is corrupted because one event was contained.

If the action was destructive or mutating, verify the authoritative persisted state before repeating it.

## 14. Runtime operation states

The persistent runtime coordinator recognizes active states:

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

The current coordinator normally creates a new lease directly in `running` state. Other persisted/runtime surfaces can still understand the wider active-state set.

Activity severity maps failed/abandoned to error, cancelling/cancelled to warning, active states to active, and normal terminal completion to success.

## 15. Runtime resource conflict

PTL resources are coordinated by `(resource_kind, resource_id, access_mode)` claims.

Current semantics are:

```text
read + read   -> allowed
read + write  -> conflict
write + read  -> conflict
write + write -> conflict
```

When an action is blocked:

1. inspect Activity for the active operation;
2. record its operation kind/subject/operation ID;
3. inspect the related feature's status;
4. allow the owning operation to reach a terminal state or use that feature's supported cancellation path;
5. retry only after the blocker is gone.

Do not manually delete `runtime_operations` or resource rows to force the action through.

The runtime claim layer is part of PTL's integrity contract, not a nuisance lock file.

## 16. Stale operation after a crash

At application composition/startup, PTL calls orphan recovery for persisted active runtime operations.

An operation is considered orphaned when it has a positive owner PID and that PID is no longer alive according to the host process check.

Recovered operations are moved to the terminal `abandoned` state. Startup reports a warning/notice when one or more operations were released this way.

Important boundary:

> orphan recovery repairs PTL's persisted coordination state; it does not prove that every external side effect or child process from the interrupted workflow was rolled back.

After a crash:

- inspect the owning workflow;
- inspect artifact/external file state;
- inspect Automation side effects separately;
- do not treat `abandoned` as equivalent to transactional rollback.

## 17. Why PTL may refuse to close immediately

The shell owns background workspace workers.

On close, PTL first runs workspace-leave/close guards and then asks registered workspaces to shut down owned background work. If a worker has not stopped yet, the close event is ignored, a background-shutdown status is shown, and the shell schedules another close attempt.

This behavior exists to avoid destroying a workspace object while its worker still owns data/state.

Do not repeatedly kill the application merely because close takes a moment during active work.

If shutdown never completes, collect the owning workspace, operation ID/status, and log evidence before force-terminating the process.

## 18. Telemetry is unavailable or incomplete

Telemetry is diagnostic support, not a prerequisite for the rest of PTL.

Current semantic states include:

```text
normal
high_load
gpu_unavailable
processes_unavailable
active
refresh_failed
```

If the base system metrics provider fails entirely, PTL returns a safe snapshot with `refresh_failed` rather than raising through the UI.

If only GPU collection fails, GPU metrics become `gpu_unavailable` while base CPU/RAM information can remain usable.

If process rows are unavailable, that state is represented separately.

Do not interpret missing NVIDIA telemetry as proof that local inference cannot run. Model execution and telemetry collection have different provider paths.

## 19. CPU/GPU load during Training or inference

Telemetry can help establish resource pressure, but PTL's status codes remain the authoritative workflow result.

Current telemetry presentation marks:

```text
CPU >= 85% -> high_load
GPU >= 90% -> high_load
```

when those metrics are available.

Those thresholds are UI diagnostics, not automatic proof of a Training failure.

For local-model `resource_exhausted`, inspect memory/VRAM pressure and the application log as well as percentage utilization.

## 20. Local model: file check fails

Use the dedicated [Local Models guide](local-models.md) for the complete contract.

The most useful distinction is diagnostic code:

```text
model_directory_missing
required_files_missing
model_check_failed
model_files_ready
```

A relative model path is workspace-relative, not terminal-CWD-relative.

Do not move the model into the source tree to make a relative path "work".

## 21. Local model: `found` but generation fails

This is not contradictory.

`found` is a shallow file-shape check. Actual generation is where PTL imports Torch/Transformers, loads the tokenizer/model, chooses the device, and executes generation.

Common later states include:

```text
inference_unavailable
resource_exhausted
generation_failed
empty_response
```

Collect the semantic status and diagnostic code rather than only the translated label.

## 22. Training run cannot be created

Creation requires:

- a valid Profile;
- an approved Dataset with a stored content SHA-256;
- a model path whose file probe is `found`;
- positive epochs, batch size, and learning rate.

Typical configuration/validation codes include:

```text
invalid_hyperparameters
profile_required
dataset_required
model_required
```

Resolve the missing/invalid input before trying to repair Training persistence.

## 23. Training run exists but Launch is unavailable or rejected

A run launches only from `ready`.

Important validation/failure states include:

```text
run_not_found
already_running
not_ready
model_missing
resource_busy
```

Training also rechecks the Profile/Dataset/model state at Launch. A run that was valid at Create time can correctly become invalid later if an input changed or disappeared.

## 24. Training refuses changed inputs

A ready run pins its Profile Training representation and approved Dataset bytes.

Controlled integrity failures include:

```text
profile_changed_after_run_creation
dataset_changed_after_run_creation
dataset_changed_after_approval
```

These are safeguards against silently training on different inputs under the same run identity.

The normal response is to understand the change and create a new run for the new intended input state—not to edit stored hashes manually.

## 25. Training reaches backend execution and fails

Use three evidence sets together:

1. Training persisted run/log state;
2. application log / correlated error evidence;
3. artifact directory state.

Potential causes include unavailable Training dependencies, invalid packed examples, resource exhaustion, model/runtime incompatibility, or artifact-save failure.

A failed run is not repaired by editing its status back to `ready`. Preserve the failed run as evidence and create a new run after correcting the underlying cause.

## 26. Training completed but model version/artifact looks wrong

A successful Training backend writes:

```text
<workspace>/artifacts/full_finetune/<run_id>/model/
<workspace>/artifacts/full_finetune/<run_id>/training_metadata.json
```

The Training view-model then attempts model-version publication.

When diagnosing a mismatch, compare stable identifiers:

```text
training run ID
model-version ID
artifact_path
Profile ID/hash
Dataset ID/hash
```

Do not infer provenance only from human-readable titles or directory names.

Remember that v1.0 does not content-hash the complete base-model directory.

## 27. Dataset or Profile appears valid but Training disagrees

Training validates the exact downstream contract, not only whether a record exists in a list.

For Datasets this includes approval state/fingerprint and current source-byte checks. For Profiles it includes the exact rendered Training representation fingerprint.

A Dataset source is external filesystem state. If the JSONL was moved, replaced, or edited outside PTL, the database row can still exist while the current source input is no longer the approved bytes.

Use the Dataset/Training identifiers and hashes rather than manually rewriting statuses.

## 28. Tests portrait is partial

A portrait run is saved as `partial` when one or more battery items fail either inference-response or score-parsing requirements.

Use **Review cases** first.

For each failed/suspicious case inspect:

- model result status;
- `VALID_SCORE`;
- normalized response;
- diagnostic response preview;
- item key/reverse flag.

A partial run can still produce some factor means from available valid scores. Therefore a visible factor value does not imply full battery coverage.

## 29. Tests opened from Agents shows no portrait

When Tests receives an exact lineage model-version context, it does not silently substitute another model version's portrait.

If the selected model version has no saved portrait, an empty selected-version state is expected.

Build a portrait for that exact version or choose the intended existing version.

## 30. Analysis Delta is unavailable

Numeric Delta requires two portrait runs with known and equal:

```text
battery_version
scoring_version
```

Two completed portraits are not automatically comparable.

For exact lineage comparison, Analysis also requires portraits for the two exact selected model-version identities; it does not silently substitute latest/previous unrelated runs.

Check the evaluation protocol IDs before treating a missing Delta as an Analysis defect.

## 31. Agents graph does not show a newly created entity

Agents builds its semantic graph from a coherent persisted SQLite snapshot and refreshes in the background.

Check:

1. whether the source workflow committed successfully;
2. whether Agents refreshed;
3. Issues/log evidence for a refresh failure;
4. whether the visible object is a canonical alias/placeholder rather than the real entity.

A failed background refresh intentionally keeps the last successful projection when one exists. Seeing old-but-consistent lineage can therefore be safer behavior than replacing it with a partial/broken projection.

## 32. Agents delete or Redo is blocked

Custom-branch deletion and protected deletion Redo obtain fresh runtime safety leases.

An operation that uses a linked real resource can block the destructive transition.

This can happen even if the original deletion succeeded earlier: after Undo, another operation may begin before Redo.

Inspect the active-operation/resource blocker. Do not remove resource links or runtime-operation rows manually to bypass the check.

## 33. Agents local history/layout appears missing after restore

Agents local state lives in:

```text
<workspace>/agents_lineage_state.json
```

Semantic Dataset/Training/model/evaluation records live in SQLite.

Restoring only `app.db` can therefore restore the semantic graph while losing custom branches/current marker/undo/redo/layout history.

Before calling this corruption, verify whether the Agents JSON came from the same backup snapshot.

## 34. Automation recipe is missing or invalid

Refresh re-discovers built-in and workspace manifests.

Workspace recipes are read from:

```text
<workspace>/automation/recipes/**/*.ptl-recipe.json
```

Malformed or duplicate manifests can produce discovery issues such as:

```text
manifest_invalid
recipe_duplicate
```

Valid recipes remain available when another manifest is bad.

Import copies the manifest only; companion scripts/data may still be missing.

## 35. Automation command/recipe is blocked before launch

Important pre-launch result codes include:

```text
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

For `operation_blocked`, inspect runtime resource claims.

For ad-hoc `host_effects_not_authorized`, explicitly review and authorize host effects if the command is truly intended.

For `audit_unavailable` / start `audit_failed`, PTL intentionally does not launch an ad-hoc command without its required structured audit path.

Do not work around an audit failure by moving the command into an untracked helper under `src/`, `tests/`, or `tools/`.

## 36. Automation launched but failed

Important terminal results include:

```text
succeeded
failed
cancelled
timeout
launch_failed
```

A non-zero child return code becomes `failed`.

A process-establishment error becomes `launch_failed`.

Timeout/cancellation terminate the contained process tree according to the platform-specific containment mechanism.

Inspect:

- operation ID;
- result code;
- return code;
- stdout/stderr;
- truncation flags;
- working directory;
- declared resource claims;
- expected host-side outputs.

Remember that Automation is trusted-host execution, not a filesystem/network sandbox.

## 37. Automation output is truncated

Stdout and stderr are captured independently with bounded storage.

The default limit is 1 MiB per stream and the hard maximum is 64 MiB per stream.

PTL keeps draining the pipe after the retained prefix reaches the limit, so truncation is a capture boundary rather than necessarily a child-process deadlock/failure.

If full output is required, make the command write a reviewed output file intentionally and preserve it as an external/workspace artifact according to the workflow's trust model.

## 38. Automation appears to leave or kill child processes

Automation owns the process tree for the one-shot run lifecycle.

On POSIX it uses a separate session/process group. On Windows it uses a Job Object configured for kill-on-close behavior.

A command should not depend on starting a detached long-lived background service and then exiting successfully while expecting that child to survive unmanaged.

If a persistent service is required, manage it through an explicit service/supervisor outside this one-shot Automation contract.

## 39. Workspace navigation is blocked during work

Some workspaces deliberately prevent ordinary navigation away while owned background work is active.

This is not the same as the whole application being frozen.

Wait for the owned operation to finish or use the feature's supported cancellation path when one exists. Training v1.0 does not expose an active cooperative Stop/Pause implementation; Automation does expose Cancel.

Do not destroy the workspace widget/process to bypass ownership guards unless performing controlled crash recovery.

## 40. Development checkout: release gate refuses to start

The release gate requires a clean Git worktree **before it creates a release report directory or runs validation steps**.

Typical message:

```text
Release audit configuration error: Release gate requires a clean Git worktree...
```

This is a configuration refusal, not a failed pytest/Ruff/mypy result.

Use:

```bash
git status --short
git diff --name-only --diff-filter=U
```

Resolve/commit the intended source state (or stash unrelated work when that is truly appropriate) before rerunning the gate.

Do not label the build "release-gate failed tests" when no gate step ran.

## 41. Development checkout: unresolved merge conflicts

Unmerged paths appear in `git status --short` with states such as:

```text
UU
AA
```

The release gate will reject that tree because it is dirty/unresolved.

Resolve each file based on intended code semantics, run targeted tests for the affected subsystem, and only then create the merge/integration commit.

Avoid mass choosing "ours" or "theirs" across architecture/persistence/UI/tests merely to obtain a clean index. A syntactically clean merge can still erase one side's semantic guarantees.

For PTL specifically, conflict resolution should preserve the current contracts for stable IDs, runtime safety, localization, Training input integrity, background ownership, and tests that prove those behaviors.

## 42. `codebase_stats.py` on a dirty tree

`tools/codebase_stats.py` deliberately has a different purpose from the release gate.

It obtains the file set with `git ls-files` but reads the **current working-tree bytes** of those tracked files. It does not require a clean tree before reporting statistics.

Therefore on a dirty or conflicted checkout:

- the printed `Commit` is the current `HEAD` identity;
- line/code counts can describe working-tree content that is **not** identical to that commit;
- unresolved conflict-marker lines can also affect the counts.

Such output is useful as an **integration/worktree size snapshot**, but it is not a reproducible commit baseline.

For a release baseline, use the `codebase-stats` result produced by a successful clean release gate, or run the standalone tool only after confirming the worktree is clean.

## 43. Quick release gate

The quick profile runs, in order:

```text
compileall
ruff
typing-audit
pytest (curated manifest, repeated --runs times)
i18n-audit
codebase-stats
```

It intentionally omits full-profile:

```text
mypy
build
```

The quick profile is therefore a faster regression gate, not a substitute for the complete release audit.

## 44. Full release gate

The full profile includes blocking:

```text
compileall
ruff
typing-audit
mypy
pytest
i18n-audit
codebase-stats
build
```

All current full-profile setup/final steps are blocking.

Removed bypass flags such as `--skip-mypy` / `--skip-build` are not accepted by the current CLI contract.

## 45. Release gate cannot resolve Git HEAD

The gate requires a Git worktree with a resolvable `HEAD`.

If metadata collection cannot obtain the commit, gate initialization fails before the audit begins.

Run the release workflow from the intended repository checkout and verify:

```bash
git rev-parse HEAD
```

before investigating test infrastructure.

## 46. Hidden ignored inputs under `src/`, `tests/`, or `tools/`

PTL's release policy protects against local ignored files that can alter execution without appearing in the recorded commit.

Release-policy tests inspect ignored/untracked content in these source trees and allow only narrow harmless debris such as Python bytecode/cache and common OS metadata.

If an ignored Python/data/helper file under these trees affects your local run, the correct fix is to make source ownership explicit—not to rely on a hidden development machine input.

This is part of the source-integrity contract.

## 47. A quick gate step fails

When the gate has actually begun, inspect the first blocking failing step and its generated log in the audit directory.

Do not immediately rerun all tests repeatedly without understanding the first deterministic failure.

Useful classification:

- `compileall`: syntax/import-compilation surface;
- `ruff`: static style/quality rule;
- `typing-audit`: type-suppression policy;
- `pytest-run-NN`: behavioral regression or environment-dependent test;
- `i18n-audit`: catalog/reference/UI-literal contract;
- `codebase-stats`: statistics tool execution;
- `mypy` (full): production type checking;
- `build` (full): packaging/build contract.

The report records the seed, platform, Python, commit, branch, quick/full mode, and per-step logs.

## 48. Repeated pytest runs disagree

The release gate can execute pytest multiple times through `--runs` while recording one seed/environment envelope.

If run 1 passes and a later run fails, treat the discrepancy as evidence of nondeterminism, hidden state, ordering, timing, or cleanup leakage.

Do not average the results or report "mostly passed".

Collect:

- failing run number;
- exact test;
- audit seed;
- all preceding run logs;
- whether the test touches temporary files, Qt state, background workers, SQLite, process state, or persistent environment variables.

## 49. What not to delete during diagnosis

Until the root cause is known, avoid casually deleting:

```text
app.db
agents_lineage_state.json
artifacts/
models/
automation/recipes/
external Dataset JSONL
release-audit logs for a failing build
```

`cache/` and stopped-operation `temp/` are lower-risk than the items above, but even those should not be the automatic first step when reproducing a defect.

Renaming/copying state before a destructive experiment is safer than irreversible deletion.

## 50. What not to edit manually

Normal recovery should not require manual edits to:

```text
runtime_operations
runtime_operation_resources
lineage_resource_links
Training input hashes
Dataset approval hashes
model-version provenance fields
```

Those values participate in integrity/safety semantics. Changing them can hide the original failure while creating a more dangerous inconsistent state.

If a future documented migration/recovery tool explicitly owns such a repair, use that tool rather than hand-editing SQLite.

## 51. Minimal evidence bundle for a reproducible bug

Before applying a destructive fix, collect this minimum bundle where applicable:

```text
1. PTL commit/version and branch
2. OS + Python version
3. actual workspace root
4. exact action that failed
5. semantic status/result/diagnostic code
6. entity IDs (Dataset/Profile/run/model-version/experiment)
7. operation ID + correlation ID
8. relevant Issues/Activity text
9. relevant Training/Automation output
10. relevant application-log excerpt
11. whether the failure followed a crash, restore, external file edit, model replacement, recipe edit, or merge
```

For ML/research workflows also record model source/revision and whether the model directory or Dataset source changed in place.

## 52. Privacy-safe sharing checklist

Before sharing diagnostic material publicly, review for:

- private Dataset text;
- Profile/personality content;
- model prompts/responses;
- local usernames/home paths;
- repository/private path names;
- environment variables;
- Automation command/output content;
- resource IDs that reveal project names;
- complete SQLite databases;
- model files;
- access tokens/keys/secrets.

PTL redacts a subset of structured context key names, but the operator remains responsible for reviewing exported/logged evidence.

## 53. Conservative escalation sequence

When the cause is not obvious, use this order:

```text
1. Stop changing state.
2. Record commit/version/workspace.
3. Record semantic status + IDs.
4. Inspect Issues and Activity.
5. Inspect feature-specific logs/results.
6. Inspect rotating application log.
7. Verify external dependencies/paths.
8. Verify runtime blockers/background ownership.
9. Reproduce with the smallest safe workflow.
10. Back up the workspace before reset/repair experiments.
```

For a source checkout, add:

```text
11. Confirm git status.
12. Resolve merge/dirty-tree state.
13. Run targeted tests.
14. Run clean quick gate.
15. Run full release gate before release acceptance.
```

## 54. Reset is a recovery tool, not a diagnostic default

A complete workspace reset disconnects or removes a large amount of authoritative and derived state.

Do it only after:

- evidence has been collected;
- important workspace/external data has been backed up;
- you understand that the reset will not undo external Automation host effects;
- you specifically want a fresh-workspace experiment or recovery baseline.

The detailed backup/reset contract is in [Workspace & Storage](workspace-and-storage.md).

## 55. Current v1.0 troubleshooting boundaries

PTL v1.0 does not claim automatic diagnosis or repair of every failure mode.

In particular, it does not provide:

- transactional rollback for arbitrary external Automation effects;
- automatic restoration of deleted external Dataset/model files;
- automatic base-model byte identity verification;
- universal CUDA/driver/model compatibility diagnosis;
- distributed/multi-host lock recovery;
- automatic repair of arbitrary manual SQLite edits;
- a guarantee that every failure is represented in Issues when diagnostic persistence itself is unavailable;
- a guarantee that every forcibly terminated external child/process effect can be reconstructed afterward.

The supported contract is to preserve clear operational boundaries, semantic status/result codes, persisted coordination state, feature-specific evidence, and best-effort structured error reporting so failures can be investigated without inventing behavior that the code does not implement.

## 56. Developer invariants

Changes to diagnostics/recovery should preserve these rules unless the product contract is deliberately revised:

1. error reporting must not crash the original workflow when its own persistence/log path fails;
2. user-visible/localized text must not replace semantic status/result/diagnostic identity;
3. runtime blockers must be resolved through operation lifecycle rather than silently bypassed;
4. source release evidence must be tied to a clean recorded commit;
5. hidden ignored runtime inputs under source/test/tool trees must not become release dependencies;
6. background workers must remain owned through workspace/application shutdown;
7. whole-workspace persistence must remain distinguishable from external Dataset/model/Automation dependencies;
8. destructive reset/cleanup must not be presented as the default fix for an unclassified incident;
9. troubleshooting documentation must distinguish a controlled integrity rejection from corruption;
10. documentation must be updated when status/result/error/recovery behavior changes.

## Next steps

- Workspace paths, backup and reset: [Workspace & Storage](workspace-and-storage.md)
- Local model readiness/generation: [Local Models](local-models.md)
- Training workflow/integrity: [Training](../user-guide/training.md)
- Agents lineage/runtime deletion safety: [Agents lineage](../user-guide/agents-lineage.md)
- Tests/evaluation/Delta: [Tests and Analysis](../user-guide/tests-and-analysis.md)
- Automation execution/audit/process containment: [Automation](../user-guide/automation.md)
- Stable guarantees/non-goals: [v1.0 Product Contract](../reference/v1-product-contract.md)
