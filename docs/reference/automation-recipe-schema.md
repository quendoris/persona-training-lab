# Automation Recipe Manifest Reference

> **Scope:** current `ptl:automation-recipe:v1` workspace-recipe manifest and discovery/import/rendering contract.
>
> For execution, process containment, runtime leases and trust boundaries, read [Automation architecture](../architecture/automation.md) and the [Automation user guide](../user-guide/automation.md).

## 1. Registry and file identity

Workspace recipes are discovered recursively below:

```text
<workspace>/automation/recipes/
```

Only files matching:

```text
*.ptl-recipe.json
```

are candidates.

The required schema marker is:

```json
"schema": "ptl:automation-recipe:v1"
```

A manifest with another schema is rejected as invalid discovery input.

PTL also supplies built-in recipes independently of filesystem manifests. The current built-in recipe is:

```text
workspace_health
```

## 2. Root object

The JSON root must be an object.

A compact valid example is:

```json
{
  "schema": "ptl:automation-recipe:v1",
  "id": "example.echo",
  "version": "1.0.0",
  "title": "Echo",
  "description": "Trusted-host example",
  "command": ["{python}", "-c", "print('{message}')"],
  "tags": ["diagnostic", "example"],
  "inputs": [
    {
      "name": "message",
      "required": true,
      "default": "",
      "description": "Text to print"
    }
  ],
  "outputs": [
    {
      "name": "stdout",
      "description": "Captured stdout"
    }
  ],
  "resources": [
    {
      "kind": "workspace",
      "id": "{workspace}",
      "access": "read"
    }
  ],
  "working_directory": "{workspace}",
  "timeout_seconds": 30
}
```

Unknown root fields are not currently rejected by the provider. They are ignored unless another layer explicitly consumes them. Do not use ignored fields as if they were enforced policy.

## 3. Field table

| Field | Required | Current parser semantics |
|---|---:|---|
| `schema` | yes | must equal `ptl:automation-recipe:v1` |
| `id` | yes | non-empty; case-folded; regex-constrained |
| `version` | yes | non-empty text; no semantic-version parser is enforced |
| `title` | no | trimmed text; defaults to recipe ID |
| `description` | no | trimmed text; defaults to empty |
| `command` | yes | non-empty JSON array; non-empty stringified tokens retained |
| `tags` | no | JSON array; tokens case-folded and de-duplicated preserving first occurrence |
| `inputs` | no | array of input objects |
| `outputs` | no | array of output objects |
| `resources` | no | array of resource-claim objects |
| `working_directory` | no | trimmed text; resolution described below |
| `timeout_seconds` | no | integer-convertible, non-negative; default `0` |

## 4. Recipe ID

`id` is required and normalized with `.casefold()` before regex validation.

Accepted grammar:

```text
^[a-z0-9][a-z0-9._-]*$
```

Examples:

```text
workspace_health
analysis.export
model-check_v2
lab-tool.1
```

Not accepted:

```text
UpperCase
 space
/tool
```

Because the ID is case-folded first, a manifest spelling such as `Echo.Recipe` becomes `echo.recipe` before validation/identity use.

Recipe ID is the registry identity, import filename basis and Automation run subject for recipe execution.

## 5. Version

`version` must be non-empty after string conversion and trimming.

The current provider does **not** parse or compare Semantic Versioning. Strings such as:

```text
1.0.0
research-2026-09
v3
```

are all parser-valid if non-empty.

Therefore version ordering/compatibility must not be inferred from the manifest parser alone.

## 6. Command

`command` must be a JSON array and must contain at least one non-empty token after each element is stringified and trimmed.

Recipe execution is always constructed as:

```text
mode = exec
```

The recipe schema does not provide a `shell` mode field.

This distinction is important:

```text
recipe command -> argv tokens -> direct exec-style execution
ad-hoc command -> may explicitly choose exec or shell
```

Shell metacharacters embedded in a recipe command token are not granted shell interpretation merely because they look like shell syntax.

## 7. Placeholder namespace

Before execution, command tokens, resource IDs and `working_directory` can be rendered using Python `str.format_map` semantics over one substitution mapping.

Reserved substitutions always supplied by PTL:

```text
{python}    -> current PTL Python executable
{workspace} -> resolved PTL workspace root
```

Each declared input name adds another substitution key.

Unknown placeholders fail recipe rendering with `recipe_invalid`; they do not become empty strings.

Malformed format syntax can also fail rendering.

### Boundary

This is string-template substitution, not shell quoting, escaping, type validation or path authorization.

## 8. Inputs

`inputs` must be an array when present.

Each item must be an object with:

| Field | Required | Meaning |
|---|---:|---|
| `name` | yes | input/placeholder identity |
| `required` | no | converted with Python truth semantics; default `false` |
| `default` | no | string value; default empty |
| `description` | no | trimmed descriptive text |

Input-name grammar:

```text
^[A-Za-z_][A-Za-z0-9_]*$
```

Reserved names:

```text
python
workspace
```

Input names must be unique within one manifest.

### 8.1 Runtime input resolution

At Run time:

1. every declared input starts with its manifest default;
2. supplied values replace defaults;
3. supplied undeclared names produce `input_unknown`;
4. required inputs whose resolved value is empty/whitespace produce `input_required`;
5. resulting values join the placeholder substitution map.

The recipe schema currently treats input values as strings. It does not provide typed integer/boolean/path/enum validation.

## 9. Outputs

`outputs` must be an array when present.

Each item must be an object with:

```text
name        required non-empty text
description optional text
```

Current parser does not impose the input-name regex on output names and does not enforce output-name uniqueness.

More importantly, outputs are **descriptive metadata**. The Automation service does not currently ingest, validate or materialize typed outputs solely because they were declared here.

A recipe declaring an output does not prove that the child process produced it.

## 10. Resource claims

`resources` must be an array when present.

Each item has:

| Field | Required | Meaning |
|---|---:|---|
| `kind` | yes | non-empty resource kind text |
| `id` | yes | non-empty resource identity/template |
| `access` | no | `read` or `write`; default `read` |

Access is case-folded before validation.

At Run time, resource IDs are placeholder-rendered and converted into `ResourceClaim` objects.

### 10.1 No-claim recipe boundary

Unlike ad-hoc Automation, a recipe manifest with no `resources` does **not** automatically receive the conservative workspace-write claim in `AutomationService.run_recipe()`.

The runtime-operation coordinator still supplies its generic fallback claim when begun with an empty claim set:

```text
resource_kind = automation_recipe
resource_id   = <recipe_id>
access        = write
```

That fallback serializes the recipe subject identity; it is **not equivalent** to claiming the workspace or every host resource the command may touch.

Therefore trusted recipe authors must declare shared PTL resource claims accurately when coordination matters.

### 10.2 Claims are coordination, not permissions

Manifest claims do not constrain filesystem/network/syscall behavior. A child process runs with PTL's OS-account authority and may touch undeclared host resources if the OS permits it.

## 11. Working directory

If `working_directory` is absent/empty:

```text
cwd = <workspace>
```

If present, placeholders are rendered first.

Then:

- an absolute path remains absolute after normalization;
- a relative path in a workspace manifest resolves relative to that manifest's directory;
- a relative path for a recipe without `source_path` falls back to the workspace root.

### 11.1 Import consequence

Import copies only the manifest into:

```text
<workspace>/automation/recipes/<recipe_id>.ptl-recipe.json
```

After import, a relative `working_directory` therefore resolves relative to the imported manifest location, not the external source manifest's former directory.

Companion scripts/data are not automatically imported.

## 12. Timeout

`timeout_seconds` defaults to `0`.

Parser rules:

```text
int(value)
value >= 0
```

Negative or non-integer-convertible values invalidate the manifest.

At execution:

```text
0        -> no timeout configured
positive -> float(seconds) passed to execution
```

This field is not a resource limit for CPU, RAM, disk or network usage.

## 13. Environment

Recipe manifests do not define an environment-object field.

Recipe execution currently inherits the PTL process environment and then forces:

```text
PTL_WORKSPACE=<resolved workspace root>
```

This means inherited environment variables are part of the trusted-host input surface even though they are not listed in the manifest.

## 14. Discovery algorithm

A refresh starts with built-in recipes, then scans workspace manifest paths in sorted order.

For each matching file:

```text
load + validate
    │
    ├─ invalid -> discovery issue manifest_invalid; continue
    │
    └─ valid
          │
          ├─ ID already present -> recipe_duplicate; skip file
          └─ first unique ID -> register recipe
```

Consequences:

- one malformed manifest does not hide unrelated valid recipes;
- built-in IDs win over colliding workspace manifests because built-ins are registered first;
- when multiple existing workspace paths have the same ID, only the first sorted valid path becomes active and later ones are reported as duplicates.

A duplicate issue is evidence of ambiguous registry input and should be corrected rather than treated as a supported override mechanism.

## 15. Import safety

Import first validates the external source manifest and derives the canonical target filename from the normalized recipe ID.

Current protected behavior is:

1. if the selected source is already exactly the canonical target file, PTL re-loads it without copying;
2. otherwise PTL refreshes current recipe IDs;
3. if that ID already belongs to a built-in or discovered workspace recipe, import raises `FileExistsError` and does not replace it;
4. target creation uses exclusive-create mode, so a concurrent creator of the same canonical target cannot be silently overwritten;
5. if target writing fails, PTL best-effort removes the partially created target before surfacing the error;
6. the written target is parsed again before it is returned as the imported recipe.

This closes an earlier architecture seam where `shutil.copy2` could silently overwrite an existing canonical workspace recipe file with the same ID.

### Boundary

The registry is still an ordinary trusted filesystem directory. External tools/another PTL process with OS write access can edit manifests independently of this import method. Import collision protection is not a filesystem sandbox or global registry lock.

## 16. Review-to-run identity boundary

Discovery returns an `AutomationRecipe` snapshot for UI presentation.

When the user later runs by `recipe_id`, `AutomationService.get_recipe()` calls the provider again and resolves the current recipe with that ID.

Therefore v1.0 does not cryptographically pin:

```text
manifest reviewed in UI
        ==
manifest resolved at Run click
```

A trusted actor modifying the registry between review and execution can change the recipe that will run.

This is why the recipe registry belongs to the trusted execution boundary.

## 17. Audit boundary

Recipe execution is normally wired to Automation audit in production, but recipe validity itself does not include:

- a signature;
- a manifest content hash pinned to the run request;
- hashes for companion executables/scripts/data;
- a proof that declared resources match real side effects.

Audit command hashing identifies the rendered command snapshot PTL launched, not full transitive executable provenance.

## 18. Result codes related to recipe schema/use

Important service results include:

```text
recipe_not_found
input_unknown
input_required
recipe_invalid
operation_blocked
audit_failed
launch_failed
cancelled
timeout
failed
succeeded
```

Discovery issues are a different contract:

```text
manifest_invalid
recipe_duplicate
```

Do not document a discovery issue as if it were a run result code.

## 19. Schema limitations

The current v1 manifest intentionally does not provide:

- typed inputs;
- output validation/ingestion;
- shell execution mode;
- per-recipe environment overrides;
- cryptographic manifest signing;
- companion-file packaging;
- content-addressed executable provenance;
- filesystem/network permission policy;
- schema-enforced resource-kind vocabulary;
- semantic version compatibility rules;
- global multi-process registry locking.

These absences are current boundaries, not promises about future design.

## 20. Author checklist

Before placing/importing a workspace recipe:

1. use exact schema `ptl:automation-recipe:v1`;
2. choose a stable lowercase-compatible ID;
3. keep command as explicit argv tokens;
4. declare every required placeholder as an input;
5. do not use reserved input names `python` or `workspace`;
6. declare realistic PTL resource claims;
7. remember claims do not restrict host effects;
8. make relative working-directory assumptions explicit;
9. remember import does not copy companion files;
10. treat inherited environment as sensitive trusted input;
11. use timeout where a bounded run is operationally required;
12. review the manifest again after Refresh and before Run.

## 21. Change checklist

Any manifest/parser change should update:

1. `infrastructure/automation/recipe_provider.py`;
2. Automation provider/service tests;
3. this reference;
4. `user-guide/automation.md` when author/operator behavior changes;
5. `architecture/automation.md` when trust/execution semantics change;
6. `reference/statuses-and-identifiers.md` for new discovery/result codes;
7. localization if new visible validation/result states appear;
8. quick release inventory for new safety-critical regression tests.
