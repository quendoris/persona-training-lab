# Training Dynamics instrumentation contract

> **Status:** proposed research architecture / implementation contract. This document specifies how the mathematical framework in [`training-dynamics-mathematics.md`](training-dynamics-mathematics.md) should become observable, persisted PTL evidence. It does **not** claim that these measurements already exist in v1.0.

## 1. Purpose

The Training Dynamics subsystem must make two classes of statements possible without confusing them:

1. **online description** — what is happening to the model while Training is running;
2. **post-run reconstruction** — what changed, where it changed, what was associated with the change, and which stronger causal claims were actually tested.

The instrumentation contract is therefore not a larger Training log. It is an evidence protocol.

The central rule is:

> A metric is interpretable only together with the structural/model/probe identity required to make that metric mathematically legal.

This matters especially when two checkpoints do not have the same serialized parameter structure.

## 2. Current v1.0 boundary

The current `LocalFullFineTuneBackend` records useful but intentionally limited run metadata:

- `schema = ptl:full-finetune:v1`;
- backend/run identity;
- model path;
- epochs/batch sizes/learning rate;
- sample/step counts;
- one scalar `trainable_params` count;
- initial/final/best loss;
- device;
- upstream provenance;
- final Training status.

The current backend obtains `trainable_params` as the sum of `numel()` over model parameters with `requires_grad=True` before optimization.

That value is **not** a complete structural signature. It does not state:

- how many named parameter tensors exist;
- whether the serialized artifact contains the same named keys as the source model;
- whether parameters are tied/shared;
- whether adapters were merged or removed;
- whether vocabulary/config dimensions changed;
- whether two artifacts with different serialized tensor counts represent different computational architectures or only different serialization/reparameterization choices.

Therefore a future Training Dynamics subsystem must never infer architecture equality from `trainable_params` alone.

## 3. The structural state is first-class evidence

For every observed model/checkpoint `t`, define a structural signature

```math
\Sigma_t = (
  A_t,
  C_t,
  T_t,
  K_t,
  S_t,
  D_t,
  R_t,
  G_t,
  P_t
).
```

Recommended meanings:

- `A_t` — architecture/model-class identifier;
- `C_t` — normalized configuration digest;
- `T_t` — tokenizer/vocabulary signature;
- `K_t` — ordered/canonical set of named parameter or state objects;
- `S_t` — shape map `name -> shape`;
- `D_t` — dtype map;
- `R_t` — trainability map;
- `G_t` — storage-sharing / weight-tying graph;
- `P_t` — artifact/parameterization representation metadata, such as adapter/merged/quantized state.

The signature must also persist several counts that must **not** be collapsed into one field:

```math
N_{tensor}(t) = |K_t|,
```

```math
N_{scalar}(t)
= \sum_{k\in K_t} \operatorname{numel}(k),
```

```math
N_{trainable}(t)
= \sum_{k\in K_t:\,requires\_grad(k)} \operatorname{numel}(k),
```

and a unique-storage count

```math
N_{unique}(t)
= \sum_{u\in U_t} \operatorname{numel}(u),
```

where `U_t` is the set of unique storage groups after accounting for tied/shared weights.

### Invariant

A report such as “320 before Training, 318 after Training” is semantically incomplete until PTL can state **what was counted**.

It may describe named state objects, serialized tensors, trainable tensors, unique storage groups, or another artifact-specific quantity. PTL must preserve that distinction rather than retroactively relabel the number as “parameter count”.

## 4. Model space is variable-dimensional

When the structural signature is fixed, a parameter state can be treated locally as

```math
\theta_t \in \Theta_A \simeq \mathbb{R}^{n_A}.
```

Across structural signatures, PTL must instead model the global state space as a disjoint family of parameter spaces:

```math
\mathcal{M}
=
\bigsqcup_{A\in\mathcal{A}}
\{A\}\times \Theta_A/G_A,
```

where `G_A` denotes parameter symmetries/reparameterizations that may leave the represented function unchanged.

A Training trajectory is consequently allowed to be hybrid/piecewise:

```text
Gamma_1  -- structural event E_1 -->  Gamma_2
         -- structural event E_2 -->  Gamma_3
         ...
```

Inside one stratum, parameter-space/Fisher/Hessian measurements are well-defined in the ordinary way. Across strata, PTL needs an explicit correspondence before any coordinate-wise parameter difference is legal.

### Fail-closed rule

If two checkpoints have incompatible parameter schemas and no explicit correspondence exists, PTL must mark direct parameter comparison as **undefined**, not coerce/truncate/pad tensors until a number can be produced.

## 5. Structural event classes

A future manifest should classify transitions rather than merely noticing count changes.

Suggested semantic classes:

### `E0 — representation-only serialization difference`

Examples:

- the same computational model stored with a different file layout;
- sharded vs unsharded serialization;
- equivalent key normalization with a proven reversible mapping.

Comparison policy: restore/derive a canonical manifest, then treat the models as structurally equivalent if the mapping is proven.

### `E1 — known reparameterization`

Examples:

- a known permutation/basis transformation;
- tied/untied representation with an explicit equivalence map;
- another invertible parameter map with documented semantics.

Comparison policy: direct parameter comparison is allowed only **after** applying the recorded correspondence; function/representation metrics remain independent checks.

### `E2 — adapter/merge/factorization transition`

Examples:

- LoRA adapter present vs merged into base weights;
- adapter removal after merge;
- a low-rank factorization expanded into a dense matrix.

Comparison policy: compare represented dense/operator effect or an explicitly matched common representation; do not compare raw serialized tensor lists as though they shared coordinates.

### `E3 — genuine architecture/schema change`

Examples:

- vocabulary/output dimension change;
- layer/head/block insertion or removal;
- changed hidden width;
- module replacement;
- another transition with no total coordinate correspondence.

Comparison policy: global parameter subtraction is undefined. Function-space, representation-space, probe-kernel and behavioral protocols become primary.

## 6. Correspondence manifest

When a cross-checkpoint parameter comparison is allowed, PTL must persist the mapping that makes it allowed.

A conceptual mapping artifact is:

```text
parameter_correspondence
  schema
  left_structure_digest
  right_structure_digest
  mapping_kind
  mappings[]
    left_name
    right_name
    transform
    shape_contract
    evidence
  unmatched_left[]
  unmatched_right[]
  coverage
```

No automatic fuzzy name match is sufficient evidence by itself.

A useful symmetric matched-parameter coverage measure is

```math
\rho_{param}(a,b)
=
\frac{
  2\sum_{k\in M_{ab}} n_k
}{
  N_{scalar}(a)+N_{scalar}(b)
},
```

where `M_ab` contains only parameters with a proven correspondence and `n_k` is the number of matched scalar degrees of freedom represented by that correspondence.

Every parameter-space result must carry this coverage when it is below 1.

## 7. Measurement legality matrix

The subsystem should determine legality before computing expensive metrics.

| Measurement | Same exact schema | Proven reparameterization | Partial correspondence | Different architecture |
|---|---|---|---|---|
| Raw parameter `L2` | yes | only after alignment | matched subset only | no |
| Fisher quadratic step | yes, locally | after local coordinate mapping | matched/local only | no global cross-stratum value |
| `SVD(Delta W)` | yes per matched block | after alignment | matched blocks only | no for unmatched blocks |
| Gradient/update cosine | yes within one run/schema | local mapping required | matched subset only | no global coordinate value |
| Output KL/JS | yes | yes | yes | yes if output protocol is compatible |
| CKA | yes | yes | yes | yes when the same probe examples are represented |
| SVCCA/principal angles | yes | yes | yes | yes for selected representations; feature width may differ |
| Empirical NTK/probe Gram | yes | yes | yes | yes when the chosen output/probe contract is compatible |
| Behavioral protocol | yes | yes | yes | yes when protocol versions are comparable |

The legality decision itself must be persisted with the result.

## 8. Evidence sampling levels

Not every quantity belongs on every optimizer step.

### 8.1 Every Training step

Cheap/high-value evidence:

- step/epoch/batch identity;
- scalar loss;
- learning rate;
- actual batch size/token count where available;
- optimizer step count;
- gradient norm after/before clipping when the distinction is measured;
- update norm where available;
- clipping event/ratio;
- selected optimizer-state summaries;
- runtime/correlation identity;
- data-slice identifiers sufficient to reconstruct which semantic subset contributed.

### 8.2 Every `N` steps

Moderate-cost sketches:

- per-layer/block gradient norms;
- update norms and gradient/update cosine;
- gradient covariance/noise sketches;
- selected probe logits/probabilities;
- lightweight representation summaries;
- structural-signature digest verification;
- change-point trigger inputs.

The interval `N` must be part of the protocol/version, not a hidden UI preference.

### 8.3 Every checkpoint

Checkpoint evidence:

- full `Sigma_t` structural manifest;
- artifact hash/inventory;
- optimizer/scheduler state identity if persisted;
- frozen probe outputs;
- selected activations or sufficient sketches for CKA/SVCCA;
- selected Jacobian/probe-NTK sketches;
- parameter-update spectra for matched blocks;
- Fisher/Hessian-vector derived quantities selected by protocol;
- environment/runtime provenance required to interpret the checkpoint.

### 8.4 Post-run

Expensive descriptive/associational analysis:

- full function-space divergence curves;
- layerwise CKA/SVCCA/principal-angle analysis;
- MMD/change-point detection;
- spectral/rank summaries;
- cross-dataset-slice gradient interference;
- TracIn-style training-example/subset attribution;
- selected Hessian/Fisher generalized analyses.

### 8.5 On-demand research intervention

Causal/mechanistic evidence:

- counterfactual replay from a pinned checkpoint;
- data subset removal/down-weighting;
- matched control run;
- layer/module freeze;
- activation patching/causal tracing/ablation;
- targeted influence-function forensic analysis when its assumptions are acceptable.

These are experiments, not derived decorations on an existing run.

## 9. Probe protocol is part of the measurement

Function/representation/kernel comparison requires the same meaningful observations on both sides.

A probe protocol must therefore persist at least:

```text
probe_protocol
  protocol_id
  version
  content_digest
  tokenizer/input-preparation contract
  output-selection contract
  generation/inference parameters
  semantic slice labels
  ordering/canonicalization rules
```

A CKA value without probe identity is not reusable evidence.

A JS/KL value without output-selection/tokenization semantics is not reusable evidence.

An empirical NTK value without specifying which outputs/Jacobian projection were used is not reusable evidence.

## 10. Training Dynamics artifact

A future run should produce one research artifact namespace rather than scattering unrelated CSV/log files.

Conceptual layout:

```text
artifacts/training_dynamics/<run_id>/
  manifest.json
  structure/
    checkpoint_<id>.json
    correspondences/
      <left>__<right>.json
  steps/
    step_metrics.parquet
    block_metrics.parquet
  probes/
    <probe_protocol_id>/
      checkpoint_<id>/...
  representations/
    checkpoint_<id>/...
  spectra/
    checkpoint_<id>/...
  analytics/
    change_points.json
    attribution.json
    interventions.json
  evidence.json
```

This path is a **proposed** research namespace. It is not the current `ptl:full-finetune:v1` artifact contract.

### Manifest requirements

The top-level manifest should include:

- schema/version;
- PTL commit/release identity;
- Training run ID and fingerprints already used by Training;
- source/base-model structural signature and artifact provenance;
- resulting checkpoint structural signatures;
- probe protocols and digests;
- measurement protocol version;
- cadence;
- enabled/disabled measurement families;
- deterministic/random seeds where meaningful;
- device/runtime/software provenance;
- files + hashes;
- incomplete/failed measurement markers.

## 11. Missing evidence must remain missing

Instrumentation failure must not silently become zero.

Examples:

- Fisher estimate unavailable -> `unavailable`, not `0`;
- activations not captured -> CKA `not_measured`, not `1.0 similarity`;
- structural mapping absent -> parameter distance `undefined_structure`, not a partial heuristic number;
- probe protocol mismatch -> functional/behavioral comparison `incomparable_protocol`;
- counterfactual replay not run -> causal evidence level remains below counterfactual.

This is part of scientific integrity, not only error handling.

## 12. Evidence levels for Analytics

Every generated explanation should carry the strongest evidence class it actually satisfies.

### `D0 — descriptive`

Examples:

- loss changed;
- Fisher step increased;
- output JS divergence changed;
- layer 22 CKA drift increased;
- singular spectrum concentrated.

Allowed wording: **“observed / changed / occurred.”**

### `D1 — associational`

Examples:

- a dataset slice has sustained gradient alignment with the observed update;
- TracIn ranks examples as strongly associated with a target behavior;
- representation drift and behavioral drift co-occur in time.

Allowed wording: **“associated / aligned / co-occurred / candidate explanation.”**

### `D2 — counterfactual`

A controlled intervention changes/removes the suspected cause while preserving an appropriate baseline and materially changes the effect.

Allowed wording: **“the intervention supports a causal contribution.”**

### `D3 — mechanistic`

Multiple converging interventions localize an internal path or mechanism, for example data intervention plus activation patching/ablation with consistent intermediate and behavioral effects.

Allowed wording must still describe the exact demonstrated mechanism rather than anthropomorphize inaccessible internal state.

## 13. Analytics answer object

The future Analytics layer should construct an evidence object before rendering prose.

Conceptually:

```text
training_change_explanation
  interval
  left_checkpoint
  right_checkpoint
  structural_relation
  comparison_coverage

  observations[]
    measurement
    value/change
    protocol
    evidence_location

  localization[]
  candidate_causes[]
  interventions[]

  evidence_level
  limitations[]
  prohibited_inferences[]
```

Natural-language explanation is a view over this object, not the source of truth.

## 14. Example: different tensor counts

Assume a source artifact appears to contain 320 named serialized tensors and a resulting artifact contains 318.

PTL must **not** immediately compute

```math
\theta_{after}-\theta_{before}
```

or conclude that Training “removed two model parameters”.

Required sequence:

1. capture both structural manifests;
2. determine whether `320`/`318` are `N_tensor`, state-dict keys, storage groups, or another count;
3. compare architecture/config/tokenizer signatures;
4. determine exact added/removed/renamed objects;
5. inspect tied/shared storage semantics;
6. classify the transition as `E0/E1/E2/E3` (or mark it unknown);
7. build a parameter correspondence only for proven matches;
8. report correspondence coverage;
9. use only legal parameter metrics on that correspondence;
10. use function-space/representation/probe-kernel/behavioral comparisons as the architecture-independent bridge;
11. leave the cause of the structural difference unresolved until artifact/config/serialization evidence proves it.

The number change itself is evidence that a structural investigation is required; it is not an explanation.

## 15. Runtime and storage safety

Training Dynamics can become large. It must therefore remain downstream evidence rather than a new hidden owner of model artifacts.

Design constraints:

- model/checkpoint artifacts remain owned by the Training/model-version provenance contract;
- measurement artifacts reference their exact checkpoint/artifact hashes;
- a partial analysis artifact must not make a completed Training artifact look invalid;
- destructive cleanup must know whether research artifacts reference a checkpoint before deleting it;
- background analysis must acquire runtime claims appropriate to the model/checkpoint resources it reads;
- on failure, incomplete research evidence is marked incomplete rather than mutating the original model version.

The existing PTL runtime-lease architecture should be reused rather than creating a second concurrency system.

## 16. Performance policy

The mathematical framework is intentionally richer than the online loop.

The default architecture should therefore separate:

```text
Training critical path
       |
       +-- cheap step metrics
       +-- bounded scheduled sketches
       +-- checkpoint manifest/probe capture

post-run / on-demand analysis
       |
       +-- expensive geometry
       +-- spectra/HVP/Jacobian analysis
       +-- attribution
       +-- interventions
```

No expensive research metric should be added to every optimizer step merely because it can be computed mathematically.

The measurement protocol must record both **what was enabled** and **what sampling rate was used**, so two runs with different instrumentation are not presented as equally observed.

## 17. Acceptance criteria before implementation is called valid

A Training Dynamics implementation should not be considered scientifically usable until tests demonstrate at least:

1. structural manifests distinguish named-tensor, scalar, trainable and unique-storage counts;
2. tied/shared weights do not double-count `N_unique`;
3. a changed tensor schema makes direct global parameter subtraction fail closed;
4. exact/known correspondence enables only the mapped parameter metrics;
5. CKA accepts different feature widths for the same probe examples;
6. function-space comparison survives parameter-dimension change when output protocol matches;
7. every persisted metric carries protocol/structural identity sufficient to reproduce its meaning;
8. missing measurements remain explicit missing states;
9. checkpoint/artifact hashes prevent accidental comparison of mislabeled bytes;
10. causal wording cannot be emitted from descriptive/associational evidence alone;
11. intervention runs are pinned to explicit checkpoints/data/protocols;
12. instrumentation failure cannot corrupt or silently change the primary Training result.

## 18. Relationship to current PTL

This contract deliberately sits ahead of the current implementation.

Current v1.0 Training already gives PTL several foundations that the subsystem should reuse:

- exact Training run identity;
- pinned Profile and Dataset fingerprints at run creation;
- local full-fine-tune artifacts;
- `training_metadata.json`;
- runtime-operation/resource claims;
- registered model versions;
- evaluation protocol/version semantics;
- Agents lineage/provenance structure.

What is still absent is the high-dimensional observation layer described here: structural manifests, checkpoint-level probe/representation geometry, Fisher/Hessian/Jacobian sketches, parameter correspondences, attribution and controlled replay evidence.

That absence must remain visible in v1.0 documentation until each corresponding component is actually implemented and tested.

## 19. Primary mathematical companion

For definitions, method selection, rejected interpretations, equations, theorem-level rationale and literature, see:

- [`training-dynamics-mathematics.md`](training-dynamics-mathematics.md)

The present document answers a different question:

> **What exactly must PTL record, validate and persist so those mathematical statements remain legal when real model artifacts, checkpoint schemas and parameter dimensions change?**
