# Key Bindings & Mouse Gestures

Persona Training Lab has an editable input-binding system for application navigation and Agents graph interactions.

This guide documents the current v1.0 behavior exactly: which bindings exist, where they are stored, how direct capture/dialog editing works, how conflicts are handled, when changes become active, and which top-level workspace currently has no default navigation shortcut.

## 1. Open Key bindings

Use the **Key bindings** workspace from the left sidebar.

The screen shows two sections:

```text
Keyboard bindings
Mouse bindings
```

Each binding card includes its current value, an Edit action, and a restore-default action.

The header also displays the actual storage path used by the running manager.

## 2. Current storage location

With production/default construction, editable bindings are stored in:

```text
~/.persona_training_lab/key_bindings.json
```

This is currently a user-home-relative file.

It is **not** stored in:

```text
<workspace>/app.db
<workspace>/agents_lineage_state.json
Qt QSettings
```

Therefore copying/resetting the PTL research workspace does not automatically copy/reset custom key bindings.

The implementation/commit history reviewed for v1.0 does not establish why this path remains outside the modern workspace. The documentation records the current behavior without inventing a rationale.

## 3. Binding file format

The current JSON format version is:

```text
2
```

Version 1 remains readable for compatibility.

Conceptually:

```json
{
  "version": 2,
  "bindings": {
    "...": "..."
  },
  "mouse_bindings": {
    "...": {
      "button": "...",
      "modifier": "..."
    }
  }
}
```

Do not rely on hand-editing the file as the normal configuration workflow; the UI/manager performs normalization and conflict validation that arbitrary JSON edits can bypass until next load.

## 4. Default keyboard bindings

Current keyboard defaults are:

| Binding ID | Default | Purpose category |
|---|---|---|
| `delete_branch` | `Del` | Agents graph/history |
| `history_toggle` | `Ctrl+Z` | Agents graph/history |
| `undo_only` | `Ctrl+Shift+Z` | Agents graph/history |
| `nav_dashboard` | `Alt+H` | Navigation |
| `nav_profiles` | `Alt+P` | Navigation |
| `nav_agents` | `Alt+A` | Navigation |
| `nav_datasets` | `Alt+D` | Navigation |
| `nav_training` | `Alt+T` | Navigation |
| `nav_snapshots` | `Alt+S` | Navigation |
| `nav_tests` | `Alt+E` | Navigation |
| `nav_analysis` | `Alt+L` | Navigation |
| `nav_style` | `Alt+Y` | Navigation |
| `nav_docs` | `Alt+O` | Navigation |
| `nav_keybindings` | `Alt+K` | Navigation |

These table values are machine defaults from the binding definitions. The visible title/description is localized in the UI.

## 5. Automation currently has no default navigation binding

Automation is a real registered/sidebar workspace, but the current binding definitions do not contain:

```text
nav_automation
```

and the shell's application shortcut routing does not include Automation.

So there is currently no editable/default application-level Automation navigation shortcut in this binding set.

This is current code behavior. No historical design rationale was found in the reviewed implementation/commit messages, so this guide does not speculate about why it is absent.

## 6. Current mouse defaults

Agents graph mouse defaults are:

| Binding ID | Button | Modifier | Trigger | Target |
|---|---|---|---|---|
| `open_node_menu` | Left | None | click | node |
| `close_node_menu` | Left | None | click | canvas |
| `pan_canvas_primary` | Left | None | drag | canvas |
| `pan_canvas_secondary` | Right | None | drag | canvas |
| `move_node` | Right | None | drag | node |
| `move_subtree` | Right | Shift | drag | node |
| `zoom_canvas` | Wheel | None | wheel | canvas |

The same physical input can be valid for different targets/triggers when the current conflict rules can distinguish them.

## 7. Supported mouse buttons

Current semantic button IDs are:

```text
left
right
middle
back
forward
wheel
```

The visible labels are localized.

## 8. Supported mouse modifiers

Current semantic modifier IDs are:

```text
none
shift
control
alt
meta
```

Direct mouse capture accepts at most one of those modifiers at a time.

If multiple supported modifiers are held during direct capture, the UI reports the semantic `too_many_modifiers` error rather than saving an ambiguous combination.

## 9. Edit a keyboard shortcut by clicking its value chip

Click the current shortcut value chip.

The chip enters a visual capture state and the screen installs an application event filter.

Then press the intended key combination.

Behavior:

- modifier-only keypresses are consumed while waiting for the real key;
- the final combination is converted to Qt PortableText;
- `Esc` cancels capture;
- clicking the same capturing chip again cancels capture;
- a successful candidate is sent to the draft session.

## 10. Edit a keyboard shortcut with the Edit dialog

The Edit button opens a `QKeySequenceEdit` dialog initialized with the current draft sequence.

The dialog currently constrains the editor to one sequence when the Qt API supports `setMaximumSequenceLength(1)`.

Save passes the PortableText sequence into the same draft validation path as direct capture.

Cancel leaves the draft unchanged.

## 11. Keyboard sequences are normalized

The manager normalizes text through:

```text
QKeySequence.fromString(..., PortableText)
        ↓
QKeySequence.toString(PortableText)
```

An empty/invalid normalized sequence is rejected.

This means the persistent/source-of-truth form is a Qt PortableText keyboard sequence, not arbitrary display text.

## 12. Edit a mouse gesture by clicking its value chip

Click the current mouse-binding value chip.

During capture:

- mouse-button press records a supported mouse button plus zero/one modifier;
- wheel movement records `wheel` plus zero/one modifier;
- `Esc` cancels capture;
- more than one supported modifier is rejected.

The candidate then enters the same draft/conflict workflow as dialog editing.

## 13. Edit a mouse gesture with the Edit dialog

The mouse Edit dialog exposes semantic button/modifier choices.

For a wheel-trigger definition, the button is fixed to `wheel` and cannot be changed to a normal mouse button.

For a non-wheel trigger, `wheel` is excluded from the button choices.

The visible option labels follow the current UI language while stored values remain stable semantic IDs.

## 14. Wheel/non-wheel compatibility is enforced

The manager/draft session rejects:

```text
wheel binding with non-wheel button
non-wheel binding with wheel button
```

The corresponding semantic errors are:

```text
wheel_required
wheel_forbidden
```

This prevents a persisted gesture from contradicting the trigger type defined by the command.

## 15. Changes use a draft session

The Key bindings screen does not immediately force every temporary edit into the active manager one-by-one.

`KeyBindingDraftSession` maintains:

```text
active keyboard bindings
active mouse bindings
current keyboard draft
current mouse draft
```

This is important for swaps/multi-step conflict resolution.

A draft may temporarily contain conflicts while the user edits the other conflicting binding.

## 16. Conflict-free changes are committed automatically

After a draft change:

- if conflicts remain, the change stays only in the draft;
- if the entire draft is conflict-free and differs from the active map, the draft is written/activated;
- if it is already identical to active state, nothing is written.

There is no separate global “Apply” button in the current draft contract for a valid conflict-free edit.

## 17. All keyboard + mouse state is written together

When a valid draft commits, `KeyBindingDraftSession` calls one manager write with the complete keyboard and mouse mapping.

Only after that write succeeds does it replace the active in-memory maps and emit:

```text
bindings_changed
```

This avoids activating an intermediate invalid mapping during a multi-step swap.

## 18. A conflicting draft is visible but not active

When two draft keyboard bindings share the same normalized sequence, or mouse gestures violate the conflict rules, the affected cards receive conflict styling and conflict text naming the other action(s).

While that conflict exists, the new mapping is not committed as the manager's active/persisted state.

So “red conflict cards are visible” and “the running shortcuts have changed” are not equivalent states.

## 19. Keyboard conflict rule

For editable keyboard definitions, one normalized sequence cannot be assigned to multiple bindings in the active mapping.

Conflict comparison is case-insensitive over the normalized PortableText form.

A conflicting draft can exist temporarily to support resolving swaps, but it must be resolved/discarded before it can become active.

## 20. Mouse conflict rule depends on target and trigger

Mouse gestures are not globally unique across the entire application.

The current draft considers two gestures conflicting when:

1. their target is the same;
2. their button+modifier combination is the same; and
3. their trigger is the same **or** the target is `node` and the combination would be ambiguous for current node click/drag behavior.

This permits deliberate canvas sharing such as click vs drag with the same left button while keeping node interaction stricter.

## 21. Leaving Key bindings with unresolved conflicts is guarded

`KeyBindingsScreen.request_leave_workspace()` is a real shell leave guard.

When the draft has conflicts, attempting to leave the workspace opens a warning dialog.

The choices are conceptually:

```text
Fix conflicts
Discard conflicting changes
```

Choosing to fix keeps navigation blocked so you can resolve them.

Choosing discard reverts only the currently conflicting binding IDs to their active values and then attempts a valid commit for any remaining non-conflicting draft changes.

## 22. A clean draft does not block navigation

If the draft has no conflicts, Key bindings allows the shell to navigate away immediately.

Any conflict-free changes have already been committed through the draft session's automatic commit behavior.

## 23. Reset one keyboard binding

Use the per-binding default/reset action.

The draft changes that binding back to its definition's default sequence.

If the reset creates a temporary conflict, it remains a draft conflict until resolved or discarded.

If the resulting complete draft is conflict-free, it commits automatically.

## 24. Reset one mouse binding

The per-binding default/reset action restores that definition's original:

```text
button
modifier
```

The same conflict/commit rules apply.

## 25. Reset all bindings

The header Reset all action first asks for confirmation.

If confirmed, the draft replaces every keyboard and mouse binding with the defaults from the definitions.

If the resulting mapping differs from active state and is valid, it is written/activated as one complete change.

## 26. Binding writes are replace-based

The manager writes JSON to a sibling temporary file:

```text
key_bindings.json.tmp
```

then replaces the target:

```text
key_bindings.json
```

If the write/replace fails, it attempts to remove the temporary file and returns a semantic write error.

The manager does not report a successful change and then silently leave only the in-memory value active.

## 27. What happens when the file does not exist

If the binding storage file is missing, the manager simply starts from built-in defaults.

Missing custom configuration is not considered a startup error.

The file is created when a change needs to be persisted.

## 28. What happens when the file cannot be read/parsed

Filesystem or JSON decode failure sets a semantic read error.

The manager retains its initialized default mapping instead of applying half-parsed configuration.

The Key bindings header can display this load warning.

## 29. Unsupported format version

If the JSON root is not an object or `version` is neither current version `2` nor supported old version `1`, the manager records an unsupported-format error and does not apply arbitrary fields.

Do not “fix” the version number alone unless you know the rest of the file matches the target schema.

## 30. Version 1 compatibility

Version 1 is accepted as an old format.

Keyboard bindings can be loaded from it.

Mouse bindings are only loaded from the current version path; otherwise mouse gestures remain at their defaults.

This is the current compatibility contract.

## 31. Persisted keyboard conflicts are repaired on load

After loading candidate keyboard values, the manager groups them by normalized sequence.

If any duplicate mapping remains, it reports a `keyboard_conflicts_repaired` semantic warning and falls back to the complete default keyboard mapping.

It does not pick an arbitrary winner from a corrupted/conflicting file.

## 32. Persisted mouse conflicts are repaired on load

Loaded mouse values are validated against the current definition/target/trigger conflict rules.

When a conflict is detected, the manager reports `mouse_conflicts_repaired` and uses the default mouse mapping.

Invalid per-entry button/modifier combinations are skipped rather than activated.

## 33. Active navigation shortcuts update immediately after accepted changes

The MainWindow listens for `bindings_changed`.

When emitted, it disables/deletes the old application navigation `QShortcut` objects and creates new ones from the manager's current sequences.

You do not need to restart PTL for an accepted navigation shortcut change to become active.

## 34. Agents graph bindings also consume the shared manager

The Agents screen receives the same shell-owned `KeyBindingManager` instance.

Therefore accepted graph/history keyboard/mouse changes and top-level navigation changes share one persisted mapping and conflict-management source.

They are not independent per-Agents-profile settings.

## 35. Bindings are user-global relative to the current code path, not workspace-local

Because the default file path is in the user's home directory and the shell creates one manager without injecting a workspace-specific path, the same file is used regardless of which PTL research workspace is active.

This is an implementation consequence of the current path.

It should not be confused with a documented product rationale for why the design *should* be global.

## 36. Workspace backup/reset does not include bindings

A normal whole-workspace backup preserves PTL research/workflow state but does not include:

```text
~/.persona_training_lab/key_bindings.json
```

If you need to reproduce the exact operator input configuration, preserve that file separately.

Likewise, moving/resetting `<workspace>` does not reset custom bindings.

## 37. Binding file is not a secret store

The file contains input mappings rather than credentials.

It is ordinary unencrypted JSON under the user's home directory.

Do not repurpose the binding format to store tokens/secrets or unrelated private configuration.

## 38. Troubleshooting: a shortcut does nothing

Check:

1. the Key bindings screen's current active/draft value;
2. whether the screen shows an unresolved conflict;
3. whether the command is one of the defined bindings;
4. whether you are expecting an Automation navigation shortcut that does not currently exist;
5. whether the storage file loaded with a warning;
6. whether another application/desktop environment intercepts the key combination before Qt receives it.

PTL can validate its own binding map; it cannot guarantee that the host desktop never reserves/intercepts a global-looking combination.

## 39. Troubleshooting: a binding keeps returning to defaults

Inspect the Key bindings header warning.

Possible manager-level reasons include:

```text
read/JSON error
unsupported format
persisted keyboard conflicts repaired
persisted mouse conflicts repaired
```

Do not repeatedly edit the JSON by hand while PTL is running; use the UI or move the broken file aside for a controlled default-state test after preserving it as evidence.

## 40. Troubleshooting: cannot leave the Key bindings screen

If conflict cards are visible, the leave guard is intentionally blocking navigation.

Resolve the conflicts, or choose the dialog action that discards the conflicting draft changes.

The shell is not frozen; it is honoring `request_leave_workspace()`.

## 41. Troubleshooting: direct capture will not accept multiple modifiers for a mouse gesture

That is current validation behavior.

Mouse capture maps zero or one modifier into the semantic IDs `none/shift/control/alt/meta`.

Two or more active supported modifiers produce `too_many_modifiers` and are rejected.

Keyboard shortcuts do not have that same one-modifier limitation; they are represented by Qt `QKeySequence`.

## 42. Troubleshooting: direct capture seems stuck

Press `Esc` or click the same active value chip again to cancel capture.

Starting capture for another chip first cancels the previous capture.

The application-level event filter is removed when capture is cancelled/completed.

## 43. Screenshot plan

The final documentation asset pass should capture:

- full Key bindings workspace showing the storage path;
- keyboard/default navigation section;
- Agents mouse gestures section;
- direct-capture active chip state;
- Edit keyboard dialog;
- Edit mouse dialog;
- visible keyboard conflict pair;
- visible mouse conflict pair;
- leave-workspace conflict dialog;
- load warning from a controlled invalid test file.

Use a temporary/injected configuration for destructive/conflict demo captures rather than corrupting a real operator's only binding file.

## 44. Current v1.0 boundaries

The binding system currently does not claim:

- workspace-local bindings;
- profile-specific binding sets;
- cloud synchronization;
- a default navigation shortcut for Automation;
- arbitrary multi-modifier mouse gestures;
- arbitrary chord sequences longer than the current one-sequence editor contract;
- host-OS reservation/conflict detection outside PTL;
- cryptographic integrity/signing of the JSON file.

## 45. Developer invariants

Changes to input bindings should preserve these rules unless deliberately redesigned:

1. machine binding IDs remain stable across locale changes;
2. accepted keyboard sequences remain normalized through Qt PortableText;
3. invalid/empty keyboard sequences are not activated;
4. persisted duplicate keyboard mappings are repaired deterministically rather than arbitrarily won;
5. mouse values remain validated against known button/modifier/trigger rules;
6. unresolved draft conflicts must not become active/persisted mappings;
7. a valid multi-change draft commits keyboard+mouse state together before emitting `bindings_changed`;
8. shell application shortcuts must resynchronize after accepted changes;
9. Key bindings leave guard must continue preventing accidental navigation away from unresolved conflicts;
10. persistence location/version behavior must be documented if changed;
11. adding a new top-level navigation screen does not automatically create a shortcut—its binding definition/routing must be added deliberately;
12. documentation must not claim `nav_automation` exists until code actually defines/routes it.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Agents lineage](agents-lineage.md)
- [Automation](automation.md)
- [UI shell architecture](../architecture/ui-shell.md)
- [Persistence architecture](../architecture/persistence.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
