# UI Shell Architecture

This document describes the actual Persona Training Lab v1.0 desktop shell: composition ownership, workspace registration/navigation, leave/close guards, background-worker shutdown, docks/panels, Operations Center integration, context navigation, shortcuts, style/localization application, durable shell state, and exception containment.

It deliberately separates shell lifecycle responsibilities from individual workspace business logic.

The central rule is:

> **The shell owns navigation, presentation chrome, application-level shortcuts, panel wiring, durable shell presentation state, and safe workspace lifetime transitions; each workspace owns its feature-specific state/actions and can veto navigation/close while it still owns work.**

## 1. Runtime composition chain

The desktop application starts through:

```text
persona_training_lab.bootstrap.app.main()
```

Startup creates/configures, in order:

```text
SafeApplication
  ↓
AppContainer / services / view-models
  ↓
Style preferences
  ↓
LocalizationManager
  ↓
Density + theme + locale font policy
  ↓
MainWindow
  ↓
Qt event loop
```

The shell is therefore created after the application/service composition and initial global presentation state are available.

## 2. MainWindow is intentionally layered

The production `MainWindow` is built through an inheritance chain:

```text
ui.shell.main_window.MainWindow
  ↓
ui.shell.main_window_context.MainWindow
  ↓
ui.shell.main_window_background.MainWindow
```

Each layer adds a focused responsibility:

- base shell/layout/workspaces/docks/theme/status/navigation;
- context navigation + Operations Center + durable window state + app shortcuts;
- background-work ownership + final close behavior.

This layering is current implementation structure, not three independent application windows.

## 3. Base shell responsibilities

The base shell owns:

```text
Sidebar
WorkspaceStack
Status bar
Inspector dock
Activity dock
Telemetry dock
Issues dock
Windows/panels menu
screen registration
style application
localization bindings
```

Feature-specific screens are constructed with their injected view-models and registered into `WorkspaceStack`.

## 4. Registered workspaces

The current shell registers these workspace keys:

```text
dashboard
profiles
agents
datasets
training
snapshots
tests
analysis
style
automation
keybindings
docs
```

The key is machine navigation identity; localized sidebar titles are presentation.

## 5. WorkspaceStack is a scrollable host around QStackedWidget

`WorkspaceStack` subclasses `QScrollArea` and embeds one `QStackedWidget`.

It:

- makes the workspace area widget-resizable;
- enables horizontal/vertical scrollbars as needed;
- registers each workspace widget with a `workspace_key` property;
- exposes lookup/list/current-key helpers;
- centralizes leave/close-guard routing.

This is why a workspace does not own the top-level application window.

## 6. Navigation is guard-aware

`WorkspaceStack.show_workspace(key)` does not blindly change the current widget.

When navigating to a different workspace it first calls:

```text
request_current_leave()
```

If the current workspace provides callable:

```text
request_leave_workspace()
```

its boolean result controls whether navigation may proceed.

A rejected leave keeps the current workspace selected and the shell restores the previous sidebar selection.

## 7. Application close has a stronger optional guard

For application shutdown, `WorkspaceStack.request_current_close()` prefers a workspace-specific:

```text
request_application_close()
```

when available.

If a workspace does not provide that hook, the shell falls back to the normal leave guard.

This lets a feature distinguish “navigate away” from “destroy the application” when necessary.

## 8. Guards are ownership contracts, not modal decoration

A leave/close guard can represent real owned work or integrity requirements.

Examples include a workspace that still owns a background worker or an active operation whose UI/controller state must not be destroyed prematurely.

The shell treats a false guard result as a lifecycle veto rather than forcing navigation.

## 9. Background work is owned by workspace widgets

The final shell iterates all registered workspaces and looks for callable:

```text
shutdown_background_work(timeout_ms)
```

Each workspace that implements it is responsible for stopping its own worker(s).

The shell aggregates the result across workspaces.

This avoids a single global worker registry knowing feature internals.

## 10. `aboutToQuit` also asks the shell to stop background work

Production startup connects:

```text
app.aboutToQuit -> window.shutdown_background_work
```

The explicit `closeEvent` path also performs ownership-safe shutdown before allowing destruction.

The application therefore has both normal close-flow ownership checks and a final Qt quit notification path.

## 11. Close is retried instead of destroying live workspace ownership

The final `closeEvent` sequence is:

```text
1. pass current workspace close guard
2. ask all workspace background workers to stop immediately/non-blocking
3. if any remains alive:
     - ignore close event
     - show background-shutdown status
     - schedule another close after 250 ms
4. when all stopped:
     - stop operations timer
     - clear guidance effect
     - save window state
     - call QMainWindow.closeEvent
```

The shell therefore does not intentionally destroy a workspace while its reported background worker still owns data.

## 12. The close guard is not repeatedly re-requested after it passes

`_close_guard_passed` remembers that the workspace close guard already accepted the shutdown request.

Subsequent timer-driven close retries focus on waiting for background ownership to end rather than repeatedly prompting/re-running the first guard decision.

## 13. Shutdown polling is event-loop based

When workers remain active, the shell schedules:

```text
QTimer.singleShot(250, _retry_close)
```

rather than blocking the GUI event loop in one long wait from `closeEvent`.

This lets worker-finished events/Qt cleanup continue to be processed while shutdown is pending.

## 14. Explicit `shutdown_background_work(timeout_ms)` supports bounded waiting

The shell method accepts an optional total timeout (default 6500 ms when called directly).

It computes one deadline and passes remaining time to each workspace shutdown hook in sequence.

`closeEvent` itself calls it with `0`, choosing the asynchronous retry behavior above.

## 15. Sidebar navigation and workspace registration are separate layers

The base sidebar owns the core navigation buttons.

`app_sidebar.Sidebar` extends it with application additions such as:

```text
automation
keybindings
```

`NAVIGATION_KEYS` maps workspace IDs to localization keys.

A screen being registered in `WorkspaceStack` and a shortcut existing for that screen are separate contracts.

## 16. Automation currently has no default application navigation shortcut

The sidebar/workspace includes:

```text
automation
```

but the current `AGENT_GRAPH_KEY_BINDINGS` navigation definitions and `TAB_SHORTCUTS` do not define/bind a `nav_automation` shortcut.

The current application-level navigation shortcut set covers:

```text
dashboard
profiles
agents
datasets
training
snapshots
tests
analysis
style
docs
keybindings
```

This document records the fact only. The code/commit history reviewed here does not establish why Automation was intentionally excluded, so no rationale is invented.

## 17. Application shortcuts are rebuilt when bindings change

The context shell listens to:

```text
KeyBindingManager.bindings_changed
```

and rebuilds its `QShortcut` objects.

Existing shortcuts are disabled/deleted before the new set is created.

Each navigation shortcut uses:

```text
Qt.ApplicationShortcut
```

so it can navigate from application context rather than being scoped to one child widget.

## 18. Sidebar shortcut hints are presentation derived from the manager

When application navigation shortcuts are synchronized, the shell also updates sidebar tooltip/hint metadata for those screens.

The sidebar does not own the source-of-truth sequence.

The sequence comes from `KeyBindingManager`.

## 19. KeyBindingManager is shell-owned but persists outside the workspace

The base shell creates:

```text
KeyBindingManager(parent=self)
```

without an explicit storage path.

Therefore the current default is:

```text
~/.persona_training_lab/key_bindings.json
```

This file stores editable keyboard and mouse bindings.

It is not in `<workspace>`, not in `app.db`, and not in Qt `QSettings`.

## 20. The home-relative key-binding path is a current architecture exception

Most modern PTL mutable research/workflow state uses the workspace contract, while shell geometry uses explicit Qt `QSettings`.

Key bindings currently use a third persistence surface:

```text
Path.home() / ".persona_training_lab" / "key_bindings.json"
```

The code/commit messages prove the path/format behavior but do not establish whether this was deliberately intended as user-global configuration or remains historical placement.

Documentation must therefore describe the location without inventing architectural motivation.

## 21. Key-binding persistence has its own versioned JSON format

Current manager format version:

```text
2
```

with support for loading old version:

```text
1
```

The payload contains:

```text
version
bindings
mouse_bindings
```

Version 1 can load keyboard bindings while the current version additionally restores editable mouse bindings.

## 22. Key-binding writes use replace semantics

The manager writes to:

```text
key_bindings.json.tmp
```

then replaces the target file.

On write failure it attempts to delete the temporary file and returns a semantic write error rather than updating the in-memory binding state as successful.

This is a local file-replacement boundary, distinct from the stronger `fsync` behavior used by `AtomicLineageStateStore`.

## 23. Invalid key-binding persistence fails toward defaults/repair

If the key-binding file is missing, defaults remain active.

Read/JSON errors produce a semantic read error and keep defaults/current safe state.

Unsupported format produces a semantic unsupported-format error.

Persisted keyboard conflicts are repaired by falling back to defaults; mouse conflicts are likewise repaired according to the current conflict rules.

The manager does not blindly activate every persisted sequence.

## 24. Keyboard conflicts are validated before saving

`set_sequence(...)`:

- validates the binding exists/editable;
- normalizes with Qt PortableText;
- rejects empty sequences;
- rejects conflicts with other editable bindings;
- writes the full new binding state;
- updates in-memory state only after write success;
- emits `bindings_changed` on actual change.

This keeps the live application shortcut map aligned with persisted accepted state.

## 25. Mouse gestures use target/trigger-aware conflict rules

Mouse definitions carry:

```text
button
modifier
trigger
target
```

The manager validates known button/modifier IDs and wheel/non-wheel trigger compatibility.

Conflict detection is contextual: some click/drag sharing is intentionally allowed on canvas, while node interactions remain stricter because click-on-release/menu behavior differs.

The shell/Agents code consumes these semantic binding IDs rather than hardcoding only visible labels.

## 26. Docks are QMainWindow-owned shell chrome

The current docks are:

```text
inspector
activity
telemetry
issues
```

Each receives stable object name:

```text
ptl.dock.<dock_id>
```

and supports movable/closable/floatable behavior.

Stable object names are important because Qt window-state serialization uses dock identity to restore layout.

## 27. Activity/Telemetry/Issues share bottom dock area

Activity, Telemetry, and Issues are registered in the bottom dock area and tabified.

Inspector is registered at the right.

The shell can rebalance visible non-floating dock sizes using current density values.

## 28. Restored dock state suppresses initial rebalance

The context shell sets `_suspend_dock_rebalance` while constructing/restoring the window.

After `WindowStateStore.restore(...)`:

- if a dock state was restored successfully, the shell keeps that restored arrangement and updates central geometry;
- otherwise it performs the normal density-based initial rebalance.

This prevents startup sizing code from immediately overwriting a valid saved dock arrangement.

## 29. Panel visibility is exposed through the shell panels menu

Each dock contributes its Qt `toggleViewAction()` to the shell's panels menu.

The normal menubar is hidden; the sidebar receives this menu through its panel/window control.

Dock-title action text is refreshed when the UI language changes.

## 30. Window geometry/dock/current-workspace state uses Qt QSettings

`WindowStateStore` persists:

```text
shell/window_geometry
shell/dock_state
shell/current_workspace
```

with state version:

```text
2
```

Production does not inject a workspace-specific settings file; the store uses platform Qt `QSettings`.

This state is outside the PTL research/workflow workspace.

## 31. Production QSettings identity is established before MainWindow creation

`bootstrap.app.main()` sets:

```text
OrganizationName = Persona Training Lab
OrganizationDomain = persona-training-lab.local
ApplicationName = Persona Training Lab
ApplicationVersion = __version__
```

before building/creating the window.

Qt uses that application identity for its platform settings backend.

## 32. Shell state restore happens after base UI construction

The context shell calls the base constructor first, which creates workspaces/docks.

It then calls:

```text
WindowStateStore.restore(self)
```

This ordering is necessary for Qt to restore geometry/dock state onto already-existing identified dock widgets.

## 33. Last workspace restore is validated against registered screens

After restoring state, the shell only navigates to the saved workspace key when:

```text
restored.workspace_key
```

is non-empty and `WorkspaceStack.workspace(key)` exists.

Otherwise it keeps normal/default shell state and refreshes operations chrome.

A stale unknown key therefore does not create a missing screen dynamically.

## 34. Window-state save failure is not currently promoted into a close veto

`WindowStateStore.save(...)` returns whether `QSettings.status()` reports no error.

The final `closeEvent` invokes save but does not branch on the returned boolean before allowing the normal close after worker ownership is safe.

Therefore shell-state persistence is best-effort presentation persistence rather than authoritative research-state durability.

## 35. Operations Center is injected into shell chrome

The context shell accepts optional:

```text
OperationsCenterService
```

Production composition supplies it.

The shell wires that service into Activity and Issues panels and also queries it directly for live sidebar/Inspector context.

## 36. Activity and Issues navigation is contextual

Panels can emit:

```text
navigate_requested(screen, focus_text)
```

The shell:

1. navigates to the target workspace through normal guard-aware routing;
2. optionally looks for a visible/enabled button/frame matching the focus text;
3. pulses a temporary drop-shadow guidance effect;
4. falls back to a status message when no specific target can be found.

This is navigation assistance, not direct mutation of the destination workflow.

## 37. Context can be passed before navigation

`_go_to_screen_with_context(screen, context)` attempts to provide lineage context to the target screen or its view-model before normal navigation.

It looks for:

```text
set_lineage_context(...)
```

on the screen first, then on its `_vm` compatibility surface.

This supports exact model-version/lineage navigation into Tests/Analysis without making the shell own evaluation business logic.

## 38. Operations chrome polls independently of panel refresh timers

The context shell runs a timer every:

```text
900 ms
```

that queries Operations Center for active items/issues and updates:

- Sidebar active workflow pills;
- Inspector runtime context/issue count.

Activity/Issues panels also have their own refresh lifecycles while visible.

These are presentation polling loops over persisted/runtime service state, not the source of operation truth.

## 39. Active workflow sidebar entries are capped for display

The shell displays up to the first six active operation items in the sidebar workflow area.

This is a visual density limit.

It does not cap the number of runtime operations in persistence or Operations Center.

## 40. Inspector receives current workspace plus runtime context

On screen selection the shell updates Inspector context to the selected workspace.

The operations poller can additionally provide active operation titles and current issue count.

Inspector is therefore shell/context presentation, not a repository/service authority.

## 41. Status bar is a shell feedback channel

The base shell owns `AppStatusBar`.

It reports states such as:

```text
ready
current workspace
current style/density
background shutdown in progress
context-navigation fallback
```

Feature semantic results remain in their feature view-models/screens; the status bar should not replace machine status codes.

## 42. Global theme application happens at QApplication scope

Startup loads persisted Style preferences and applies theme/density before MainWindow creation.

Later shell Style actions call `apply_theme(app, theme, accent)` on the application instance and update status presentation.

The shell does not apply an independent per-workspace theme engine.

## 43. UI density is resolved as application presentation state

Startup calls `apply_density(...)` and scaled styles on the QApplication.

The shell reads `screen_density()` and derives default/minimum window and dock dimensions through scaling helpers.

Density values affect layout sizes, not persisted domain semantics.

## 44. Localization is injected/bound rather than read from global literals

Startup creates one `LocalizationManager` from the persisted locale.

The manager is passed to MainWindow/screens/panels, and bindings update window/dock/sidebar/status text when language changes.

The shell's navigation machine keys remain stable while presentation text changes.

See [Localization architecture](localization.md) for catalog/RTL/font details.

## 45. Locale font policy is applied at QApplication scope

Startup reads locale metadata and applies the locale font policy to the application.

Language changes trigger the same policy update.

This lets Arabic/RTL-capable font behavior be global rather than each screen selecting its own ad-hoc fallback.

## 46. Tests workspace has a direct Analysis navigation signal

During shell construction, the Tests screen's:

```text
open_analysis_requested
```

signal is wired to navigate to Analysis.

This is a shell-level workflow transition because switching top-level workspaces is shell ownership.

The Tests screen still owns when/why it emits that request.

## 47. Sidebar visual state follows successful navigation

`_go_to_screen(screen)` updates sidebar selection then calls the selection handler.

If `WorkspaceStack.show_workspace(screen)` rejects navigation because the current workspace leave guard fails, the shell restores the previous sidebar selection.

Visual navigation state therefore does not intentionally claim a screen switch that did not occur.

## 48. Shell view-model navigation is notified only after workspace switch succeeds

After a successful workspace change the shell:

```text
updates _current_screen
calls ShellViewModel.navigate(screen)
updates Inspector context
updates status
```

A blocked leave does not advance that shell navigation state.

## 49. SafeApplication is the Qt event-dispatch exception boundary

The QApplication subclass overrides `notify(...)`.

When a Python exception escapes an event handler, it reports through `ApplicationErrorReporter`, stores the last reported error identity/message on application properties, and returns `False` for that event instead of deliberately re-raising it through the Qt event loop.

This gives the shell/application a containment boundary for recoverable UI event failures.

## 50. Python/Qt global exception boundaries are installed outside MainWindow

`bootstrap.app` additionally installs:

```text
sys.excepthook          -> python.main_thread
threading.excepthook    -> python.worker_thread
qInstallMessageHandler  -> qt.message
```

These are application boundaries, not per-screen try/except wrappers.

The shell consumes/presents resulting Issues/Activity evidence through Operations Center.

## 51. Qt messages are diagnostic events, not stderr-only noise

Qt debug messages are ignored by the installed normal boundary.

Info/warning/critical/fatal messages are sent into `ApplicationErrorReporter.report_message(...)` with Qt context fields such as file/line/function/category where available.

This allows UI/runtime diagnostic problems to appear through the same structured evidence path as other application notices.

## 52. Shell architecture does not own business persistence

The shell must not directly write Dataset/Training/model-version/evaluation/runtime domain rows merely because it owns the widgets.

Business mutations flow through feature view-model/service/repository paths.

The shell owns only its own presentation/lifecycle persistence surfaces:

```text
QSettings window state
KeyBindingManager JSON
Style changes routed through StyleViewModel
```

Even Style persistence is performed through its injected service/repository rather than raw SQL from MainWindow.

## 53. Shell architecture does not make every worker global

Feature work can use feature-owned worker threads/controllers.

The shell requirement is that the workspace expose a shutdown ownership hook when destruction could race with worker-owned state.

This keeps feature-specific threading details out of the top-level window while retaining safe lifetime coordination.

## 54. Shell persistence topology

Current presentation persistence is split:

```text
app.db / ui_preferences
  -> theme, accent, button style, UI scale, language

Qt QSettings
  -> window geometry, dock state, last workspace

~/.persona_training_lab/key_bindings.json
  -> editable keyboard/mouse bindings
```

This three-way split is current implementation truth.

It is not correct to document “all UI preferences live in app.db” or “all user settings live in the PTL workspace.”

## 55. Architecture rationale known vs unknown

The code/tests establish why some mechanisms exist operationally (for example leave guards protecting worker ownership, stable dock IDs enabling restore, binding validation preventing conflicts).

The reviewed code/commit messages do **not** establish a documented rationale for why editable key bindings remain in the historical home-relative path rather than the modern workspace or Qt settings store.

Until historical project context or an explicit new decision resolves that question, documentation records the current path without manufacturing a reason.

## 56. Current UI shell non-goals

The shell does not claim:

- business-domain authority over feature services;
- unconditional navigation that ignores workspace ownership;
- forced synchronous shutdown of all workers inside one blocking close call;
- one universal settings backend for every UI preference;
- a default app navigation shortcut for Automation;
- persistence of every ephemeral widget selection/scroll position;
- cryptographic integrity of QSettings/key-binding presentation state;
- recovery of feature external side effects by restoring shell state.

## 57. Developer invariants

Shell changes must preserve these current rules unless deliberately redesigned:

1. workspace navigation must respect current-workspace leave guards;
2. application close must respect application-close/leave guards before destruction;
3. a workspace with owned background work must have a shutdown path the shell can await/retry;
4. shell close must not knowingly destroy a workspace while its shutdown hook reports work still alive;
5. successful dock-state restore must not be immediately overwritten by default rebalance;
6. stable workspace keys/dock object names must remain machine identity independent of localization;
7. application shortcut updates must follow accepted `KeyBindingManager` state;
8. feature business mutations remain behind feature view-model/service layers;
9. Operations Center chrome remains a projection of operation/event state, not its authority;
10. Qt/global exception boundaries must report rather than silently disappear;
11. QSettings/key-binding persistence locations must be documented accurately if they move;
12. presentation status text must not replace semantic workflow result codes;
13. context navigation must still pass through normal guard-aware workspace routing;
14. new global UI state must declare which persistence backend owns it and how backup/reset treats it.

## 58. Audit questions for new shell features

Before adding a new top-level screen/panel/global control, answer:

```text
What is its stable workspace/dock/binding ID?
Who owns its business state?
Can it own background work?
What blocks leaving/closing safely?
How does shutdown complete?
Does it need Operations Center navigation/context?
Does it need an application shortcut?
Where is its user preference persisted?
Is that state workspace-local, QSettings, key-binding JSON, or intentionally ephemeral?
How is it localized/RTL-safe?
What happens when restore/persistence fails?
```

If these answers are unclear, the shell integration is not complete merely because the widget appears.

## Related documentation

- [Architecture Overview](overview.md)
- [Persistence architecture](persistence.md)
- [Localization architecture](localization.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Agents lineage architecture](agents-lineage.md)
- [Automation architecture](automation.md)
- [Interface Tour](../user-guide/interface-tour.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Security, Trust & Privacy Boundaries](../operations/security-boundaries.md)
