# Profiles

Profiles are the structured personality definitions used by later Persona Training Lab workflows.

Use the **Profiles** workspace to create a profile, select an existing profile, review its readiness/summary, and edit the fields that define how the personality should be described and constrained.

## 1. What a profile contains

A v1.0 profile stores the following editable fields:

- **Title** — the human-readable name of the profile.
- **Description** — the high-level description of the personality.
- **Communication style** — how the personality should communicate.
- **Principles** — the principles the profile is intended to follow.
- **Constraints** — explicit limits or constraints associated with the profile.
- **Notes** — optional supporting notes.

The first five fields are required when creating or updating a profile. Notes are optional.

Profiles are persistent workspace records. They are not just text boxes kept in memory until PTL closes.

## 2. Profiles workspace layout

The workspace is divided into three main columns.

### Left: profile registry

The left panel contains:

- **Create** action;
- **Edit** action;
- the list of profiles in the current workspace.

Only one profile is selected at a time.

Selecting another list item updates the detail panels without opening a second window.

### Center: current profile

The center area shows the selected profile's presentation model, including:

- summary/readiness information;
- constraints presentation;
- trait/readiness metric cards.

These cards are a view of the selected profile state. Edit the profile through the editor rather than trying to manipulate the cards directly.

### Right: relationships and next step

The right area presents:

- linked artifacts/related items exposed by the profile view model;
- a next-step guidance card.

This helps connect a profile to the workflows that use it later.

## 3. Create your first profile

1. Open **Profiles** from the sidebar.
2. Select **Create**.
3. The profile editor opens as a modal dialog.
4. Complete the required fields:
   - Title
   - Description
   - Communication style
   - Principles
   - Constraints
5. Add Notes if useful.
6. Select **Save**.

If a required field is blank after trimming whitespace, PTL rejects the save and reports the corresponding validation state rather than creating a partial profile.

After a successful create, PTL generates a profile identifier with the form:

```text
prf_<8 hexadecimal characters>
```

The created profile is stored with status `ready`.

## 4. Writing useful profile content

The editor is deliberately structured so different kinds of intent do not have to be mixed into one prompt-like paragraph.

A practical division is:

### Description

Explain *who this profile is intended to represent* at a high level.

### Communication style

Describe *how it should express itself* — tone, directness, formality, verbosity, conversational habits, and other communication properties relevant to your research/workflow.

### Principles

Describe positive behavioral principles or values you want represented explicitly in the profile definition.

### Constraints

Describe limits, boundaries, or conditions that should remain distinct from the general principles.

### Notes

Keep context that is useful to the human operator but does not belong in the more structured fields above.

PTL does not infer that one field can substitute for another during validation. Required fields must contain actual text.

## 5. Field normalization and limits

On save PTL trims leading/trailing whitespace and stores bounded text lengths.

Current v1.0 storage limits are:

| Field | Maximum stored length |
|---|---:|
| Title | 120 characters |
| Description | 2000 characters |
| Communication style | 2000 characters |
| Principles | 3000 characters |
| Constraints | 3000 characters |
| Notes | 3000 characters |

If a value exceeds its limit, PTL truncates it to fit and appends an ellipsis rather than storing an unbounded value.

The short `subtitle` representation used elsewhere in the UI is derived from Description and is limited separately.

**Recommendation:** keep the important information well inside the limits. Do not rely on truncation as an editing tool.

## 6. Edit an existing profile

1. Select the profile in the registry.
2. Select **Edit**.
3. The editor opens with the currently stored values.
4. Make the required changes.
5. Select **Save**.

The same required-field validation used for creation also applies to edits.

On success PTL updates the existing record rather than creating a second profile ID.

## 7. When Edit is unavailable

The Edit action is disabled when the view model is showing its synthetic empty/error states rather than a real persisted profile.

If Edit is unexpectedly disabled:

1. verify that a real profile exists in the registry;
2. select it explicitly;
3. check the workspace subtitle/Issues surface for a load error;
4. if the workspace was recently reset, create a new profile first.

## 8. Persistence behavior

Profiles are stored in the workspace SQLite database in `persona_profiles`.

Persistent profile data includes:

- identifier;
- title/subtitle;
- description;
- communication style;
- principles;
- constraints;
- notes;
- status;
- creation/update timestamps.

A complete workspace reset removes these records. See [Workspace & Storage](../operations/workspace-and-storage.md) before deleting or replacing the workspace.

## 9. Profile status

Profiles created or updated through the current v1.0 editor are persisted with status:

```text
ready
```

Readiness text and trait cards shown in the UI are presentation-level information built from the selected profile view. Do not manually edit the SQLite status to force a workflow state.

## 10. Relationship to datasets and training

Profiles are intended to participate in downstream workflows rather than remain isolated documents.

Typical flow:

```text
Create profile
    ↓
Prepare / validate dataset linked to the intended profile
    ↓
Select profile + dataset + base model for training/evaluation work
    ↓
Inspect resulting model/version lineage and analysis
```

The exact relationship is explained in the Dataset and Training guides.

## 11. A safe first profile

For a first-run/demo workspace, create a small profile with meaningful but non-sensitive content. This makes it easier to learn Datasets/Training without putting valuable research data into a workspace you may later reset.

For example, use:

- a short recognizable title;
- one paragraph of description;
- a compact communication-style definition;
- three to five principles;
- a few explicit constraints;
- optional notes describing why the profile exists.

The purpose of the first profile is to learn the workflow, not to create a perfect research artifact on the first attempt.

## 12. What Profiles does not do

The Profiles workspace does not by itself:

- train a model;
- import a dataset;
- run an evaluation;
- create a full workspace backup;
- execute Automation commands.

It defines persistent profile state used by other PTL systems.

## 13. Screenshot plan for v1.0

The final documentation capture session will add:

1. **Profiles workspace overview** — registry, selected profile summary/traits, linked/next-step column.
2. **Create Profile dialog** — numbered required fields and Save/Cancel.
3. **Validation example** — one required field intentionally omitted, showing what the user sees.

Screenshots will use a clean demo profile rather than private research content.

## Next steps

- Learn the shell: [Interface Tour](interface-tour.md)
- Understand persistence: [Workspace & Storage](../operations/workspace-and-storage.md)
- Prepare data: `datasets.md` (next v1.0 user-guide chapter)
- Understand the stable release boundary: [v1.0 Product Contract](../reference/v1-product-contract.md)
