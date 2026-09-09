# Background work lifecycle and shutdown ownership

Status: **current implementation contract** for PTL desktop background work on the v1.0 candidate branch.

This document answers a narrow but safety-critical question: **what actually owns long-running work in PTL, how does application shutdown wait for it, and which objects are merely status registries rather than execution supervisors?**

The distinction matters because PTL holds a cooperative writer lease for the workspace. That lease must not be released while a background owner can still mutate workspace state.

## 1. Executive contract

PTL does not have one universal background-job scheduler.

Current runtime work is split across three different mechanisms:

```text
UI-owned worker lifetime
    -> QThread owned by a workspace screen

persistent resource coordination
    -> RuntimeOperationCoordinator + SQLite runtime operations/claims

application/workspace lifetime
    -> MainWindow shutdown aggregation
       + bootstrap final drain
       + WorkspaceOwnership lease
```

A fourth type, `WorkflowSupervisor`, exists in `application.workflows`, but it is **not** the authority for current Training, Tests, Automation process lifetime, runtime leases, or shell shutdown.

The standard desktop shutdown rule is:

> **The workspace writer lease is retained until every registered workspace background owner reports that its worker has stopped.**

This protects the handoff between one PTL desktop process and the next cooperating process that opens the same workspace.

## 2. Why there are several lifecycle layers

The mechanisms answer different questions.

### UI worker lifetime

“Is the Python/Qt worker still executing work on behalf of this screen?”

### Runtime operation lifetime

“Which semantic resources are currently claimed by a persisted PTL operation, and would another operation conflict?”

### Workspace ownership lifetime

“May another normal PTL desktop process begin mutable bootstrap against this workspace?”

Those questions are related but not equivalent.

For example, a Training worker can execute a synchronous backend call inside a `QThread` while its `RuntimeOperationLease` records the semantic resource claims for the Training operation. The thread object and SQLite lease have different purposes and different cleanup paths.

## 3. Workspace screens are the current worker owners

`WorkspaceStack` stores the live workspace widgets registered in the main window.

For shutdown, `MainWindow.shutdown_background_work()` iterates every registered workspace and dynamically looks for:

```text
shutdown_background_work(timeout_ms)
```

A workspace without that method is treated as having no shell-managed background worker.

This is the current registration contract. There is no separate central table of QThreads in the bootstrap container.

The shell therefore owns shutdown **through the workspace objects that own the workers**, rather than by inspecting arbitrary Python threads globally.

## 4. Training worker lifetime

`TrainingScreen` currently owns two possible `QThread` workers:

```text
local inference
training start/run service call
```

The worker objects execute synchronous view-model methods in those threads.

`TrainingScreen.shutdown_background_work(timeout_ms)`:

1. stops its polling timer;
2. closes the Training logs dialog;
3. visits both known worker threads;
4. calls `thread.quit()` for a running thread;
5. waits only for the supplied remaining timeout budget;
6. returns `False` if either thread remains alive.

The crucial boundary is:

> `QThread.quit()` requests termination of the thread's Qt event loop; it does not forcibly interrupt arbitrary synchronous Python/model-training code that is already executing in the worker callback.

Therefore PTL does not claim instant cancellation of full fine-tuning during application shutdown.

If the synchronous Training call is still running, the application can remain in shutdown-drain state while continuing to own the workspace.

## 5. Tests / evaluation worker lifetime

`TestsScreen` owns one `QThread` for synchronous evaluation execution.

The current sequence is:

```text
begin_run()
    ↓
create QThread + _TestsWorker
    ↓
worker.run()
    ↓
TestsViewModel.run_tests_sync()
    ↓
ExperimentsService evaluation workflow
```

`TestsScreen.shutdown_background_work(timeout_ms)` closes the cases dialog, requests `thread.quit()`, optionally waits for the supplied timeout and returns whether the thread is actually stopped.

Like Training, this is **not a force-cancellation primitive** for a synchronous model-generation/evaluation call already executing inside the worker.

This screen participates in the shell-wide shutdown aggregation so the workspace lease is not released merely because the top-level window or Qt event loop is closing.

## 6. Automation worker lifetime is stronger

`AutomationScreen` owns one QThread and one `_AutomationRunWorker` for the selected recipe/ad-hoc command.

Its shutdown path first calls:

```text
worker.cancel()
```

which sets a cooperative cancellation flag consumed by `AutomationService` / process execution.

The Automation process runner additionally owns OS-level process-tree containment:

```text
POSIX
    new process session/group
    SIGTERM
    grace period
    SIGKILL if necessary

Windows
    Job Object
    kill-on-close / explicit termination
```

So Automation shutdown has two layers:

```text
UI worker cooperative cancellation
        +
contained child-process termination
```

This is stronger than the current Training/Tests shutdown contract. It still does not make Automation a filesystem/network sandbox; containment is a process-lifetime property, not a host-effect rollback mechanism.

## 7. Main-window shutdown aggregation

The outer `ui.shell.main_window_background.MainWindow` implements the application-level background-work guard.

`shutdown_background_work(timeout_ms)`:

1. creates one total deadline from the supplied timeout;
2. iterates every registered workspace;
3. calls each callable `shutdown_background_work(remaining_ms)`;
4. does not stop visiting later owners merely because an earlier owner failed to stop;
5. returns `True` only when every participating owner reports stopped.

This means the timeout is a **shared total budget**, not a fresh full timeout for every workspace.

## 8. Normal close is deliberately non-blocking on the GUI thread

`MainWindow.closeEvent()` does not wait several seconds in the GUI event handler.

The sequence is:

```text
request current workspace close/leave guard
        ↓
shutdown_background_work(0)
        │
        ├── all stopped
        │      ↓
        │   save shell state
        │      ↓
        │   accept close
        │
        └── something still running
               ↓
            ignore close event
               ↓
            show background-shutdown status
               ↓
            schedule retry after 250 ms
```

The leave/close guard is latched after it succeeds so a delayed shutdown does not repeatedly ask the current workspace to approve the same application close.

This keeps the Qt GUI responsive while workers finish.

## 9. Event-loop exit has a second safety net

Normal window-close handling is not the only possible way `app.exec()` can return.

Bootstrap therefore contains a second boundary:

```text
try:
    return app.exec()
finally:
    if window exists:
        _drain_background_work(window)
    workspace_ownership.release()
```

`_drain_background_work()` repeatedly calls:

```text
window.shutdown_background_work(slice_ms=500)
```

and sleeps briefly between unsuccessful attempts until all registered owners report stopped.

Only after that drain returns is `WorkspaceOwnership.release()` executed.

This ordering is a safety invariant:

```text
background workspace owners stopped
        ↓
workspace writer lease may be released
```

not the reverse.

## 10. Why the final drain matters

Without the final drain, this sequence would be possible in principle:

```text
process A Qt event loop exits
        ↓
process A worker still mutates workspace
        ↓
process A releases .ptl-workspace.lock
        ↓
process B acquires workspace ownership
        ↓
process A and B overlap mutable generations
```

That would defeat the single-writer-per-workspace contract even though both desktop processes individually obeyed `WorkspaceOwnership`.

The final drain closes that handoff gap for registered workspace-owned workers.

## 11. `aboutToQuit` is advisory cleanup, not the ownership proof

Bootstrap also connects:

```text
app.aboutToQuit -> window.shutdown_background_work
```

This gives workers an early shutdown opportunity while Qt is leaving the event loop.

However, Qt does not use the Python boolean return value of that signal handler to decide whether it may quit.

Therefore the `aboutToQuit` callback is **not** the proof that all work stopped.

The proof used for workspace-ownership release is the subsequent blocking `_drain_background_work()` loop in bootstrap.

## 12. RuntimeOperationCoordinator is not the QThread supervisor

`RuntimeOperationCoordinator` persists semantic operation identity and resource claims through its repository.

For the SQLite atomic repository, operation creation can perform conflict detection and claim insertion inside one repository-level atomic transaction.

Its responsibilities include concepts such as:

```text
operation ID
operation kind
subject identity
owner PID
state
heartbeat
resource read/write claims
conflict detection
crash/orphan recovery
```

It does **not** own Qt thread objects and does not replace screen `shutdown_background_work()`.

Likewise, stopping a QThread is not equivalent to proving that every runtime-operation row has reached its intended terminal semantic state. Feature services own that transition logic.

## 13. Operations Center is observational/projection infrastructure

The shell's live active-workflow chrome, Activity and Issues surfaces are fed by `OperationsCenterService`, which reads runtime operations and event evidence.

That visible activity stream must not be confused with ownership of worker execution.

The Operations Center can describe and route to work; the screen/feature service still owns the actual worker and semantic operation lifecycle.

## 14. `WorkflowSupervisor` has a much smaller current role

The repository also contains:

```text
application/workflows/state.py
application/workflows/supervisor.py
```

`WorkflowSupervisor` is currently an in-memory dictionary keyed by `workflow_id` with three operations:

```text
register(state)
finish(workflow_id)
list_active()
```

`ShellViewModel` receives one `WorkflowSupervisor` from the composition root and exposes:

```text
active_workflow_count()
```

as the length of `list_active()`.

Current audited composition does **not** make this object the authority for:

- Training QThreads;
- Tests/evaluation QThreads;
- Automation QThreads or child processes;
- persisted runtime-operation leases;
- Operations Center active items;
- application close/drain;
- workspace ownership release.

Accordingly, documentation must not describe `WorkflowSupervisor` as the current background-job scheduler or lifecycle coordinator.

Its present implementation is best classified as a **small in-memory workflow-state registry / compatibility abstraction** unless future audited code gives it a stronger role.

Whether it should remain, be renamed, or be removed as architectural residue is a separate code-design decision. This document records current behavior rather than inventing a rationale.

## 15. Worker lifetime and runtime lease lifetime can diverge during failures

A robust mental model is:

```text
QThread lifetime
    = execution carrier lifetime

RuntimeOperation lifetime
    = persisted semantic coordination lifetime

WorkspaceOwnership lifetime
    = outer cooperating-desktop writer lifetime
```

A crash can interrupt the first while leaving the second persisted. Startup recovery then detects runtime operations whose recorded owner PID is no longer alive and marks them `abandoned`.

That recovery does not reconstruct or roll back arbitrary model/filesystem side effects.

Conversely, a live worker must not be considered harmless merely because a UI status stopped updating.

## 16. Current cancellation matrix

| Work type | UI thread | Cooperative cancel request | Child-process containment | Shutdown may wait for synchronous work |
|---|---|---|---|---|
| Local model smoke/inference from Training screen | yes | no dedicated interrupt in screen shutdown | no | yes |
| Full Training service call | yes | no dedicated force-cancel in screen shutdown | backend-specific work, not a generic shell child-process kill contract | yes |
| Tests/evaluation | yes | no dedicated force-cancel in screen shutdown | no generic shell containment | yes |
| Automation | yes | yes, worker cancellation flag | yes, POSIX process group / Windows Job Object | yes, until worker/process terminates |

This table describes application-close behavior, not every feature-specific runtime state or timeout.

## 17. What the shell does not promise

The current background-work contract does not claim that:

- arbitrary third-party threads are discovered automatically;
- every future workspace is safe merely because it inherits `QWidget`;
- `QThread.quit()` interrupts synchronous Python or native model execution;
- closing PTL rolls back partially produced Training artifacts;
- closing PTL reverses Automation host effects;
- runtime-operation recovery proves every descendant process is gone after an abnormal OS failure;
- background work outside registered workspace ownership is automatically included in the final drain.

A new long-running workspace feature must therefore explicitly join the shutdown ownership contract.

## 18. Extension rule for new background work

A new feature that starts work capable of surviving beyond one GUI event handler should answer all of the following before release:

1. **Who owns the worker object?**
2. **How is duplicate start prevented?**
3. **Does it need persisted runtime resource claims?**
4. **How does normal completion reach a terminal state?**
5. **How does application shutdown request cancellation/termination?**
6. **Can shutdown safely wait if force-cancellation is impossible?**
7. **Does its workspace expose `shutdown_background_work(timeout_ms)`?**
8. **What happens after crash/restart?**
9. **Which filesystem/external side effects may remain after failure?**
10. **Which tests prove the close/drain contract?**

If those answers are absent, the feature is not yet integrated into the current workspace-lifetime architecture.

## 19. Test evidence

`tests/test_background_close_guard.py` currently covers important shell/worker invariants, including:

- close retries do not repeat the already-passed workspace leave guard;
- shell shutdown visits every registered background owner;
- Training shutdown does not pretend a still-running worker stopped;
- Tests/evaluation participates in the same shell close guard;
- Automation requests cooperative cancellation before waiting;
- the final bootstrap drain retries instead of treating one unsuccessful stop attempt as permission to release ownership.

Feature-specific Training, Tests, Automation and runtime-operation tests provide additional behavior coverage outside this narrow shutdown suite.

This is test evidence for the implemented contract, not proof that arbitrary future worker implementations automatically comply.

## 20. Relationship to workspace ownership

The lifecycle hierarchy is:

```text
WorkspaceOwnership (.ptl-workspace.lock)
        │
        ├── application / Qt event-loop lifetime
        │       │
        │       └── MainWindow background-owner aggregation
        │               │
        │               ├── Training workers
        │               ├── Tests/evaluation worker
        │               └── Automation worker/process tree
        │
        └── released only after final registered-worker drain
```

Persisted runtime-operation leases run orthogonally through feature services inside that ownership envelope.

## 21. Related documents

- [Workspace concurrency and ownership](workspace-concurrency.md)
- [UI shell architecture](ui-shell.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Persistence architecture](persistence.md)
- [Automation architecture](automation.md)
- [Training pipeline specification](../training_pipeline.md)
- [Backup, reset and recovery](../operations/backup-reset-recovery.md)
- [Troubleshooting and diagnostic evidence](../operations/troubleshooting.md)
