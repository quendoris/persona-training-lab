# Visual audit

PTL includes a repository-local Qt capture harness in `tools/visual_audit.py`. It is designed to produce reproducible visual evidence from the actual application composition rather than from isolated mock widgets.

That distinction matters: the harness builds the real container, creates `SafeApplication`, applies persisted style preferences through the normal view-model path, creates `MainWindow`, and navigates the registered application routes.

The independent `quendoris/snippets` repository now contains reusable descendants of some low-level ideas (`app-screenshotter` for in-process Qt capture/manifests and `archive-bundler` for deterministic evidence packaging). PTL does **not** use those repositories as release dependencies at this point. `tools/visual_audit.py` remains the PTL visual-audit source of truth.

## What the harness captures

The tool supports two modes:

- **automatic** — walks every registered route for one or more locales and captures the main window;
- **interactive** — opens PTL, lets the operator arrange the current state, and captures all visible top-level widgets when a hotkey is pressed.

Both modes write a manifest plus PNG captures and package the session into `visual-audit.zip`.

## Important data-safety boundary

The harness launches the real PTL composition. A visual capture can therefore contain real workspace-derived information, including visible names, IDs, paths, model/dataset metadata, logs, issue text, window state or other operator-visible content.

**Do not assume a visual-audit bundle is safe to publish merely because the capture tool itself is an engineering utility.**

For screenshots intended for documentation, issues, releases or public discussion:

1. use a clean/demo workspace or otherwise controlled non-sensitive state;
2. inspect every captured top-level window, not only the main route image;
3. inspect `manifest.json` and interactive `state.json` metadata for paths/window titles;
4. do not publish the ZIP wholesale without reviewing its contents.

The capture harness does not implement a privacy scrubber or automatic redaction stage.

## Automatic audit

Run all complete locales with the default maximized-window behavior:

```bash
uv run --locked python tools/visual_audit.py
```

Use a fixed geometry for reproducible comparisons:

```bash
uv run --locked python tools/visual_audit.py \
  --width 1440 \
  --height 900
```

Capture only one locale:

```bash
uv run --locked python tools/visual_audit.py \
  --locale ru-RU \
  --width 1440 \
  --height 900
```

Multiple `--locale` arguments can be supplied.

The default locale list is loaded from the packaged catalogs with `ru-RU` placed first. Unsupported requested locales fail the session instead of being silently skipped.

## Route coverage

Automatic mode takes its route list from `NAVIGATION_KEYS`, the same navigation registry used by the shell.

For each requested locale it:

1. switches locale without persisting that switch as an operator preference;
2. activates every registered route;
3. verifies that the workspace reports the requested route as active;
4. stabilizes window geometry;
5. captures the main window as PNG.

This makes the route inventory a current-code property rather than a duplicated hard-coded screenshot list.

## Geometry behavior

By default, width and height are zero and the tool uses maximized mode.

When either fixed dimension is provided, both must be provided. Values are clamped to minimums of 960×620. Automatic mode checks that the requested fixed geometry was actually obtained and fails on persistent geometry drift.

Example:

```bash
uv run --locked python tools/visual_audit.py \
  --width 1280 \
  --height 800 \
  --settle-ms 500
```

The settle delay allows Qt events/layout work to complete before capture. The default is 250 ms.

## Style controls

The current defaults are:

- UI scale: `0.90`;
- theme: `velvet`;
- accent: `cyan`.

They can be overridden:

```bash
uv run --locked python tools/visual_audit.py \
  --scale 1.00 \
  --theme velvet \
  --accent cyan \
  --width 1440 \
  --height 900
```

The harness records these inputs in the manifest. A comparison is meaningful only when relevant capture conditions are held constant.

## Interactive mode

Launch an interactive session with:

```bash
uv run --locked python tools/visual_audit.py --interactive
```

The default capture hotkey is `F12`.

You can choose another Qt key-sequence string:

```bash
uv run --locked python tools/visual_audit.py \
  --interactive \
  --capture-hotkey "Ctrl+F12"
```

Interactive mode allows normal route, locale, dock and window arrangement. On capture, the tool records every currently visible top-level Qt widget, not only `MainWindow`.

For automated testing of interactive capture itself:

```bash
uv run --locked python tools/visual_audit.py \
  --interactive \
  --capture-on-start \
  --exit-after-captures 1 \
  --locale ru-RU \
  --width 960 \
  --height 620 \
  --settle-ms 0
```

`--exit-after-captures 0` keeps the session open until the application is closed.

## Output structure

The default repository output root is:

```text
artifacts/visual-audit/
```

A session directory is named from UTC timestamp plus the first 12 characters of the current commit; interactive sessions add an `interactive` suffix.

Automatic sessions contain approximately:

```text
<session>/
├── manifest.json
├── summary.txt
├── screenshots/
│   ├── <locale>__<route>.png
│   └── ...
└── visual-audit.zip
```

Interactive sessions additionally contain per-capture directories:

```text
interactive/<index>/
├── state.json
├── 00__<window>.png
├── 01__<window>.png
└── ...
```

The manifest schema marker is currently:

```text
ptl:visual-audit:v1
```

## Manifest evidence

The manifest records capture-relevant metadata including:

- mode;
- commit and branch;
- whether Git appeared dirty;
- capture timestamp;
- route and locale inventory;
- window mode/geometry;
- UI scale/theme/accent;
- `QT_QPA_PLATFORM`;
- settle delay;
- capture records;
- failures.

Interactive state records additionally include current route/locale, window geometry, application density/scale properties, theme/accent and metadata for each visible top-level widget.

## Offscreen execution

For CI/headless use:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked python tools/visual_audit.py \
  --locale ru-RU \
  --width 960 \
  --height 620 \
  --settle-ms 0
```

The automated tests use this pattern.

Offscreen captures prove that the Qt composition can render and be traversed in that environment. They do not prove pixel-equivalent rendering on Linux/X11/Wayland, Windows or macOS native desktops.

## Reusable extraction vs PTL evidence

The independent snippets intentionally expose narrower contracts:

```text
app-screenshotter
  -> caller-selected QWidget / visible top-level capture
  -> PNG + per-capture metadata + SHA-256 manifest

archive-bundler
  -> caller-selected files/directories
  -> deterministic ZIP representation + SHA-256 inventory
```

PTL's harness does substantially more:

```text
production PTL composition
  -> workspace/container/style/localization setup
  -> route and locale traversal
  -> PTL-specific geometry/readiness checks
  -> PTL visual-audit schema/state records
  -> automatic and interactive workflows
  -> PTL-specific ZIP/session layout
```

Therefore an independently passing `app-screenshotter` or `archive-bundler` test does not prove PTL visual-audit behavior, and PTL's harness tests do not automatically prove every generic snippet contract. The code bases share engineering provenance, not a hidden dependency relationship.

See [Developer tooling](tooling.md) for the project-local/shared-tool ownership rule.

## Relationship to the release gate

The current `tools/release_gate.py` does **not** invoke `tools/visual_audit.py` as one of its gate steps. Visual evidence is a separate release/documentation activity.

Therefore:

- a successful release-gate summary does not mean visual captures were generated or reviewed;
- a successful visual audit does not mean mypy, pytest, build or the other release-gate layers passed.

The final release process should preserve both forms of evidence when visual review is required.

## Tests protecting the harness

`tests/test_visual_audit_tool.py` verifies the current tool contract by launching it in offscreen mode. It checks complete-locale defaults, route coverage, PNG signatures, manifest fields, ZIP contents and interactive top-level-window capture.

If the manifest schema, route source, capture layout or output contract changes, update both the tool tests and this document in the same change.
