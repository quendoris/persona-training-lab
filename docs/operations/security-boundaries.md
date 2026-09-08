# Security, Trust & Privacy Boundaries

This guide defines the security/trust/privacy boundaries that Persona Training Lab v1.0 actually implements.

It is not a generic security checklist and it does not infer guarantees from UI wording. The statements here follow current composition, persistence, model-loading, Dataset/Training, Automation, runtime-coordination, diagnostic, shell/settings, and release-policy code.

The central rule is:

> **PTL coordinates trusted local research workflows inside the authority of the current operating-system account. It is not a sandbox, privilege boundary, encrypted secret vault, or hostile-input execution environment.**

For operational failures and evidence handling, read [Troubleshooting & Diagnostic Evidence](troubleshooting.md). For backup/storage boundaries, read [Backup, Reset & Recovery](backup-reset-recovery.md), [Workspace & Storage](workspace-and-storage.md), and the [Workspace layout reference](../reference/workspace-layout.md).

## 1. Security model at a glance

| Boundary | What PTL currently does | What it does **not** mean |
|---|---|---|
| OS account | Runs PTL and trusted-host child processes with current-user authority | PTL is not a lower-privilege sandbox |
| Workspace ownership | Keeps normal research/workflow mutable state under a stable root | Workspace is not an access-control sandbox |
| External presentation stores | Uses QSettings + a user-home key-binding JSON for shell/input configuration | These stores are not encrypted/secret merely because they are outside the workspace |
| Runtime claims | Coordinates read/write use of known PTL resources | Claims do not constrain syscalls/files/network |
| Model loading | Does not opt into `trust_remote_code=True` | Model parsing is not hostile-input sandboxing |
| Dataset approval | SHA-256 fingerprints approved JSONL bytes | Hashing is not confidentiality/authorship/signing |
| Training pinning | Pins Profile representation + Dataset SHA-256 | Complete base-model bytes are not content-addressed |
| Automation authorization | Ad-hoc host commands require explicit host-effect authorization | Authorization does not reduce child privileges |
| Automation audit | Records structured execution metadata | Audit is not prevention/rollback and not a secret vault |
| Process containment | Owns/terminates ordinary descendant process trees | Containment is not filesystem/network isolation |
| Error context redaction | Recursively redacts selected sensitive structured-context key names through bounded mappings/collections | Exception text/traceback and arbitrary values are not comprehensively secret-scrubbed |
| Release gate | Binds validation evidence to a clean recorded source state | Green validation is not formal proof against every vulnerability |

Keep these concepts separate. Most dangerous overclaims come from treating one narrow boundary as if it provided another.

## 2. The OS account is the primary authority boundary

PTL is a local desktop process. Files it can read/write, libraries it loads, and trusted child commands it executes are ultimately constrained by the authority of the OS account that launched it.

PTL v1.0 does not create a separate low-privilege identity for model loading, Dataset parsing, Training, evaluation, or Automation.

If stronger isolation is required, use OS account separation, filesystem permissions, disk encryption, network controls, containers/VMs, or other host controls appropriate to the threat model.

## 3. Workspace ownership is organization, not isolation

Typical workspace state is:

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

This prevents ordinary runtime state from silently depending on repository/process CWD.

It does not prevent PTL or an authorized trusted process from accessing external Dataset/model/tool paths allowed by the OS account.

## 4. Security/privacy must include state outside the workspace

Two PTL presentation/configuration stores are outside the workspace:

```text
Qt QSettings
  -> shell geometry
  -> dock state
  -> last workspace

~/.persona_training_lab/key_bindings.json
  -> keyboard mappings
  -> Agents mouse mappings
```

Security/privacy statements about “the workspace” do not automatically cover those stores.

They are ordinary local configuration state governed by the host/platform. PTL does not add application-level encryption to either.

## 5. Key-binding JSON is not a secret store

`~/.persona_training_lab/key_bindings.json` is readable JSON containing input mappings and format version state.

It can reveal operator customization/interaction preferences. It does not normally contain research content by design, but it must not be treated as encrypted or inherently public.

The manager writes through a temporary sibling file followed by replace. That is a file-write integrity/recovery technique, not confidentiality or authentication.

## 6. Qt `QSettings` state is platform configuration

Shell geometry/dock/current-workspace values are stored through the platform Qt settings backend under the PTL organization/application identity.

PTL does not define one portable encrypted file for this state.

The exact native backend/location is platform-dependent. Protect it according to the host account/platform policy when shell/session metadata matters.

## 7. Data at rest is ordinary host state

PTL v1.0 does not add product-level encryption to:

```text
app.db
agents_lineage_state.json
logs/
artifacts/
automation/recipes/
exports/
workspace-local model files
~/.persona_training_lab/key_bindings.json
Qt QSettings shell state
```

Nor does it encrypt arbitrary external Dataset/model/Automation dependencies.

Confidentiality at rest therefore depends on the OS/filesystem/storage/backup controls chosen by the operator.

## 8. `app.db` can contain sensitive research data

SQLite stores Profiles, Dataset metadata/paths/hashes, Training state/logs, model-version metadata, experiments/evaluation payloads, event history, runtime operations, lineage links, and Style/localization preferences.

Evaluation payloads and operational messages can contain model behavior/research data that should not be assumed public.

Do not attach a complete database to a bug report without review.

## 9. Agents local JSON can expose research structure

`agents_lineage_state.json` can contain custom branches, current research position, archive/override state, undo/redo history, layouts, and protected-deletion metadata.

It is not “just cache”. Treat it according to the sensitivity of the research organization/history it describes.

## 10. Logs are evidence, not a privacy boundary

Production rotating logs live under:

```text
<workspace>/logs/persona_training_lab.log
```

Diagnostics can contain component names, IDs, exception type/message, bounded traceback text, structured context, paths, notices, and workflow detail.

Review log excerpts before sharing them.

## 11. Structured context redaction is recursive but key-name based

`ApplicationErrorReporter._safe_context(...)` recursively walks structured mappings and common collection containers before persistence/logging. When a mapping key name contains one of the current sensitive tokens, its value is replaced with:

```text
<redacted>
```

Current key-name tokens are:

```text
password
secret
token
api_key
key_material
authorization
cookie
credential
private_key
access_key
```

The traversal is bounded to avoid pathological diagnostic structures. Revisited cyclic containers are represented by a cycle marker and over-deep structures by a truncation marker rather than allowing diagnostic serialization to recurse indefinitely.

The filter is still **key-name based**. It does not inspect arbitrary string values for credential-like content. A password placed under an innocuous key such as `value` can therefore still be logged.

Do not describe this as a general secret scanner or data-loss-prevention system.

## 12. Exception messages and tracebacks bypass that key-name filter

Captured errors store:

```text
exception_message = str(error)
traceback = bounded traceback tail
```

separately from the structured-context redactor.

If exception text contains credentials, private prompts/data, paths, command fragments, or other sensitive material, the structured key-name filter does not remove it.

Therefore:

> **PTL logs/error events are not automatically secret-safe.**

## 13. Error/event persistence is best-effort, not tamper-evident audit

Application error event persistence is deliberately allowed to fail without replacing the original workflow failure.

Repeated identical incidents can also be throttled from SQLite event persistence inside a duplicate window while still reaching the normal logging path.

This improves resilience/storage behavior; it means the ordinary error/event system is not a cryptographically complete append-only forensic ledger.

## 14. Error/correlation/operation IDs are not credentials

Identifiers such as:

```text
err_<...>
corr_<...>
op_<...>
```

exist for correlation/diagnosis. Possessing one does not authenticate a user, authorize an operation, or prove ownership.

See [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md) for exact current shapes.

## 15. Local model files are trusted inputs

The local model path can point inside or outside the workspace.

The readiness probe checks a shallow expected file shape. It does not prove provenance, scan for malicious content, verify every tensor/config/tokenizer file, or guarantee runtime compatibility/resource availability.

Use model files from sources whose integrity/provenance you are prepared to trust.

## 16. `trust_remote_code=True` is deliberately prohibited in production loaders

Release policy audits production model-loading calls and rejects explicit:

```python
trust_remote_code=True
```

This narrows one Transformers remote-code execution surface.

It does not turn model/config/tokenizer/weight parsing or third-party libraries into hostile-input-safe sandbox execution.

## 17. Model readiness is not trust approval

A local-model status:

```text
found
```

means expected file categories were found under the shallow readiness contract.

It does not mean the model is signed, trusted, compatible, complete, memory-safe to load, or guaranteed to generate successfully.

## 18. Base-model identity is path/reference based in v1.0

Training stores/resolves the base-model path/reference but does not persist a digest of every file in the base-model directory.

Replacing bytes under the same path can therefore change effective model input without changing the stored path identity.

For controlled research, preserve external revision/checksum provenance and keep intended model directories immutable by operating policy.

## 19. Dataset files are external data inputs

Import stores a path; it does not copy source bytes into SQLite.

Validation/approval computes SHA-256 over current JSONL bytes, and Training pins the approved digest.

This protects supported downstream content identity. It does not encrypt the Dataset, attest authorship/ethics/legal status, or recover deleted bytes.

## 20. Dataset SHA-256 has narrow integrity meaning

The stored hash answers:

> Are these bytes identical to the bytes PTL approved/pinned?

It does not answer who authored them, whether they are private, whether they are trustworthy, or whether another party signed them.

Keep byte identity separate from provenance/authorship/confidentiality.

## 21. Profile Training fingerprints have narrow meaning

Training hashes the exact Training-relevant Profile representation. Operator notes are excluded from that representation by the current input contract.

The digest protects run-input identity for the supported workflow. It is not author authentication and does not encrypt the Profile.

## 22. Runtime resource claims are cooperative coordination

Runtime claims use:

```text
(resource_kind, resource_id, read|write)
```

Read/read can coexist; a competing write conflicts for the same semantic resource key.

Deletion safety can treat any active claim as a blocker.

Claims coordinate cooperating PTL workflows. They are not OS ACLs.

## 23. Runtime claims do not police arbitrary effects

A declared claim does not constrain syscalls or prove that model/library/Automation code only accesses declared paths/resources.

Claims express application coordination intent and enforce PTL's own supported conflict checks.

This distinction is critical for Automation.

## 24. Runtime rows are not user-editable lock bypasses

`runtime_operations`, `runtime_operation_resources`, and `lineage_resource_links` participate in safety/integrity behavior.

Do not hand-edit/delete them to make a blocked action proceed.

Resolve/cancel/recover the owning workflow instead.

## 25. Orphan recovery is not security rollback

Startup can mark active operations `abandoned` when their recorded owner PID is no longer alive.

That repairs coordination state. It does not undo external filesystem/network effects or prove all descendant effects/processes disappeared after abnormal termination.

## 26. Automation effect scope is explicitly `trusted_host`

The current execution effect scope is:

```text
trusted_host
```

Automation runs a normal host process with the authority available to the PTL OS account.

Automation is **not** a hostile-code sandbox.

## 27. Automation does not provide host isolation primitives

Current Automation does not claim:

- container isolation;
- chroot/filesystem virtualization;
- syscall filtering;
- network isolation;
- a separate low-privilege account;
- automatic filesystem allowlisting;
- automatic rollback of host effects.

Process-tree ownership and runtime claims solve different problems.

## 28. Ad-hoc commands require explicit host-effects authorization

`AutomationService.run_command(...)` checks:

```text
host_effects_authorized
```

before constructing/executing the request.

Without it, the stable result code is:

```text
host_effects_not_authorized
```

This is explicit user-intent acknowledgement through the intended service/UI contract. It does not reduce command privileges after authorization.

## 29. Recipe consent/trust is different from ad-hoc authorization

`run_recipe(...)` does not use the ad-hoc `host_effects_authorized` flag.

A recipe is trusted executable configuration because it is built-in or present/imported into the workspace recipe registry and then selected for execution.

Operators must review workspace/imported recipes as code-like trusted inputs.

Do not imply that an ad-hoc authorization checkbox also gates recipes.

## 30. Recipe manifests are structurally validated, not signed

Workspace manifests use:

```text
ptl:automation-recipe:v1
```

with validated recipe/input/resource/command fields.

Structural validation rejects malformed contract state. It does not authenticate the author or cryptographically sign/content-address the recipe/dependencies.

## 31. Current recipe execution is `exec`, not shell

The current filesystem recipe schema stores a command array and `run_recipe(...)` constructs:

```text
AutomationExecution(mode="exec")
```

Current recipe manifests therefore do not select shell-mode parsing.

Ad-hoc `AutomationCommandRequest` can select either:

```text
exec
shell
```

When ad-hoc shell mode is selected, quoting/expansion/pipelines/redirects/substitution become part of the trusted shell surface.

Prefer `exec` when shell semantics are unnecessary.

## 32. Recipe import copies a manifest, not a sealed bundle

Import validates/loads the selected manifest and copies it into the workspace registry.

It does not automatically copy or hash every external executable, script, model, or data dependency the command can use.

A valid manifest can therefore depend on mutable external files.

## 33. Recipe review and execution are not cryptographically bound

The UI can show one discovered recipe snapshot while `run_recipe(recipe_id)` resolves the recipe again before execution.

v1.0 does not persist a signed hash binding the reviewed detail pane to the later Run request.

Avoid concurrent external mutation; refresh/re-review after recipe edits.

## 34. Automation working directories are not workspace confinement

Empty ad-hoc CWD defaults to the workspace. Relative ad-hoc paths resolve under the workspace. Absolute paths remain absolute host paths.

Recipe relative working directories resolve according to recipe source-path semantics.

The command CWD therefore does not imply filesystem confinement.

## 35. Environment inheritance can expose process secrets

Recipe execution snapshots the current PTL process environment and forces:

```text
PTL_WORKSPACE=<resolved workspace>
```

Ad-hoc commands may inherit the parent environment or use only explicit overrides plus the forced PTL workspace marker.

If the parent environment contains credentials/private configuration, an inherited trusted process receives them.

Use inheritance deliberately.

## 36. `PTL_WORKSPACE` cannot be overridden by ad-hoc overrides

The environment builder applies supplied overrides and then sets `PTL_WORKSPACE` to the actual resolved workspace.

This protects the marker's meaning. It is not a general environment sandbox.

## 37. Automation audit stores environment keys, not values

The structured audit records sorted environment variable **names** and does not copy values into the normal audit payload.

That reduces one obvious persistence exposure, but key names can still reveal operational context and child processes still receive the actual inherited/overridden values.

## 38. Automation audit hashes the command snapshot

The audit serializes the command snapshot and stores:

```text
command_sha256
command_parts
```

rather than plaintext command content in the normal structured command metadata.

This is not transitive executable provenance. Command content can still be exposed through UI/process/errors/external tooling/operator captures.

## 39. stdout/stderr are not secret-redacted

The runner captures bounded stdout/stderr into the run result.

PTL does not scan those streams for passwords/tokens/private data.

A trusted command can print any value it can access. Review output before sharing it.

## 40. Structured Automation audit omits stdout/stderr bodies

`ptl:automation-audit:v1` terminal records keep return/truncation/terminal metadata, not stream contents.

This reduces persistent audit exposure but does not make the output itself safe/public.

## 41. Ad-hoc audit path fails closed before launch

For ad-hoc execution:

```text
no audit trail -> audit_unavailable
start audit write failure -> audit_failed
```

The process is not launched in those conditions.

This is a deliberate accountability property of the ad-hoc service path.

## 42. Production recipe audit is wiring-dependent

Production composition supplies `AutomationAuditTrail(event_log_repo)`, so normal production recipe runs are audited.

The service-level hard `audit_unavailable` precondition exists specifically in `run_command(...)`. A separately constructed `AutomationService` without an audit trail can execute a recipe.

Do not elevate production wiring into an unconditional type-level guarantee for arbitrary test/custom composition.

## 43. Audit start failure prevents audited process launch

When `_execute(...)` has an audit trail, it creates the runtime lease and records `started` before calling the process runner.

If that audit write raises, the lease is failed and the result is:

```text
audit_failed
```

without launching the process.

## 44. Terminal audit failure cannot undo already-run host effects

After a child process has executed, a failure while writing its terminal audit record can produce `audit_failed` and fail the lease.

It cannot reverse filesystem/network/other effects the process already completed.

Audit success/failure and host transactionality are separate concepts.

## 45. Process containment is lifecycle containment

On POSIX, Automation starts a new session/process group and terminates the group on cancellation/timeout/finalization.

On Windows, the runner uses a Job Object with kill-on-close semantics around the helper/process tree.

This owns ordinary descendants for lifecycle cleanup. It does not restrict what those descendants can do while running.

## 46. Cancellation/timeout do not roll back side effects

Killing the process tree cannot automatically undo a file write, network request, database mutation, or other effect already performed.

Design trusted commands to be idempotent/transactional when their own operation requires those properties.

## 47. Output bounds are resource-safety controls

Stdout/stderr retained limits are:

```text
default: 1 MiB per stream
hard max: 64 MiB per stream
```

Excess data is drained but not retained, reducing memory growth/pipe blockage risk.

These bounds do not limit files or network output created directly by the child.

## 48. Built-in `workspace_health` is diagnostic, not a sandbox proof

The built-in recipe declares a workspace read claim and runs through the trusted-host execution path.

The claim coordinates PTL resources. It does not prove every syscall/library can only read the workspace.

## 49. Release validation is tied to recorded source state

The release gate refuses a dirty worktree before producing release-audit evidence/running the gated validation sequence.

This prevents a report for commit X from silently validating unrecorded source edits.

A dirty-tree refusal is a source-integrity/configuration refusal, not a failing pytest/Ruff result.

## 50. Ignored hidden source inputs are release defects

Release-policy tests inspect ignored/untracked material under:

```text
src/
tests/
tools/
```

and reject unexpected runtime-affecting hidden inputs outside narrow debris exceptions.

Do not make a required source/runtime input “pass” by hiding it in `.gitignore`.

## 51. Release policy audits remote-code opt-in

Production model-loader calls are parsed and explicit `trust_remote_code=True` is rejected.

This is executable policy for one trust boundary. It is not formal proof that all model/dependency parsing is vulnerability-free.

## 52. Green release gates are evidence, not formal verification

Quick/full gates cover compilation, static/test/i18n/source policies and additional full-release checks.

They do not formally prove absence of malicious host code, dependency vulnerabilities, every race/DoS/privacy leak, hostile parser exploits, or all platform-specific process behavior.

Security claims remain limited to implemented/audited contracts.

## 53. Third-party dependencies remain trusted code

PTL relies on PySide6, psutil, and optional Torch/Transformers/training dependencies.

Installing/running them executes third-party code in the same host/Python authority boundary.

Locking dependencies improves reproducibility; it is not a sandbox or complete supply-chain security solution.

## 54. Localization is not an authorization boundary

Localized labels are presentation. Canonical statuses/result codes/IDs carry machine meaning.

Do not build security/recovery automation by matching rendered Russian/English/Spanish/Arabic text when a semantic code exists.

Changing UI language does not change Automation authority, runtime claims, model trust, or Dataset integrity semantics.

## 55. Visible titles are not stable security identity

Profiles/Datasets/Training/model versions/Agents expose human-readable titles while persistence/runtime safety uses stable IDs/resource identities where available.

Titles may collide or change. Use stable IDs and explicit claims for blockers/provenance/safety logic.

## 56. Agents custom branches are organization, not data isolation

Creating/renaming/archiving/deleting a local Agents branch does not clone/sandbox referenced model/Dataset/Training bytes.

Runtime links guard supported destructive graph operations while resources are in use; they do not isolate real resources from other host processes.

## 57. Protected history is integrity machinery, not secure erasure

Agents delete/Undo/Redo preserve/restore resource-link metadata and reacquire runtime deletion leases where required.

This prevents history actions from bypassing current PTL runtime safety.

It does not securely wipe referenced artifacts or storage sectors.

## 58. Delete/archive does not imply secure deletion

Across PTL, removing something from a UI/local state does not imply overwriting WAL/history/backups/external files/artifacts/storage media.

v1.0 does not claim cryptographic secure deletion. Apply OS/storage destruction procedures when required by policy.

## 59. Backups inherit all contained sensitivity

Workspace backups can contain database records, Agents state, generated models, logs, recipes, paths, and evaluation data.

Separately preserved key-binding/QSettings state can reveal operator personalization/session layout.

PTL does not automatically encrypt/sign these backup sets.

## 60. Recipe manifests are not secret stores

Recipe manifests are ordinary JSON in the workspace registry and are included in normal workspace backups.

Do not place secrets there merely because structured Automation audit does not persist plaintext commands/environment values.

Use appropriate host/runtime secret management while remembering trusted child processes can access values deliberately provided/inherited.

## 61. Command lines and exception text are observable diagnostic material

Do not treat them as secret channels.

Command text can appear through UI/process/external tooling even though structured audit stores a hash; exception messages/tracebacks can enter logs/event payloads.

## 62. Network effects are governed by the host

Automation does not provide network isolation. Trusted commands can use network access allowed by the host account/firewall/network policy.

Runtime claims are not network ACLs.

## 63. Local-first is not an air gap

PTL uses local persistence/processing as its core architecture, but dependencies, trusted commands, external tools, and the host can still possess network capability.

An air-gap requirement must be enforced and verified outside PTL at the host/environment/network boundary.

## 64. Safe normal-operation assumptions

The current contract assumes:

1. the host/OS account is trusted and appropriately protected;
2. model and Dataset inputs come from sources the operator is willing to process locally;
3. recipes/ad-hoc commands are reviewed as trusted host execution;
4. dependencies/external tools are part of the trusted software supply chain;
5. users with filesystem access are allowed to see/modify ordinary local PTL state according to OS policy;
6. runtime claims coordinate cooperating PTL workflows rather than defend against malicious local processes.

If these assumptions do not hold, additional external isolation is required.

## 65. PTL v1.0 non-claims

PTL v1.0 does not claim:

- defense against an attacker already holding equivalent/higher host-account privileges;
- hostile-code sandboxing for Automation;
- hostile model-file parsing sandboxing;
- encrypted workspace/database/QSettings/key-binding storage;
- built-in secret-vault semantics;
- network isolation;
- signed Automation manifests;
- secure deletion;
- distributed authorization/locking;
- cryptographic whole-backup signing;
- complete automatic secret redaction from logs/output;
- formal proof of dependency security.

These are explicit boundaries.

## 66. Operator checklist before sensitive work

1. protect the host account/device/storage appropriately;
2. verify workspace location/permissions;
3. remember that workspace files, key bindings, and QSettings are ordinary local state;
4. trust/verify model and Dataset sources;
5. avoid placing secrets into loggable exception/command/config text unless required;
6. review recipes/ad-hoc commands before execution;
7. disable ad-hoc environment inheritance when unnecessary;
8. treat shell mode as shell execution;
9. review diagnostics/output before sharing;
10. protect/encrypt backups according to contained data sensitivity.

## 67. Security-relevant bug-report evidence

Provide only reviewed minimum evidence:

```text
PTL commit/version
OS/Python
workspace location type
feature/workflow
semantic result/error code
operation/correlation ID when safe
input class: model/Dataset/recipe/ad-hoc/settings
Automation mode when relevant
whether environment inheritance was enabled
expected vs actual trust-boundary behavior
```

Do not attach live credentials, complete environment dumps, private workspaces, raw weights, or sensitive responses unless a specifically secure disclosure channel requires them.

## 68. Security findings must change code or contract

If audited code weakens an existing documented guarantee, treat it as a release defect.

Either fix implementation + regression evidence or deliberately narrow the guarantee when the behavior is intended/acceptable.

Do not hide a boundary behind vague terms like “safe”, “isolated”, or “protected” when implementation only supplies coordination, hashing, bounded output, replacement, or best-effort redaction.

## 69. Developer invariants

Security-sensitive changes must preserve these rules unless the product contract is deliberately revised:

1. Automation `trusted_host` is never described as sandboxed execution;
2. runtime claims remain coordination semantics, not OS permissions;
3. ad-hoc commands require explicit host-effects authorization;
4. production ad-hoc execution fails closed when its audit path is unavailable/fails at start;
5. current recipe execution is documented as exec-array execution unless the recipe schema/service deliberately adds shell mode;
6. production model loaders must not silently opt into `trust_remote_code=True`;
7. release validation remains tied to a clean recorded Git commit;
8. hidden ignored runtime-affecting inputs do not become release dependencies;
9. Dataset/Profile hashes are described only for their implemented integrity identities;
10. base-model path identity is not documented as complete content-addressed provenance;
11. redaction claims do not exceed the recursive bounded key-name filtering applied by `_safe_context`; exception messages, tracebacks and arbitrary non-key content remain outside that guarantee;
12. process containment is not described as filesystem/network isolation;
13. workspace, QSettings, key-binding and backup confidentiality are not implied without encryption;
14. recipe validation/version fields are not described as cryptographic signatures;
15. external presentation stores remain in the security map while code stores them outside the workspace;
16. security documentation is updated whenever trust/authorization/audit/isolation/persistence behavior changes.

## Next steps

- Diagnose incidents safely: [Troubleshooting](troubleshooting.md)
- Backup/restore/reset: [Backup, Reset & Recovery](backup-reset-recovery.md)
- Workspace/data ownership: [Workspace & Storage](workspace-and-storage.md)
- Exact store/path map: [Workspace layout reference](../reference/workspace-layout.md)
- Machine codes/IDs: [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md)
- Input configuration: [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md)
- Local model trust: [Local Models](local-models.md)
- Automation trust/process/audit: [Automation](../user-guide/automation.md)
- Runtime coordination architecture: [Runtime resource safety](../architecture/runtime-resource-safety.md)
- Stable release promises/non-goals: [v1.0 Product Contract](../reference/v1-product-contract.md)
