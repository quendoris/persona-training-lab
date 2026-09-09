# Mathematical Framework for Training Dynamics Analysis

> **Status:** proposed architecture / research design. This document defines the mathematical language PTL should use to observe, describe, and later explain neural-network change during Training. It does **not** claim that the complete instrumentation described here already exists in v1.0.

## Purpose

Persona Training Lab needs to answer two different questions without collapsing them into one vague metric:

1. **During Training:** what is happening to the model right now?
2. **After Training:** what kind of change was that, where did it happen, which data/optimization forces were associated with it, and what evidence supports saying why it happened?

The central design decision is that no single scalar, coordinate system, or mathematical object can answer those questions for a modern neural network.

A useful Training observation must therefore track the same trajectory simultaneously in several coupled spaces:

```text
parameter / optimizer space
        ↕
information geometry
        ↕
function / output-distribution space
        ↕
representation geometry
        ↕
behavior / evaluation space
```

The framework is intentionally mathematically richer than the equations PTL will need to solve. Most quantities can be estimated from checkpoints, gradients, Jacobian-vector products, Hessian-vector products, activation samples, and controlled probe sets. We do not need a closed-form solution of the Training dynamics in order to describe the observed trajectory.

## 1. The object being observed

Let the trainable model at Training time/index `t` be

```math
f_{\theta_t}
```

with parameters

```math
\theta_t \in \Theta.
```

For an optimizer with persistent state, the true dynamical state is not only `theta`.

Write

```math
S_t = (\theta_t, o_t, d_t)
```

where:

- `theta_t` is the model parameter state;
- `o_t` is optimizer state such as momentum/Adam moments, scheduler state, scaler state, and related update memory;
- `d_t` records the sampled Training-data state needed to interpret the update.

For analysis we augment this physical Training state with observable projections:

```math
X_t = (S_t, P_t, R_t, B_t).
```

Here:

- `P_t` is model behavior in probability/function space on a fixed probe distribution;
- `R_t` is internal representation geometry;
- `B_t` is measured external behavior/evaluation state.

The sequence

```math
\Gamma = \{X_t\}_{t=0}^{T}
```

is the observed Training trajectory.

PTL should analyze `Gamma`, not only the final loss and not only `theta_T - theta_0`.

## 2. Why raw parameter distance is not enough

Neural-network parameter coordinates contain symmetries.

Examples include:

- permutation of equivalent hidden units/heads/features;
- rescalings that can be absorbed by adjacent layers;
- basis changes in internal subspaces that leave the represented function nearly unchanged;
- large parameter motion that produces tiny functional motion;
- small parameter motion in a sensitive direction that produces large behavioral motion.

Therefore

```math
\|\theta_b - \theta_a\|_2
```

is useful as an engineering quantity but is not a coordinate-independent statement of how much the model changed.

Conceptually the physical model lives closer to an equivalence class

```math
[\theta] \in \Theta / G
```

where `G` represents parameter symmetries that do not materially change the realized function.

PTL therefore uses raw parameter-space quantities only together with geometry/function/representation measurements.

## 3. Information geometry as the primary local parameter metric

For probabilistic models the natural local metric is the Fisher information metric.

For conditional model distribution

```math
p_\theta(y\mid x),
```

define

```math
F(\theta)
=
\mathbb{E}_{x,y}
\left[
\nabla_\theta \log p_\theta(y\mid x)
\nabla_\theta \log p_\theta(y\mid x)^\top
\right].
```

For an infinitesimal parameter update `d theta`, the local Fisher-Rao line element is

```math
ds^2 = d\theta^\top F(\theta) d\theta.
```

This is valuable because it measures parameter motion according to how strongly that motion changes the model's output distribution.

### 3.1 Quantities to record

For update

```math
\Delta\theta_t = \theta_{t+1} - \theta_t,
```

record or estimate:

```math
\delta_{FR,t}^2
=
\Delta\theta_t^\top F_t\Delta\theta_t.
```

The accumulated Fisher-Rao path length is

```math
L_{FR}
=
\sum_t
\sqrt{\Delta\theta_t^\top F_t\Delta\theta_t}.
```

This answers a more meaningful question than raw Euclidean path length:

> how far did Training move through directions that actually affect predictive distributions?

### 3.2 Practical approximation

PTL should not attempt to materialize the full Fisher matrix for a large model.

Useful approximations include:

- empirical Fisher quadratic forms;
- diagonal/blockwise approximations;
- K-FAC-style layer blocks where justified;
- direct Jacobian-vector products sufficient to evaluate selected quadratic forms.

The target is the observable geometry, not a dense matrix artifact.

### Why Fisher rather than raw L2

Raw L2 is cheap but parameterization-sensitive. Fisher geometry is tied directly to local probability-distribution change and is therefore a better primary local metric of meaningful model motion.

## 4. Function-space distance: what changed at the output

Parameter geometry still does not tell us which behavior changed.

Choose a frozen probe distribution/set

```math
Q = \{x_i\}_{i=1}^{N}
```

that is versioned and independent of the Training minibatch stream.

For each probe, compare model distributions across checkpoints.

### 4.1 Jensen-Shannon divergence for bounded dashboard-scale change

For two predictive distributions `p` and `q`, define

```math
JS(p,q)
=
\tfrac12 KL(p\|m)
+
\tfrac12 KL(q\|m),
\qquad
m=\tfrac12(p+q).
```

Aggregate across probes:

```math
D_{func}(a,b)
=
\frac{1}{N}
\sum_{i=1}^{N}
JS(
 p_{\theta_a}(\cdot\mid x_i),
 p_{\theta_b}(\cdot\mid x_i)
).
```

JS is useful for an operator-facing scale because it is symmetric and bounded.

### 4.2 KL remains important locally

For very small changes,

```math
KL(p_{\theta}\|p_{\theta+d\theta})
\approx
\tfrac12 d\theta^\top F(\theta)d\theta.
```

This connects function-space change to Fisher geometry.

PTL should exploit that connection rather than treating output divergence and parameter geometry as unrelated metrics.

### 4.3 Additional output observables

Depending on the probe protocol:

- predictive entropy;
- token-rank/margin changes;
- probability mass transferred between semantic alternatives;
- calibration error;
- response-length/distribution changes;
- refusal/compliance or other explicitly defined behavioral probabilities.

These remain probe-dependent measurements, not universal personality truths.

## 5. Representation geometry: how internal organization changed

Raw neuron-to-neuron comparison is fragile because internal bases can rotate or permute while representing the same subspace.

PTL should therefore compare representations geometrically.

Let

```math
H_t^{(\ell)} \in \mathbb{R}^{N\times d_\ell}
```

be activations for a fixed probe set at layer `ell`.

### 5.1 Centered Kernel Alignment (CKA)

CKA compares representation geometry through centered Gram matrices and is invariant to orthogonal basis changes and isotropic rescaling.

A layerwise drift score can be written

```math
D_{CKA}^{(\ell)}(a,b)
=
1-CKA(
 H_a^{(\ell)},
 H_b^{(\ell)}
).
```

This gives a layer-local answer to:

> where inside the network did the representation reorganize?

### 5.2 Principal angles / SVCCA as a secondary view

For selected layers/subspaces, principal angles or SVCCA-style comparisons describe subspace rotation more explicitly.

They are useful when CKA reports a large change and we want to characterize which dominant subspace moved.

### 5.3 Representation spectrum

For centered representation covariance `C_l`, track its eigenvalue spectrum.

Useful summaries include effective/participation rank:

```math
r_{eff}
=
\frac{(\sum_i \lambda_i)^2}{\sum_i \lambda_i^2}.
```

This helps distinguish:

- simple rotation with similar dimensional structure;
- concentration into fewer dominant directions;
- expansion into a higher-dimensional representation.

### Why CKA/subspaces rather than neuron matching

A feature may move to another basis coordinate without disappearing. Neuron-by-neuron identity is therefore too brittle to serve as the primary representation metric.

## 6. Spectral analysis of the parameter update

For each matrix-like trainable block `W_l`, define checkpoint update

```math
\Delta W_l = W_{l,b}-W_{l,a}.
```

Compute or approximate its singular spectrum

```math
\Delta W_l = U\Sigma V^\top.
```

Record:

- leading singular values;
- spectral norm;
- Frobenius norm;
- stable/effective rank;
- cumulative energy captured by the first `k` singular directions;
- alignment of dominant update directions with dominant existing weight/activation subspaces.

This tells us whether learning is broadly distributed or concentrated in a small number of directions.

A low-rank-looking update is descriptive evidence of concentrated adaptation. It is not by itself evidence for a single causal feature.

## 7. Gradient and optimizer dynamics

The optimizer supplies the immediate force acting on parameter state.

Let

```math
g_t = \nabla_\theta L_t
```

and actual optimizer update

```math
u_t = \theta_{t+1}-\theta_t.
```

For SGD `u_t` is closely related to `-g_t`; for Adam-like optimizers it is transformed by optimizer state.

PTL should therefore record both gradient and actual update geometry.

### 7.1 Core quantities

```math
\|g_t\|,
\qquad
\|u_t\|,
\qquad
\cos(g_t,-u_t)
=
\frac{-g_t^\top u_t}{\|g_t\|\|u_t\|}.
```

Also track per-layer versions.

### 7.2 Path efficiency

Raw displacement from the start:

```math
D_t=\|\theta_t-\theta_0\|.
```

Accumulated path length:

```math
L_t=\sum_{k<t}\|u_k\|.
```

Their ratio

```math
\eta_{path}=D_t/L_t
```

is a crude but useful measure of directness versus wandering in raw coordinates.

A Fisher-weighted analogue is preferred for semantic interpretation.

### 7.3 Turning angle

```math
\alpha_t
=
\arccos
\frac{u_{t-1}^\top u_t}
{\|u_{t-1}\|\|u_t\|}.
```

Large sustained turning can indicate a change in the dominant optimization regime, data regime, or conflict structure.

It is a trigger for deeper analysis, not an explanation by itself.

## 8. Gradient noise and stochastic dynamics

Minibatch Training is a stochastic dynamical system.

Decompose a stochastic gradient as

```math
g_t^{(batch)}
=
\bar g_t + \varepsilon_t,
```

where `bar g_t` is an estimate of the local full-data drift and `epsilon_t` is minibatch noise.

PTL can estimate:

- gradient covariance in selected blocks/subspaces;
- signal-to-noise ratio;
- gradient noise scale;
- anisotropy of stochastic updates.

A continuous stochastic differential equation can be used as an **interpretive approximation**,

```math
d\theta
=
- A(\theta,t)\nabla L\,dt
+
B(\theta,t)dW_t,
```

but PTL does not need to solve this SDE. The observed discrete trajectory remains authoritative.

### Why use the SDE viewpoint at all

It gives precise language for separating systematic drift from stochastic diffusion and for comparing optimizer/data regimes.

### Why not make it the sole model

Real optimizers are discrete, adaptive, scheduled, stateful, and can operate outside the small-step assumptions under which the continuous approximation is cleanest.

## 9. Gradient interference and transfer between data subsets

To explain why one behavior improves while another degrades, PTL needs interaction measurements between objectives/data slices.

For two versioned subsets/objectives `A` and `B`, estimate gradients

```math
g_A=\nabla L_A,
\qquad
g_B=\nabla L_B.
```

Define gradient alignment

```math
I_{AB}
=
\cos(g_A,g_B).
```

Interpretation:

```text
I_AB > 0  -> locally synergistic directions
I_AB ~ 0  -> locally independent/orthogonal
I_AB < 0  -> locally conflicting directions
```

The full matrix across research slices provides an interference/transfer map.

This is especially useful for Persona Training because desired traits can compete locally even when aggregate loss decreases.

## 10. Curvature: what local landscape the optimizer encountered

Let

```math
H_t=\nabla_\theta^2 L(\theta_t)
```

be the Hessian.

PTL should not materialize a full dense Hessian. Instead use Hessian-vector products and stochastic spectral estimators to obtain:

- leading eigenvalues/eigenvectors;
- trace estimates;
- curvature along the actual update direction;
- curvature along selected behavioral/gradient directions.

Directional curvature is

```math
\kappa(u)
=
\frac{u^\top H u}{u^\top u}.
```

A more geometry-aware generalized comparison is conceptually

```math
H v = \lambda F v,
```

which compares loss curvature to information-geometric scale.

### Why not use “sharpness” as the verdict

Raw Hessian eigenvalues and Euclidean sharpness depend on parameterization/scaling and can be misleading across equivalent neural-network parameterizations.

Curvature is valuable as one local dynamical observable, especially when interpreted relative to update/Fisher geometry, not as a one-number theory of generalization.

## 11. Jacobian and NTK drift: feature learning versus local linearization

For fixed probes, let `J_t` be the model Jacobian with respect to selected outputs and parameters.

The empirical Neural Tangent Kernel is

```math
K_t = J_tJ_t^\top.
```

Track normalized kernel drift such as

```math
\delta_K(t)
=
\frac{\|K_t-K_0\|_F}{\|K_0\|_F}.
```

Interpretation:

- small kernel drift with substantial output fitting is evidence consistent with a more locally linear / “lazy” regime on the chosen probes;
- large kernel drift indicates stronger change of the feature/Jacobian geometry.

### Why NTK is diagnostic rather than the master model

Finite-width transformers under practical fine-tuning need not remain in a fixed-kernel regime. NTK is therefore useful for answering **whether local linearization remained adequate**, not for assuming that it did.

## 12. Multi-scale dynamical-system view

Build a lower-dimensional observable macrostate

```math
z_t=
[
L_t,
\delta_{FR,t},
D_{func,t},
D_{CKA,t}^{(1)},...,D_{CKA,t}^{(L)},
r_{eff,t},
\delta_{K,t},
B_t,...
].
```

After robust normalization, treat `z_t` as the trajectory used for phase analysis.

Useful derived quantities are:

- velocity `z_{t+1}-z_t`;
- acceleration / second differences;
- turning angle in macrostate space;
- path length;
- recurrence or stabilization;
- change points.

## 13. Change-point detection: when did the regime change?

Training often contains phases rather than one homogeneous process.

Examples:

- rapid initial adaptation;
- slower consolidation;
- onset of interference/forgetting;
- learning-rate transition;
- representation reorganization;
- plateau or instability.

PTL should detect candidate regime boundaries from multivariate `z_t`, not from loss alone.

Suitable families include:

- energy-distance change-point methods;
- kernel/MMD change-point methods;
- robust likelihood/Bayesian change-point methods where an explicit probabilistic model is justified.

The output should be an interval/boundary with evidence, not a mystical label such as “the network changed personality here”.

## 14. Behavioral state is its own mathematical projection

A Persona Training run ultimately matters because externally measured behavior changes.

Let a versioned behavioral battery produce vector

```math
B_t \in \mathbb{R}^m
```

or a richer collection of distributions/ordinal outcomes.

For checkpoint pair `(a,b)`:

```math
\Delta B_{a\to b}=B_b-B_a.
```

PTL should attach uncertainty to behavioral estimates where repeated sampling is relevant.

Behavioral change must then be related to, but not identified with, internal change.

The system should be able to say:

```text
behavior changed strongly
representations changed weakly in early layers
representations changed strongly in late layers
functional divergence concentrated on probe family X
```

without forcing those observations into one scalar score.

## 15. “What happened?” and “Why?” are different epistemic levels

This distinction is mandatory.

### Level 0 — descriptive

Evidence from the observed run only.

Examples:

- loss decreased;
- Fisher-Rao path length increased sharply;
- CKA changed in layers 18–24;
- one update block became low-rank;
- behavior score `B_7` shifted.

This answers **what happened**.

### Level 1 — associational / attributional

Connects changes statistically or geometrically.

Examples:

- updates during interval `I` aligned strongly with Dataset slice `A`;
- functional divergence on probe family `Q_A` rose at the same change point;
- layer-22 representation drift correlated with behavioral shift `B_7`.

This suggests **what was associated with the change**.

It does not yet prove cause.

### Level 2 — counterfactual

Repeat or replay Training under a controlled intervention.

Examples:

- remove/reweight Dataset slice `A`;
- freeze candidate layers;
- replace one optimizer/schedule component while holding other inputs fixed;
- remove a candidate feature/adapter direction;
- replay the same interval from the same checkpoint with matched random seeds where feasible.

Compare resulting trajectories and behavioral outcomes.

This can support statements of the form:

> under intervention `do(A=0)`, the observed shift was substantially reduced.

### Level 3 — mechanistic causal evidence

Combine controlled interventions with internal localization.

Examples:

```text
Dataset slice A
    ↓
consistent gradient direction in layers 20–23
    ↓
representation/subspace change
    ↓
output-distribution change on probe family Q
    ↓
behavioral delta B
```

Only here should PTL use strong causal wording such as “this change was driven primarily by...”, and even then it should attach the intervention/evidence scope.

## 16. Influence and data attribution

For a Training sample/subset `z`, a first-order influence-style question is:

> how aligned was this sample's gradient with the parameter/function change we care about?

A scalable checkpointed proxy is gradient dot-product attribution, as used by TracIn-like methods:

```math
A(z, target)
\propto
\sum_{t\in C}
\eta_t
\nabla L(z;\theta_t)^\top
\nabla L(target;\theta_t).
```

Classical influence functions use Hessian-inverse structure such as

```math
-H^{-1}\nabla L(z).
```

They are mathematically elegant but rely on local assumptions that are difficult in large non-convex neural networks and are expensive at scale.

### PTL choice

Use gradient/checkpoint attribution as the practical first attribution layer. Reserve Hessian-inverse influence methods for targeted post-hoc analysis where assumptions and approximation quality can be audited.

Neither attribution method alone proves causality; controlled replays remain stronger evidence.

## 17. Causal interventions should be first-class research objects

For important “why” claims, PTL should support paired or multi-arm replay experiments.

Example:

```text
checkpoint C
   ├─ run A: original data
   ├─ run B: remove subset S
   ├─ run C: downweight subset S
   └─ run D: freeze candidate layers
```

Measure differences in the complete trajectory, not only final score.

For each intervention `I`, record

```math
\Delta_I(t)=z_t^{(I)}-z_t^{(control)}.
```

This lets the analytics layer answer both:

- whether an intervention changed the final outcome;
- when and through which internal measurements the trajectories diverged.

## 18. Mechanistic feature analysis is optional, not the foundation

Sparse autoencoders, dictionary learning, activation patching, causal tracing, or other feature-level methods can deepen an explanation after a region/layer/interval has been localized.

They should not be the first universal measurement layer because:

- feature dictionaries themselves have alignment/identity problems across checkpoints;
- decomposition quality depends on training choices;
- running them everywhere is expensive;
- a “feature” is not automatically a causal variable.

PTL should use them as targeted microscope tools after coarse geometry identifies where to look.

## 19. Optimal transport is a secondary alignment tool

When representations/features cannot be matched by index, entropic optimal transport / Sinkhorn matching can align sets of features or distributions across checkpoints.

This is especially useful when CKA says “the space changed” but we need a more explicit correspondence between two learned feature sets.

It is not the default metric because it requires choosing a ground cost, is more expensive, and can create an appearance of exact correspondence where the model has genuinely reorganized.

## 20. Topological data analysis is exploratory, not core

Persistent homology can characterize large-scale topology of activation clouds or trajectories.

It is interesting for detecting structural changes that covariance/subspace metrics miss, but should remain optional because:

- results depend strongly on sampling and metric choice;
- high-dimensional activation topology is expensive;
- causal interpretation is weak;
- simpler geometric/spectral methods are easier to validate and explain.

TDA is therefore a research microscope, not a release-critical primary observable.

## 21. Why not mutual information / “information bottleneck” as the primary theory

Naive mutual-information estimates in high-dimensional deterministic neural representations can be ill-posed, estimator-dependent, or dominated by noise/discretization assumptions.

PTL should use directly measurable quantities first:

- output entropy/divergence;
- representation Gram/covariance geometry;
- gradients/Jacobians;
- behavioral distributions.

Mutual-information analyses can be added only when the random variables, estimator, and interpretation are explicitly defined.

## 22. Why not PCA/t-SNE/UMAP as the explanation

### PCA

Useful for visualization and dominant linear variance directions, but alone it does not distinguish functional equivalence, causality, or Training force.

### t-SNE / UMAP

Useful exploratory visualizations, but their geometry depends on hyperparameters and projection choices. Distances in a 2-D embedding must not be promoted to primary quantitative evidence of neural-network change.

PTL may display these as views. It should not base “why” claims on them.

## 23. Why not loss alone

Two models can have nearly identical Training loss while differing strongly in:

- calibration;
- response distribution;
- robustness;
- internal representation;
- personality/evaluation behavior;
- interference with untouched tasks.

Conversely, a large internal reparameterization can leave behavior nearly unchanged.

Loss is a necessary optimization observable, not a complete state descriptor.

## 24. Why not Hessian sharpness alone

Sharpness is parameterization-sensitive and local. It can be useful for identifying curvature regimes but not as a universal scalar explanation of learning or generalization.

PTL should prefer directional/generalized curvature measurements and combine them with Fisher/function/behavior evidence.

## 25. Why not one giant learned embedding of “model state”

A learned meta-embedding could compress telemetry, but it would make the explanatory layer dependent on another opaque model.

The primary research record should remain decomposable into auditable quantities with known mathematical definitions.

A learned summarizer can sit on top of those measurements later; it must not replace them as source evidence.

## 26. Measurement cadence: not every quantity belongs at every step

A practical system should be multi-resolution.

### Tier A — cheap, frequent

Every step or short interval where available:

- loss;
- learning rate;
- gradient norm;
- update norm;
- gradient/update cosine;
- optimizer statistics;
- selected per-layer norms;
- memory/throughput/runtime telemetry.

### Tier B — medium cadence

Every `N` steps / validation interval:

- fixed-probe output divergence;
- entropy/calibration summaries;
- selected CKA layers;
- update singular-spectrum sketches;
- gradient interference on selected Dataset slices.

### Tier C — checkpoint cadence

At durable checkpoints:

- broad layerwise CKA/subspace analysis;
- Fisher-Rao displacement/path estimates;
- Jacobian/NTK sketches;
- Hessian leading-spectrum/trace estimates;
- complete behavioral battery;
- model-version comparison artifacts.

### Tier D — post-hoc targeted

Only after an interesting interval is detected:

- influence analysis;
- counterfactual replay;
- layer freezing/ablation;
- activation patching/causal tracing;
- feature dictionaries/SAEs;
- optimal-transport feature matching;
- topological analysis.

This keeps the default Training path observable without making instrumentation more expensive than Training itself.

## 27. Event segmentation

A mathematically meaningful Training event is an interval, not merely a log line.

Represent event candidate

```math
E_k=[t_a,t_b]
```

with:

```text
entry state
exit state
change-point evidence
parameter/information-geometric path
functional drift
representation drift by layer
optimizer/gradient regime
behavioral delta
associated Dataset slices
counterfactual evidence, if any
```

The analytics layer can then answer:

> “Between checkpoints C17 and C21, the run entered a new adaptation regime.”

rather than pretending one minibatch “caused personality”.

## 28. The analytics answer format

A strong PTL explanation should be layered.

### What changed?

Example structure:

```text
Functional change: high on probe family social-boundary-v3
Behavioral change: assertiveness +0.42 ± uncertainty
Representation change: concentrated in layers 19–24
Parameter update: 71% of update energy in first 8 singular directions
Fisher-Rao motion: 3.1× previous interval
```

### When?

```text
Primary change interval: steps 12,400–14,100
Detected from multivariate trajectory change point
```

### What was associated with it?

```text
Dataset slice boundary-dialogue had strongest gradient alignment
with the observed behavioral/output direction during the interval.
```

### Why do we believe it happened?

Weak form:

```text
Association only — no counterfactual run performed.
```

Strong form:

```text
Removing boundary-dialogue from a matched replay reduced the behavioral
shift by 68% and removed most of the layer-22 representation transition.
Freezing layers 21–23 reduced it by a further controlled amount.
Evidence level: counterfactual + localized intervention.
```

The system must never silently upgrade the first statement into the second.

## 29. Example of one complete explanatory chain

Suppose fine-tuning changes a measured conversational trait.

Observed facts:

```text
loss falls smoothly
raw parameter norm changes only modestly
Fisher-Rao step size spikes in interval I
JS divergence rises mostly on boundary-setting probes
CKA shows concentrated drift in late transformer blocks
Delta-W spectra in those blocks become strongly low-rank
Dataset slice S has persistent positive gradient alignment with the new behavior
```

At this point PTL can say:

> the behavioral transition coincided with a localized, information-geometrically large adaptation associated with Dataset slice S.

It **cannot yet** say S caused the transition.

Now replay from the same checkpoint with S removed while holding the protocol as fixed as practical.

If the transition largely disappears, then reweight S and/or freeze the localized blocks in additional arms.

If those interventions systematically control the effect, the final explanation gains causal support.

This is the intended difference between Analytics as visualization and Analytics as research inference.

## 30. Confidence/evidence taxonomy

Every generated explanation should carry an evidence class.

```text
DESCRIPTIVE
  observed trajectory only

ASSOCIATIONAL
  statistical/geometric attribution

COUNTERFACTUAL
  matched intervention/replay evidence

MECHANISTIC
  counterfactual evidence + localized internal intervention/path
```

Confidence within a class should reflect replication/uncertainty, but confidence must not substitute for evidence class.

A 99% confident correlation is still not a randomized intervention.

## 31. Reproducibility requirements

Every dynamics artifact must identify enough context to interpret it, including where applicable:

```text
Training run ID
checkpoint/model-version IDs
base-model reference + stronger external revision/hash when available
Profile fingerprint
Dataset fingerprint
optimizer/scheduler configuration
random seed/state scope when captured
probe battery version
behavioral battery/scoring version
layer/module naming map
precision/device/runtime configuration
analysis method + method version
sampling/approximation parameters
```

A metric without versioned probe/data/method identity is not stable research evidence.

## 32. Numerical computation strategy

The framework intentionally favors matrix-free estimators.

For large neural networks use:

- JVP/VJP rather than dense Jacobians;
- HVP rather than dense Hessians;
- Lanczos/power iteration for leading spectra;
- Hutchinson-style trace estimates;
- randomized SVD/sketching for update/activation spectra;
- probe subsets for Fisher/NTK estimates;
- streaming covariance/Gram accumulation.

This is why an unlimited mathematical abstraction level does not imply impossible runtime/storage requirements.

The formulas define what the quantity means; the implementation can estimate the required functional/quadratic/spectral observable without constructing the full tensor.

## 33. What PTL should not claim

Even with this framework PTL should not claim:

- that one metric uniquely identifies a mental/personality state;
- that parameter distance is semantic distance;
- that CKA identifies a specific causal feature;
- that low-rank updates imply one interpretable concept;
- that gradient attribution proves causality;
- that Hessian sharpness predicts generalization universally;
- that NTK remains fixed during practical fine-tuning;
- that a 2-D projection preserves high-dimensional geometry;
- that a counterfactual with uncontrolled changes isolates one cause;
- that one replay is universal proof across seeds/model families;
- that internal geometry is directly equivalent to a human psychological construct.

## 34. Why this combination of methods

The selected stack is deliberately redundant in the scientific sense: independent views must agree before PTL makes a strong interpretation.

| Question | Primary method | Why |
|---|---|---|
| How large was locally meaningful parameter motion? | Fisher-Rao quadratic/path measures | ties parameter update to output-distribution sensitivity |
| What output behavior changed? | fixed-probe JS/KL + behavioral batteries | measures the realized function rather than coordinates |
| Where did internal organization change? | CKA + subspace/spectral analysis | robust to many basis/permutation ambiguities |
| What force moved the model? | gradients + actual optimizer updates | observes the immediate Training dynamics |
| Were objectives/data slices helping or fighting? | gradient-alignment/interference matrix | local transfer/conflict measurement |
| Did local curvature/regime change? | HVP spectral/directional curvature | matrix-free local landscape information |
| Was Training approximately lazy or feature-learning? | Jacobian/NTK drift | explicitly tests local-linearization stability |
| When did a new regime begin? | multivariate change-point analysis | detects phases from coupled observables rather than loss alone |
| Which data were associated with the change? | checkpointed gradient attribution | scalable attribution before expensive intervention |
| Why should we believe a cause? | controlled replay/ablation/intervention | causality requires changing the candidate cause |

No row replaces the others. They answer different projections of the same trajectory.

## 35. Design principle for Persona Training Lab

The mathematical architecture should enforce one epistemic rule:

> **PTL may summarize a complex Training trajectory in ordinary language, but every sentence must be reducible to explicit mathematical observables and its evidence level.**

The target is not a decorative dashboard full of losses and PCA plots. The target is an instrument capable of saying:

```text
what changed,
where it changed,
when it changed,
how large the change was in several invariant/observable senses,
which optimization/data forces were aligned with it,
and what intervention evidence justifies saying why.
```

That is the minimum mathematical standard for turning Persona Training from “the weights moved and the tests changed” into an auditable study of neural-network development.
