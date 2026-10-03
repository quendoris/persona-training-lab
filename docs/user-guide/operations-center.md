# Operations Center: Activity, Issues & Runtime Context

Persona Training Lab exposes operational state through two lower dock panels — **Activity** and **Issues** — plus a compact active-workflow summary in the sidebar and runtime context in the Inspector.

The central rule is:

> **Operations Center is a projection of persisted runtime-operation state plus structured application events. It is not a second workflow engine and it is not a complete forensic ledger.**

For exact event/error payloads, read [Event and diagnostic schema](../reference/event-and-diagnostic-schema.md). For runtime lease semantics, read [Runtime resource safety](../architecture/runtime-resource-safety.md). For incident triage, read [Troubleshooting](../operations/troubleshooting.md).

## 1. What feeds Operations Center

Production composition supplies one `OperationsCenterService` with two read sources:

```text
runtime_operations
    -> active operations
    -> recent operation history

event_log
    -> recent structured application events
```

The service maps both sources into immutable `OperationsCenterItem` records for presentation.

Telemetry does not feed this service. Training feature logs are also a separate stream.

## 2. Activity panel

Activity answers two different questions:

```text
What is active now?
What happened recently?
```

The panel asks the service for:

```text
active_items()
recent_activity(24)
```

and removes active operation IDs from the recent-history section so one active operation is not shown twice.

The UI renders separate **Now** and **Recent** sections when those sets are non-empty.

## 3. Activity refresh lifecycle

The Activity panel uses an in-process Qt timer:

```text
refresh interval = 1000 ms
```

When the panel is hidden, its timer stops. When shown again, the timer restarts and the panel immediately requests a forced refresh.

This timer only refreshes the projection. It does not create or own the underlying runtime operation.

## 4. Runtime-operation projection

A persisted runtime operation contributes fields such as:

```text
operation_id
operation_kind
subject_kind / subject_id
state
correlation_id
started_at / finished_at
error_message
```

Operations Center derives presentation severity from the runtime state:

```text
failed / abandoned    -> error
cancelling / cancelled -> warning
starting / running     -> active
other terminal states  -> success
```

This severity is presentation metadata. The canonical runtime-operation state remains the machine value stored by the runtime coordinator.

## 5. Structured-event projection

Recent Activity can also include structured application events.

Current projection deliberately excludes event types beginning with:

```text
automation.run.
```

from the Activity event list because Automation runs already have persisted runtime-operation rows. The Automation audit event remains in persistent event storage; it is merely not duplicated as a second Activity row for the same run.

Therefore:

> Absence of an Automation audit row from the Activity panel does not mean the audit event was not persisted.

## 6. Recent ordering and deduplication

The service combines recent operation items and eligible event items, de-duplicates them by projected item identity, sorts by `occurred_at` descending, and returns at most the requested limit.

The panel currently requests:

```text
24 recent items
```

This is a bounded operator view, not an unbounded history browser.

## 7. Issues panel

Issues is narrower than Activity.

It reads recent structured events and keeps only:

```text
event_type in {
    application.error,
    application.notice
}

severity in {
    warning,
    error,
    critical
}
```

Informational notices are therefore not Issues.

A clean Issues panel means only that the current query returned no qualifying recent issue. It does not prove that every dependency or workflow is healthy.

## 8. Issues refresh lifecycle

The Issues panel refresh timer is:

```text
1500 ms
```

Like Activity:

- the timer stops while the panel is hidden;
- showing the panel restarts it;
- showing performs an immediate forced refresh.

The service itself remains read-only with respect to the source runtime/event records.

## 9. Localized semantic messages

Structured notices can carry a locale-independent `UserMessage`:

```text
key
values
```

When such a message exists and the current locale knows the key, the panel renders it in the active language.

The same persisted event can therefore render differently after a live locale change without changing its machine identity.

If a persisted message key is unknown, presentation falls back to the diagnostic summary instead of pretending the event is unreadable.

## 10. Correlation identity

Rows can expose or retain:

```text
correlation_id
operation_id
error_id
```

These are evidence/correlation identities, not credentials.

Use them to connect:

```text
Activity / Issues row
        ↕
runtime operation
        ↕
application log / event payload
        ↕
feature-specific evidence
```

Do not infer authorization or ownership from possession of an ID.

## 11. Clicking a row

Activity and Issues rows are interactive.

A projected item can carry:

```text
target_screen
focus_text / focus_key
```

Clicking the row asks the shell to navigate to the related workspace.

When a focus target is available, the shell attempts to highlight a matching visible/enabled control. If no exact visible control can be found, PTL still navigates to the workspace and reports contextual status rather than inventing a hidden target.

This is navigation guidance, not workflow execution.

## 12. Current routing examples

Current operation routing includes mappings such as:

```text
training            -> Training
personality_test    -> Tests
automation_recipe   -> Automation
automation_command  -> Automation
```

Structured application events are routed from their entity/component context when the service can determine a meaningful workspace.

Unknown/unmapped context can fall back to a general workspace instead of manufacturing a false feature identity.

## 13. Sidebar active-workflow summary

The shell separately asks:

```text
OperationsCenterService.active_items()
```

and displays up to six active workflow summaries in the sidebar.

That sidebar block is only another projection of the same persisted runtime-operation source. It does not come from `WorkflowSupervisor`, and it does not own worker lifetime.

## 14. Inspector runtime context

The shell also projects:

```text
active workflow titles
current issue count
```

into the Inspector runtime context.

This gives the current workspace a compact operational summary without replacing Activity/Issues as the detailed operator surfaces.

## 15. Failure isolation

Operations Center read methods are intentionally defensive.

If runtime-operation reads fail:

- `active_items()` returns no active projection;
- recent Activity can still attempt event-log projection.

If event-log reads fail:

- recent operation history can still remain available;
- Issues can become empty because its source is unavailable.

These fallbacks keep the shell usable, but they also mean:

> an empty panel is not proof that its backing persistence layer succeeded.

Use application-log evidence when panel content is unexpectedly absent.

## 16. What Operations Center does not own

Operations Center does **not**:

- start or cancel Training by itself;
- own QThreads;
- own the workspace writer lease;
- replace feature-specific logs;
- roll back failed operations;
- repair abandoned operations;
- persist Telemetry samples;
- guarantee a complete append-only forensic history;
- turn localized labels into machine state.

It is an operational projection/navigation layer.

## 17. Crash and orphan semantics

Startup orphan recovery belongs to the runtime-operation coordinator/bootstrap path, not to Activity/Issues.

When an active persisted operation belongs to a dead owner PID, startup can mark it:

```text
abandoned
```

Operations Center then displays that recovered terminal state.

`abandoned` means the coordination record was recovered. It does not prove external side effects or descendant processes were rolled back.

## 18. Automation-specific boundary

Automation has both:

```text
runtime operation rows
structured automation audit events
```

Activity intentionally suppresses duplicate `automation.run.*` event rows when the runtime operation already represents the run.

For exact Automation audit semantics, use the [Automation architecture](../architecture/automation.md) rather than reconstructing them from the Activity card alone.

## 19. Privacy boundary

Activity/Issues can expose operational metadata such as:

```text
entity IDs
operation kinds
subject IDs
correlation/error IDs
component names
diagnostic summaries
error text
timestamps
```

These can reveal research or host context.

PTL's structured-context redaction is bounded and key-name based; exception text and arbitrary rendered diagnostic content are not guaranteed secret-safe.

Review screenshots and copied diagnostics before sharing them.

## 20. Troubleshooting an empty or stale panel

If Activity/Issues looks wrong:

1. confirm the relevant panel is visible;
2. wait for or trigger the next normal panel refresh by showing it;
3. verify the feature's own status;
4. inspect the rotating application log;
5. record operation/correlation/error IDs when available;
6. verify whether runtime/event persistence itself reported an error;
7. do not delete runtime-operation/event rows merely to make the panel look clean.

For a reproducible incident, preserve the current workspace before destructive repair experiments.

## 21. Developer invariants

Operations Center changes should preserve these rules unless deliberately redesigned:

1. Activity and Issues remain projections, not workflow owners;
2. canonical runtime/event machine state stays separate from localized text;
3. active operations are not duplicated into Activity recent history;
4. `automation.run.*` audit events are not duplicated as Activity rows when runtime-operation identity already represents the run;
5. warning/error/critical application events remain distinct from informational notices in Issues;
6. panel read failures do not crash the shell;
7. navigation guidance must not execute the target workflow automatically;
8. correlation/error/operation IDs remain diagnostic identities, not authorization tokens;
9. hidden panels must not continue their UI refresh timers unnecessarily;
10. documentation must be updated when routing, limits, event filtering, or refresh cadence changes.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
- [Event and diagnostic schema](../reference/event-and-diagnostic-schema.md)
- [Runtime resource safety](../architecture/runtime-resource-safety.md)
- [UI shell architecture](../architecture/ui-shell.md)
- [Automation](automation.md)
