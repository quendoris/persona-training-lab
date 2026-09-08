# Localization architecture

## Purpose

Persona Training Lab uses catalog-driven runtime localization with live language switching, locale-aware plural handling, Qt translation integration, stable shell geometry, and explicit RTL text behavior.

This document describes the current v1.0 localization architecture. It is not a migration plan.

The user-facing workflow is documented in [Appearance & Language](../user-guide/appearance-and-language.md).

## 1. Supported locale set

The current complete application catalog set is:

```text
ar
en-US
es-ES
ru-RU
```

`ru-RU` is the catalog-set base locale used for completeness/signature validation.

Direction metadata is part of each root catalog:

```text
ar     -> rtl
en-US  -> ltr
es-ES  -> ltr
ru-RU  -> ltr
```

The available-language selector is derived from the validated catalog set rather than from a hard-coded assumption that only Russian and English exist.

## 2. Catalog layout

Catalogs live under:

```text
src/persona_training_lab/i18n/catalogs/
```

A locale has a root JSON catalog, for example:

```text
ar.json
en-US.json
es-ES.json
ru-RU.json
```

and can also have fragment files under a same-locale directory:

```text
catalogs/<locale>/*.json
```

Root catalog metadata schema `1` requires:

```text
schema
locale
name
native_name
direction
```

Root `messages` entries are either:

- non-empty strings; or
- plural-form objects.

Fragment schema `1` requires:

```text
schema
locale
fragment
```

A fragment must live under the directory matching its locale and its filename stem must match its declared fragment name.

Duplicate keys between the root catalog and fragments are rejected.

## 3. Catalog completeness is validated as a set

`CatalogSet.load(..., base_locale="ru-RU")` loads every root catalog and its fragments, then validates the complete set.

For every locale, PTL requires:

- the same message-key set as the base catalog;
- no extra keys relative to the base catalog;
- the same placeholder signature for every message key.

A locale that violates those rules causes catalog loading to fail rather than being exposed as a silently incomplete interface.

Missing translation keys also fail at lookup time with `CatalogValidationError`; PTL does not silently fall back to another application catalog for an absent key.

## 4. Message and placeholder contract

A simple catalog value is a string:

```json
{
  "nav.agents": "Agents"
}
```

A plural message is an object whose keys are plural categories:

```text
zero
one
two
few
many
other
```

Only the categories actually required by a locale/message need to be present, but every plural message must contain:

```text
other
```

Placeholder names are collected across plural forms and compared across locales. A translation therefore cannot silently rename or drop a formatting field used by the base message.

Formatting also validates that all required placeholder values are supplied at render time.

## 5. Plural selection

PTL implements explicit plural rules for the richer supported locales.

### Russian

Russian distinguishes:

```text
one
few
many
```

according to the current integer-rule implementation.

### Arabic

Arabic distinguishes:

```text
zero
one
two
few
many
other
```

### English and Spanish

The current fallback used for these supported LTR languages is:

```text
count == 1 -> one
otherwise  -> other
```

Plural selection operates on integer counts. Localization count values of another type are rejected at the UI-manager boundary.

## 6. `LocalizationManager`

`ui.i18n.manager.LocalizationManager` owns the runtime application-localization state.

It manages:

- the validated `CatalogSet`;
- the active application catalog;
- the active locale identifier;
- optional Qt base translator state;
- live widget text bindings;
- locale-aware text rendering;
- text-direction refresh for supported leaf widgets;
- `language_changed` notification;
- optional persisted-locale callback.

Its default initial/base locale is:

```text
ru-RU
```

The catalog directory is resolved from the packaged `persona_training_lab.i18n/catalogs` resource unless explicitly injected.

## 7. Live locale switching is pre-rendered before activation

`set_locale(...)` does not first mutate every widget and hope rendering succeeds later.

The current order is conceptually:

```text
resolve target catalog
    ↓
pre-render registered bindings against target catalog
    ↓
prepare Qt translator
    ↓
replace Qt translator
    ↓
activate catalog + locale
    ↓
keep application shell layout direction LTR
    ↓
set QLocale default / PTL locale properties
    ↓
apply pre-rendered binding text
    ↓
emit language_changed
    ↓
refresh leaf text directions
    ↓
persist locale when requested
```

Because binding rendering happens before the active catalog is replaced, missing keys/placeholder failures are detected before normal binding application proceeds.

The surrounding feature screens can also listen to `language_changed` and refresh dynamic presentation models without rebuilding their domain/persistent state.

## 8. Binding model

The manager supports semantic-key bindings for common presentation setters including:

```text
setText
setTitle
setToolTip
setWindowTitle
setPlaceholderText
```

A binding stores:

- a weak reference to the target;
- the setter name;
- the semantic catalog key;
- optional dynamic values/count providers;
- whether leaf text direction should be applied.

Destroyed targets are pruned from the binding registry.

This keeps machine/domain state separate from translated presentation text.

## 9. Qt system translations

PTL also prepares a Qt `QTranslator` for non-English locales so standard Qt-owned text can follow the selected language where matching Qt translation resources are available.

For a locale language code such as `ru` or `ar`, the manager looks under Qt's translations directory for:

```text
qtbase_<language>.qm
qt_<language>.qm
```

English does not install a Qt translator.

If the required non-English Qt translation resource cannot be found/loaded, locale activation raises `CatalogValidationError` rather than pretending that the application can guarantee a complete switched interface.

Application-owned dialogs and custom text remain catalog-key driven independently of Qt's base translator.

## 10. RTL is a text-direction policy, not whole-shell mirroring

Arabic is an RTL locale, but PTL deliberately keeps application-level layout direction:

```text
LeftToRight
```

This preserves stable shell geometry: sidebar/docks/splitters/workspace topology do not mirror merely because Arabic text is active.

RTL ownership is applied at text leaves.

For RTL catalog mode, a supported leaf widget is set to RTL only when its displayed text contains a strong RTL character. Otherwise it remains LTR.

The current automatic leaf inspection covers widgets such as:

```text
QLabel
QCheckBox
QComboBox
QLineEdit
```

This supports mixed Arabic and machine-oriented LTR content such as paths, model names, IDs, and numeric/token strings without mirroring the entire desktop shell.

## 11. Locale/font policy

Arabic rendering is not left solely to arbitrary host-font fallback.

PTL bundles and registers:

```text
NotoSansArabicUI-Regular.ttf
NotoSansArabicUI-Bold.ttf
```

The font policy prefers packaged/known Arabic-capable families and applies the chosen family at application scope for RTL mode while remembering the prior family stack.

When PTL returns to an LTR locale, the previous application font families are restored while retaining density/point-size changes made independently of the locale switch.

The bundled-font provenance/integrity workflow is documented by the repository's font manifest/tooling and [Developer Tooling](../development/tooling.md).

## 12. Persistence boundary

The selected application language is part of PTL's SQLite UI preferences rather than Qt shell geometry state.

Conceptually:

```text
app.db / ui_preferences
    -> language

Qt QSettings
    -> shell geometry / docks / current workspace
```

Locale persistence is performed through the callback supplied to `LocalizationManager` by application composition.

See [Persistence architecture](persistence.md) for the complete settings-store split.

## 13. Localization audit

The repository-local audit command is:

```bash
uv run --locked python tools/i18n_audit.py
```

Machine-readable output:

```bash
uv run --locked python tools/i18n_audit.py --json
```

A stricter targeted source-literal mode is available:

```bash
uv run --locked python tools/i18n_audit.py --strict-ui-literals
```

The audit validates catalog completeness/placeholders and source/reference usage, then augments the result with the deeper literal audit.

The current release gate invokes the JSON audit without `--strict-ui-literals`; therefore the strict flag must not be described as a release-gate step unless the release-gate implementation changes.

Current release evidence for a specific commit belongs in that commit's release-audit report, not in this architecture document.

## 14. Runtime documentation language boundary

Application localization and Markdown-document translation are separate contracts.

The in-app Documentation workspace localizes its surrounding topic metadata/UI, but its registered Markdown body is loaded as source text and is not automatically translated when the UI locale changes.

See [Runtime Documentation Architecture](../development/documentation-runtime.md).

## 15. Evaluation protocol language boundary

The built-in portrait/evaluation questionnaire currently uses Russian prompt/item content independently of the selected UI locale.

UI localization therefore must not be interpreted as silently translating the scientific/evaluation protocol.

Battery/scoring identity and comparison rules are documented in the [Evaluation contract](../reference/evaluation-contract.md).

## 16. Structured operational messages

Activity and Issues can display durable structured application events from `event_log`. Those rows are a presentation surface even though the underlying event also carries diagnostic data.

Current error/notice reporting can therefore persist an optional semantic `UserMessage` reference alongside the raw diagnostic fields:

```text
user_message.key
user_message.values
```

`OperationsCenterService` preserves that semantic reference in the projected item, and the panel localization boundary renders it against the **current** application locale. Diagnostic identity such as `error_id`/`correlation_id` remains separate from the translated sentence.

This matters for startup/runtime notices: application code must not persist a source-language sentence merely because the event is first created before the UI is visible. The orphaned-runtime-operation recovery notice, for example, persists a machine diagnostic plus:

```text
operations.notice.recovered_abandoned
```

with structured `count`, so the same persisted notice can render in Arabic, English, Spanish, or Russian after the shell opens or the locale changes.

Historical or externally produced events can lack a semantic message reference. In that compatibility case the Operations Center can still show the stored diagnostic summary. Likewise, if a persisted semantic key is invalid or no longer renderable, the panel falls back to the diagnostic summary instead of allowing one malformed event row to break the panel.

Raw exception text, Qt diagnostics, paths, IDs, component names, and other machine/diagnostic material are not automatically translated. The semantic user-facing message and the diagnostic evidence are deliberately separate layers.

## 17. Current invariants

The v1.0 localization contract includes:

1. all exposed application catalogs pass catalog-set completeness/signature validation;
2. missing application translation keys do not silently fall back to another locale;
3. semantic keys remain distinct from rendered source-language text;
4. locale changes do not require recreating the whole main window;
5. shell geometry remains stable while RTL/LTR is handled at text leaves;
6. Arabic uses packaged Arabic UI fonts when the bundled font policy resolves them;
7. machine-oriented/path/ID text can remain LTR inside Arabic mode;
8. Qt base translations and PTL application catalogs are separate translation layers;
9. persisted machine status/result identifiers are not replaced by translated labels;
10. user-facing operational notices can persist semantic message identity separately from raw diagnostic text;
11. malformed/legacy event-message metadata does not remove the diagnostic fallback;
12. UI locale changes do not rewrite the in-app Markdown body or evaluation battery content.

## 18. Validation boundaries

A passing catalog/i18n audit proves catalog/reference/source-literal properties checked by that tool. It does not by itself prove:

- pixel-perfect layout for every string at every native DPI;
- availability of every host/Qt font or platform integration outside the bundled policy;
- behavior of every native operating-system dialog;
- semantic quality of each human translation;
- extreme geometry/stress behavior.

Visual evidence is collected separately through [`tools/visual_audit.py`](../development/visual-audit.md), including route/locale captures. Native interactive review remains distinct from offscreen automated rendering.

## Related documentation

- [Appearance & Language](../user-guide/appearance-and-language.md)
- [Interface Tour](../user-guide/interface-tour.md)
- [Persistence architecture](persistence.md)
- [UI shell architecture](ui-shell.md)
- [Runtime Documentation Architecture](../development/documentation-runtime.md)
- [Evaluation contract](../reference/evaluation-contract.md)
- [Testing](../development/testing.md)
- [Visual audit](../development/visual-audit.md)
