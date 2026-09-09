# Workspace concurrency and ownership

Status: **current implementation contract** for the desktop bootstrap path on the v1.0 candidate branch.

This document answers one narrow question: **which concurrency guarantees apply when PTL reads and mutates one workspace?** It deliberately separates in-process locks, SQLite transaction guarantees, process ownership, and atomic file replacement. Those mechanisms solve different problems and must not be treated as interchangeable.

## 1. Executive contract

The production desktop bootstrap is a **single-writer-per-workspace** application.

Before `build_container()` opens `app.db`, performs schema bootstrap, recovers abandoned runtime operations, or constructs mutable workspace services, `bootstrap.app.main()` creates a `WorkspaceOwnership` object for the resolved `AppSettings.workspace_dir` and acquires a Qt `QLockFile` at:

```text
<workspace>/.ptl-workspace.lock
```

If that writer lease cannot be acquired, the second PTL desktop process exits with status `2` and does not continue into mutable workspace bootstrap.

The lease remains held for the lifetime of the Qt event loop and is explicitly released after `app.exec()` returns, including exceptional exit from the guarded bootstrap block.

This is a **cooperative application ownership rule**, not a filesystem access-control boundary. Another program, a manually started internal PTL component, or code that bypasses the standard desktop bootstrap can still access workspace files if the operating system permits it.

## 2. Why the writer lease exists

PTL does not store all mutable state in one transactional database.

Important state currently spans at least:

- `<workspace>/app.db`;
- `<workspace>/agents_lineage_state.json`;
- training/model artifacts below `<workspace>/artifacts/`;
- Automation recipe and audit-related workspace files;
- external Dataset/model paths referenced by records;
- Qt `QSettings` state outside the workspace;
- `~/.persona_training_lab/key_bindings.json` outside the workspace.

SQLite can serialize conflicting database writers, but it cannot make a transaction atomic with `agents_lineage_state.json` or arbitrary filesystem artifacts. `AtomicLineageStateStore` protects one JSON replacement from being torn; it does not by itself perform compare-and-swap against another process that loaded an older JSON generation.

Without a workspace-level writer rule, two desktop processes could therefore observe different generations and independently perform valid local operations whose combination loses state or breaks a cross-store invariant. A particularly dangerous startup interaction is runtime recovery: a second process must not classify the first process's active operations as abandoned merely because it started later.

For the v1.0 desktop architecture, preventing concurrent mutable PTL owners is simpler and stronger than pretending every store participates in one distributed transaction.

## 3. Concurrency layers

### 3.1 Process ownership

`WorkspaceOwnership` is the outermost mutable-workspace guard.

It canonicalizes the workspace path with `Path.resolve()`, ensures the directory exists, and asks `QLockFile.tryLock(0)` for immediate ownership. There is no waiting queue in the current bootstrap contract: a process either owns the workspace when it starts or fails closed.

The lock filename is an implementation detail of the current contract. It is not user data and must not be copied as evidence that a backup was taken while PTL was offline.

### 3.2 In-process repository serialization

Most repositories sharing the main writable SQLite connection use `RepositoryLock`, which wraps `threading.RLock`.

That lock serializes access between threads in **one Python process** when those repositories share the same lock/connection context. It is not an interprocess mutex and does not protect a second process.

The workspace writer lease is therefore not redundant with `RepositoryLock`.

### 3.3 SQLite transaction isolation

`app.db` is opened with:

```text
foreign_keys = ON
journal_mode = WAL
synchronous = NORMAL
busy_timeout = 5000
```

Normal repository write helpers use an application transaction wrapper around the shared writable connection.

Runtime resource acquisition is stronger: `SQLiteRuntimeOperationsRepository.try_create_operation()` performs the conflict check and claim inside an immediate SQLite transaction. `RuntimeOperationCoordinator` requires an immediately transactional repository because correctness depends on another database connection not interleaving a conflicting claim between the check and the insert.

That database guarantee remains valuable even with single desktop ownership: it protects the atomicity of the runtime-operation database protocol and makes the repository contract explicit. It must not be reinterpreted as a guarantee that all PTL filesystem/JSON state is safe under multiple desktop writers.

### 3.4 Atomic Agents JSON replacement

`AtomicLineageStateStore` writes a complete JSON payload to a temporary file in the same directory, flushes and `fsync()`s that file, then publishes it with `os.replace()`. Directory `fsync()` is attempted as a best-effort durability step.

This provides **atomic publication of one writer's complete payload** and process-local memory rollback when publication fails.

It does not provide:

- a generation number shared with another process;
- compare-and-swap against the file generation originally loaded;
- an interprocess read/modify/write lock;
- an ACID transaction with `lineage_resource_links` in SQLite.

Cross-store branch creation and protected Undo/Redo therefore use explicit compensation and recorded safety metadata, while the outer workspace writer lease prevents a second desktop process from concurrently running another such protocol.

### 3.5 Preferences outside the workspace

`WindowStateStore` persists shell state through Qt `QSettings`. `KeyBindingManager` persists keyboard/mouse bindings to `~/.persona_training_lab/key_bindings.json` using temporary-file replacement.

These stores are outside the workspace ownership boundary. The current product contract prevents two standard PTL desktop processes from sharing the **same workspace**, but it is not a global per-user application singleton. If future product work permits two different workspaces to be open concurrently, both processes may still address the same QSettings/key-binding preference stores.

That is a separate concurrency problem and must not be hidden by the workspace lock. The current v1.0 product does not claim cross-process transactional semantics for those preference stores.

## 4. What the lease does and does not prove

When the standard desktop bootstrap owns `<workspace>/.ptl-workspace.lock`, PTL may rely on there being no second cooperating desktop bootstrap mutating that same workspace concurrently.

The lease does **not** prove that:

- no external program has opened `app.db`;
- no user is manually editing JSON/artifacts;
- a copied workspace is quiescent;
- a network/distributed filesystem implements every local-filesystem locking semantic identically;
- subprocesses launched by PTL are automatically contained by the lock file;
- QSettings or home-relative key bindings are exclusively owned.

For backup and recovery, the operational requirement remains: stop PTL and any relevant child/background work before copying a workspace snapshot.

## 5. Failure semantics

### Writer lease unavailable

The desktop bootstrap reports that the workspace is already open for writing and returns exit status `2` before constructing the application container.

It does not:

- open the workspace database through `build_container()`;
- run runtime-operation orphan recovery;
- create the main window;
- silently downgrade to a second writable instance.

### Failure after ownership is acquired

The bootstrap holds the writer lease around container construction and the entire event loop. The `finally` boundary releases it if container construction, UI setup, or the event loop exits by exception.

This ownership cleanup does not replace subsystem-specific rollback, shutdown, or recovery logic.

## 6. Test contract

`tests/test_workspace_ownership.py` covers two properties:

1. a second `WorkspaceOwnership` object cannot acquire the same workspace while the first owns it, and the workspace becomes acquirable after release;
2. the same exclusion is verified with a separate Python process, not only two objects in one interpreter.

The test is part of the blocking quick release inventory.

This proves the PTL wrapper's expected lock behavior in the release environment. It does not prove every external filesystem or deployment environment has identical locking behavior.

## 7. Architectural consequence

The current consistency model is intentionally layered:

```text
standard desktop bootstrap
        |
        v
workspace writer lease (cross-process, cooperative)
        |
        +--> RepositoryLock (in-process thread serialization)
        |
        +--> SQLite transactions / BEGIN IMMEDIATE where required
        |
        +--> atomic file replacement for lineage JSON
        |
        +--> explicit compensation for JSON <-> SQLite protocols
```

Removing the writer lease in the future would be an architectural change, not a bootstrap cleanup. Multi-writer support would require explicit generation/conflict semantics for non-SQLite stores and a new answer for cross-store protocols, startup recovery, preference ownership, and filesystem artifacts.

## 8. Related documents

- [Persistence architecture](persistence.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Agents lineage](agents-lineage.md)
- [Persistence schema](../reference/persistence-schema.md)
- [Backup, reset, and recovery](../operations/backup-reset-recovery.md)
- [Troubleshooting](../operations/troubleshooting.md)
