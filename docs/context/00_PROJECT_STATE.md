# Persona Training Lab — Project State

## 1. Purpose

Persona Training Lab (PTL) is a desktop-first local research workstation for building personality-oriented datasets/profiles, running local Training and evaluation, tracking model/version lineage, comparing evidence, and operating the surrounding runtime safely.

The project is no longer an MVP scaffold. The current repository contains a mature PySide6 desktop shell, SQLite-backed workspace state, local-model support, Training, Tests/Analysis, Agents lineage/history, Automation, Telemetry, localization, release tooling, and a large canonical documentation set.

## 2. Current stage

The current stage is **v0.1.0 pre-release closure**.

The goal before the first public release is not to add new research features. The goal is to:

1. finish documentation from the code that actually exists;
2. use that documentation pass to expose ownership/lifecycle/persistence/provenance cracks;
3. repair only concrete findings and turn them into permanent regression/audit contracts;
4. run final visual, full-gate and packaging/install acceptance;
5. freeze and tag the first normal public release.

Training Dynamics runtime instrumentation, the Mathematical Inspector and the later adversarial/falsification program are post-v0.1.0 work.

## 3. Working branch and evidence

Working branch:

```text
agent/history-keyguard-poller
```

The most recent clean local quick-gate evidence before the current documentation commits is tied to:

```text
39d25de13568571a019992fe84ec8a616b6e7048
```

That candidate produced:

- compileall PASS;
- Ruff PASS;
- typing audit PASS with zero blocking findings;
- curated pytest inventory: **603 passed ×3**;
- i18n audit PASS with zero missing references and zero UI literals;
- docs audit PASS;
- clean codebase statistics.

This evidence is historical once later documentation commits move HEAD. Final release evidence must be generated again on the exact final candidate.

## 4. Current architecture truths worth preserving

- Workspace persistence is not just `app.db`; filesystem artifacts, Agents state, Automation recipes and external preference stores have separate ownership/boundaries.
- Runtime-operation leases coordinate shared resources but are not OS sandboxing.
- Long-running UI work has explicit owner/lifecycle/shutdown contracts.
- Agents is a projection/integration workspace, not an alternative source of truth for persisted Training/Dataset/model/evaluation data.
- Training pins Profile/Dataset identity and stages final artifact publication; it does not content-address the complete base-model or trained-artifact directory.
- Automation is trusted-host execution with explicit review/runtime/audit boundaries, not a sandbox.
- Telemetry host collection runs outside the Qt GUI thread and participates in shell shutdown.
- Localization is catalog-driven for `ru-RU`, `en-US`, `es-ES`, and `ar`; Arabic is RTL and uses bundled font support.
- Proposed Training Dynamics documents are research architecture only until runtime code exists.

## 5. Canonical documentation

Current product/engineering truth lives primarily in:

- `README.md`;
- `docs/README.md`;
- `docs/DOCUMENTATION_MAP.md`;
- `docs/architecture/*`;
- `docs/operations/*`;
- `docs/reference/*`;
- `docs/development/*`;
- feature user guides and `docs/training_pipeline.md`.

The files under `docs/context/` are compact working/handoff aids. They must summarize canonical state; they must not override current code/tests/canonical documentation.

## 6. Immediate next work

The immediate sequence is:

```text
documentation/code crack audit
        ↓
repair only concrete findings
        ↓
quick gate on each clean candidate
        ↓
final full gate
        ↓
visual acceptance
        ↓
wheel/sdist + clean-install acceptance
        ↓
v0.1.0 freeze/tag/release
```

After v0.1.0, the project can move into deeper research instrumentation, mathematics and later adversarial/falsification coverage.
