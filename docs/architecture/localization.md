# Localization architecture

## Goal

Persona Training Lab must never present a partially translated workspace. A
locale is user-selectable only after every user-facing string, dialog, tooltip,
empty state, error, status and workflow hint required by the release has a
validated translation.

The first supported locales are:

- `ru-RU` — base authoring locale;
- `en-US` — complete English interface.

A language switch must be live, atomic and reversible. It must not rebuild the
main window, discard drafts, reset the selected lineage node or interrupt a
runtime operation.

## Non-negotiable invariants

1. User-visible strings use stable semantic IDs, not source-language text as a
   translation key.
2. All supported catalogs contain exactly the same key set.
3. Placeholder names match across every locale.
4. Plural messages include an `other` form and use locale-aware selection.
5. Missing keys never silently fall back to another language.
6. An incomplete locale is not shown in the language selector.
7. Standard Qt dialogs and buttons must follow the application locale.
8. Native dialogs that cannot guarantee the selected language are replaced by
   application-owned dialogs or opened in non-native mode.
9. Language changes are persisted only after the target catalog is validated
   and all registered bindings can be rendered.
10. The release gate blocks when hard-coded user-facing literals remain.

## Catalog format

Catalogs live under:

```text
src/persona_training_lab/i18n/catalogs/
```

Each JSON file contains metadata and a `messages` object. Keys describe meaning,
not wording:

```json
{
  "meta": {
    "schema": 1,
    "locale": "en-US",
    "name": "English",
    "native_name": "English",
    "direction": "ltr"
  },
  "messages": {
    "nav.agents": "Agents",
    "language.unavailable_incomplete":
      "Locale {locale} is unavailable because its translation is incomplete."
  }
}
```

Plural values use named forms:

```json
{
  "operations.active_count": {
    "one": "{count} active operation",
    "other": "{count} active operations"
  }
}
```

The Russian catalog may use `one`, `few`, `many` and `other`; the English
catalog uses `one` and `other`. The placeholder signature is compared across
locales as a union of all plural forms.

## Runtime model

`LocalizationManager` owns:

- the validated catalog set;
- the active application catalog;
- the optional Qt base translator;
- live widget bindings;
- locale-aware formatting and plural selection;
- the `language_changed` signal.

A widget is migrated by binding a semantic key to a setter:

```python
localization.bind_text(title_label, "agents.title")
localization.bind_tooltip(delete_button, "agents.delete.tooltip")
```

Dynamic screens may additionally subscribe to `language_changed` and rebuild
only their text model. They must not recreate domain state or long-running
operations.

Switching follows this order:

1. resolve and validate the target catalog;
2. pre-render every registered binding;
3. prepare the Qt system translator;
4. replace the active translators;
5. apply every pre-rendered string;
6. emit `language_changed` for dynamic sections;
7. persist the locale.

A failure before step 4 leaves the current language untouched.

## Dialog policy

Application dialogs use centralized wrappers with explicit message IDs for:

- title;
- body;
- informative text;
- detailed text;
- every button label.

`QDialogButtonBox` standard buttons are not accepted as proof of translation by
themselves. During migration they must either receive explicit localized labels
or be covered by a verified Qt base translation.

Native file, colour and font dialogs may follow the operating-system locale
instead of the application locale. For strict language consistency the release
uses non-native dialogs unless the platform adapter proves that the requested
locale is honoured.

## Source audit

Run the inventory at any time:

```bash
uv run python tools/i18n_audit.py
```

This validates catalogs, referenced keys and placeholder signatures, then lists
hard-coded strings passed to known user-interface constructors and setters.

The final blocking form is:

```bash
uv run python tools/i18n_audit.py --strict-ui-literals
```

The strict command becomes part of `tools/release_gate.py` only after the
migration branch reaches zero hard-coded user-facing literals. Until then the
inventory is an explicit migration backlog, not an ignored warning.

## Migration order

1. common buttons, dialog wrappers and application errors;
2. shell, sidebar, docks, status bar and Inspector;
3. Dashboard and guided navigation;
4. Profiles and Datasets;
5. Training and Snapshots;
6. Agents and lineage canvas;
7. Tests and Analysis;
8. Appearance, Documentation and Key bindings;
9. dynamic domain statuses and operation messages;
10. documentation content, exports and release notes.

Every migrated area receives tests for Russian, English and live switching.

## Release acceptance

`v0.1.0` may expose the language selector only when:

- both catalogs have identical validated key coverage;
- the strict source audit reports zero hard-coded UI literals;
- all standard and custom dialogs are translated;
- repeated RU → EN → RU switching preserves UI and domain state;
- long English labels do not clip at supported scales;
- Russian plural forms and English singular/plural forms pass tests;
- a clean wheel contains both catalogs;
- screenshots cover both languages for the shell and every primary workspace.
