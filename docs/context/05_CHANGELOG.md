# Persona Training Lab — Accepted Changes

This is a compact engineering-history summary, not the public release changelog and not a substitute for the canonical architecture/reference docs.

## Current accepted baseline direction

- PTL is a full desktop research workstation rather than the old Phase 2.x scaffold.
- The first public package release is `0.1.0`.
- Pre-release scope is frozen to documentation/code consistency, concrete defect repair, visual acceptance, full automated gate, packaging/install acceptance and release evidence.
- Training Dynamics runtime features and the Mathematical Inspector are post-v0.1.0 work.
- The later adversarial/falsification battery is intentionally separated from ordinary regression testing and comes after the mathematical/instrumentation layer can actually be falsified.

## Major accepted architecture changes

- Workspace ownership is independent from process current working directory.
- SQLite/persistence/runtime operations have explicit ownership and concurrency contracts.
- Long-running UI operations participate in explicit shutdown ownership.
- Agents lineage uses coherent persisted projection data plus separate local graph/history/layout state.
- Destructive Agents history binds to exact safety identity and fails closed on mismatches.
- Projection publication reconciles resource links before a new generation becomes screen-accepted.
- Training pins Profile/Dataset input identity and publishes final artifacts only after staging completes.
- Automation is an explicit trusted-host surface with runtime claims, audit records, process-tree containment and review-to-run semantic identity.
- Telemetry collection moved off the GUI thread and participates in shell shutdown.
- Localization is catalog-driven across `ru-RU`, `en-US`, `es-ES`, and RTL `ar`.
- UI literal inventory reached zero in the current audit.
- Documentation audit is a blocking release-gate step.

## Most recent executed evidence before documentation moved HEAD

Commit:

```text
39d25de13568571a019992fe84ec8a616b6e7048
```

Evidence:

- compileall PASS;
- Ruff PASS;
- typing audit: zero blocking findings;
- quick pytest inventory: **603 passed ×3**;
- i18n audit PASS;
- docs audit PASS;
- clean tracked-tree statistics.

This evidence is not automatically inherited by later commits.

## Current documentation findings

- The old v0.1.0 checklist described a pre-refactor release and has been replaced with a post-refactor release-close checklist.
- Release/testing docs had fallen behind the real gate by omitting the blocking `docs-audit` step; they are synchronized again.
- The Training pipeline contained a duplicated “Artifact layout and publication” section/numbering block; the duplicate was removed.
- Legacy `docs/context/*` files were materially stale and are being rewritten as compact current handoff context rather than competing architecture truth.
