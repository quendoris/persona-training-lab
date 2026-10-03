# Persona Training Lab — UI Rules

This is a compact design/handoff document. Current runtime behavior is defined by the UI code, localization catalogs and canonical UI/user documentation.

## 1. Product feel

The interface should feel like a calm, precise research workstation: dense enough for serious work, but not visually noisy.

## 2. Themes and colors

Shared theme/style infrastructure is the authority for reusable colors, surfaces, borders, focus states and light/dark behavior.

Do not introduce per-screen hard-coded palette values for a pattern that belongs in the theme layer.

Custom accent input accepts only the documented exact color form; malformed persisted/external values remain defensive-fallback territory rather than a reason to spread local color parsing across screens.

## 3. Localization

The UI is not Russian-only.

Current complete selectable locales are:

- Russian — `ru-RU`
- English — `en-US`
- Spanish — `es-ES`
- Arabic — `ar`

Language changes are live. Domain/application state must remain semantic while localized strings are rendered at presentation boundaries.

Arabic requires RTL-safe geometry/text handling and the bundled Arabic UI font policy. Do not “fix” RTL by creating a separate screen implementation.

## 4. Layout

- Long/complex workspaces may use scroll shells, but nested opaque containers should not create unnecessary visual rectangles.
- Important card text should wrap rather than disappear through aggressive elision.
- Compact status/summary elements may elide according to actual available width.
- Layout must remain usable across supported UI scale/window geometry.
- Docked and floating supporting panels have explicit geometry/lifecycle behavior and must be reviewed in both states.

## 5. Navigation and input

The shell owns application navigation. Key bindings and Agents graph mouse/keyboard interactions use the configurable binding subsystem rather than scattered hard-coded shortcuts.

Bindings are draftable/conflict-checked and persist outside the workspace in their documented user-level store.

## 6. Dynamic state

Empty, loading, running, blocked, failed and completed states should be distinguishable without relying only on color.

Long-running work must not block the GUI thread. Closing/leaving a workspace must respect the owner background-work contract.

## 7. Visual audit

Visual correctness is not inferred from unit tests alone.

Before release:

- run the repository visual-audit harness;
- inspect native/manual captures on the primary desktop environment;
- cover representative RU/EN/ES/AR states;
- inspect RTL, long text, dialogs, docks, scroll areas and lineage geometry;
- do not publish screenshots containing private workspace data.

## 8. Assets

Sidebar/brand/icons should use repository assets and shared style behavior. New assets must preserve packaging/runtime-path assumptions and remain available from the installed package.
