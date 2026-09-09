# Preference persistence and ownership boundaries

Status: **current implementation contract** for PTL user-interface preferences and shell/input state.

This document answers one specific question: **where do PTL preferences live, which workspace/process owns them, and what concurrency guarantees exist for each store?**

The answer is intentionally not “all settings are in the workspace”. Current PTL uses three separate persistence systems with different lifetimes and transactional properties.

## 1. Executive contract

Current preference-like state is split as follows:

```text
workspace-local SQLite
    <workspace>/app.db :: ui_preferences
        -> theme
        -> accent_palette
        -> button_style_preset
        -> ui_scale
        -> language

platform/user Qt settings
    QSettings
        -> shell/window_geometry
        -> shell/dock_state
        -> shell/current_workspace

user-home JSON
    ~/.persona_training_lab/key_bindings.json
        -> editable keyboard bindings
        -> editable mouse bindings / Agents gestures
```

These are **three independent persistence boundaries**.

The workspace writer lease covers the first store indirectly by excluding a second cooperating PTL desktop writer from the same workspace. It does not make QSettings or the home-relative binding file part of the workspace transaction.

## 2. Why the distinction matters

The stores differ in all of the following:

- path/location ownership;
- backup behavior;
- transaction semantics;
- failure reporting;
- cross-process scope;
- relationship to workspace restore/reset;
- portability across machines/users.

Documentation must therefore not use “PTL preferences”, “workspace settings”, or “UI state” as though they were one atomic object.

## 3. SQLite style/localization preferences

`SQLiteUIPreferencesRepository` stores one effective preferences row in the workspace database.

Current fields are:

```text
theme
accent_palette
button_style_preset
ui_scale
language
updated_at
```

The repository also supplies defaults when no row exists:

```text
theme               = velvet
accent_palette      = cyan
button_style_preset = soft_glow
ui_scale            = auto
language            = ru-RU
```

Writes use the shared SQLite connection, the connection-associated repository lock and a SQLite transaction context.

Therefore these preferences participate in the same workspace database durability/backup boundary as other `app.db` rows.

## 4. StyleViewModel performs read-modify-write of the full preference row

The current view model preserves fields outside the immediate edit by first loading the current row and then saving a complete preference mapping.

Examples:

```text
save_ui_scale(new_scale)
    -> load current theme/accent/button/language
    -> write complete row with new scale

save_language(new_language)
    -> load current theme/accent/button/scale
    -> write complete row with new language
```

Inside the standard desktop application this normally executes through one UI/application process owning the workspace.

This is not a general compare-and-swap protocol for independent concurrent writers. The outer single-writer workspace rule is part of the current consistency model.

## 5. Window/dock state is not in `app.db`

`WindowStateStore` uses Qt `QSettings` for:

```text
shell/window_geometry
shell/dock_state
shell/current_workspace
```

and records a shell-state schema/version marker currently equal to:

```text
2
```

On save it calls `QSettings.sync()` and returns whether Qt reports `NoError`.

On restore it:

1. checks the saved version;
2. attempts geometry restoration;
3. attempts dock-state restoration using the same version;
4. returns the saved workspace key as presentation/session state.

The exact native backing path/registry location depends on platform and QSettings backend.

## 6. Shell-state save failure is best-effort, not a close veto

The main window saves shell state during a successful application close, but the current product does not promote a failed `WindowStateStore.save()` boolean into a refusal to close PTL.

This is an intentional description of current behavior, not a claim about historical rationale.

Consequences:

- research/workflow state is not considered invalid merely because window geometry cannot be persisted;
- a subsequent launch can fall back to default shell layout/session state;
- operators must not treat successful PTL shutdown as proof that QSettings presentation state was durably written.

## 7. Key bindings are a separate user-home file

`KeyBindingManager.default_storage_path()` currently resolves to:

```text
~/.persona_training_lab/key_bindings.json
```

This path is independent of `AppSettings.workspace_dir`.

Current write format is version 2 and stores both:

```text
keyboard bindings
mouse bindings
```

Version 1 remains readable as a compatibility format.

Because the file is user-home relative, switching/restoring a PTL workspace does not by itself switch/restore key bindings.

## 8. Key-binding commit semantics

Editing uses a draft/commit model.

A draft may temporarily contain conflicts. `commit(...)` first validates the complete keyboard and mouse set. Invalid/conflicting drafts are rejected before they become active or persisted.

For a valid set, the current write path is:

```text
construct complete JSON payload
        ↓
write <storage-path>.tmp
        ↓
replace target with temporary file
        ↓
update in-memory bindings
        ↓
emit bindings_changed
```

If filesystem write/replace fails, the manager best-effort removes the temporary file, leaves the old active in-memory bindings intact and returns a semantic error message.

This is stronger than writing directly into the target file, but it is not equivalent to the Agents atomic-state durability protocol: the key-binding writer does not currently perform file/directory `fsync()` durability steps.

## 9. The key-binding file has no interprocess compare-and-swap contract

The current manager does not record a generation/version hash of the file it originally loaded and does not compare that generation before replacement.

It also does not own an interprocess lock for the user-home binding file.

Therefore the API must not be documented as supporting independent concurrent processes safely performing read-modify-write edits to the same binding file.

A theoretical two-process sequence can be:

```text
process A loads generation X
process B loads generation X
process A writes generation A
process B writes generation B derived from old X
        ↓
A's independent change can be lost
```

The fixed `.tmp` sibling can also be contended by independent writers.

This is a **concurrency limitation**, not evidence of a current normal-path race between two standard PTL instances using the same default workspace, because the workspace writer lease rejects the second cooperating desktop process earlier.

## 10. Workspace ownership does not make PTL a global per-user singleton

`WorkspaceOwnership` is keyed to one resolved workspace root:

```text
<workspace>/.ptl-workspace.lock
```

Its guarantee is:

> no second cooperating standard desktop bootstrap may write the **same workspace** concurrently.

It is not a global lock for every PTL process under one OS user account.

The current production `main()` constructs default `AppSettings()` and does not expose a normal command-line workspace selector. Consequently, ordinary launches under the same user normally resolve to the same default workspace and collide at the workspace lease.

However, controlled code/tests can construct `AppSettings(workspace_dir=...)`, and a future product feature could expose multiple simultaneous different workspaces.

If that product model is introduced, QSettings and the home-relative key-binding file require an explicit decision because they are not namespaced by workspace today.

## 11. Different-workspace concurrency boundary

Consider a future arrangement:

```text
PTL process A
    workspace = /research/A

PTL process B
    workspace = /research/B
```

The workspace leases do not conflict, which is correct for `app.db`, Agents JSON and workspace artifacts.

But both processes can still address the same user-level stores:

```text
QSettings application identity
~/.persona_training_lab/key_bindings.json
```

Current PTL does not claim transactional cross-process semantics for that case.

Before simultaneous different-workspace operation becomes a supported product capability, architecture must choose one of several explicit models rather than inherit accidental behavior.

Possible design families include:

```text
A. global per-user preferences with explicit interprocess coordination
B. workspace-scoped preferences
C. profile/account-scoped preferences with generation/CAS semantics
D. global application singleton even across different workspaces
```

This document does not choose among them because current code/product behavior does not prove the intended future model.

## 12. Backup semantics

A whole-workspace backup captures:

```text
app.db :: ui_preferences
```

but does not automatically capture:

```text
QSettings shell state
~/.persona_training_lab/key_bindings.json
```

Therefore a workspace restore can restore theme/language/scale while leaving the machine/user's current dock layout and key bindings unchanged.

For exact presentation/input-personalization restoration, those external stores require separate platform/user-level preservation.

## 13. Reset semantics

Resetting/removing only a workspace can reset the SQLite-backed preferences when a fresh `app.db` is created.

It does not inherently reset:

- saved Qt window geometry;
- saved dock layout;
- saved last workspace key;
- custom keyboard mappings;
- custom mouse mappings.

Conversely, resetting key bindings does not alter workspace research records or SQLite style preferences.

The stores must remain separate in recovery instructions.

## 14. Security/privacy boundary

None of these persistence mechanisms should be described as encryption.

They are local state stored with the permissions and protection supplied by the host OS/user profile/filesystem/backend.

In particular:

- SQLite UI preferences are ordinary database fields;
- QSettings uses the platform's native settings backend;
- key bindings are JSON text in the user's home directory.

The values are not high-sensitivity research data by design, but documentation must not derive a stronger secrecy guarantee from their location.

## 15. Current architecture assessment

The three-store split is internally coherent for the current standard desktop model:

```text
research/workspace-specific appearance locale/scale
    -> workspace SQLite

machine/user shell geometry/session layout
    -> QSettings

user-level input customization
    -> home JSON
```

What is **not** proven by code/history is whether that exact scope split was an intentional long-term product decision.

Accordingly:

- current placement is documented as fact;
- no rationale is invented;
- no automatic migration is performed during documentation work;
- future multi-workspace support must revisit the user-level concurrency boundary explicitly.

## 16. Known engineering seams

The current audit leaves these seams visible rather than hiding them:

1. key-binding persistence has temp-then-replace publication but no interprocess generation/CAS or lock contract;
2. key-binding durability is weaker than Agents JSON because no explicit `fsync()` protocol is implemented;
3. QSettings is outside the workspace lease and its backend-level cross-process semantics are not elevated into a PTL transaction contract;
4. shell-state save failure does not block shutdown;
5. `ui_preferences` updates are full-row read-modify-write operations whose current safety relies partly on the standard single-writer workspace model.

None of these facts alone requires a v1.0 migration while the supported desktop process model remains single-writer on the default workspace. They are constraints on future architecture and on what current documentation may promise.

## 17. Extension rule

Any future preference or personalization field must declare:

```text
scope
    workspace / user / machine / account / project

store
    SQLite / QSettings / file / other

writer model
    one process / coordinated multi-process / CAS / append-only / etc.

backup scope
    included in workspace snapshot? yes/no

failure semantics
    blocking / best-effort / default fallback

privacy classification
    what data is actually stored
```

Adding a field without those answers risks turning a UI convenience into an undocumented persistence/concurrency dependency.

## 18. Related documents

- [Workspace concurrency and ownership](workspace-concurrency.md)
- [UI shell architecture](ui-shell.md)
- [Persistence architecture](persistence.md)
- [Workspace layout reference](../reference/workspace-layout.md)
- [Appearance & Language](../user-guide/appearance-and-language.md)
- [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md)
- [Keyboard & mouse bindings reference](../reference/keyboard-mouse-bindings.md)
- [Backup, Reset & Recovery](../operations/backup-reset-recovery.md)
