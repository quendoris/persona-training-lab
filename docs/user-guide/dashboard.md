# Dashboard

Dashboard is Persona Training Lab's read-only orientation and workflow-routing workspace.

It aggregates current state from the main v0.1.0 workflow services and turns that state into summaries, attention hints, lineage shortcuts and a suggested next action. It does **not** own the underlying Training, Dataset, model-version, evaluation or lineage records.

The central rule is:

> **Dashboard summarizes and routes; the owning workspace remains authoritative for every underlying operation.**

## 1. What Dashboard reads

Production composition gives `DashboardViewModel` these services:

```text
ProjectsService
TrainingService
ModelVersionsService
DatasetsService
ExperimentsService
```

The four workflow services after Projects are present in normal production wiring. Their presence selects the current live-workflow Dashboard mode.

Dashboard does not write through those services.

## 2. Projects is a compatibility/fallback source

The SQLite schema still contains:

```text
projects
```

and `ProjectsService` exposes read-only:

```text
list_projects()
```

There is no current Projects workspace and no Dashboard create/edit/delete project action.

When none of the live workflow services is connected, Dashboard can fall back to a Projects count/latest-project summary. In normal production wiring, Dashboard instead presents Training, Snapshots/model versions, Datasets and portrait/evaluation state.

Therefore the existence of the `projects` table must not be documented as a complete current project-management feature.

## 3. Screen structure

The current Dashboard screen contains:

```text
header
stats grid
quick actions
recent activity
system/workflow progress
attention
quick lineage
```

The center/main column carries stats, actions, activity and progress. The side column carries attention and lineage summaries.

Dashboard refreshes all of these projections when the screen is shown.

## 4. Dashboard is not Operations Center

Dashboard's **Recent activity** is feature-summary activity derived from current workflow records.

The lower **Activity** dock belongs to Operations Center and projects persisted runtime operations plus structured events.

Keep these separate:

```text
Dashboard recent activity
    -> latest Training/version/portrait/Dataset summaries

Operations Center Activity
    -> runtime_operations + event_log
```

See [Operations Center](operations-center.md) for the runtime/event contract.

## 5. Stats in normal production mode

When live workflow services are available, the four Dashboard stat cards summarize:

```text
Training
Snapshots/model versions
Datasets
Portrait/evaluation
```

Examples of what they use:

- latest Training status/title;
- number of model versions and latest version;
- Dataset count/readiness summary;
- latest portrait factor-score line when parseable.

These are projections of feature state, not duplicate persisted Dashboard records.

## 6. Project fallback stats

If no live workflow services are connected, Dashboard falls back to the read-only Projects source.

The fallback can display:

```text
project count
latest project title
latest project status
```

A Projects read failure becomes an unavailable/load-failed presentation rather than a shell crash.

This fallback is primarily compatibility/scaffolding behavior in the current product composition.

## 7. Quick actions

Dashboard currently exposes three navigation-oriented quick actions:

```text
1. suggested next step
2. build/open portrait workflow
3. open Analysis
```

The cards are keyboard-focusable and can be activated with Return, Enter or Space as well as the mouse.

Activation emits a route to the shell. Dashboard itself does not execute the target workflow.

## 8. Suggested next-step state machine

The current next-step logic follows the available workflow state approximately in this order:

```text
workflow services unavailable
    -> Documentation

no Dataset
    -> Datasets / Add

no approved Dataset
    -> Datasets / Validate/approve

no Training run
    -> Training / Create run

latest Training unfinished and no artifact
    -> Training / Start/finish

no registered model version
    -> Snapshots / Refresh

no portrait
    -> Tests / Build portrait

latest portrait has failures
    -> Tests / Build/repair portrait

fewer than two portraits
    -> Training / continue workflow toward another version/portrait

otherwise
    -> Analysis
```

This is navigation guidance, not a workflow scheduler and not proof that the suggested action is the only valid next action.

## 9. Recent feature activity

Dashboard builds up to four recent summary rows from the latest available:

```text
Training run
model version
portrait
Dataset
```

If none of those exists but a compatibility Project row exists, that Project can be shown instead.

If there is no usable activity, Dashboard shows an empty state that routes toward adding a Dataset.

The rows navigate to the owning workspace.

## 10. Workflow progress bars

The **System** card is a product-workflow readiness/progress view, not host hardware telemetry.

It currently summarizes:

```text
Training progress
Dataset readiness
portrait readiness
snapshot/model-version presence
```

Do not confuse these bars with the lower Telemetry dock's CPU/RAM/GPU measurements.

## 11. Attention cards

Dashboard attention combines current workflow guidance with portrait/comparison context.

It can include:

- the current suggested next step;
- latest portrait condition;
- an arithmetic factor delta when at least two parseable portraits provide common scores;
- a documentation/protocol reminder.

The Dashboard delta presentation is an orientation summary. The canonical scientific comparison rules remain in Analysis and the Evaluation contract.

## 12. Quick lineage

The Dashboard quick-lineage section projects the latest available chain-like identities:

```text
base model
Dataset
Training run
model version / Snapshot
portrait
```

Each row routes to the owning feature workspace.

This is a convenience projection. Agents remains the dedicated integrated lineage workspace.

## 13. Identity and labels

Dashboard routes using explicit `DashboardRoute` values and displays values taken from service summaries.

Human-readable titles are presentation data. Stable run/version/entity IDs remain the stronger machine identity where supplied by the underlying service.

Dashboard must not reconstruct entity identity by parsing a displayed localized label.

## 14. Status compatibility

Dashboard contains a presentation compatibility normalizer for several historical English/Russian status spellings.

That normalizer exists to render mixed/legacy service values coherently.

It is not permission for new persistence code to write localized Dashboard labels as canonical domain status.

Use each owning subsystem's canonical status contract for new state.

## 15. Portrait parsing boundary

Dashboard derives portrait score summaries from persisted experiment payloads.

This is a compact orientation projection and does not replace the full Tests/Analysis parser/contract.

If stronger comparison semantics matter, use:

- [Tests and Analysis](tests-and-analysis.md);
- [Evaluation & Analysis architecture](../architecture/evaluation-analysis.md);
- [Evaluation contract](../reference/evaluation-contract.md).

## 16. Refresh behavior

`DashboardScreen.showEvent(...)` refreshes the complete Dashboard projection.

A user returning to Dashboard therefore gets a fresh read from the view-model/service layer rather than only the values captured when the application window was first constructed.

Dashboard does not run a continuous polling timer while visible.

## 17. Navigation and focus guidance

A `DashboardRoute` contains:

```text
screen
focus_key
```

The screen emits the target and localized focus text to the shell.

The shell navigates to the requested workspace and, when possible, highlights a matching visible/enabled control.

A focus hint is guidance only; it does not invoke the control automatically.

## 18. Failure boundaries

Dashboard service reads are defensive.

Feature-specific helper methods return empty projections when the optional/read source fails, allowing the rest of the Dashboard to remain usable.

That means an empty card can represent either truly absent state or unavailable source data depending on the path. Use the owning workspace and Issues/application log when the distinction matters.

Do not treat Dashboard as the only evidence source for a workflow failure.

## 19. Localization boundary

Dashboard presentation uses semantic localization keys and structured values.

Routes, entity IDs, raw machine identifiers and underlying service state are not translated before persistence.

Changing locale re-renders the Dashboard without changing workflow identity.

## 20. What Dashboard does not do

Dashboard does not currently provide:

- a Projects CRUD workspace;
- creation/edit/deletion of `projects` rows;
- Training execution ownership;
- Dataset validation ownership;
- model-version registration ownership;
- portrait inference ownership;
- canonical protocol comparison authority;
- runtime-operation/event-log history ownership;
- host Telemetry sampling;
- an independent persistence table for Dashboard cards.

It is an aggregation and routing surface.

## 21. Developer invariants

Dashboard changes should preserve these rules unless deliberately redesigned:

1. underlying feature services remain authoritative for their state;
2. Dashboard actions navigate rather than secretly execute target workflows;
3. current production mode uses live workflow services when they are present;
4. the Projects table/service is not documented as a full current project-management feature while it remains read-only fallback state;
5. Dashboard activity remains distinct from Operations Center runtime/event activity;
6. workflow progress bars remain distinct from host Telemetry;
7. status compatibility rendering must not become a new localized persistence contract;
8. explicit routes/IDs outrank parsing visible titles;
9. Analysis/Evaluation remains the authority for scientific comparison semantics;
10. documentation must change if Dashboard gains a real mutating workflow rather than only projection/routing.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Operations Center](operations-center.md)
- [Telemetry](telemetry.md)
- [Training](training.md)
- [Datasets](datasets.md)
- [Snapshots and model versions](snapshots.md)
- [Tests and Analysis](tests-and-analysis.md)
- [Agents lineage](agents-lineage.md)
- [Evaluation & Analysis architecture](../architecture/evaluation-analysis.md)
