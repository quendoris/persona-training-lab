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

The human participant is not treated as a message relay between a task and a
code generator. Architectural ownership requires understanding the system,
formulating invariants, challenging generated solutions, making product and
engineering judgments, and remaining able to explain why the resulting design
has its shape. AI assistance is useful precisely because it participates in
that engineering loop rather than replacing human understanding with opaque
routine generation.

## 5. Third-locale validation for localization

Russian and English are the active foundation locales while localization is
being completed. Spanish is reserved as an independent third-locale validator
for the completed architecture rather than as an excuse to add locale-specific
branches during migration.

A localization foundation is not considered complete merely because ru-RU and
en-US work. A complete es-ES catalog must later be installable and selectable
without Python changes, locale-specific UI code, duplicated layouts, special
state handling, or a restart-only escape hatch. Representative live UI must be
able to switch through ru-RU -> en-US -> es-ES -> ru-RU while preserving the
same domain state, drafts, selection, active operations and lineage state.

If adding Spanish requires a special-case code path, the localization
foundation is still incomplete.

## 6. External AI isolation

External AI systems are treated as untrusted execution and review contours,
regardless of vendor or reputation. This is a deliberately conservative threat
model, not an accusation about a particular provider.

Codex, Qwen Coder and other external agents receive dedicated branches and only
the repository scope, credentials and secrets required for their bounded task.
They do not share a writable integration branch with each other or with the
canonical working branch. Their results are reviewed and deliberately merged
by the original collaboration after comparison against the project's current
contracts and release gates.

Open-source publication does not remove the need for least-privilege access
during development: unpublished state, credentials, local files, unrelated
repositories and intermediate research may still be sensitive even when the
final source will eventually be public.

## 7. Licensing, provenance and release integrity are distinct concerns

File-level license and copyright notices are part of the final legal hardening
pass. Commentable project files should carry concise machine-readable license
metadata and provenance information, while canonical full license texts remain
in repository-level license files. Files that cannot safely carry comments may
use an adjacent or repository-level metadata mechanism.

The final release may additionally contain a generated provenance manifest with
a stable file identifier, path and cryptographic digest for every covered file.
That manifest is evidence for the exact composition and provenance of a release;
it is not the source of the software license and it is not an application
runtime trust root.

Provenance manifests, file identifiers and release checksums are introduced only
after the foundation, final audit and adversarial/stress-test repair cycle have
stabilized the file set. Creating them earlier would turn routine foundation
changes into meaningless integrity churn and encourage treating provisional
artifacts as canonical.

Release tooling and CI may verify license metadata and provenance manifests for
an official release. The application itself must not refuse to start, disable
features, or otherwise punish a user merely because files were modified, added,
reformatted or do not match the official release manifest. Local forks,
experiments, plugins and personal modifications are legitimate open-source use
cases. Integrity evidence exists to identify an official release and detect
unexpected drift, not to create removable DRM around a modifiable program.
