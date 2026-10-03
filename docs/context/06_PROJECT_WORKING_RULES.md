# Persona Training Lab — Working Rules

These rules describe the current engineering sequence. Canonical runtime behavior still lives in code/tests and the maintained architecture/reference documentation.

## 1. First release comes before the next research expansion

The current goal is to finish and publish v0.1.0.

Before that release:

1. synchronize documentation with the code that actually exists;
2. use the documentation pass to expose architectural cracks;
3. repair concrete release-critical findings;
4. add regression/audit coverage for those repairs;
5. run final automated, visual and package-install evidence;
6. freeze the release commit.

Do not start the Mathematical Inspector or new Training Dynamics runtime implementation merely because the design is already interesting.

## 2. Ordinary regression tests and adversarial falsification are different

Regression/contract/safety tests are added continuously whenever an implemented invariant needs protection. They are construction and release evidence.

The later adversarial/falsification phase has a different purpose: actively search for counterexamples to claimed behavior or mathematical/causal interpretations.

For the research layer this phase belongs **after** the relevant mathematical model and instrumentation exist. Otherwise the project would spend effort “falsifying” a claim that the runtime cannot yet measure precisely.

A defect found by later adversarial testing becomes a permanent regression contract after the cause is understood and repaired.

## 3. Documentation is an engineering verification pass

Documentation is not decoration after coding.

A precise architecture/operator/reference description forces the project to state:

- who owns mutable state;
- where transaction boundaries stop;
- which worker owns which lifetime;
- what is and is not atomic;
- which identifiers represent semantic identity;
- which inputs are content-pinned vs path/external;
- what failure modes are intentionally fail-soft or fail-closed;
- what the product explicitly does not promise.

If the code cannot support the documented invariant, that is a crack to investigate. If the code is correct and the prose overclaims, the documentation must be narrowed.

## 4. Release-scope change rule

During v0.1.0 closure, runtime code changes require a concrete finding.

“Could be cleaner” or “could be more elegant” is not enough.

Valid reasons include a reproducible bug, broken invariant, unsafe lifecycle/concurrency path, wrong provenance claim, packaging failure, localization leak, visual defect or contradictory documentation/test contract.

## 5. Localization contract

The current release catalog set is:

- `ru-RU`
- `en-US`
- `es-ES`
- `ar`

Spanish is no longer a future validator; it is a current complete catalog. Arabic adds the real RTL/bidi/font/layout validation dimension.

Adding or changing a locale must remain catalog/content driven. Locale-specific Python branches should be treated as an architecture smell unless a platform/text-layout boundary genuinely requires them.

Representative switching should preserve domain state rather than reconstructing the product around language.

## 6. Human/AI collaboration and review

Human authors retain product and engineering judgment. AI tools can implement, audit, compare and challenge the system, but their output is not automatically accepted as product truth.

External agents/reviewers should receive the least repository/account scope required for their task. Their findings are inputs to review, not self-authorizing merges.

## 7. Release provenance

Release provenance is tied to the exact final commit and generated artifacts.

Final release evidence should include:

- full release-gate report;
- codebase statistics;
- visual-audit evidence;
- wheel/sdist identity and checksums;
- clean-install/package-content acceptance;
- release notes/known limitations.

These artifacts identify what was actually tested and published. They do not create DRM or prevent legitimate forks/modification.

If the candidate changes after evidence is produced, rerun the affected evidence.

## 8. Post-v0.1.0 direction

After the first release, the project may expand the research apparatus:

```text
runtime instrumentation
        ↓
mathematical/analytical models
        ↓
intervention and sensitivity experiments
        ↓
mechanistic/causal hypotheses
        ↓
adversarial / falsification battery
        ↓
new invariants and discoveries
```

The research documents can be ambitious now, but they remain proposed until implementation/evidence catches up.
