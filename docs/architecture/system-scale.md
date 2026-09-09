# System scale and measured codebase anatomy

Status: **current engineering scale record** with one frozen clean measurement baseline.

This document answers a narrow question: **how large is Persona Training Lab, what exactly is being counted, and what conclusions are and are not justified by those counts?**

It is not a productivity score and it is not a substitute for architecture, test quality, or release evidence.

## 1. Frozen clean measurement baseline

The current scale baseline was measured from a separate clean Git worktree at:

```text
branch source : origin/agent/history-keyguard-poller
commit        : 69ef4d28013d1ae666a73bcbe2470ae257bcf3ee
worktree mode : detached at the exact commit
working tree  : clean
Dirty         : no
```

The measurement command was:

```bash
python tools/codebase_stats.py --top 30
```

`tools/codebase_stats.py` enumerates tracked files with `git ls-files`; untracked files are therefore not included in the line statistics. The tool now reports repository root, branch/detached state, full commit SHA, upstream and dirty-state provenance before the measurements.

This section is intentionally a **frozen measurement of commit `69ef4d28...`**. Later documentation commits, including this document itself, naturally change the current repository size and do not retroactively change this recorded baseline.

## 2. Measured totals

At the baseline above:

| Category | Files | Physical lines | Nonblank lines | Python code lines |
|---|---:|---:|---:|---:|
| Production Python | 323 | 44,726 | 39,976 | 39,737 |
| Tests Python | 135 | 24,033 | 20,074 | 20,145 |
| Tools Python | 6 | 2,123 | 1,897 | 1,897 |
| Documentation | 60 | 25,681 | 17,196 | — |
| SVG assets | 13 | 41 | 41 | — |
| Configuration | 82 | 7,004 | 6,963 | — |
| Other text | 2 | 213 | 195 | — |
| **Tracked text total** | **621** | **103,821** | **86,342** | — |
| **All Python** | **464** | **70,882** | **61,947** | **61,779** |

The most useful compact scale statement for this baseline is therefore:

> **PTL contains about 104 thousand tracked physical text lines, including about 61.8 thousand measured Python code lines, of which about 39.7 thousand are production code and 20.1 thousand are tests.**

## 3. What `Python code lines` means

The `Python code` column is not equivalent to `wc -l`.

For Python files, `tools/codebase_stats.py` parses source structure and tokenizes the file. It excludes:

- blank lines;
- comments;
- module/class/function docstrings;
- indentation/dedentation tokens;
- newline-only structural tokens.

It counts physical source lines containing meaningful remaining Python tokens.

Therefore:

```text
Production Python physical lines : 44,726
Production Python code lines     : 39,737
```

means that the production layer contains roughly 39.7k lines with executable/declarative Python syntax under the tool's current definition, not merely 44.7k newline characters in `.py` files.

The metric is still a source-anatomy measurement, not a semantic complexity score.

## 4. Test-to-production ratio

Using the tool's Python-code measure:

\[
R_{test/prod}=\frac{20\,145}{39\,737}\approx0.507.
\]

So the clean baseline has approximately:

```text
0.51 test-code lines per production-code line
```

or, informally, about one measured test-code line for every two production-code lines.

This is a useful **scale and verification-investment** indicator. It does not prove 50.7% behavioral coverage, branch coverage, fault coverage, or architectural correctness.

A small number of high-value adversarial tests can prove more than a large number of shallow assertions; conversely, a large test corpus can still miss a cross-store or lifecycle invariant. PTL therefore treats this ratio as context, never as release proof.

## 5. Python composition

Measured Python code is distributed approximately as:

\[
\begin{aligned}
\text{production} &\approx 64.3\% \\
\text{tests} &\approx 32.6\% \\
\text{tools} &\approx 3.1\%
\end{aligned}
\]

of all measured Python code.

The project is therefore not a 61.8k-line application in the narrow sense. About one third of the Python implementation is verification code and another small dedicated layer is engineering tooling.

## 6. Documentation is a first-class subsystem

At the same baseline, tracked documentation contains:

```text
60 files
25,681 physical lines
17,196 nonblank lines
```

The physical documentation line count is approximately:

\[
\frac{25\,681}{44\,726}\approx0.574
\]

of the production Python physical line count.

That ratio should not be interpreted as “57.4% documented.” Markdown lines and Python lines do not represent equivalent units of knowledge.

The useful conclusion is narrower: **the documentation corpus is large enough to require its own architecture, coverage map, consistency rules, provenance and release checks.**

That is why `docs/DOCUMENTATION_MAP.md` is maintained separately from feature documentation.

## 7. Configuration is materially large

The clean baseline also contains:

```text
82 configuration files
7,004 physical lines
6,963 nonblank lines
```

This category includes machine-readable project/runtime/test/build/localization-related text recognized by the current counter.

A large configuration layer matters architecturally because behavior can move without changing Python LOC. Locale catalogs, manifests, build configuration, schema-like data and policy inputs can alter the effective system while the production-code count remains nearly unchanged.

Therefore PTL scale reviews must not collapse the repository to Python alone.

## 8. Why line count is not system complexity

A codebase of this size can still be architecturally simple or architecturally difficult.

PTL's engineering difficulty comes from the interaction of several state and trust domains, including:

```text
Qt desktop shell
  + navigation / docks / live localization / QSettings

application workflows
  + Training / evaluation / Automation / lineage

SQLite persistence
  + WAL / transactions / runtime leases / recovery

filesystem state
  + Agents atomic JSON / model artifacts / recipes / logs

external research inputs
  + Dataset bytes / base-model directories / executables

cross-store protocols
  + compensation / same-snapshot recovery / runtime safety links

verification and release evidence
  + pytest / static audits / i18n / visual audit / package checks

research methodology
  + evaluation protocol / proposed Training Dynamics evidence architecture
```

The important property is not merely that these layers exist, but that one user action can cross several of them.

For example, a protected Agents history transition can involve local JSON history, SQLite safety links, a runtime-operation lease and UI state. A raw LOC number cannot express that coupling.

## 9. Responsibility anatomy

A useful high-level decomposition is:

```text
Persona Training Lab
│
├── Product / presentation
│   ├── Qt shell and workspaces
│   ├── localization / RTL / themes / density
│   └── user interaction and evidence presentation
│
├── Application / domain behavior
│   ├── Profiles / Datasets / Training
│   ├── model versions / Agents lineage
│   ├── Tests / Analysis
│   └── Automation / projects / docs / telemetry
│
├── Persistence / runtime safety
│   ├── SQLite repositories and schema
│   ├── runtime operation/resource coordination
│   ├── atomic Agents local state
│   └── cross-store compensation and recovery
│
├── Verification / engineering
│   ├── tests
│   ├── release gate
│   ├── static/i18n/typing audits
│   ├── codebase statistics
│   └── visual/package evidence
│
└── Research methodology
    ├── personality/evaluation protocol
    ├── methodology limits
    └── proposed Training Dynamics mathematics/instrumentation
```

This is why PTL documentation is organized by reader intent rather than mirroring source directories mechanically.

## 10. Counts that are deliberately kept separate

The following values answer different questions and must not be merged into one “LOC” number:

### Physical lines

“How many newline-delimited source/document/config lines are present in tracked recognized text files?”

### Nonblank lines

“How many of those physical lines contain non-whitespace text?”

### Python code lines

“How many physical Python lines contain meaningful non-comment/non-docstring tokens under the current counter?”

### File count

“How many tracked recognized files contribute to the corresponding category?”

### Repository bytes / installed size / model artifacts

These are separate measurements. The codebase statistics tool intentionally does not pretend that source LOC describes model weights, runtime workspaces, generated Training artifacts, virtual environments or packaged installation size.

## 11. What the clean baseline does prove

The baseline proves that, for one exact clean tracked source tree at commit `69ef4d28...`:

- the reported files belonged to Git-tracked recognized text input;
- no working-tree/index/untracked dirtiness was reported by the measurement identity block;
- the production/test/tool/document/configuration counts above correspond to that exact source state;
- the test/production ratio above is reproducible from the recorded counts and tool definition.

It does **not** prove:

- that the commit passes the release gate;
- that every test is valuable;
- that every architectural path is covered;
- that documentation is correct merely because it is large;
- that runtime model/workspace data is included in source LOC;
- that future commits have the same counts.

Release readiness remains a separate evidence problem.

## 12. How to regenerate a trustworthy measurement

Prefer an exact clean checkout/worktree rather than a locally integrated tree:

```bash
git fetch --prune origin
git worktree add --detach /tmp/ptl-volume origin/agent/history-keyguard-poller
cd /tmp/ptl-volume
python tools/codebase_stats.py --top 30
```

Before using the result as evidence, verify the identity block says:

```text
Commit : <the intended full SHA>
Dirty  : no
```

For machine-readable evidence:

```bash
python tools/codebase_stats.py --json > codebase-stats.json
```

If the report says `Dirty: yes`, the numbers can still describe the current tracked working tree, but they must not be presented as a reproducible measurement of the printed commit.

## 13. Scale trends must compare like with like

Historical growth comparisons are only meaningful when both endpoints use compatible counting rules.

Do not compare:

- raw `wc -l` from one commit against token-aware Python code lines from another;
- a dirty integration checkout against a clean release candidate without labeling the distinction;
- source repository LOC against runtime workspace/model artifact size;
- old counter output against a newer counter whose category or code-line algorithm changed, unless the older commit is re-measured with the same tool version or the methodology difference is explicitly accounted for.

For longitudinal research, preserve both the measurement commit and the counter implementation commit/version.

## 14. Architectural consequence

PTL is now large enough that “read the code” is not an adequate maintenance strategy by itself.

The scale requires at least four synchronized maps:

```text
code architecture
persistence/runtime ownership
verification/release evidence
documentation coverage
```

The documentation effort is therefore not post-hoc prose. It is part of architecture reconstruction: when a behavior cannot be stated precisely, the implementation is re-audited; when the implementation violates the intended safety invariant, the code is fixed before the documentation proceeds.

## 15. Related documents

- [Documentation Coverage Map](../DOCUMENTATION_MAP.md)
- [Architecture Overview](overview.md)
- [Persistence architecture](persistence.md)
- [Workspace concurrency and ownership](workspace-concurrency.md)
- [UI shell architecture](ui-shell.md)
- [Runtime resource safety](runtime-resource-safety.md)
- [Testing and engineering audits](../development/testing.md)
- [Developer tooling](../development/tooling.md)
- [Release process](../development/release-process.md)
