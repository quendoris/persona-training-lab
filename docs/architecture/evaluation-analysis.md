# Evaluation & Analysis Architecture

Persona Training Lab v0.1.0 separates **evaluation execution** from **analysis of persisted evaluation results**.

The central rule is:

> **Tests may run model inference and persist a portrait; Analysis reads persisted portrait evidence and derives presentation/comparison results without running new inference.**

For the exact battery, serialized case grammar, scoring formula and methodological limits, read the [Evaluation contract](../reference/evaluation-contract.md). For the user workflow, read [Tests and Analysis](../user-guide/tests-and-analysis.md).

## 1. Main composition

Production wiring provides:

```text
LocalModelService
ModelVersionsService
RuntimeOperationCoordinator
        │
        ▼
ExperimentsService
        │
        ├───────────────┐
        ▼               ▼
TestsViewModel      experiments persistence
        │               │
        ▼               ▼
TestsScreen        AnalysisViewModel
                        │
                        ▼
                   AnalysisScreen
```

A separate `AnalysisService` / `analysis_results` repository remains as a compatibility/fallback path, but the production application wires the experiments-backed lineage Analysis view-model.

## 2. Evaluation execution owner

`ExperimentsService.run_personality_portrait_test_pack(...)` owns the current portrait execution contract.

Its main responsibilities are:

1. resolve the intended model version;
2. resolve/probe the actual model artifact path;
3. load the bundled portrait battery;
4. acquire runtime-operation claims when a coordinator is available;
5. run every questionnaire item through `LocalModelService.generate_at(...)`;
6. validate/normalize the short `SCORE: N` response contract;
7. persist one experiment payload;
8. close the runtime lease with a terminal state.

The UI does not implement a second scoring engine.

## 3. Exact model-version selection

When an explicit `model_version_id` is supplied, evaluation searches for that exact persisted version.

If it does not exist:

```text
result = model_version_not_found
```

and PTL does **not** silently use the latest model.

When the exact version exists, its `artifact_path` is the model path probed and used for generation.

This exact-selection rule is important for lineage comparison: a human-readable title is not enough to establish model identity.

## 4. Default model selection

If no explicit model version is requested, the service can use the first registered version returned by the model-version service.

If no registered version is available, it falls back to the configured local-model path.

That fallback is useful for ordinary local evaluation, but it is weaker provenance than an exact registered model-version run.

## 5. Runtime resource coordination

A portrait operation can claim:

```text
experiment:<experiment_id>        write
model_path:<resolved path>         read
compute_device:local_inference     write
model_version:<version_id>         read   # when known
artifact_path:<artifact_path>      read   # when known
```

The runtime coordinator therefore prevents supported PTL workflows from blindly overlapping incompatible use of the same semantic resources.

These claims are application coordination, not an OS-level GPU/filesystem lock.

## 6. Evaluation runtime identity

A new portrait run receives:

```text
evr_<8 hex>
```

The runtime operation, when present, is separate from that evaluation ID and has its own operation/correlation identity.

Do not merge the concepts:

```text
evaluation record identity
        !=
runtime-operation identity
        !=
model-version identity
```

## 7. Battery loading

The current battery is loaded from the packaged resource:

```text
persona_training_lab.application.experiments.test_batteries/
    big_five_short_v1.jsonl
```

Every non-empty line is JSON and becomes a `PortraitTestCase`.

Battery metadata includes fields such as:

```text
battery_version
instrument
scoring_version
trait
key
item
reverse
scale_min
scale_max
response_format
```

Malformed/missing required battery fields fail the battery-load stage rather than being silently skipped.

## 8. Generation contract

Each battery item is executed with an explicit instruction prompt requiring:

```text
SCORE: N
```

where `N` is an integer from 1 through 5.

The evaluator intentionally asks for a compact machine-parseable response. It does not ask Analysis to infer a score from arbitrary prose later.

## 9. Per-case success predicate

A case is successful only when both are true:

```text
model result normalizes to responding
AND
SCORE: [1-5] can be parsed
```

A model response can therefore exist while the case is still invalid because it violated the scoring grammar.

The persisted payload keeps both normalized response and bounded diagnostic raw-response information.

## 10. Complete vs partial evaluation

After all cases:

```text
failures == 0  -> completed
failures > 0   -> partial
```

A partial result is intentionally persisted rather than discarded.

The outward result is:

```text
portrait_completed
portrait_partial
```

while the persisted evaluation status remains the canonical lifecycle value.

## 11. Safe-stop boundary

Unexpected portrait exceptions are captured through `ApplicationErrorReporter` when available.

The stable outward result becomes:

```text
safe_stop
```

and the runtime lease is failed.

A final guard also fails any still-open lease with:

```text
operation_without_terminal_status
```

so the normal service path does not deliberately leave a successful-looking active lease after an unclassified exit.

## 12. Tests UI thread boundary

The Tests screen does not execute the synchronous portrait loop directly on the Qt GUI thread.

It creates a worker object, moves that worker to a `QThread`, and receives the final `ExperimentRunResult` through a signal.

This means the normal questionnaire inference loop does not block Qt event dispatch.

The thread is an execution carrier. Semantic operation ownership still belongs to the runtime-operation layer.

## 13. Tests shutdown boundary

Tests participates in the shell background-work shutdown contract.

On shutdown it asks its QThread to quit and can wait for a bounded interval.

That does not imply arbitrary model generation is cooperatively cancellable mid-call. The outer application therefore retains workspace ownership until registered background workers actually stop.

See [Background work lifecycle](background-work-lifecycle.md).

## 14. Tests projection from persistence

After execution, Tests reads the experiment repository and parses portrait payloads.

Without an exact model-version target it uses the repository's current ordering.

With:

```text
target_model_version_id
```

it filters to portraits whose persisted parsed `model_version_id` exactly equals that target.

If no portrait exists for the selected version, Tests shows a target-empty state. It does not substitute another version's portrait.

## 15. Tests metrics are presentation of persisted evidence

Current Tests metrics include:

```text
run count / version run count
latest status
valid item count / total
failure count
```

The item metric is coverage, not a normalized personality percentage.

The failure count is derived from invalid/non-responding cases plus persisted summary/status compatibility rules.

## 16. Analysis is read-only with respect to model execution

The production Analysis path does not call:

```text
LocalModelService.generate_at(...)
```

It parses persisted portrait records and derives:

```text
factor means
current summary
previous summary
delta
insights
case comparison rows
```

Thus Analysis results are deterministic with respect to the persisted payload and current parser/presentation code.

## 17. Default Analysis pair

Without exact lineage context, current Analysis first projects the generic experiment registry to personality-portrait records, then preserves repository order:

```text
latest   = portrait_experiments[0]
previous = portrait_experiments[1] when present
```

The current semantic experiment-title protocol identifies new portrait rows; structured legacy payloads beginning with `PORTRAIT:` or `SUMMARY:` remain accepted for compatibility. Other experiment rows are excluded from Tests/Analysis portrait history.

One portrait is sufficient for current factor display.

Two portraits are required for a before/after delta.

## 18. Protocol identity

The comparable protocol key is:

```text
(battery_version, scoring_version)
```

It is unknown if either element is empty or represented as `—`.

Numeric delta is allowed only when both keys are known and exactly equal.

## 19. Protocol mismatch fails closed for delta

If two portrait records use different battery/scoring identities:

- the latest portrait remains individually visible;
- the previous portrait can remain visible;
- numeric delta becomes `—`;
- the UI explains that the protocols must match.

PTL does not perform cross-protocol arithmetic merely because both payloads contain similarly named factors.

## 20. Exact lineage comparison

When lineage context provides both:

```text
selected.model_version_id
current.model_version_id
```

the lineage Analysis view-model resolves a portrait for each exact ID.

If one side is missing, no unrelated portrait is substituted.

If both exist but protocol identities differ, the exact pair remains visible as the intended comparison context while numeric delta remains unavailable.

## 21. Factor calculation boundary

Factor means come from parsed valid case scores.

Reverse-scored values use the current 1–5 scale rule documented in the Evaluation contract.

Analysis does not invent values for missing factors.

A partial run can therefore expose a mean computed from fewer than the nominal number of items for that factor.

## 22. Delta meaning

For a common factor in a protocol-compatible pair:

```text
delta = latest_mean - previous_mean
```

The result is an arithmetic difference.

It is **not** automatically:

```text
statistical significance
causal effect
effect size
clinical change
mechanistic explanation
```

Those stronger claims require additional methodology/evidence.

## 23. Compatibility `analysis_results` path

`AnalysisService` still exposes rows from the `analysis_results` repository.

That path exists for compatibility/fallback composition.

It must not be described as the normal producer of current portrait Analysis because production wiring supplies `ExperimentsService` to the lineage-aware Analysis view-model.

The normal current screen derives its comparison from persisted `experiments`.

## 24. Persistence boundary

The principal current portrait evidence is stored in the `experiments` record.

The serialized subtitle/payload contains protocol/model/artifact metadata and bounded per-case diagnostic data.

This is intentionally not a normalized scientific warehouse.

It does not contain complete model-directory hashes, a complete software/hardware environment manifest, or full unbounded generations.

## 25. Provenance boundary

Current evaluation can strongly preserve:

```text
experiment ID
explicit model-version ID when selected
artifact path reference
battery_version
scoring_version
case validity / score data
evaluation status
```

It does not cryptographically prove the complete evaluated model-directory bytes.

See [Provenance & External-State Boundaries](provenance-and-external-state.md).

## 26. Methodology boundary

The current portrait pipeline is a versioned product/research protocol.

It is not a clinical human personality assessment and Analysis must not silently translate its means/deltas into claims about inaccessible internal mental state.

The stronger mathematical/mechanistic framework belongs to the proposed Training Dynamics layer and remains separate from current v0.1.0 instrumentation.

## 27. Regression contract

Current tests protect important parts of this architecture, including:

- exact requested model-version selection;
- no fallback when an explicit model version is missing;
- persisted model-version/artifact metadata;
- matching protocol versions allowing delta;
- mismatched battery versions blocking delta;
- mismatched scoring versions blocking delta;
- unknown protocol identity blocking delta;
- exact lineage pair mismatch without substitution;
- selected-version Tests scoping;
- evaluation semantic status/result presentation.

These are behavioral regression contracts, not proof of scientific validity.

## 28. Developer invariants

Evaluation/Analysis changes should preserve these rules unless deliberately redesigned:

1. explicit model-version selection must never silently substitute another version;
2. Tests execution must stay off the GUI thread while it contains synchronous model inference;
3. runtime-operation ownership and QThread lifetime must remain separate concepts;
4. partial evaluations remain visibly partial;
5. Analysis must not perform new inference on the normal current path;
6. numeric delta requires known/equal battery + scoring identities;
7. exact lineage pair selection must not substitute another portrait;
8. `analysis_results` compatibility storage must not be documented as the primary current portrait-analysis pipeline;
9. bounded raw-response storage must not be called a full transcript;
10. artifact path identity must not be called complete artifact-byte provenance;
11. product score/delta output must not be upgraded into causal/clinical claims;
12. protocol-changing code/battery changes require corresponding version/test/documentation review.

## Related documentation

- [Tests and Analysis](../user-guide/tests-and-analysis.md)
- [Evaluation contract](../reference/evaluation-contract.md)
- [Statuses, Result Codes & Identifiers](../reference/statuses-and-identifiers.md)
- [Provenance & External-State Boundaries](provenance-and-external-state.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Background work lifecycle](background-work-lifecycle.md)
- [Training Dynamics mathematics](training-dynamics-mathematics.md)
- [Training Dynamics instrumentation](training-dynamics-instrumentation.md)
