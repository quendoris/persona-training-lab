# Security, Trust & Privacy Boundaries

This guide defines the security/trust/privacy boundaries that Persona Training Lab v1.0 actually implements.

It is not a generic security checklist and it does not infer guarantees from UI wording. The statements here follow current PTL composition, persistence, model-loading, Automation, runtime-coordination, logging, and release-policy code.

The central rule is:

> **PTL coordinates trusted local research workflows inside the authority of the current operating-system account. It is not a sandbox, privilege boundary, secret vault, or hostile-input execution environment.**

For operational failures and evidence handling, read [Troubleshooting & Diagnostic Evidence](troubleshooting.md). For backup/storage boundaries, read [Backup, Reset & Recovery](backup-reset-recovery.md) and [Workspace & Storage](workspace-and-storage.md).

## 1. Security model at a glance

PTL v1.0 combines several different kinds of boundaries:

| Boundary | What PTL currently does | What it does **not** mean |
|---|---|---|
| OS account | Runs the desktop application and trusted-host Automation under the current user's authority | PTL is not a lower-privilege sandbox |
| Workspace ownership | Keeps PTL mutable state under a stable workspace root | The workspace is not an access-control sandbox |
| Runtime claims | Coordinates read/write use of known PTL resources | Claims do not constrain syscalls/files/network |
| Model loading | Does not enable `trust_remote_code=True` | Model files are not untrusted-safe/sandboxed |
| Dataset approval | SHA-256 fingerprints approved JSONL bytes | A hash does not make content confidential or restore deleted bytes |
| Training pinning | Pins Profile Training text and Dataset SHA-256 | Base-model bytes are not fully content-addressed |
| Automation authorization | Ad-hoc host commands require explicit host-effects authorization | Authorization does not reduce command privileges |
| Automation audit | Records structured execution metadata | Audit is not prevention/rollback and is not secret-free by definition |
| Process containment | Owns/terminates Automation descendant process trees | Containment is not filesystem/network isolation |
| Error context redaction | Redacts selected structured-context key names | Tracebacks/exception text are not comprehensively secret-scrubbed |
| Release gate | Requires a clean recorded source state and rejects hidden source inputs | A green gate is not formal proof against all vulnerabilities |

Keep these concepts separate. Most dangerous misunderstandings come from treating one boundary as if it provided another.

## 2. The operating-system account is the primary authority boundary

PTL is a local desktop process.

Files that PTL itself can read/write, child commands it can execute, and host resources accessible to trusted Automation are ultimately constrained by the permissions of the OS account that launched PTL.

PTL v1.0 does not create a separate low-privilege user identity for model loading, Training, Dataset parsing, or Automation.

If the PTL account can modify a host path, trusted-host Automation can potentially modify that path too.

Use OS filesystem permissions, account separation, disk encryption, network controls, and host security policy when stronger boundaries are required.

## 3. The PTL workspace is a persistence root, not a sandbox

The workspace gives PTL a stable ownership location for mutable state.

Typical root:

```text
<workspace>/
├── app.db
├── agents_lineage_state.json
├── artifacts/
├── automation/recipes/
├── cache/
├── exports/
├── logs/
├── models/
└── temp/
```

This prevents accidental dependence on repository/process CWD for normal runtime state.

It does **not** prevent PTL or trusted child processes from accessing paths outside the workspace when the code/workflow explicitly uses them.

Examples include external Dataset files, explicit model directories, and Automation absolute working directories.

## 4. Data at rest is ordinary host filesystem state

The current persistence implementation uses normal SQLite and ordinary files/directories.

PTL v1.0 does not add an application-level encryption layer to:

```text
app.db
agents_lineage_state.json
logs/
artifacts/
automation/recipes/
exports/
workspace-local model files
```

Confidentiality at rest therefore depends on the underlying OS/filesystem/storage protection chosen by the operator.

A whole-workspace backup likewise contains ordinary research data unless the backup destination/tool provides encryption.

## 5. `app.db` can contain sensitive research metadata/content

SQLite stores structured state including Profiles, Dataset metadata, Training information/logs, model-version metadata, experiments/evaluation payloads, event history, runtime operations, and lineage links.

Evaluation case payloads and operational messages can contain research/model behavior that should not be assumed public.

Do not upload a complete `app.db` as a bug attachment without reviewing its contents and the surrounding privacy requirements.

## 6. `agents_lineage_state.json` can be sensitive

Agents local state can contain custom branch names, current research position, archive/override state, undo/redo history, layout snapshots, and protected deletion metadata.

Even though it is not the semantic Dataset/Training/model database, those labels/history can disclose research plans or internal project structure.

Treat the file as workspace data, not harmless UI cache.

## 7. Logs are diagnostic data, not a privacy boundary

Production logging writes to:

```text
<workspace>/logs/persona_training_lab.log
```

with rotation.

The application error reporter can include:

- component;
- operation/error/correlation identity;
- exception type;
- exception message;
- a bounded traceback tail;
- structured context;
- diagnostic notice text.

This is useful evidence and can also be sensitive.

Review log excerpts before sharing them.

## 8. Structured context redaction is intentionally narrow

`ApplicationErrorReporter` redacts a structured context value when the **context key name** contains one of:

```text
password
secret
token
api_key
key_material
```

The replacement is:

```text
<redacted>
```

This filter applies to the explicit `context` mapping passed through `_safe_context(...)`.

It is not a general secret scanner.

## 9. Exception messages and tracebacks are not passed through that context-key redactor

The reporter stores `str(error)` as `exception_message` and records a traceback tail separately.

If an exception message/traceback itself contains credentials, private prompt/data text, paths, command fragments, or other sensitive values, the structured-context key filter does not automatically remove them.

Therefore:

> **Do not describe PTL logs/error events as automatically secret-safe.**

The operator/developer remains responsible for not embedding secrets into exception text where avoidable and for reviewing diagnostics before disclosure.

## 10. Error-report persistence is best-effort, not tamper-proof audit

Application error reporting deliberately avoids crashing the original workflow when logging/event persistence fails.

That is a resilience property.

It also means the normal application error path is not a security-grade append-only/tamper-evident audit ledger.

Repeated identical incidents can be throttled from SQLite event persistence within the duplicate window while still being sent to the normal logging path.

Use the error/event system for diagnosis, not as a cryptographically complete forensic ledger.

## 11. Correlation IDs are identifiers, not secrets

Identifiers such as:

```text
err_<...>
corr_<...>
op_<...>
```

help correlate incidents and operations.

They are not authentication tokens and should not be treated as proof of authorization or ownership.

Sharing a correlation ID may still expose project timing/context when combined with other data, but possession of the ID does not grant PTL privileges.

## 12. Local model files are trusted inputs

PTL's local model path can point inside or outside the workspace.

The file readiness probe checks only a shallow expected shape, including model config/tokenizer/weight markers.

It does not scan model files for malicious content, prove tensor/config integrity, or sandbox the libraries that parse/load them.

Use model files from a source whose integrity/provenance you are prepared to trust.

## 13. `trust_remote_code=True` is deliberately absent

Production model loading does not opt into Hugging Face:

```text
trust_remote_code=True
```

The release-policy test scans production model-loading calls and rejects this opt-in.

This narrows the model-loading trust surface by not intentionally authorizing repository-supplied Python through that Transformers mechanism.

It does **not** turn model/config/tokenizer/weight parsing into hostile-input-safe sandbox execution.

## 14. Model readiness is not model trust validation

A model probe result:

```text
found
```

means the expected local file categories are present under the current shallow contract.

It does not mean:

- the source is trustworthy;
- every file is structurally valid;
- model bytes match a known checksum;
- the model architecture is safe/compatible;
- enough memory exists;
- inference/Training will succeed.

Do not use `found` as a security approval badge.

## 15. Base-model identity is path-based in v1.0

Training stores the resolved base-model path/reference and re-probes the path at operation boundaries.

It does not persist a cryptographic digest of the entire base-model directory.

Replacing bytes under the same path can therefore change the effective model input without changing the stored path identity.

For controlled research, make model directories immutable by operating policy and record external revision/checksum information when exact identity matters.

## 16. Dataset files are external trusted data inputs

Dataset records can point to external `.jsonl` files.

Import does not copy the complete source into SQLite.

Validation/approval fingerprints the current bytes with SHA-256 and Training pins the approved hash, which protects against silent content substitution in the supported downstream workflow.

This integrity mechanism does not encrypt the Dataset or make arbitrary private content safe to publish.

## 17. Dataset SHA-256 is integrity identity, not confidentiality/authenticity by itself

The stored Dataset hash answers a narrow question:

> Are these bytes the same bytes PTL approved/pinned?

It does not by itself answer:

- who authored the data;
- whether the data is trustworthy/ethical/legal to use;
- whether it contains private material;
- whether another party signed/attested it;
- whether deleted bytes can be restored.

Keep provenance/authorship policy separate from content identity.

## 18. Profile Training fingerprints have a narrow meaning

Training fingerprints the exact rendered Profile Training representation that includes the current Training-relevant persona fields and deliberately excludes operator notes.

That hash protects run input identity for the supported contract.

It is not a signature of the human author, and it does not encrypt the Profile.

## 19. Runtime resource claims are cooperative coordination

PTL operations can declare resource claims:

```text
(resource_kind, resource_id, read|write)
```

Read/read can coexist. A write conflicts with another claim for the same resource identity.

This protects PTL workflows from known conflicting application operations.

The claims are **not** OS access-control rules.

## 20. Runtime claims do not police arbitrary filesystem/network effects

A runtime claim such as:

```text
workspace=<path>, access=read
```

does not make the process unable to write elsewhere.

PTL does not intercept arbitrary system calls to prove that a command/model/library touches only declared resources.

Resource claims express coordination intent inside PTL.

This distinction is especially important for Automation.

## 21. Runtime operation rows are not user-editable locks

The persisted `runtime_operations`, `runtime_operation_resources`, and `lineage_resource_links` participate in safety/integrity semantics.

Do not hand-edit/delete them to bypass a blocker.

An action being blocked because another operation owns a resource is a safety result, not a database defect.

Use the owning workflow's lifecycle/cancellation/recovery path.

## 22. Crash orphan recovery is not security rollback

At startup PTL can mark persisted active operations `abandoned` when their recorded owner PID is no longer alive.

That repairs PTL coordination state.

It does not roll back external filesystem/Automation side effects or prove that every process/resource effect from the interrupted work disappeared.

After abnormal termination, inspect the affected host state before retrying sensitive operations.

## 23. Automation is explicitly `trusted_host`

The only current Automation effect scope is:

```text
trusted_host
```

The executed process is a normal host process with the authority of the PTL OS account.

Automation is **not** a hostile-code sandbox.

This is the single most important Automation security boundary.

## 24. Automation does not provide container/syscall/filesystem/network isolation

Current Automation does not claim:

- container isolation;
- chroot/filesystem virtualization;
- syscall filtering;
- network isolation;
- a separate low-privilege user;
- automatic filesystem allowlisting;
- automatic rollback of host effects.

Process-tree ownership and runtime claims solve different problems.

## 25. Ad-hoc commands require explicit host-effects authorization

`run_command(...)` checks:

```text
host_effects_authorized
```

before constructing/launching the ad-hoc execution.

Without authorization the result is:

```text
host_effects_not_authorized
```

This acknowledgement prevents an accidental ad-hoc launch through the intended UI/service contract.

It does **not** reduce the permissions of an authorized command.

## 26. Trusted recipes have a different consent boundary

Recipe execution does not use the ad-hoc `host_effects_authorized` flag.

A recipe is treated as trusted executable input because it is a built-in recipe or a manifest present/imported into the trusted workspace recipe registry and deliberately selected for execution.

Therefore operators must review imported/workspace recipes as code-like executable configuration.

Do not infer that the ad-hoc authorization checkbox also protects recipe execution.

## 27. Recipe manifests are validated structurally, not signed

Workspace manifests must use:

```text
ptl:automation-recipe:v1
```

and satisfy ID/input/resource/command schema checks.

Structural validation prevents malformed contract fields from silently becoming execution state.

It does not authenticate the manifest author and does not cryptographically sign/content-address the recipe.

## 28. Recipe import copies the manifest, not a sealed executable bundle

Import validates and copies the manifest to the workspace recipe registry.

It does not automatically copy/hash every companion executable, script, model, or data file referenced by the recipe.

A valid imported manifest can therefore depend on mutable external files.

Preserve/review those dependencies separately when reproducibility or trust matters.

## 29. Recipe review and Run are not cryptographically bound

The UI can show a discovered recipe snapshot, while `run_recipe(recipe_id)` resolves the recipe again through the provider before execution.

v1.0 does not persist a signed/content hash binding the reviewed detail pane to the later execution request.

Avoid concurrent external modification of the trusted recipe registry between review and Run.

Refresh and re-review after edits.

## 30. `exec` mode and `shell` mode have different parsing boundaries

Automation distinguishes:

```text
exec
shell
```

`exec` requires non-empty argv and uses `shell=False` on POSIX.

`shell` requires a command string and deliberately enables shell semantics.

When shell mode is selected, quoting, expansion, pipelines, redirects, substitutions, and shell-specific behavior become part of the trusted command surface.

Prefer `exec` when shell semantics are unnecessary.

## 31. Absolute Automation working directories are allowed

An empty working directory defaults to the workspace.

A relative ad-hoc working directory is resolved under the workspace, but an absolute path remains an absolute host path.

Recipes can also resolve explicit working directories according to their source/manifest semantics.

The workspace therefore does not confine command CWD to itself.

## 32. Automation environment inheritance can expose process secrets to trusted commands

Recipe execution snapshots the current PTL process environment and adds:

```text
PTL_WORKSPACE=<resolved workspace>
```

Ad-hoc commands can either inherit the current environment or use only explicit overrides plus the forced PTL workspace marker.

If the PTL process environment contains credentials or private configuration, an inherited trusted command can receive those values.

Use environment inheritance deliberately.

## 33. `PTL_WORKSPACE` cannot be overridden by ad-hoc environment values

The environment builder applies user overrides and then sets:

```text
PTL_WORKSPACE=<actual resolved workspace>
```

This prevents a supplied environment mapping from redefining PTL's workspace marker to another value.

This is an identity/contract protection, not a general environment sandbox.

## 34. Automation audit stores environment **keys**, not values

The structured audit records sorted environment variable names.

It does not write their values into the normal Automation audit payload.

This reduces one obvious secret-exposure path.

Environment key names themselves can still reveal sensitive operational information, and child processes still receive actual values according to inheritance/overrides.

## 35. Automation audit does not persist plaintext command as the normal command record

The audit serializes the execution command snapshot, computes SHA-256, and stores:

```text
command_sha256
command_parts
```

rather than copying plaintext command content into the structured audit payload.

This is a privacy-conscious metadata choice.

It is not transitive executable provenance and it does not mean command content can never appear elsewhere (for example, UI state, child error text, external shell/process diagnostics, or user-captured output).

## 36. Automation stdout/stderr are not automatically secret-redacted

The process runner captures bounded stdout and stderr for the run result.

PTL does not automatically scan those streams for passwords/tokens/private Dataset content.

A trusted child command can print secrets it received from environment/files.

Review command output before sharing screenshots/log captures.

## 37. Structured Automation audit does not copy stdout/stderr payloads

The normal `ptl:automation-audit:v1` terminal record stores return state/truncation metadata but not stdout/stderr contents.

This reduces persistent audit exposure.

It does not make the command/output harmless: output remains visible in the Automation result/UI and may be captured elsewhere by the operator/toolchain.

## 38. Ad-hoc Automation audit fails closed before launch

For ad-hoc commands, `AutomationService.run_command(...)` returns:

```text
audit_unavailable
```

when no audit trail is configured.

When an audit trail is configured but the start audit write fails, execution returns:

```text
audit_failed
```

and the process is not launched.

This is a deliberate security/accountability property of the ad-hoc path.

## 39. Production recipe audit vs service-level recipe construction

Production composition wires one `AutomationAuditTrail(event_log_repo)` into `AutomationService`, so normal production recipe runs receive structured audit handling too.

However, the service-level hard `audit_unavailable` precondition exists specifically in `run_command(...)` for ad-hoc execution.

A separately constructed/test `AutomationService` with no audit trail can execute a recipe through the service contract.

Do not generalize the ad-hoc precondition into a universal type-level guarantee for every possible service construction.

## 40. Audit failure during an audited recipe/command start prevents process launch

When `_execute(...)` has an audit trail, it creates the runtime lease and writes the `started` audit record before invoking the process runner.

If that start record raises, the lease is failed and the result is `audit_failed` without calling the process runner.

This applies to production recipe/ad-hoc execution because production wiring supplies the audit trail.

## 41. Automation process containment is lifecycle containment

On POSIX, the runner creates a new session/process group and terminates the group on cancellation/timeout/finalization.

On Windows, it uses a Job Object with kill-on-close behavior around the launched helper/process tree.

This is designed to prevent ordinary descendant processes from escaping the one-shot Automation lifecycle.

It is not a security sandbox around what those descendants can do while alive.

## 42. Automation timeout/cancellation cannot undo already completed effects

If a command writes a file, sends a request, modifies a database, or performs another side effect before cancellation/timeout, terminating the process tree does not automatically reverse that effect.

Treat cancellation as process-lifecycle control, not transaction rollback.

Design trusted commands to be idempotent/transactional when the operation itself requires those properties.

## 43. Automation output bounds are a resource-safety boundary

Stdout and stderr are drained independently with:

```text
default retained limit: 1 MiB per stream
hard maximum:          64 MiB per stream
```

Excess bytes are still drained but not retained.

This reduces unbounded in-memory output growth and pipe deadlock risk.

It does not limit files/network output produced directly by the child process.

## 44. Built-in `workspace_health` is diagnostic, not a sandbox proof

The built-in recipe declares a workspace `read` runtime claim and is intended as a safe first Automation workflow.

That declaration participates in PTL runtime coordination.

Like all claims, it is not an OS-level proof that every library/syscall involved in executing the Python process can only read the workspace.

Use it as a product diagnostic, not as a general host security verifier.

## 45. Source-checkout integrity is part of the release boundary

The release gate binds audit evidence to one Git commit.

It refuses a dirty worktree before creating the audit report/running validation.

This prevents release evidence from claiming to validate commit X while actually executing unrecorded source edits.

A dirty-tree refusal is a source-integrity control, not a failed test result.

## 46. Hidden ignored source inputs are rejected by release policy

Release-policy tests inspect ignored/untracked content under:

```text
src/
tests/
tools/
```

and reject unexpected hidden runtime-affecting files outside narrow harmless debris exceptions.

This protects against a local editable checkout passing because of a helper/data/module absent from the recorded commit/clean clone.

Do not “fix” a release failure by hiding required source inputs with `.gitignore`.

## 47. Production model loaders are audited for remote-code opt-in

The release policy parses production Python calls and rejects explicit:

```python
trust_remote_code=True
```

This makes that model trust rule executable policy rather than documentation-only intent.

It remains one narrow check; it does not prove every dependency/file format is vulnerability-free.

## 48. The release gate is validation evidence, not formal security verification

Quick/full gates cover compilation, static checks, type policy, tests, i18n/source policies, codebase stats, and—in the full profile—mypy/build.

A green release gate does **not** claim formal proof against:

- malicious host code;
- unknown dependency vulnerabilities;
- all filesystem races;
- all denial-of-service cases;
- all privacy leaks;
- hostile model/data parser exploits;
- all platform-specific process behavior.

Security claims remain limited to implemented/audited contracts.

## 49. Dependency trust remains outside PTL's own code boundary

PTL relies on packages such as PySide6, psutil, and optional Torch/Transformers/training dependencies.

Installing/running those packages executes third-party code inside the same Python/OS-account trust environment.

`uv.lock` helps make the resolved source environment reproducible, but dependency provenance/vulnerability management is still a supply-chain responsibility rather than a PTL sandbox feature.

Do not interpret local-only application design as “no third-party code trust.”

## 50. UI localization is not an authorization boundary

Localized labels/status descriptions are presentation.

Machine semantic codes/IDs drive application contracts.

Do not build security/recovery automation by matching a Russian/English/Spanish/Arabic rendered sentence when a semantic status/result/diagnostic code exists.

Changing UI language does not change the authority of an Automation command, runtime claim, model file, or Dataset approval hash.

## 51. Visible titles are not stable security/resource identity

Agents/Training/Datasets/Profiles can display human-readable titles while persistence/runtime safety uses stable IDs where available.

Two entities can share a visible title.

When diagnosing access/blocking/provenance, use stable IDs and resource claims rather than relying on labels.

## 52. Agents custom branches are not filesystem/model isolation

A custom Agents branch is local research organization.

Creating/renaming/archiving/deleting it does not clone/sandbox model bytes or Dataset files.

Runtime resource links help prevent unsafe local branch deletion while real resources are in use; they do not isolate those real resources from other OS processes.

## 53. Protected Agents deletion history is integrity machinery

Delete/Undo/Redo preserve/restore resource-link metadata and reacquire runtime deletion leases where required.

This prevents history actions from becoming a bypass around current PTL runtime safety.

It is not a secure erase mechanism.

Deleting a local branch does not securely wipe referenced Training/model/Dataset artifacts from disk.

## 54. “Delete” and “archive” do not imply secure erasure

Across PTL, removal from a UI/local state should not be assumed to overwrite underlying storage sectors, backups, WAL/history, external files, or generated artifacts.

v1.0 does not claim cryptographic secure deletion.

When regulated/private-data destruction requirements matter, apply appropriate OS/storage procedures outside the normal PTL UI contract.

## 55. Backups inherit the sensitivity of the workspace

A backup can include database content, local Agents research state, generated models, logs, recipes, paths, and evaluation data.

PTL does not automatically encrypt/sign whole-workspace backups.

Use backup tooling/storage policy appropriate to the confidentiality/integrity requirements of the research.

## 56. Do not place secrets in recipe manifests unless you intend them to be ordinary workspace files

Recipe manifests are ordinary JSON files in the workspace registry and are included in normal whole-workspace backups.

The manifest schema is not a secret-store format.

Prefer runtime/environment/OS secret management appropriate to the command when secrets are required, while remembering inherited environment values are visible to the trusted child process.

## 57. Do not use command-line/exception text as a secret channel

Even though structured Automation audit hashes command snapshots instead of storing plaintext, command text can still be exposed through UI/process/tooling pathways outside that audit record.

Likewise, application exception messages/tracebacks can be logged.

Treat command lines and exception strings as observable diagnostic material, not protected secret storage.

## 58. Network effects of trusted-host commands are governed by the host, not PTL

Automation does not provide network isolation.

A trusted host command can use whatever network access the OS account/process environment and host firewall/network policy permit.

Runtime resource claims do not represent network ACLs.

Apply host/network controls when a command must be offline or restricted.

## 59. PTL's local-first design is not equivalent to an air gap

The application stores/operates on local workspace state and does not rely on a remote SaaS service as its core persistence model.

That architectural property alone does not guarantee that every installed dependency, operator command, external tool, or host process has no network capability.

An air-gapped requirement must be enforced and verified at the host/environment/network boundary.

## 60. Threat assumptions for safe normal operation

The current v1.0 contract is suitable when these assumptions are reasonable:

1. the OS account/device is trusted and appropriately protected;
2. model files and external Dataset inputs come from sources the operator is willing to process locally;
3. workspace Automation recipes and ad-hoc commands are reviewed as trusted host execution;
4. external tools/dependencies are managed as part of the host/software supply chain;
5. users with filesystem access to the workspace are allowed to see/modify its unencrypted research state according to OS policy;
6. PTL runtime claims coordinate cooperating PTL workflows rather than defending against malicious local processes.

If these assumptions do not hold, additional isolation outside PTL is required.

## 61. What PTL v1.0 does not claim to defend against

PTL v1.0 does not claim protection against an attacker who already has equivalent/higher privileges on the same OS account/host.

It also does not claim:

- hostile-code sandboxing for Automation;
- hostile model-file parsing sandboxing;
- encrypted workspace/database storage;
- built-in secret-vault semantics;
- network isolation;
- signed Automation manifests;
- secure deletion;
- distributed authorization/locking;
- cryptographic whole-workspace backup signing;
- complete automatic secret redaction from logs/output;
- formal proof of dependency security.

These are explicit boundaries, not missing footnotes.

## 62. Operator security checklist before sensitive work

Before using PTL with sensitive research data:

1. protect the OS account/device/storage appropriately;
2. verify the actual workspace path and its filesystem permissions;
3. understand that `app.db`, logs, Agents JSON, recipes, and artifacts are ordinary local files;
4. trust/verify local model and Dataset sources;
5. avoid embedding secrets in Profiles/Datasets/loggable exception text unless required by the research;
6. review Automation recipes/ad-hoc commands before execution;
7. disable ad-hoc environment inheritance when a trusted command does not need the parent environment;
8. treat shell mode as shell execution, not argv-safe exec mode;
9. review diagnostic/output data before sharing;
10. encrypt/protect backups according to data sensitivity.

## 63. Security-relevant bug-report evidence

When reporting a security/trust-boundary defect, include only the minimum reviewed evidence required to reproduce it:

```text
PTL commit/version
OS/Python
workspace location type (not necessarily private full path)
feature/workflow
semantic result/error code
operation/correlation ID when safe
whether input was model/Dataset/recipe/ad-hoc command
whether Automation used exec or shell
whether environment inheritance was enabled
expected vs actual trust-boundary behavior
```

Do not attach live credentials, full environment dumps, private workspaces, raw model weights, or sensitive Dataset/model responses unless an explicitly secure disclosure channel requires them.

## 64. Security findings must change either code or contract

If code review discovers a real behavior that weakens an existing documented guarantee, it is a release defect.

Resolve it by either:

- fixing the implementation and adding regression evidence; or
- narrowing the product/documentation guarantee when the behavior is intentional and acceptable.

Do not hide a trust boundary behind vague wording such as “safe”, “isolated”, or “protected” when the implementation only provides coordination, hashing, bounded output, or best-effort redaction.

## 65. Developer invariants

Security-sensitive changes must preserve these rules unless the product contract is deliberately revised:

1. Automation `trusted_host` must never be described as sandboxed execution;
2. resource claims remain coordination semantics, not OS permissions;
3. ad-hoc commands require explicit host-effects authorization;
4. production ad-hoc execution fails closed when its audit path is unavailable/fails at start;
5. production model loaders must not silently opt into `trust_remote_code=True`;
6. release validation remains tied to a clean recorded Git commit;
7. hidden ignored runtime-affecting inputs must not become release dependencies;
8. Dataset/Profile hashes are described only for their implemented integrity identities;
9. base-model path identity must not be documented as complete content-addressed provenance;
10. log/audit redaction claims must not exceed the actual fields passed through redaction;
11. process containment must not be described as filesystem/network isolation;
12. workspace/backup confidentiality must not be implied without an actual encryption layer;
13. recipe validation/version fields must not be described as cryptographic signing;
14. security documentation must be updated whenever trust/authorization/audit/isolation behavior changes.

## Next steps

- Diagnose incidents safely: [Troubleshooting](troubleshooting.md)
- Backup/restore/reset: [Backup, Reset & Recovery](backup-reset-recovery.md)
- Workspace/data ownership: [Workspace & Storage](workspace-and-storage.md)
- Local model trust: [Local Models](local-models.md)
- Automation trust/process/audit details: [Automation](../user-guide/automation.md)
- Runtime coordination architecture: [Runtime resource safety](../architecture/runtime-resource-safety.md)
- Stable release promises/non-goals: [v1.0 Product Contract](../reference/v1-product-contract.md)
