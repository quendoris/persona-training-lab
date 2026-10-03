# Persona Training Lab — Git Workflow

## 1. Current model

Git is the provenance backbone for PTL engineering and release evidence.

Current working branch:

```text
agent/history-keyguard-poller
```

Release/audit claims must always name an exact commit. A successful gate on an older commit does not make a later documentation/code commit green.

## 2. Normal development

Before changing files:

```bash
git status --short
git rev-parse HEAD
git branch --show-current
```

Keep semantic changes small enough that their diff can be reviewed. Commit accepted fixes before asking for release evidence.

## 3. Clean local audit worktree

For local release-style runs, a detached worktree is preferred so an unrelated local branch/upstream state cannot contaminate the candidate:

```bash
git fetch origin
git worktree add --detach ../zero_2.11-run <expected-sha>
cd ../zero_2.11-run
git status --short
git rev-parse HEAD
```

To move that audit worktree to a newer committed candidate:

```bash
git fetch origin
git switch --detach <new-expected-sha>
```

Do not set an upstream merely to silence `git pull` in a detached release worktree.

## 4. Gates

Iteration evidence:

```bash
uv run --locked python tools/release_gate.py --quick --runs 3
```

Final automated evidence:

```bash
uv run --locked python tools/release_gate.py --runs 1
```

The release gate refuses dirty worktrees. Preserve the generated audit directory when the run is evidence for a candidate.

## 5. Change discipline

Good release work:

- derives a change from a concrete finding;
- keeps code/tests/docs synchronized;
- turns repaired failure modes into regression/audit coverage;
- records the exact candidate SHA;
- reruns evidence after candidate-changing commits.

Avoid:

- merging unrelated cleanup into a release-blocker fix;
- working from memory when the current branch is available;
- describing an old green run as proof for a newer commit;
- changing files during a release-gate run and treating its report as evidence for the modified tree;
- force-updating a branch over unknown concurrent work.
