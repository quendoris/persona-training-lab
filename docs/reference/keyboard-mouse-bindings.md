# Keyboard & Mouse Bindings Reference

This is the machine-oriented v1.0 binding reference for Persona Training Lab.

For the editing workflow, conflict handling, direct capture, persistence, and troubleshooting, see [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md).

## 1. Keyboard binding model

Each `KeyBindingDefinition` contains:

```text
binding_id
sequence
auto_repeat
editable
category_id
```

Defaults:

```text
auto_repeat = false
editable    = true
category_id = history
```

Localized presentation keys are derived from stable IDs:

```text
keybindings.binding.<binding_id>.title
keybindings.binding.<binding_id>.description
keybindings.category.<category_id>
```

## 2. Current keyboard bindings

| Binding ID | Default sequence | Category | Auto-repeat | Editable |
|---|---|---|---:|---:|
| `delete_branch` | `Del` | `history` | no | yes |
| `history_toggle` | `Ctrl+Z` | `history` | no | yes |
| `undo_only` | `Ctrl+Shift+Z` | `history` | **yes** | yes |
| `nav_dashboard` | `Alt+H` | `navigation` | no | yes |
| `nav_profiles` | `Alt+P` | `navigation` | no | yes |
| `nav_agents` | `Alt+A` | `navigation` | no | yes |
| `nav_datasets` | `Alt+D` | `navigation` | no | yes |
| `nav_training` | `Alt+T` | `navigation` | no | yes |
| `nav_snapshots` | `Alt+S` | `navigation` | no | yes |
| `nav_tests` | `Alt+E` | `navigation` | no | yes |
| `nav_analysis` | `Alt+L` | `navigation` | no | yes |
| `nav_style` | `Alt+Y` | `navigation` | no | yes |
| `nav_docs` | `Alt+O` | `navigation` | no | yes |
| `nav_keybindings` | `Alt+K` | `navigation` | no | yes |

## 3. Graph-only keyboard subset

`agent_graph_key_bindings_by_id()` intentionally returns only:

```text
delete_branch
history_toggle
undo_only
```

The navigation definitions live in the same master binding tuple but are not part of the Agents graph-only subset.

## 4. Current top-level navigation mapping

| Binding ID | Workspace key |
|---|---|
| `nav_dashboard` | `dashboard` |
| `nav_profiles` | `profiles` |
| `nav_agents` | `agents` |
| `nav_datasets` | `datasets` |
| `nav_training` | `training` |
| `nav_snapshots` | `snapshots` |
| `nav_tests` | `tests` |
| `nav_analysis` | `analysis` |
| `nav_style` | `style` |
| `nav_docs` | `docs` |
| `nav_keybindings` | `keybindings` |

The shell creates these navigation shortcuts with Qt application-wide shortcut context.

## 5. No current `nav_automation`

The current binding definitions do **not** contain:

```text
nav_automation
```

although `automation` is a registered/sidebar workspace.

There is therefore no current default/editable application-level Automation navigation binding in this binding system.

No reviewed code/commit rationale proves why; this reference records the implementation fact only.

## 6. Keyboard normalization

Editable keyboard values are normalized through Qt PortableText:

```text
QKeySequence.fromString(value, PortableText)
QKeySequence.toString(PortableText)
```

An empty normalized sequence is invalid.

Conflict identity is based on normalized sequence text case-insensitively.

## 7. Mouse binding model

Each `MouseBindingDefinition` contains:

```text
binding_id
button
modifier
trigger
target
category_id
```

Default category:

```text
mouse
```

Localized presentation keys are derived as:

```text
keybindings.mouse_binding.<binding_id>.title
keybindings.mouse_binding.<binding_id>.description
keybindings.category.<category_id>
```

## 8. Supported mouse button IDs

```text
left
right
middle
back
forward
wheel
```

These are machine IDs. Visible labels are localized.

## 9. Supported mouse modifier IDs

```text
none
shift
control
alt
meta
```

Direct mouse capture currently maps at most one supported modifier.

## 10. Current mouse bindings

| Binding ID | Button | Modifier | Trigger | Target |
|---|---|---|---|---|
| `open_node_menu` | `left` | `none` | `click` | `node` |
| `close_node_menu` | `left` | `none` | `click` | `canvas` |
| `pan_canvas_primary` | `left` | `none` | `drag` | `canvas` |
| `pan_canvas_secondary` | `right` | `none` | `drag` | `canvas` |
| `move_node` | `right` | `none` | `drag` | `node` |
| `move_subtree` | `right` | `shift` | `drag` | `node` |
| `zoom_canvas` | `wheel` | `none` | `wheel` | `canvas` |

## 11. Trigger/button compatibility

Current trigger rules require:

```text
trigger == wheel  -> button must be wheel
trigger != wheel  -> button must not be wheel
```

Semantic validation errors used by the editing path include:

```text
wheel_required
wheel_forbidden
```

## 12. Mouse conflict identity

Mouse conflict checks consider:

```text
target
button
modifier
trigger
```

The current draft rules allow some same-button canvas click/drag sharing when trigger/target disambiguate the gesture.

Node interactions are stricter because the current node click/menu/drag semantics can make same-combination bindings ambiguous.

Use the user guide for the complete editing behavior.

## 13. Current binding persistence

Default file:

```text
~/.persona_training_lab/key_bindings.json
```

Current format:

```text
version = 2
```

Supported older load format:

```text
version = 1
```

Version 2 stores keyboard + mouse mappings. Version 1 compatibility restores keyboard mappings while current mouse definitions remain available from defaults.

## 14. Persistence payload shape

Conceptually:

```json
{
  "version": 2,
  "bindings": {
    "delete_branch": "Del",
    "nav_dashboard": "Alt+H"
  },
  "mouse_bindings": {
    "move_subtree": {
      "button": "right",
      "modifier": "shift"
    }
  }
}
```

Only the editable value fields are persisted; trigger/target/category/default definitions come from current code definitions.

## 15. Why trigger/target are not stored as editable values

The current mouse definition declares `trigger` and `target` as command semantics.

The persisted editable mapping stores only:

```text
button
modifier
```

Therefore changing the trigger/target of a binding is a code/definition change, not a normal user preference edit.

## 16. Persistence write boundary

The manager writes the complete mapping to:

```text
key_bindings.json.tmp
```

and then replaces:

```text
key_bindings.json
```

The write path is replace-based but does not currently implement the explicit flush/fsync/directory-fsync sequence used by Agents `AtomicLineageStateStore`.

Do not describe the two file stores as having identical durability mechanics.

## 17. Load repair behavior

Current load behavior:

| Condition | Result |
|---|---|
| file missing | built-in defaults, no load error |
| file read/JSON failure | semantic read error, safe defaults retained |
| unsupported root/version | unsupported-format error, values not applied |
| duplicate/conflicting keyboard mapping | `keyboard_conflicts_repaired`, keyboard defaults used |
| invalid/conflicting mouse mapping | invalid entries skipped / `mouse_conflicts_repaired`, mouse defaults used according to current repair path |

The manager does not choose an arbitrary winning shortcut from a persisted conflict.

## 18. Draft vs active identity

The Key bindings workspace maintains a draft mapping separate from the manager's active mapping.

A draft can temporarily contain conflicts.

Only a complete conflict-free changed draft is written/activated.

After write success:

```text
active maps update
bindings_changed emitted
shell/Agents consumers resynchronize
```

## 19. Direct keyboard capture controls

Current direct-capture semantics:

```text
Esc                    -> cancel
modifier-only keypress -> wait/consume
final key combination  -> PortableText candidate
click active chip again -> cancel
start another capture   -> previous capture cancelled first
```

## 20. Direct mouse capture controls

Current direct-capture semantics:

```text
mouse press -> button + zero/one modifier candidate
wheel       -> wheel + zero/one modifier candidate
Esc         -> cancel
>1 supported modifier -> too_many_modifiers
```

## 21. Stable IDs vs localized labels

Do not automate/configure behavior from translated titles such as “Dashboard”, “Панель”, or other visible text.

Stable contracts are:

```text
binding_id
workspace key
mouse button ID
mouse modifier ID
trigger
target
```

Localized labels can change with locale without changing binding identity.

## 22. Adding a new keyboard binding

A complete new binding normally requires deliberate updates to the relevant surfaces:

```text
KeyBindingDefinition
localization title/description/category keys
manager/default mapping
consumer/routing code
editing UI coverage
conflict behavior/tests
reference/user documentation
```

For a top-level navigation binding, shell shortcut routing must also map the binding ID to a registered workspace key.

## 23. Adding a new mouse binding

A complete new mouse binding requires:

```text
MouseBindingDefinition
valid trigger/target semantics
localized title/description
consumer routing
conflict-rule compatibility
default mapping persistence behavior
tests + docs
```

Adding an ID to the persistence file alone does not create an executable gesture.

## 24. Reference non-goals

The current system does not define:

- `nav_automation`;
- multi-profile binding sets;
- workspace-local binding sets;
- cloud-synchronized bindings;
- arbitrary user-editable mouse target/trigger semantics;
- multi-modifier direct mouse capture;
- cryptographic signing of binding configuration;
- host desktop/global shortcut reservation detection.

## 25. Reference invariants

If a default/binding ID changes, update:

- this reference;
- [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md);
- shell/Agents routing tests;
- localization catalogs;
- visual/documentation capture inventory.

If storage/version semantics change, also update:

- [Workspace Layout Reference](workspace-layout.md);
- [Workspace & Storage](../operations/workspace-and-storage.md);
- [Persistence architecture](../architecture/persistence.md);
- backup/recovery documentation when inclusion scope changes.

## Related documentation

- [Key Bindings & Mouse Gestures](../user-guide/key-bindings.md)
- [UI shell architecture](../architecture/ui-shell.md)
- [Agents lineage](../user-guide/agents-lineage.md)
- [Workspace Layout Reference](workspace-layout.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
