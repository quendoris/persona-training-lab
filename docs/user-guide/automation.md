# Automation

Automation is Persona Training Lab's explicit host-execution workspace. It can run trusted PTL recipes and operator-authored ad-hoc commands while coordinating shared runtime resources, capturing bounded output, containing descendant processes, and recording structured audit metadata.

The most important rule is simple:

> **Automation is a controlled execution surface, not a security sandbox.**

Commands execute with the permissions of the PTL process/OS account. Review every recipe or ad-hoc command as executable code before running it.

For implementation details, read [Automation architecture](../architecture/automation.md).

## 1. What the Automation screen contains

The workspace is split into three functional areas.

### Registry

The left side shows:

- discovered recipes;
- search/filter;
- Refresh;
- Import;
- recipe-discovery issues.

### Recipe / ad-hoc detail

The center area shows the selected recipe's:

- title and description;
- recipe ID/version/source/tags;
- declared inputs;
- declared outputs;
- declared runtime resource claims;
- rendered command template.

The same area also contains the **ad-hoc command** editor.

### Runner

The right side contains:

- Run recipe;
- Run command;
- Cancel;
- run status;
- runtime operation ID and return code;
- execution mode/effect scope/working directory;
- command/stdout/stderr output.

Only one Automation worker is started by this screen at a time.

## 2. Trust model

Automation currently exposes one effect scope:

```text
trusted_host
```

That means the executed process is a normal host process under the PTL user's operating-system permissions.

Automation does **not** currently provide:

- a container boundary;
- filesystem virtualization;
- a restricted syscall sandbox;
- a separate low-privilege OS identity;
- automatic network isolation;
- automatic secret redaction inside child-process stdout/stderr;
- a proof that a declared resource claim matches every real side effect of the command.

Runtime resource claims coordinate PTL workflows; they are not an operating-system permission system.

## 3. Recipe registry location

Workspace recipes live under:

```text
<workspace>/automation/recipes/
```

The provider recursively discovers files matching:

```text
*.ptl-recipe.json
```

The manifest schema is:

```text
ptl:automation-recipe:v1
```

PTL also exposes the built-in recipe:

```text
workspace_health
```

which performs a read-only workspace diagnostic.

## 4. Refresh and discovery

Refresh re-scans built-in and workspace recipes.

A malformed manifest does not make every valid recipe disappear. PTL keeps valid recipes available and reports the bad file as a discovery issue.

Examples of discovery failures include:

```text
manifest_invalid
recipe_duplicate
```

A duplicate recipe ID is not silently allowed to replace an existing built-in/workspace recipe.

## 5. Importing a recipe

Import validates the selected manifest and copies it into the workspace registry as:

```text
<workspace>/automation/recipes/<recipe_id>.ptl-recipe.json
```

Import copies the **manifest file**. It does not automatically package arbitrary companion scripts, binaries, models, or data referenced by that manifest.

### Relative-path consequence

For an imported workspace recipe, a relative `working_directory` is resolved relative to the imported manifest's directory.

Therefore a recipe that depended on files beside its original external manifest may need those companion files copied/referenced explicitly after import.

Do not assume importing one JSON file makes an external tool bundle self-contained.

## 6. Recipe manifest essentials

A minimal recipe looks conceptually like:

```json
{
  "schema": "ptl:automation-recipe:v1",
  "id": "example.echo",
  "version": "1.0.0",
  "title": "Echo",
  "description": "Example trusted-host recipe",
  "command": ["{python}", "-c", "print('hello')"]
}
```

Recipe IDs must match:

```text
[a-z0-9][a-z0-9._-]*
```

The `command` is a non-empty array of string tokens. Recipe execution uses explicit **exec** mode rather than shell parsing.

## 7. Recipe placeholders

Recipe command/resource/working-directory text can use declared substitutions.

PTL always provides:

```text
{python}
{workspace}
```

where:

- `{python}` is the current PTL Python interpreter;
- `{workspace}` is the resolved PTL workspace root.

Declared recipe inputs become additional placeholders.

Unknown placeholders make the recipe invalid at execution time rather than silently becoming empty text.

Reserved input names include:

```text
python
workspace
```

## 8. Recipe inputs

Inputs can declare:

- `name`;
- `required`;
- `default`;
- `description`.

Unknown supplied input names are rejected.

Missing required inputs are rejected before process launch.

Typical result codes are:

```text
input_required
input_unknown
recipe_invalid
```

## 9. Recipe outputs

Recipe `outputs` are descriptive contract metadata. They help the operator understand what a recipe is expected to produce.

They are not currently an automatic typed artifact-ingestion system.

The built-in `workspace_health` recipe declares a JSON stdout output and returns a payload with schema:

```text
ptl:automation-output:workspace-health:v1
```

## 10. Recipe resource claims

A manifest can declare runtime coordination claims:

```json
{
  "resources": [
    {
      "kind": "workspace",
      "id": "{workspace}",
      "access": "read"
    }
  ]
}
```

Supported access values are:

```text
read
write
```

These claims participate in the same runtime-operation coordination used by other PTL workflows.

Read/read can coexist. A conflicting write blocks.

### Important limitation

Resource claims describe coordination intent. PTL does not inspect arbitrary process syscalls to prove that a recipe touches only the resources it declared.

A trusted recipe that lies about its effects can still affect host resources permitted by the OS account.

## 11. Recipe working directory

If a recipe does not define `working_directory`, PTL runs it from:

```text
<workspace>
```

For a workspace manifest, a relative `working_directory` resolves relative to the manifest's directory.

An absolute path remains absolute after normalization.

## 12. Recipe environment

Recipe execution inherits the PTL process environment and always receives:

```text
PTL_WORKSPACE=<resolved workspace root>
```

The recipe manifest does not currently expose the same arbitrary environment-override editor used by ad-hoc commands.

Treat inherited environment variables as potentially sensitive inputs to trusted recipes.

## 13. Recipe timeout

A manifest can declare:

```json
{
  "timeout_seconds": 30
}
```

`0` means no recipe timeout is configured.

Positive values become an execution timeout.

## 14. Recipe review boundary

Workspace recipe files are mutable trusted-host execution inputs.

The Automation detail pane shows a discovered recipe snapshot, but v1.0 does **not** cryptographically pin that displayed manifest to the later Run click.

`Run` resolves the recipe again by `recipe_id` before execution.

Therefore:

1. edit/import the recipe;
2. use **Refresh**;
3. review the displayed command/inputs/resources;
4. avoid modifying the manifest between review and Run.

If another program can modify the recipe directory concurrently, treat that directory as part of your trusted execution boundary.

## 15. Running a recipe

A normal recipe run is:

1. select a recipe;
2. review source/version/tags;
3. review the command template;
4. review declared resources;
5. enter required inputs;
6. press **Run**;
7. watch run status;
8. inspect operation ID, return code, stdout/stderr;
9. confirm expected filesystem/output effects separately when they matter.

The process runs on an owned background worker rather than the Qt GUI thread.

## 16. Ad-hoc commands

The ad-hoc editor is for explicitly operator-authored host commands.

It supports two execution modes:

```text
exec
shell
```

These modes are intentionally different.

## 17. `exec` mode

In `exec` mode the command field must be a JSON array of strings.

Example:

```json
["python", "-c", "print('hello')"]
```

The first item is the executable. Remaining items are arguments.

PTL does not send this array through a shell.

Use `exec` when shell parsing/features are unnecessary. It makes the argv boundary explicit and avoids accidental shell interpretation.

Invalid/empty arrays are rejected before execution.

## 18. `shell` mode

In `shell` mode the command field is one shell command string.

Example:

```text
printf 'hello\n'
```

Shell syntax, expansion, quoting, pipelines, redirection, and shell-specific behavior now become part of the command's trust boundary.

Use shell mode only when you actually need shell semantics.

## 19. Host-effects authorization

Ad-hoc commands require explicit host-effect authorization.

The UI checkbox corresponds to:

```text
host_effects_authorized = true
```

Without it, PTL refuses to launch the command:

```text
host_effects_not_authorized
```

This checkbox is an acknowledgement, not a sandbox switch. Enabling it means you authorize the command to act as the current PTL/OS user.

## 20. Ad-hoc working directory

An empty ad-hoc working directory means:

```text
<workspace>
```

A relative path is resolved below the workspace root.

An absolute path is allowed and remains an absolute host path.

## 21. Ad-hoc environment

The environment editor accepts a JSON object of string keys and string values.

Example:

```json
{
  "MY_MODE": "diagnostic",
  "PYTHONUNBUFFERED": "1"
}
```

With **inherit environment** enabled, these values override the inherited PTL environment.

With inheritance disabled, the child receives only your supplied values plus PTL's mandatory workspace marker.

PTL always forces:

```text
PTL_WORKSPACE=<actual resolved workspace>
```

after applying overrides, so an ad-hoc environment cannot redefine `PTL_WORKSPACE` to a different value.

## 22. Ad-hoc resource claims

The resource editor accepts a JSON array.

Example:

```json
[
  {"kind": "dataset", "id": "dataset-17", "access": "write"},
  {"kind": "model_version", "id": "model-2", "access": "read"}
]
```

If you provide no claims, ad-hoc execution defaults to a conservative claim:

```text
workspace = <resolved workspace>
access = write
```

This prevents a no-claim ad-hoc command from silently bypassing all PTL coordination for the workspace.

Custom claims remain declarations; they are not OS enforcement.

## 23. Timeout

The ad-hoc timeout field accepts a non-negative number of seconds.

```text
0
```

means no timeout.

A positive value causes PTL to terminate the contained process tree when the deadline is reached.

The resulting status is:

```text
timeout
```

and the runtime lease finishes as failed.

## 24. Output capture limits

Stdout and stderr are drained concurrently and captured independently.

Default per-stream capture limit:

```text
1 MiB
```

Hard maximum per stream:

```text
64 MiB
```

When a stream exceeds its limit, PTL continues draining the process pipe but only retains the bounded prefix and marks the stream as truncated.

This avoids making process output an unbounded UI-memory sink.

A limit of `0` captures no output bytes while still draining the stream.

## 25. Cancel

While a run is active, **Cancel** requests cancellation from the Automation worker.

Cancellation is polled by the process runner and terminates the contained process tree.

The result code becomes:

```text
cancelled
```

The runtime operation is recorded as cancelled.

Cancellation is not equivalent to a cooperative application-level shutdown inside the child command. PTL terminates the process containment group/job.

## 26. Descendant-process containment

Automation is designed not to leave ordinary descendant processes behind after cancellation/timeout.

### POSIX

PTL starts the command in a new session/process group.

Termination sends `SIGTERM`, then escalates to `SIGKILL` after the termination grace period when needed.

### Windows

PTL launches through a Windows Job Object configured for kill-on-close behavior.

The Job Object contains the launched process tree so cancellation/finalization can terminate descendants as a group.

This is process containment, not filesystem/network sandboxing.

## 27. Successful runs and background descendants

Automation finalization is intentionally stricter than simply waiting for the direct child's exit code.

A command should not rely on launching a detached long-lived child and then exiting while expecting that child to survive as an unmanaged background service.

Automation owns the process tree for the run lifecycle.

If you need a persistent service, manage it through an explicit service/supervisor mechanism outside this one-shot Automation contract.

## 28. Runtime coordination

Before launch, Automation asks the runtime-operation coordinator for a lease covering the declared/default resource claims.

If a conflicting PTL operation already owns an incompatible claim, launch is blocked:

```text
operation_blocked
```

The command is not started.

Do not manually edit `runtime_operations` or resource-claim rows to bypass a blocker.

## 29. Audit behavior

Production Automation is wired to the shared PTL `event_log` through:

```text
ptl:automation-audit:v1
```

Typical event types include:

```text
automation.run.started
automation.run.finished
automation.run.blocked
automation.run.launch_failed
```

The audit stores execution metadata such as:

- operation/correlation identity;
- mode/effect scope;
- working directory;
- SHA-256 of the command snapshot;
- number of command parts;
- environment **keys**;
- timeout;
- output limit;
- resource claims;
- terminal state/return code/truncation flags.

## 30. What the audit intentionally does not store

The structured Automation audit does not persist the plaintext command merely as an unrestricted command log.

Instead it stores a SHA-256 fingerprint of the command snapshot plus structural metadata.

It also stores environment-variable names, not inherited environment-variable values.

Stdout/stderr contents are not copied into the Automation audit payload by the v1 implementation.

### Privacy boundary

This does **not** make every audit row non-sensitive.

The audit can still reveal working directories, resource kinds/IDs, environment key names, operation subjects, error details, and timing/return-state metadata.

Review `app.db`/event exports before sharing them publicly.

## 31. Ad-hoc audit fail-closed behavior

An ad-hoc command will not launch if Automation audit infrastructure is unavailable.

Possible results include:

```text
audit_unavailable
audit_failed
```

If the start-audit record cannot be persisted, PTL fails the runtime lease and does not launch the command.

This protects the explicit operator-command path from silently becoming unaudited.

Production recipe execution also receives the configured audit trail, but the service-level hard `audit_unavailable` precondition is specific to ad-hoc commands.

## 32. Run result codes

Important Automation result codes include:

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

A non-zero child return code becomes `failed`.

A launch error before a child process can be established becomes `launch_failed`.

## 33. Workspace-leave behavior

The Automation screen blocks ordinary navigation away from the workspace while its run worker is active.

This avoids leaving a live run behind while the user accidentally changes workspaces and loses local run context.

Application shutdown has separate background-worker ownership/shutdown handling.

## 34. Safe first workflow

Start with the built-in diagnostic:

1. open Automation;
2. select `workspace_health`;
3. review its read-only workspace claim;
4. press **Run**;
5. confirm `succeeded`;
6. inspect stdout JSON;
7. verify the reported workspace path is the one you expect.

Then try a harmless ad-hoc `exec` command:

```json
["python", "-c", "print('PTL automation OK')"]
```

Use an empty working directory, inherited environment, empty resources, and explicit host-effect authorization. The empty ad-hoc resource list becomes the default workspace write claim.

## 35. Troubleshooting

### Recipe does not appear

Check the `.ptl-recipe.json` suffix, schema, recipe ID format, duplicate IDs, discovery issue list, and Refresh after edits.

### Recipe runs a different relative path than expected

Remember that imported manifests live under `<workspace>/automation/recipes/`. Relative recipe `working_directory` is based on the current manifest source directory.

### Ad-hoc Run says host effects are required

Enable the explicit host-effect authorization checkbox only after reviewing the command.

### `exec` command is rejected

Use a JSON array of strings, not a shell command line.

### Command is blocked

Inspect the active runtime-operation conflict. Your claims overlap an incompatible PTL operation.

### Output ends abruptly

Look for the truncated-output marker. Increase the capture limit only when justified and stay below the 64 MiB hard maximum per stream.

### Recipe changed after I reviewed it

Refresh and review again. v1 does not content-pin the displayed workspace manifest to the later recipe Run click.

## 36. Backup implications

Back up:

```text
<workspace>/automation/recipes/
```

when custom recipes are valuable.

A workspace backup preserves imported manifests but not arbitrary external tools/data referenced by absolute paths or by companion files that were never copied into the workspace.

Audit metadata lives in `app.db` through the shared event log.

## 37. Screenshot plan

The final documentation capture pass should include at least:

1. Automation full-window overview;
2. built-in `workspace_health` selected;
3. recipe inputs/outputs/resources contract area;
4. recipe discovery issue from an intentionally invalid demo manifest;
5. Import workflow immediately after successful import;
6. successful recipe result with operation ID and stdout;
7. ad-hoc `exec` editor with JSON argv;
8. ad-hoc `shell` editor and shell warning/help text;
9. host-effects authorization unchecked/error state;
10. explicit environment JSON + inherit toggle;
11. explicit resource-claims JSON;
12. blocked run caused by a demo runtime claim conflict;
13. cancelling state;
14. timeout result;
15. truncated stdout/stderr result;
16. audit/event example with command hash/environment keys but no plaintext values.

Capture from a clean demo workspace. Do not put real secrets, tokens, personal paths, or destructive commands into release screenshots.

## 38. v1.0 boundaries

v1.0 Automation does not claim:

- arbitrary commands are safe merely because PTL launches them;
- resource claims enforce OS permissions;
- workspace recipes are cryptographically signed/content-pinned;
- imported manifests package all external dependencies;
- stdout/stderr are a durable run-history store;
- detached background services survive Automation finalization;
- distributed/multi-host runtime coordination;
- exhaustive stress qualification for maximum process-tree/concurrency complexity.

It does provide a coherent local trusted-host execution contract with explicit ad-hoc authorization, bounded output, timeout/cancellation, process-tree containment, runtime claims, and structured audit metadata.

## Related documentation

- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Automation architecture](../architecture/automation.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
- [v1.0 Product Contract](../reference/v1-product-contract.md)
