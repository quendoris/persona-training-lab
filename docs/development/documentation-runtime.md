# Runtime Documentation Architecture

Persona Training Lab has two related but distinct documentation surfaces:

1. the repository's canonical documentation tree rooted at `docs/README.md`;
2. the in-application **Docs** workspace backed by `DocsService`, `DocsViewModel`, and `DocsScreen`.

They share source files, but they are **not equivalent navigation surfaces**. This distinction is part of the current v1.0 behavior and must not be collapsed into the claim that every canonical document is automatically exposed inside the application.

For the user-facing workflow and troubleshooting behavior, see [Documentation Workspace](../user-guide/documentation.md). This document owns the implementation/packaging contract behind that surface.

## Canonical documentation vs runtime topics

`docs/README.md` is the canonical documentation home and indexes the current user/operator/architecture/reference/development set.

The runtime service currently exposes exactly these topic descriptors:

```text
quickstart
  -> docs/quickstart.md

training_pipeline
  -> docs/training_pipeline.md

personality_portrait
  -> docs/personality_portrait.md

experiment_protocol
  -> docs/experiment_protocol.md

methodology_limits
  -> docs/methodology_limits.md
```

The source of truth for this runtime list is `application/docs/service.py::DOC_TOPICS`.

Therefore documents such as:

```text
docs/user-guide/...
docs/operations/...
docs/architecture/...
docs/reference/...
docs/development/...
```

can be canonical repository/bundled documentation without appearing as selectable topics in the current Docs workspace.

Adding a Markdown file to `docs/` does not automatically register a runtime topic.

## Runtime topic identity

Application-layer `DocTopic` deliberately contains only:

```text
topic_id
path
```

It does not store user-facing title, summary, or next-step text.

Those presentation strings are mapped by `DocsViewModel` from `topic_id` to localization keys:

```text
docs.topic.<topic>.title
docs.topic.<topic>.summary
docs.topic.<topic>.next_step
```

This keeps runtime topic identity/path separate from localized presentation metadata.

The view model also provides localized semantic models for:

- quick-reference rows;
- contextual-help rows;
- missing-content/read-failure messages.

## Document body localization boundary

The document body is not translated by `DocsViewModel` when the application locale changes.

`DocsViewModel.topic_content()` returns either:

- the UTF-8 text read from the registered Markdown path; or
- a localized semantic `DocText` error message when content is missing/unreadable.

`tests/test_docs_i18n.py` explicitly protects the current distinction:

1. select a topic;
2. record its body text;
3. switch `en-US -> ru-RU -> en-US`;
4. verify localized topic/card metadata changes;
5. verify the body text remains byte-for-presentation equivalent in the editor.

Do not document runtime language switching as translating the Markdown body. It currently localizes the surrounding Docs UI and topic metadata, not source-document content.

## Markdown rendering boundary

`DocsScreen` displays topic content through:

```python
self._content.setPlainText(...)
```

The widget is a read-only `QTextEdit`, but current topic content is inserted as **plain text**, not rendered Markdown/HTML.

Consequences:

- Markdown headings, tables, code fences, links, and emphasis remain literal text syntax;
- repository Markdown remains readable as source text but is not presented as a browser-like rendered document;
- link navigation inside the body is not implied by the current screen implementation.

Changing this surface to rendered Markdown/HTML would be a user-visible behavior and safety-contract change, not a documentation-only correction.

## Documentation root resolution

`DocsService` does not depend on the process current working directory for its default root.

Its current resolution order is:

```text
package root = Path(service.py).parents[2]

if <package root>/docs exists:
    use package root
else:
    use repository root = Path(service.py).parents[4]
```

### Installed/package case

The wheel build force-includes:

```toml
[tool.hatch.build.targets.wheel.force-include]
"docs" = "persona_training_lab/docs"
```

After installation, the package therefore has:

```text
persona_training_lab/docs/...
```

and the first root-resolution branch can serve bundled documentation.

### Source-checkout case

In a normal source checkout there is no `src/persona_training_lab/docs/` directory. `DocsService` falls back to the repository root and reads:

```text
<repository>/docs/...
```

`tests/test_docs_service.py` changes the process CWD to an unrelated temporary directory and verifies that default-root reading still succeeds. CWD is therefore not part of the default DocsService lookup contract.

## Direct root injection

Tests and callers may construct:

```python
DocsService(root=some_path)
```

When an explicit root is supplied, `read_topic(path)` simply resolves:

```text
root / path
```

and reads UTF-8 text.

A missing file raises `FileNotFoundError` at the service layer.

`DocsViewModel` maps that specific error to:

```text
docs.content.missing
```

and maps other read exceptions to:

```text
docs.content.read_failed
```

The application service itself does not localize the exception.

## Runtime screen structure

The current Docs screen has three conceptual columns:

```text
Topics
  -> QListWidget of registered runtime topics

Content
  -> localized topic title
  -> localized summary
  -> read-only plain-text document body

Next/context
  -> localized next-step text
  -> localized contextual-help rows
```

When the locale changes, `_apply_language()` updates card text, topic labels and contextual metadata while retaining the current topic selection.

## Packaging contract

The whole repository `docs` directory is force-included into the wheel destination `persona_training_lab/docs`.

That package rule is broader than `DOC_TOPICS`: bundled files and runtime-selectable topics are separate concepts.

This matters when reviewing package output:

- a document can be bundled but not registered in the Docs workspace;
- a registered runtime topic must still point to a bundled/source file that exists;
- successful packaging does not prove every canonical document has runtime navigation;
- successful DocsService topic tests do not prove every bundled Markdown file is linked from `docs/README.md`.

The [Packaging](packaging.md) and [Release Process](release-process.md) guides therefore require package/documentation inspection separately from runtime topic behavior.

## Tests that protect the current contract

`tests/test_docs_service.py` currently checks, among other things:

- runtime topics contain semantic IDs/paths rather than user-facing strings;
- known Markdown content can be read;
- default root is independent of CWD;
- wheel configuration force-includes `docs` at `persona_training_lab/docs`;
- missing service content raises `FileNotFoundError`;
- the view model exposes localized semantic metadata;
- missing runtime content maps to a semantic localized message.

`tests/test_docs_i18n.py` additionally checks that locale switching:

- updates Docs workspace metadata;
- preserves topic selection;
- does not mutate/retranslate the loaded Markdown body.

## Change checklist

When adding or changing canonical documentation, decide explicitly whether the change affects only repository/bundled documentation or also the runtime Docs workspace.

For a new runtime topic, review together:

```text
application/docs/service.py
  -> DOC_TOPICS id/path

ui/viewmodels/docs.py
  -> localized metadata key mapping

i18n catalogs
  -> title/summary/next-step keys

docs/<registered path>
  -> actual UTF-8 content

tests/test_docs_service.py
tests/test_docs_i18n.py
```

If runtime rendering changes from plain text to Markdown/HTML, update screen behavior, safety assumptions, tests and both the developer/user documentation in the same change.

## Current non-goals / limits

The runtime Docs workspace currently does not claim:

- automatic discovery of all Markdown under `docs/`;
- rendered Markdown;
- in-document link navigation;
- automatic translation of Markdown body content;
- equivalence with the complete canonical `docs/README.md` navigation tree;
- independent versioning of individual bundled documents.

These are current implementation limits and should be documented as such rather than implied features.

## Related documentation

- [Documentation Workspace](../user-guide/documentation.md)
- [Interface Tour](../user-guide/interface-tour.md)
- [Packaging](packaging.md)
- [Release Process](release-process.md)
