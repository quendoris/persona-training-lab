# Interface Tour

This guide explains the stable v1.0 desktop shell before you begin a specific workflow.

You do not need to understand PTL's internal architecture to use the interface. The goal of this page is spatial: know where navigation lives, where feature work happens, where PTL reports context and problems, and which workspace to open for a task.

> The final v1.0 screenshot set will add a numbered full-window reference image to this page. The text below is written so the guide remains usable without that image.

## 1. The window at a glance

The main window has four functional regions:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Sidebar │                 Active workspace              │ Inspector │
│         │                                               │           │
│         │                                               │           │
│         │                                               │           │
├─────────┴───────────────────────────────────────────────┴───────────┤
│         Activity / Telemetry / Issues dock area                     │
├─────────────────────────────────────────────────────────────────────┤
│ Status bar                                                          │
└─────────────────────────────────────────────────────────────────────┘
```

The exact dock sizes can change with screen density, user resizing, floating docks, and which panels are visible. The conceptual structure does not change.

## 2. Sidebar

The left sidebar is the primary navigation surface.

It contains navigation for the main PTL workspaces and shell-level controls such as panel visibility, appearance controls, UI scale, and active-workflow information.

A navigation item becomes the current workspace when selected. PTL also synchronizes the Inspector and status bar with the selected workspace.

### Stable navigation geometry

PTL keeps the physical navigation geometry stable for both LTR and RTL languages:

- the navigation icon/badge remains on the left;
- the active indicator remains on the right;
- Arabic text aligns appropriately inside the text area without mirroring the entire shell.

This matters because the interface can switch to Arabic at runtime without moving the entire application topology.

## 3. Active workspace

The large central area is the `WorkspaceStack`.

Only one main workspace is active at a time. Switching workspaces does not launch a second application window; the shell replaces the central feature surface while keeping the sidebar, docks, and status bar available.

Before PTL leaves a workspace it can ask that workspace whether leaving is currently safe. This is used to prevent navigation/closing from silently discarding state in flows that own a leave guard.

## 4. Inspector

The Inspector is a dock panel placed on the right by default.

Its context follows the active workspace. Use it as a supporting information surface rather than a second navigation tree.

The Inspector can be:

- moved;
- closed;
- floated;
- restored from the Panels menu in the sidebar.

## 5. Bottom docks

PTL provides three bottom supporting panels:

### Activity

Activity is the operational surface for work occurring in the application. It is intended to help answer: *what is PTL doing?*

### Telemetry

Telemetry presents system observations from the available telemetry providers, including general process/system data and NVIDIA GPU information when NVIDIA-SMI data is available.

### Issues

Issues is the problem-oriented surface. It complements the persistent error/event infrastructure by giving the UI a dedicated place to surface failures and warnings.

Activity, Telemetry, and Issues share the bottom dock area as tabs by default. They can also be moved, closed, or floated.

## 6. Panels menu

The normal menu bar is hidden in the v1.0 shell. Dock visibility is controlled from the **Panels** menu exposed through the sidebar.

Use it when you close Inspector, Activity, Telemetry, or Issues and want the panel back.

Closing a dock is not the same as disabling the underlying subsystem. For example, hiding Telemetry changes the visible shell, not the persistence model of the rest of PTL.

## 7. Status bar

The status bar spans the bottom of the main window.

It reports application/workspace status and also shows the current style context, including the selected theme/accent/density information.

When you navigate, the status text updates to identify the current workspace.

## 8. Workspace map

PTL v1.0 registers twelve main workspaces.

### Dashboard

**Use Dashboard when:** you need a high-level view of the current PTL workspace and the state of major working areas.

Dashboard is an overview, not the owner of the underlying records. Actions that belong to Profiles, Datasets, Training, and other systems remain owned by those systems.

### Profiles

**Use Profiles when:** you are creating or maintaining the personality definition used by later workflows.

Profiles persist structured persona/profile state. They are referenced by dataset/training/evaluation flows rather than being only free-form notes.

### Agents

**Use Agents when:** you need to inspect and operate on model/persona lineage.

Agents is one of the most interaction-dense PTL workspaces. It includes lineage/version relationships, history navigation, graph interaction, context navigation, and guarded destructive branch operations.

Do not treat the graph as a decorative visualization. It reflects persistent lineage/resource relationships and participates in runtime safety.

A dedicated [Agents & Lineage](agents-lineage.md) guide will document gestures, history semantics, selection/context behavior, and deletion safety in detail.

### Datasets

**Use Datasets when:** you need to import, validate, inspect, or manage dataset records/versions used by PTL workflows.

Dataset persistence includes source path/format, validation counts, readiness information, linked profile information, and validation diagnostics.

A dedicated dataset workflow guide will explain supported import/validation behavior step by step.

### Training

**Use Training when:** you need to inspect the local model and create/monitor training work.

Training integrates profile, dataset, local-model, runtime-operation, artifact, and model-version concerns. Because training can be long-running and resource-sensitive, follow the Training guide rather than treating every control as a harmless preview action.

Inference/training Python dependencies are optional installation extras; the core PTL shell can launch without installing the complete model-training stack.

### Snapshots

**Use Snapshots when:** you need to inspect or work with persisted snapshot/version state exposed by the snapshot workflow.

Snapshots should be understood as explicit persistent product state, not as the same thing as copying the whole PTL workspace directory. Workspace backup/reset is documented separately.

### Tests

**Use Tests when:** you need to run or inspect the product's personality/evaluation testing workflows.

The Tests workspace can direct the shell to Analysis when a result needs deeper analysis.

This workspace is unrelated to the repository's `pytest` developer test suite. User-facing Tests are product evaluation workflows; `pytest` validates PTL itself.

### Analysis

**Use Analysis when:** you need to inspect stored analysis/evaluation results and comparisons.

The analysis persistence model includes left/right comparison fields, deltas, insights, and example output comparisons.

### Style

**Use Style when:** you want to change visual presentation or interface language.

The v1.0 style surface includes theme/accent choices and application UI language. UI density/scale also participates in the shell's presentation model.

Changing language does not require restarting PTL.

Complete v1.0 catalogs ship for:

- Arabic (`ar`);
- English (`en-US`);
- Spanish (`es-ES`);
- Russian (`ru-RU`).

Arabic uses RTL text behavior without mirroring the complete shell geometry.

### Automation

**Use Automation when:** you want PTL to execute an explicit workspace automation recipe/command under the Automation execution controls.

Automation is powerful. Commands execute with the permissions of the PTL process and operating-system account. PTL provides lifecycle controls and audit metadata; it does not transform arbitrary commands into sandboxed untrusted code.

Read the Automation guide before using recipes that modify files, spawn child processes, or affect external tools.

### Key bindings

**Use Key bindings when:** you need to inspect or customize keyboard/mouse interaction mappings exposed by PTL.

This is particularly important for Agents, where history/navigation gestures have explicit routing and ownership rules.

### Documentation

**Use Documentation when:** you want the documentation surface available from inside PTL.

The repository `docs/` tree is the canonical documentation source. The in-app Documentation workspace reads packaged documentation rather than relying on the process current working directory.

## 9. Themes, accents, and density

The shell loads saved style preferences during startup and applies theme/accent before normal interaction.

The status bar reflects the active theme/accent/density context.

UI scale is not the same as operating-system display scaling. PTL applies its own density/scale system on top of the Qt application environment.

When documenting or reporting a layout problem, include:

- screen resolution;
- PTL UI scale/density;
- selected locale;
- selected theme/accent;
- whether a dock is floating or docked.

These variables materially affect geometry.

## 10. Languages and RTL

PTL's localization behavior is intentionally split into two concepts:

1. **Application geometry** — sidebar, workspace, docks, icon reservations and major layout remain stable.
2. **Text direction** — Arabic text leaves and mixed-direction content receive appropriate RTL/LTR handling.

Do not expect Arabic mode to move the sidebar to the right. That would violate the v1.0 shell contract.

Machine-oriented strings such as IDs, paths, model names, key combinations, and log fragments can remain LTR inside an Arabic interface.

## 11. Window resizing and docks

The shell has a minimum supported window geometry and density-aware default sizing. Docks are rebalanced after visibility/floating changes.

If you make the window unusually narrow, feature workspaces may become more constrained. The post-v1.0 stress program will explore additional extreme geometry envelopes; v1.0 documentation describes the audited normal operating UI rather than claiming every pathological dimension is equally usable.

## 12. A safe first exploration

For a first session, explore in this order:

1. open **Dashboard** and identify the sidebar, Inspector, and lower dock tabs;
2. open the **Panels** menu and observe how docks can be hidden/restored;
3. open **Style** and inspect theme/language controls;
4. switch to **Profiles** and **Datasets** without creating important data yet;
5. open **Agents** and inspect the graph workspace without performing deletion actions;
6. open **Documentation** so you know where task-specific instructions live;
7. leave **Automation** for after reading its dedicated safety guide.

This gives you a mental map of PTL without starting a long-running or destructive workflow.

## 13. Screenshot reference plan for v1.0

During the final documentation capture session this page will receive a reproducible visual set captured from a clean demo workspace:

1. **Full shell overview** — numbered callouts for Sidebar, Workspace, Inspector, lower docks, Status bar.
2. **Sidebar close-up** — navigation, Panels control, appearance/scale controls, active-workflow area.
3. **Dock controls** — Inspector plus Activity/Telemetry/Issues tabs.
4. **Arabic shell reference** — demonstrates RTL text with stable shell geometry.

The screenshots will be captured from a recorded commit and documented UI state so they remain auditable documentation assets rather than arbitrary development screenshots.

## Next steps

- New installation: [Getting Started](getting-started.md)
- Data location and reset/backup behavior: [Workspace & Storage](../operations/workspace-and-storage.md)
- Stable-release promises and boundaries: [v1.0 Product Contract](../reference/v1-product-contract.md)
- Internal system map: [Architecture Overview](../architecture/overview.md)
