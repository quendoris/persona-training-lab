# Documentation Workspace

Persona Training Lab includes a **Documentation** workspace inside the desktop application. It is a compact, in-product reference surface for a curated set of project documents.

The in-app workspace is useful when you want guidance without leaving PTL, but it is **not the complete canonical documentation tree**. The full current documentation set is indexed by [`docs/README.md`](../README.md).

## Opening Documentation

Use the **Documentation** item in the left sidebar.

The current machine workspace key is:

```text
docs
```

The current editable navigation binding is:

```text
binding_id = nav_docs
default    = Alt+O
```

Because navigation bindings are user-editable, `Alt+O` is the default rather than a permanent physical shortcut. The sidebar tooltip follows the active binding after binding changes are applied.

See [Key Bindings & Mouse Gestures](key-bindings.md) for editing and persistence behavior.

## What the workspace contains

The current in-app topic registry contains exactly five selectable documents:

| Topic identity | Source document |
|---|---|
| `quickstart` | `docs/quickstart.md` |
| `training_pipeline` | `docs/training_pipeline.md` |
| `personality_portrait` | `docs/personality_portrait.md` |
| `experiment_protocol` | `docs/experiment_protocol.md` |
| `methodology_limits` | `docs/methodology_limits.md` |

This is a curated runtime list. Files under the larger documentation tree are not discovered automatically.

For example, the following canonical documentation groups are bundled with PTL but are not individually selectable in the current Documentation workspace:

```text
docs/user-guide/
docs/operations/
docs/architecture/
docs/reference/
docs/development/
```

Therefore:

> **Bundled documentation is broader than in-app topic navigation.**

Adding another Markdown file to the repository does not make it appear in the Documentation workspace unless the application topic registry is also changed.

## Screen layout

The current workspace is a three-column surface:

```text
┌────────────────┬──────────────────────────────────────┬────────────────┐
│ Topics         │ Content                              │ Next / context │
│                │                                      │                │
│ topic list     │ localized title                     │ next step      │
│                │ localized summary                   │ context rows   │
│                │ read-only document source text      │                │
└────────────────┴──────────────────────────────────────┴────────────────┘
```

### Topics column

The left column lists the registered runtime topics.

Selecting a row changes the active document displayed in the center without opening another window.

The first registered topic is selected automatically when the workspace is created.

### Content column

The center column contains:

1. the localized topic title;
2. the localized topic summary;
3. the document body in a read-only text editor.

The body can be selected/copied like text, but the workspace is not an editor for documentation files.

### Next/context column

The right column shows localized guidance associated with the Documentation workspace and the selected topic, including a next-step label and contextual reminder rows.

These presentation strings are application localization content. They are separate from the Markdown body itself.

## Markdown is currently shown as source text

The current Documentation workspace does **not** render Markdown into formatted HTML-style documentation.

The application inserts document contents through a read-only `QTextEdit` using plain-text display. Markdown syntax therefore remains visible literally.

For example, source such as:

```markdown
# Heading

- item one
- item two

`machine_id`
```

is displayed as Markdown source text rather than being converted into a rendered heading/list/code presentation.

Current consequences:

- headings remain `#`-prefixed source lines;
- Markdown tables remain source tables;
- code fences remain literal fences;
- emphasis markers remain visible syntax;
- Markdown links are not an in-app navigation mechanism.

This is an implementation boundary of the current workspace, not a statement that the repository documentation itself is plain-text-only. When viewed on GitHub or in another Markdown renderer, the same files can render normally.

## Language switching

Changing PTL's interface language updates the Documentation workspace presentation without requiring a restart.

The following elements are localized:

- Documentation/sidebar label;
- topic titles;
- topic summaries;
- card titles/subtitles;
- next-step guidance;
- context/help rows;
- semantic missing/read-failure messages.

The **document body is not automatically translated** when the interface locale changes.

The current tested behavior preserves both the selected topic and its body when switching, for example:

```text
en-US -> ru-RU -> en-US
```

while the surrounding labels and topic metadata change locale.

This distinction matters when reading a document whose source language differs from the currently selected application locale.

For the general locale/RTL contract, see [Appearance & Language](appearance-and-language.md).

## Canonical docs vs the in-app subset

Use the in-app workspace for the five registered quick/reference topics.

Use [`docs/README.md`](../README.md) as the canonical documentation map when you need the complete v1.0 set, including:

- end-to-end user workflows;
- operations/recovery/security guidance;
- architecture contracts;
- machine references;
- developer/testing/release documentation.

The distinction can be summarized as:

```text
docs/README.md
  -> canonical navigation for the complete documentation set

packaged docs tree
  -> all documentation copied into the installed wheel

Documentation workspace
  -> five explicitly registered runtime topics
```

These surfaces share files, but they do not have identical navigation coverage.

## Where document bytes come from

The normal user does not need to configure a documentation path manually.

PTL resolves the default documentation root from the application installation/source layout rather than from the shell's current working directory.

### Installed package

The wheel includes the repository `docs/` tree under:

```text
persona_training_lab/docs/
```

The runtime service uses that packaged copy when it is present.

### Source checkout

When PTL is launched from a source checkout, the runtime service falls back to the repository root and reads:

```text
<repository>/docs/...
```

Changing the terminal's working directory therefore is not supposed to change which normal bundled/source documentation root PTL resolves.

For implementation details, see [Runtime Documentation Architecture](../development/documentation-runtime.md).

## Missing or unreadable topic content

The application distinguishes a missing file from another read failure at the view-model boundary.

A missing registered document is presented through the localized semantic message identified by:

```text
docs.content.missing
```

Other read failures use:

```text
docs.content.read_failed
```

These are failure states. They do not cause the runtime service to silently substitute a different document with a similar title.

If a packaged installation shows a missing registered topic, treat that as a packaging/documentation-integrity problem rather than as expected content discovery behavior.

## The Inspector and Documentation

When Documentation is active, the shell's Inspector switches to the Documentation context.

The Inspector supplies localized checks/next-step/risk guidance for the workspace. That Inspector text is supporting shell guidance; it is not the source of the selected Markdown document.

The central Documentation topic remains sourced from the registered document path.

## What the workspace does not currently do

The current in-app Documentation surface does not claim to provide:

- automatic discovery of every `docs/**/*.md` file;
- the complete navigation structure from `docs/README.md`;
- rendered Markdown;
- clickable in-body Markdown navigation;
- editing/saving of documentation files;
- automatic body translation when locale changes;
- independent per-document version selection;
- remote documentation fetching;
- a replacement for repository documentation during development/audit work.

## Safe expectations for packaged releases

For a normal release package, you can expect the registered Documentation topics to read from the bundled documentation tree rather than requiring a separately downloaded manual.

However, package inclusion and runtime topic registration are separate contracts:

```text
file exists in packaged docs
    does not imply
file is selectable in Documentation
```

and:

```text
topic is registered in code
    still requires
its source file to exist in the package/source tree
```

Release validation therefore checks documentation packaging separately from the runtime topic list.

## Troubleshooting

### Documentation opens, but I cannot find a newer user/architecture guide

That can be normal. The workspace exposes only its registered five-topic subset.

Open the canonical [`docs/README.md`](../README.md) from the repository/package documentation tree for the full current map.

### Markdown looks unformatted

That is the current v1.0 display behavior. The body is shown as read-only plain text, so Markdown syntax remains visible.

### I changed the interface language, but the document text did not change

That is also the current contract. Topic metadata and surrounding UI localize; the Markdown body itself is not translated dynamically.

### `Alt+O` does not open Documentation

`Alt+O` is the built-in default for `nav_docs`, but keyboard mappings are editable and persisted separately. Check the **Key bindings** workspace for the current assigned value.

Also remember that the desktop environment can intercept a shortcut before Qt receives it.

### A registered topic reports missing content

For a source checkout, verify the expected `docs/<file>.md` exists in the checked-out repository.

For an installed build, this points toward package/documentation integrity and should be investigated as a packaging problem rather than repaired by creating arbitrary files beside the executable.

## Screenshot plan

The final v1.0 documentation capture set for this workspace should include:

1. **Documentation workspace overview** — Topics, Content and Next/context columns visible;
2. **one selected runtime topic** — title/summary plus the read-only Markdown source body;
3. **locale switch pair** — same selected topic before/after locale change, demonstrating localized metadata with stable body;
4. **plain-Markdown boundary** — visible heading/list/link syntax in the body;
5. **missing-content state** — controlled demo build/test state only, if included in internal troubleshooting assets.

Captures intended for publication should use a clean/demo workspace and the same reproducible capture rules as the rest of PTL documentation.

## Related documentation

- [Interface Tour](interface-tour.md)
- [Getting Started](getting-started.md)
- [Appearance & Language](appearance-and-language.md)
- [Key Bindings & Mouse Gestures](key-bindings.md)
- [Runtime Documentation Architecture](../development/documentation-runtime.md)
- [Packaging](../development/packaging.md)
- [Release Process](../development/release-process.md)
