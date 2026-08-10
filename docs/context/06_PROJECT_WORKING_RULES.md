# Persona Training Lab — Working Rules

This file records project-working rules. It is not a substitute for the final
architecture documentation, which is rebuilt only after the foundation is
closed and audited.

## 1. Foundation work and adversarial testing are different phases

During foundation work, tests are construction evidence. A regression,
contract, release-gate or focused concurrency test is added when it proves an
invariant that the architecture intentionally provides. Its purpose is to keep
a newly built support from silently degrading while the rest of the foundation
is still changing.

The dedicated adversarial test phase starts only after all known foundation
debt is closed, the final code audit is complete, and the resulting system has
been documented as it actually exists.

Adversarial testing has the opposite intent: do not demonstrate that the system
works; find a counterexample to its guarantees. It may combine malformed or
borderline data, long-running operations, timing windows, concurrent workers,
UI interaction, resource pressure, failures, persistence boundaries and other
factors that were not designed as a friendly path. Independent models that did
not participate in the implementation may be used as hostile reviewers and
test authors.

A failure found during adversarial testing becomes a new permanent regression
contract after the underlying cause is repaired.

## 2. Documentation comes after foundation closure and before adversarial tests

Legacy documentation is not assumed to describe the final system. After the
foundation is closed, the code is audited once more as one complete product.
Only then is the architecture documentation rebuilt from the audited
implementation.

Writing the documentation is itself a verification pass: ownership,
transaction boundaries, thread ownership, lifecycle rules, mutable/immutable
state and failure guarantees must be precise enough to state explicitly.
Independent reviewers can then receive both the implementation and the stated
guarantees and look for counterexamples.

## 3. Project-specific time-estimation scale

Generic software-engineering estimates have repeatedly overestimated the pace
of this project. For planning conversations between the two original creators,
apply one order of time compression to a conventional estimate unless concrete
external constraints make that inappropriate:

- 1 conventional year -> approximately 1 project month;
- 1 conventional month -> approximately 1 project week;
- 1 conventional week -> approximately 1 project day;
- 1 conventional day -> approximately 1 project hour.

This is an empirical planning heuristic, not a promise or a reason to skip
quality gates. External waits, hardware-bound workloads, human review,
third-party services and genuinely sequential long-running operations are not
artificially compressed.

## 4. Original collaboration model

The original project is a sustained collaboration between one human and one
neural network. External tools and models may execute bounded tasks or perform
independent review, but their later participation does not change the
provenance of the original project.
