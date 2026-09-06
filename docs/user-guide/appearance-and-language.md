# Appearance, Language & UI Scale

Persona Training Lab applies theme, accent, interface scale, and language as live application-wide presentation settings.

This guide documents what the current v1.0 code actually does: which choices exist, where they are persisted, what changes immediately, how automatic scale is calculated, how Arabic text direction works without mirroring the shell, and what current validation boundaries remain.

## 1. Where appearance settings are exposed

PTL currently exposes presentation controls in two places:

```text
Style workspace
  -> interface language
  -> theme
  -> accent / custom accent
  -> preview + Apply appearance

Sidebar
  -> quick theme buttons
  -> UI scale slider
  -> Auto scale reset
```

These controls operate on one persisted Style preference record rather than independent per-screen themes.

## 2. Persisted appearance fields

The SQLite `ui_preferences` record stores:

```text
theme
accent_palette
button_style_preset
ui_scale
language
updated_at
```

The current defaults are:

```text
theme               = velvet
accent_palette      = cyan
button_style_preset = soft_glow
ui_scale            = auto
language            = ru-RU
```

These preferences live in `<workspace>/app.db`.

They are separate from:

```text
Qt QSettings
  -> shell window geometry / dock layout / last workspace

~/.persona_training_lab/key_bindings.json
  -> editable keyboard/mouse bindings
```

## 3. Current themes

PTL currently defines three theme IDs:

| Theme ID | Display name | Mode |
|---|---|---|
| `velvet` | Velvet | dark |
| `eclipse` | Eclipse | dark |
| `pearl` | Pearl | light |

The theme ID is the persisted machine value. The visible theme label in the Style workspace is localized through the catalog.

## 4. Current built-in accents

PTL currently defines four named accent IDs:

```text
violet
cyan
emerald
rose
```

The default is:

```text
cyan
```

Built-in accent labels are localized in the Style workspace.

## 5. Custom accent

The Style workspace also provides a custom accent text field with placeholder:

```text
#RRGGBB
```

and a color-picker button.

When the picker returns a valid color, PTL writes its Qt color name into the custom field.

On Apply, any non-empty custom text beginning with `#` takes precedence over the selected built-in accent.

## 6. Current custom-accent validation boundary

The Style screen currently checks only whether custom text starts with `#` before choosing it as the persisted accent value.

The theme renderer later parses it with `QColor`. If Qt considers that value invalid, the rendered accent palette falls back to the built-in cyan color.

Therefore current behavior is narrower than a strict “Style validates `#RRGGBB` before saving” claim.

The safest user path for a custom accent is the color picker, which supplies a valid Qt color.

## 7. Applying appearance from the Style workspace

Pressing **Apply appearance**:

1. reads the selected theme ID;
2. prefers a custom `#...` accent when present, otherwise the selected built-in accent ID;
3. saves theme/accent with `button_style_preset="soft_glow"` while preserving current scale/language;
4. applies theme/accent to the running `QApplication`.

A restart is not required for the theme/accent application path.

## 8. Quick theme buttons in the sidebar

The sidebar contains a collapsible theme block with one quick button per defined theme.

Choosing one:

- preserves the sidebar's current accent;
- saves the new theme through `StyleViewModel`;
- reapplies the application theme immediately.

This is another control surface for the same persisted theme preference, not a separate sidebar-only theme.

## 9. Theme application is application-wide

`apply_theme(...)` stores current presentation identity on the `QApplication`:

```text
ptl_theme_name
ptl_accent_name
```

then rebuilds the global stylesheet and reapplies scrollbar styling to existing `QScrollArea` children.

Individual workspaces do not maintain independent theme engines.

## 10. Theme fallback behavior

When the theme renderer receives an unknown/empty theme ID, it renders with the default `velvet` theme tokens.

When a named accent is unknown, it renders with the default `cyan` accent.

For an invalid custom `#...` value, color construction likewise falls back to cyan-compatible rendering.

This is defensive rendering behavior; it does not imply that every invalid persisted string is rewritten back to the canonical default immediately.

## 11. Theme tokens affect more than background color

The global stylesheet derives presentation tokens including:

```text
window/surface backgrounds
primary/secondary/muted text
borders
title bars
selection background
accent/hover/pressed colors
accent soft/text variants
scrollbars
buttons
cards
menus
docks
status bar
telemetry components
form controls
```

Switching theme/accent is therefore a global token/style change rather than a single palette swatch.

## 12. Current button-style preset

The persisted preference includes:

```text
button_style_preset
```

and the current default/currently written preset is:

```text
soft_glow
```

The current Style workspace does not expose a selector for multiple button-style presets; it writes `soft_glow` when applying theme/accent.

Do not document a user-selectable button-preset feature that the current screen does not provide.

## 13. Current interface languages

Repository catalog validation/tests prove the current complete locale set is:

| Locale ID | Native name | Direction metadata |
|---|---|---|
| `ar` | العربية | `rtl` |
| `en-US` | English | `ltr` |
| `es-ES` | Español | `ltr` |
| `ru-RU` | Русский | `ltr` |

The locale selector displays each catalog's `native_name`.

## 14. Language changes live without rebuilding screens

The Style language selector calls:

```text
LocalizationManager.set_locale(...)
```

The manager pre-renders registered live text bindings for the target catalog, changes its active catalog/Qt translator, reapplies bound text, emits `language_changed`, refreshes runtime text directions, and persists the locale through `StyleViewModel.save_language(...)`.

Screens/widgets bound to localization update without requiring application restart.

Tests explicitly cycle:

```text
ru-RU -> en-US -> es-ES -> ar -> ru-RU
```

without losing the selected Style theme/accent state.

## 15. Language persistence

The selected locale ID is stored in SQLite:

```text
ui_preferences.language
```

Startup loads that value before constructing the main shell.

If no preference exists, the current default is:

```text
ru-RU
```

## 16. Startup presentation order

Production startup currently performs the presentation setup in this broad order:

```text
load Style preferences
create LocalizationManager(initial locale)
apply UI density/scale
apply theme/accent
apply scaled styles immediately
apply locale font policy
construct MainWindow
```

This means the primary shell is created with the persisted locale/theme/scale already selected rather than rendering a complete default shell first and then switching it afterward.

## 17. Catalog completeness is validated as a set

Catalog loading uses Russian (`ru-RU`) as the base locale.

Every loaded locale must have the same message-key set as the base catalog.

A locale with missing or extra keys causes `CatalogValidationError` during catalog-set validation rather than silently appearing as a partially translated interface.

## 18. Placeholder signatures must match across locales

For every translation key, catalogs must preserve the same formatting-placeholder signature as the base locale.

A translation that changes, removes, or introduces required placeholders is rejected during catalog validation.

This prevents a language switch from silently breaking formatted runtime messages because one locale expects a different parameter set.

## 19. Missing translation keys do not silently fall back

Requesting an unsupported locale or missing message key raises `CatalogValidationError`.

The current catalog contract deliberately does not hide incomplete translation behind an implicit fallback to Russian/English at the point of lookup.

Completeness is a release contract, not best-effort presentation.

## 20. Catalog fragments

A locale can be split into a root catalog plus JSON fragments under:

```text
catalogs/<locale>/*.json
```

Fragments declare:

```text
schema
locale
fragment
```

and are merged into the root catalog.

Duplicate keys between the root/previous fragments and another fragment are rejected rather than silently overwritten.

## 21. Current catalog schema

Root locale catalog metadata uses schema:

```text
1
```

and requires:

```text
schema
locale
name
native_name
direction
```

Direction must be exactly:

```text
ltr
rtl
```

The filename stem must match the declared locale ID.

## 22. Qt system translations are a separate dependency

PTL's own catalog translates PTL text.

For non-English locales, `LocalizationManager` also attempts to load a Qt system translation file from Qt's translations directory:

```text
qtbase_<language>.qm
qt_<language>.qm
```

English deliberately installs no Qt translator.

If a required non-English Qt translation file cannot be found/loaded, locale switching raises `CatalogValidationError` rather than silently claiming the entire Qt-native UI is translated.

## 23. Locale switch prepares the target before replacing the active state

`set_locale(...)` first resolves the target catalog, renders existing bindings against it, and prepares the Qt translator.

Only after those preparation steps succeed does it remove/install translators and switch `_catalog` / `_locale`.

This reduces the chance of committing a locale switch that cannot even prepare its required translation resources.

## 24. `QLocale` is updated

After a successful locale switch, PTL calls:

```text
QLocale.setDefault(...)
```

using the locale ID with `-` converted to `_`.

The application also exposes:

```text
ptl_locale
ptl_text_direction
```

properties for current presentation/runtime inspection.

## 25. Arabic does **not** mirror the whole shell

Arabic catalog metadata declares:

```text
direction = rtl
```

but PTL deliberately keeps:

```text
QApplication.layoutDirection = LeftToRight
```

for every locale.

This preserves stable application geometry rather than automatically mirroring inherited Qt layouts, docks, splitters, workspace columns, and graph controls.

## 26. RTL is applied at text leaves

For bound text/placeholder widgets, PTL decides layout direction from:

- the active locale direction metadata; and
- the actual rendered text.

Under an RTL locale, a text widget becomes RTL only when its displayed string contains a Unicode bidi character classified as `R` or `AL`.

Otherwise that leaf remains LTR.

## 27. Mixed Arabic/human text vs machine identifiers

The runtime direction pass means a visible value such as:

```text
مجموعات البيانات · personality_test_dataset
```

can be RTL because it contains Arabic text, while a machine-only value such as:

```text
model_version_id=mdl_001
```

remains LTR even under Arabic.

This protects readability of machine identifiers/paths/protocol values while still rendering Arabic prose in the expected direction.

## 28. Runtime text directions are refreshed after language change

After changing locale, the manager traverses top-level widgets and descendant leaf widgets it knows how to inspect:

```text
QLabel
QCheckBox
QComboBox
QLineEdit
```

It recalculates their text direction from current displayed text.

A zero-delay second pass runs after locale change so widgets created immediately around the initial locale/main-window construction can also receive the text-direction policy without granting RTL ownership to parent layouts.

## 29. Stable geometry is part of the RTL contract

The deliberate current behavior is therefore:

```text
shell/layout geometry: LTR/stable
Arabic textual leaves: RTL when displayed content is RTL
machine/Latin text leaves: LTR
```

Do not describe Arabic mode as “mirror the entire UI.”

## 30. Bundled Arabic UI fonts

PTL packages:

```text
NotoSansArabicUI-Regular.ttf
NotoSansArabicUI-Bold.ttf
```

with a provenance/license manifest.

The font registration code loads packaged fonts through `QFontDatabase.addApplicationFont(...)` and prefers the resulting `Noto Sans Arabic UI` family when available.

## 31. RTL font fallback order

The current preferred RTL UI families are:

```text
Noto Sans Arabic UI
Noto Sans Arabic
Noto Naskh Arabic UI
Noto Naskh Arabic
FreeSerif
```

Packaged font families are considered together with system Arabic-capable families.

If no preferred family is available, the policy returns no selected override rather than fabricating a font family name.

## 32. Switching to RTL preserves the base font-family stack

When entering an RTL locale and a preferred Arabic UI family exists, PTL remembers the current base font families and places the RTL family first, followed by those fallbacks.

When returning to an LTR locale, it restores the remembered family stack.

## 33. RTL font switching does not roll back UI scale

The font policy remembers/restores font **families** independently from the current point size.

Tests explicitly verify this sequence:

```text
base font size
-> enter RTL family
-> change scaled point size
-> return LTR
```

and confirm the LTR family is restored while the newer scaled point size remains.

This keeps language/font policy from undoing density changes.

## 34. UI scale lives in the sidebar

The scale control is part of the sidebar's presentation block, not the Style workspace form.

It contains:

- current scale label;
- horizontal slider;
- status/hint text;
- Auto button.

## 35. Manual scale range

The code defines:

```text
MIN_UI_SCALE = 0.68
MAX_UI_SCALE = 1.12
```

The slider therefore represents:

```text
68% .. 112%
```

with one-percentage-point steps and a four-point page step.

## 36. Manual scale applies while dragging

On every slider `valueChanged`:

1. the value is converted to a scale factor;
2. application properties are updated;
3. the global scaled stylesheet is scheduled/applied through the density system;
4. the window geometry/update path is nudged;
5. the displayed percentage/hint updates.

The visual scale change is therefore live.

## 37. Slider changes are persisted on release

The current manual scale is persisted only from the slider's `sliderReleased` handler.

At release, PTL:

```text
applies scaled styles immediately
saves ui_scale as a two-decimal string
reloads current prefs
shows saved state
```

A live intermediate drag value is not the same thing as a successfully persisted value until the release/save path runs.

## 38. Reset scale to Auto

The sidebar Auto action:

1. reads the current computed automatic scale;
2. sets application density properties back to auto mode;
3. applies that scale immediately;
4. saves:

```text
ui_scale = auto
```

5. resynchronizes slider/value/hint controls.

## 39. Automatic scale thresholds

Current automatic density calculation is based on primary-screen available width/height:

| Condition | Auto scale | Density name |
|---|---:|---|
| height <= 760 **or** width <= 1366 | 0.78 | `compact-xs` |
| height <= 850 **or** width <= 1440 | 0.84 | `compact` |
| height <= 950 **or** width <= 1600 | 0.90 | `dense` |
| height <= 1080 | 0.94 | `balanced` |
| height <= 1250 | 1.00 | `comfortable` |
| otherwise | 1.05 | `large` |

If Qt reports no primary screen, the density code uses a fallback geometry of `1440x900` for calculation.

## 40. Manual values are clamped

When a persisted/manual scale can be parsed as a float, it is clamped to:

```text
0.68 .. 1.12
```

Invalid, empty, or `auto` values are treated as no manual override and fall back to the automatic scale.

## 41. Scale changes global font and component dimensions

The density system applies:

- application font point size;
- global widget font-size overrides;
- title/card/metric sizes;
- nav/button heights/padding/radii;
- form-control padding/radii;
- dock-title padding;
- telemetry sizing;
- root/shell/dock dimensions via `UiDensity` helpers.

Scale is therefore a real UI-density control, not merely text zoom.

## 42. Scale stylesheet updates are debounced

Normal live slider changes are coalesced through a single-shot timer with current debounce interval:

```text
140 ms
```

This avoids rebuilding the full Qt stylesheet for every high-frequency slider event.

Startup, slider release, theme changes/reset paths can request immediate application.

## 43. Theme application and scale stylesheet coexist

The scale subsystem marks its injected stylesheet block with internal begin/end markers.

When applying a new scale, it strips the previous scale block from the current application stylesheet and appends the newly generated one.

Startup/theme changes then explicitly reapply scale where needed so theme token styling and UI-density styling remain composed rather than one permanently replacing the other.

## 44. Style preview is illustrative UI, not a separate live theme instance

The Style workspace contains a preview card with brand text, example buttons, and status badges.

Those widgets are ordinary children under the same application's global stylesheet.

The preview helps inspect appearance before/around Apply but does not create an isolated theme sandbox.

## 45. Language selection does not reset theme/accent

Changing language calls the language persistence path while preserving the currently persisted:

```text
theme
accent_palette
button_style_preset
ui_scale
```

Tests explicitly verify theme/accent selections survive locale cycling.

## 46. Scale changes do not reset theme/language

`StyleViewModel.save_ui_scale(...)` reloads the current preference record and writes the new scale while preserving theme/accent/button preset/language values.

Likewise theme Apply preserves current scale/language, and language save preserves current theme/accent/scale.

This is one coordinated preference record rather than independent writes that intentionally erase the other fields.

## 47. Appearance persistence and shell geometry are different

A whole PTL workspace backup includes the SQLite Style preferences above.

It does **not** automatically include Qt `QSettings` shell geometry/dock/last-workspace state.

So after restoring the same workspace on another settings context, the theme/language/scale can restore while the exact top-level window/dock geometry does not.

## 48. Appearance persistence and key bindings are different

Custom keyboard/mouse bindings live in:

```text
~/.persona_training_lab/key_bindings.json
```

not the Style preference row.

Changing/resetting appearance does not reset those bindings, and restoring only the research workspace does not restore that external binding file.

## 49. Troubleshooting: language selector shows the locale but switching fails

Separate PTL catalog completeness from Qt system translation availability.

The repository catalogs can be complete while the host/package Qt translations needed for a non-English locale are missing.

A failed `set_locale(...)` raises a catalog-validation error through the normal application exception boundary rather than silently pretending the switch succeeded.

Collect Issues/application-log evidence and verify the Qt installation's translation resources.

## 50. Troubleshooting: Arabic did not mirror the sidebar/docks

That is expected current behavior.

PTL intentionally leaves the application/shell layout direction LTR and applies RTL only to relevant textual leaves.

Do not treat unchanged dock/sidebar geometry as evidence that Arabic mode failed.

Instead verify Arabic text content/direction and the selected RTL font family.

## 51. Troubleshooting: a machine ID/path remains LTR in Arabic

That is also expected when the displayed value contains no RTL character.

The leaf-direction policy deliberately keeps machine/Latin strings LTR for readability.

## 52. Troubleshooting: Arabic glyph rendering looks wrong

Check:

1. that bundled Arabic font files are present in the installed package;
2. that Qt successfully registers a preferred Arabic UI family;
3. the `ptl_rtl_ui_font_family` application property when debugging;
4. whether the issue is font rendering vs text direction vs missing translation.

The packaged preferred family is currently `Noto Sans Arabic UI`.

## 53. Troubleshooting: scale changed but did not persist

Remember the distinction between live dragging and persistence.

The slider applies live on `valueChanged`, but persistence happens on `sliderReleased`.

After a normal mouse/keyboard slider release the sidebar updates the hint to the saved state.

For a reproducible report record the persisted `ui_preferences.ui_scale`, not only a transient screenshot while dragging.

## 54. Troubleshooting: custom accent text renders cyan

If a custom value begins with `#` but Qt does not recognize it as a valid color, the current renderer falls back to the default cyan color.

The invalid custom text may still have been chosen/saved by the current Style screen because its pre-save test is only `startswith("#")`.

Use the color picker or a valid Qt hex color value.

This is a current validation boundary worth preserving in a bug report rather than describing the rendered cyan as random theme corruption.

## 55. Screenshot plan

The documentation asset pass should capture at least:

- Style workspace in default Velvet/Cyan;
- theme selector showing all three themes;
- accent selector showing built-ins;
- custom color picker/input;
- Pearl light theme;
- sidebar scale panel in Auto mode;
- sidebar scale panel with a manual percentage;
- English Style workspace;
- Spanish Style workspace;
- Arabic Style workspace demonstrating stable shell geometry + RTL text leaves;
- an Arabic screen containing a machine ID that remains LTR;
- bundled-font/RTL visual validation at a documented scale.

Capture metadata should include commit, locale, theme, accent, scale, and host scale/DPI context.

## 56. Current v1.0 boundaries

The current presentation system does not claim:

- per-workspace independent themes;
- a user-selectable multi-preset button-style UI beyond current `soft_glow` persistence;
- strict `#RRGGBB` validation before custom accent persistence;
- whole-shell RTL mirroring for Arabic;
- silent fallback for incomplete locale keys;
- bundled Qt `.qm` translations independent of the installed Qt translation resources;
- UI scale outside the 68–112% manual clamp;
- workspace ownership of shell QSettings/key-binding JSON;
- exact cross-machine window geometry as part of Style preference restore.

## 57. Developer invariants

Appearance/localization changes should preserve these rules unless deliberately redesigned:

1. machine theme/accent/locale IDs remain distinct from localized display labels;
2. complete catalog key/placeholder parity remains validated before a locale is accepted;
3. missing keys/unsupported locales must not silently fall back and hide incomplete localization;
4. live language changes must preserve unrelated Style settings;
5. shell/application geometry must not be globally mirrored merely because locale metadata is RTL under the current stable-geometry contract;
6. RTL leaf direction must remain based on actual displayed text so machine identifiers can stay LTR;
7. bundled Arabic font provenance/license/integrity tests must remain valid when font assets change;
8. returning to LTR must restore base font families without rolling back current density/point size;
9. manual scale stays clamped and Auto remains a distinct persisted state;
10. live scale and persisted scale timing must be documented if slider behavior changes;
11. theme application must remain composed with scale overrides;
12. persistence locations must stay accurate in Workspace/Persistence docs;
13. custom-accent validation claims must not exceed the actual validator;
14. user-facing documentation must be updated whenever locales/themes/accents/scale bounds change.

## Related documentation

- [Getting Started](getting-started.md)
- [Interface Tour](interface-tour.md)
- [Key Bindings & Mouse Gestures](key-bindings.md)
- [Localization architecture](../architecture/localization.md)
- [UI shell architecture](../architecture/ui-shell.md)
- [Persistence architecture](../architecture/persistence.md)
- [Workspace & Storage](../operations/workspace-and-storage.md)
- [Troubleshooting & Diagnostic Evidence](../operations/troubleshooting.md)
