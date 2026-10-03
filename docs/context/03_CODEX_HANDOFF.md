# Persona Training Lab — Engineering Handoff

## 1. Current objective

Finish the v0.1.0 release candidate.

Do **not** expand into the post-release mathematical/research feature set yet. The current job is documentation/code consistency, crack discovery, concrete repair, and release evidence.

## 2. Working branch

```text
agent/history-keyguard-poller
```

The clean quick-gate evidence immediately before the current documentation commits was produced at:

```text
39d25de13568571a019992fe84ec8a616b6e7048
```

with **603 passed ×3**, compileall/Ruff/typing-audit/i18n/docs-audit PASS.

Because HEAD has moved during documentation work, that result is evidence for the old candidate only. Do not claim the new HEAD is green until it is executed.

## 3. Source-of-truth order

When sources disagree, use this order:

1. current checked-in code and executable tests/audits;
2. canonical current docs under `docs/architecture`, `docs/operations`, `docs/reference`, `docs/development`, user guides, and `docs/training_pipeline.md`;
3. `docs/DOCUMENTATION_MAP.md` as a coverage/status map;
4. `docs/context/*` as compact handoff/context;
5. historical release/audit notes only as history.

Context files must not silently override code or canonical documentation.

## 4. Release-change rule

After the start of final release audit, “this architecture could be prettier” is not sufficient reason to change runtime code.

A runtime change needs a concrete finding such as:

- violated documented invariant;
- ownership/lifecycle bug;
- transaction/cross-store consistency defect;
- unsafe destructive path;
- stale or wrong provenance;
- error-boundary failure;
- localization/presentation leakage;
- packaging/install/runtime-doc failure;
- visual defect demonstrated by the visual audit.

Every repaired crack should gain regression/audit coverage.

## 5. Immediate sequence

```text
continue code ↔ docs audit
        ↓
repair concrete cracks
        ↓
quick gate --runs 3
        ↓
full release gate
        ↓
visual audit + native review
        ↓
wheel/sdist inspection + clean install
        ↓
final docs/link/runtime-doc check
        ↓
v0.1.0 tag/release
```

## 6. Post-release boundary

After v0.1.0, development can move to Training Dynamics instrumentation, the Mathematical Inspector, intervention/sensitivity research workflows, and eventually the deliberately adversarial/falsification test program.

Normal regression/safety tests continue throughout development. The later “armour-piercing” phase is different: it is designed to falsify mathematical/causal claims after the corresponding instrumentation exists.

## 7. Git write discipline

- Fetch the full current file before replacing it.
- Use the fresh blob SHA for sequential contents updates.
- Prefer atomic commits by one semantic change.
- Inspect exact diff after broad documentation/code rewrites.
- Never force through a stale SHA conflict.
- Tie release evidence to an exact clean commit.
